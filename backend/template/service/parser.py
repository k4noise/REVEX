from __future__ import annotations

import base64
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from dedoc import DedocManager
from pydantic import BaseModel, Field

from files.services.hybrid_storage import HybridStorage
from template.schemas.template_element import (
    AnyElementPayload,
    AnyPatch,
    AnswerElementPayload,
    CellElementPayload,
    ContainerElementPayload,
    CreateElementPatch,
    DisplayMode,
    ElementType,
    HeaderElementPayload,
    ImageElementPayload,
    PatchAction,
    QuestionElementPayload,
    RowElementPayload,
    TableElementPayload,
    TextElementPayload,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParserConfig:
    IMAGE_EXTENSIONS: frozenset = frozenset(
        {"png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "tiff"}
    )
    PLACEHOLDER_RE: re.Pattern = re.compile(r"_{3,}")
    MULTI_SPACE_RE: re.Pattern = re.compile(r" {2,}")
    PAGE_NUMBER_RE: re.Pattern = re.compile(
        r"[Сс]траница\s+\d+\s+из\s+\d+|Page\s+\d+\s+of\s+\d+",
        re.I,
    )
    MARKER_RE: re.Pattern = re.compile(
        r"^((?:\d+(?:\.\d+)*)[\.\)]|[a-zA-Zа-яА-ЯёЁ][\.\)]|[•\-\*●])[\s\xA0]+"
    )
    ORPHAN_DOT_RE: re.Pattern = re.compile(r"^\.\s+")
    BULLET_NORMALIZE_RE: re.Pattern = re.compile(r"^[●·■]\s*")
    STYLE_TO_LEVEL: Dict[str, int] = field(
        default_factory=lambda: {
            "title": 1,
            "heading1": 1,
            "heading2": 2,
            "heading3": 3,
            "heading4": 4,
            "heading5": 5,
            "heading6": 6,
        }
    )
    MAX_TREE_DEPTH: int = 200
    SKIP_TYPES: frozenset = frozenset(
        {
            "question",
            "header",
            "table",
            "image",
            "answer_field",
            "row",
            "cell",
        }
    )
    MEDIA_TYPES: frozenset = frozenset({"table", "image"})


CONFIG = ParserConfig()


class NodeType(str, Enum):
    RAW_TEXT = "raw_text"
    HEADER = "header"
    QUESTION = "question"
    ANSWER_FIELD = "answer_field"
    TABLE = "table"
    ROW = "row"
    CELL = "cell"
    IMAGE = "image"
    CONTAINER = "container"


class InternalNode(BaseModel):
    node_id: str
    text: str = ""
    node_type: NodeType = NodeType.RAW_TEXT
    metadata: Dict[str, Any] = Field(default_factory=dict)
    annotations: List[dict] = Field(default_factory=list)
    children: List["InternalNode"] = Field(default_factory=list)

    def copy_with(
            self,
            text: Optional[str] = None,
            node_type: Optional[NodeType] = None,
            metadata: Optional[Dict[str, Any]] = None,
            children: Optional[List["InternalNode"]] = None,
    ) -> "InternalNode":
        return InternalNode(
            node_id=self.node_id,
            text=text if text is not None else self.text,
            node_type=node_type if node_type is not None else self.node_type,
            metadata=metadata if metadata is not None else self.metadata.copy(),
            annotations=self.annotations,
            children=children if children is not None else self.children.copy(),
        )

    def has_content(self) -> bool:
        if self.text.strip():
            return True
        if self.node_type in {
            NodeType.ANSWER_FIELD,
            NodeType.TABLE,
            NodeType.ROW,
            NodeType.CELL,
            NodeType.IMAGE,
        }:
            return True
        return any(child.has_content() for child in self.children)


def _is_image_type(file_type: str, file_name: str = "") -> bool:
    normalized_type = file_type.lower().lstrip(".")
    if normalized_type.startswith("image/"):
        return True
    if normalized_type in CONFIG.IMAGE_EXTENSIONS:
        return True
    extension = os.path.splitext(file_name)[-1].lstrip(".").lower()
    return extension in CONFIG.IMAGE_EXTENSIONS


def _clean_text(raw: str) -> Tuple[Optional[str], str]:
    if not raw:
        return None, ""

    text = raw.strip()
    text = CONFIG.PAGE_NUMBER_RE.sub("", text).strip()

    if not text:
        return None, ""

    text = CONFIG.BULLET_NORMALIZE_RE.sub("• ", text)
    text = text.replace("\t", " ")

    marker: Optional[str] = None
    match = CONFIG.MARKER_RE.match(text)

    if match:
        marker = match.group(1)
        text = text[match.end():].strip()
        if marker == ".":
            marker = "•"
    else:
        orphan = CONFIG.ORPHAN_DOT_RE.match(text)
        if orphan:
            text = text[orphan.end():].strip()

    text = CONFIG.MULTI_SPACE_RE.sub(" ", text)
    return marker, text


def _detect_heading_level_by_style(annotations: List[dict]) -> Optional[int]:
    for annotation in annotations:
        if annotation.get("name") != "style":
            continue
        style = annotation.get("value", "").replace(" ", "").lower()
        for key, level in CONFIG.STYLE_TO_LEVEL.items():
            if key in style:
                return level
    return None


def _annotation_value(annotations: List[dict], name: str) -> Optional[str]:
    for annotation in annotations:
        if annotation.get("name") == name:
            return annotation.get("value")
    return None


def _has_placeholder(text: str) -> bool:
    return bool(CONFIG.PLACEHOLDER_RE.search(text or ""))


def _is_placeholder_only(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    without_placeholder = CONFIG.PLACEHOLDER_RE.sub("", stripped).strip()
    if not without_placeholder:
        return True
    return bool(re.fullmatch(r"\(.*?\)", without_placeholder))


def _extract_hint(text: str) -> str:
    without_placeholder = CONFIG.PLACEHOLDER_RE.sub("", text).strip()
    match = re.match(r"^\((.*?)\)$", without_placeholder)
    return match.group(1).strip() if match else without_placeholder


def _preferred_display_mode() -> Optional[DisplayMode]:
    for mode in DisplayMode:
        signature = f"{mode.name} {getattr(mode, 'value', '')}".lower()
        if "prefer" in signature:
            return mode
    return None


def _build_table_node(table_data: dict) -> InternalNode:
    rows: List[InternalNode] = []

    for row in table_data.get("cells", []):
        cells: List[InternalNode] = []

        for cell in row:
            # Пропускаем ячейки, которые были поглощены при объединении (merge)
            # В противном случае HTML сетка таблицы на клиенте сломается
            if cell.get("invisible", False):
                continue

            lines = [
                line.get("text", "").strip()
                for line in cell.get("lines", [])
                if line.get("text", "").strip()
            ]
            content = InternalNode(
                node_id=str(uuid.uuid4()),
                node_type=NodeType.RAW_TEXT,
                text="\n".join(lines),
            )

            # Достаем rowspan/colspan из спарсенных dedoc данных
            cell_metadata = {}
            if cell.get("rowspan", 1) > 1:
                cell_metadata["rowspan"] = cell.get("rowspan")
            if cell.get("colspan", 1) > 1:
                cell_metadata["colspan"] = cell.get("colspan")
            cells.append(
                InternalNode(
                    node_id=str(uuid.uuid4()),
                    node_type=NodeType.CELL,
                    metadata=cell_metadata,
                    children=[content],
                )
            )

        # Добавляем строку только если в ней остались видимые ячейки
        if cells:
            rows.append(
                InternalNode(
                    node_id=str(uuid.uuid4()),
                    node_type=NodeType.ROW,
                    children=cells,
                )
            )

    return InternalNode(
        node_id=str(uuid.uuid4()),
        node_type=NodeType.TABLE,
        children=rows,
    )


def _build_image_node(att_uid: str, att: dict, text: str = "") -> InternalNode:
    metadata = att.get("metadata", {}) or {}
    return InternalNode(
        node_id=str(uuid.uuid4()),
        node_type=NodeType.IMAGE,
        text=text,
        metadata={
            "attachment_uid": att_uid,
            "file_name": metadata.get("file_name", ""),
            "media_key": metadata.get("storage_path", att_uid),
        },
    )


def _extract_inline_question(text: str) -> Tuple[str, str]:
    hint = ""
    parts: List[str] = []
    placeholder_seen = False

    for part in CONFIG.PLACEHOLDER_RE.split(text):
        content = CONFIG.MULTI_SPACE_RE.sub(" ", part).strip()
        if not content:
            placeholder_seen = True
            continue

        if placeholder_seen and not hint:
            match = re.match(r"^\((.*?)\)\s*(.*)$", content)
            if match:
                hint = match.group(1).strip()
                content = match.group(2).strip()

        if content:
            parts.append(content)

        placeholder_seen = True

    return " ".join(parts).strip(), hint


def _make_question(
        text: str,
        marker: Optional[str] = None,
        hint: str = "",
) -> InternalNode:
    metadata: Dict[str, Any] = {"max_score": 1.0}
    if marker:
        metadata["marker"] = marker

    return InternalNode(
        node_id=str(uuid.uuid4()),
        node_type=NodeType.QUESTION,
        text=text.strip(),
        metadata=metadata,
        children=[
            InternalNode(
                node_id=str(uuid.uuid4()),
                node_type=NodeType.ANSWER_FIELD,
                metadata={"hint": hint},
            )
        ],
    )


class TreeRefiner:
    def __init__(self) -> None:
        self.tables: Dict[str, dict] = {}
        self.attachments: Dict[str, dict] = {}

    def refine(self, root: InternalNode) -> InternalNode:
        refined_root = self._transform_node(root, depth=0)
        self._apply_header_metadata(refined_root)
        self._normalize_questions(refined_root)
        return self._filter_empty(refined_root)

    def _transform_node(self, node: InternalNode, depth: int) -> InternalNode:
        if depth > CONFIG.MAX_TREE_DEPTH:
            logger.warning("max nesting depth %d reached", CONFIG.MAX_TREE_DEPTH)
            return node

        node = self._inject_media(node)

        children = [
            self._transform_node(child, depth + 1)
            for child in node.children
        ]
        children = self._transform_children(children)
        children = self._group_header_media(children)
        children = [child for child in children if child.has_content()]

        return node.copy_with(children=children)

    def _inject_media(self, node: InternalNode) -> InternalNode:
        table_uid = _annotation_value(node.annotations, "table")
        attachment_uid = _annotation_value(node.annotations, "attachment")
        extra_children: List[InternalNode] = []

        if table_uid and table_uid in self.tables:
            extra_children.append(_build_table_node(self.tables[table_uid]))

        if attachment_uid and attachment_uid in self.attachments:
            attachment = self.attachments[attachment_uid]
            metadata = attachment.get("metadata", {}) or {}
            if _is_image_type(metadata.get("file_type", ""), metadata.get("file_name", "")):
                extra_children.append(_build_image_node(attachment_uid, attachment, node.text))

        if not extra_children:
            return node

        return node.copy_with(children=extra_children + node.children)

    def _transform_children(self, nodes: List[InternalNode]) -> List[InternalNode]:
        nodes = self._merge_text_with_next_placeholder(nodes)
        nodes = self._convert_inline_placeholders(nodes)
        nodes = self._convert_nodes_with_placeholder_descendants(nodes)
        return nodes

    def _merge_text_with_next_placeholder(self, nodes: List[InternalNode]) -> List[InternalNode]:
        if len(nodes) < 2:
            return nodes

        result: List[InternalNode] = []
        index = 0

        while index < len(nodes):
            current = nodes[index]

            if current.node_type.value in CONFIG.SKIP_TYPES:
                result.append(current)
                index += 1
                continue

            if (
                    current.text.strip()
                    and not _has_placeholder(current.text)
                    and index + 1 < len(nodes)
                    and _is_placeholder_only(nodes[index + 1].text)
            ):
                hint = _extract_hint(nodes[index + 1].text)
                result.append(
                    _make_question(
                        text=current.text,
                        marker=current.metadata.get("marker"),
                        hint=hint,
                    )
                )
                index += 2
                continue

            result.append(current)
            index += 1

        return result

    def _convert_inline_placeholders(self, nodes: List[InternalNode]) -> List[InternalNode]:
        result: List[InternalNode] = []

        for node in nodes:
            if node.node_type.value in CONFIG.SKIP_TYPES:
                result.append(node)
                continue

            if not node.text.strip():
                result.append(node)
                continue

            if not _has_placeholder(node.text):
                result.append(node)
                continue

            if _is_placeholder_only(node.text):
                result.append(node)
                continue

            question_text, hint = _extract_inline_question(node.text)
            result.append(
                _make_question(
                    text=question_text,
                    marker=node.metadata.get("marker"),
                    hint=hint,
                )
            )

        return result

    def _has_placeholder_descendant(self, node: InternalNode, max_depth: int = 5) -> bool:
        if max_depth <= 0:
            return False

        for child in node.children:
            if _is_placeholder_only(child.text):
                return True
            if self._has_placeholder_descendant(child, max_depth - 1):
                return True

        return False

    def _find_first_placeholder_hint(self, node: InternalNode, max_depth: int = 5) -> str:
        if max_depth <= 0:
            return ""

        for child in node.children:
            if _is_placeholder_only(child.text):
                return _extract_hint(child.text)
            hint = self._find_first_placeholder_hint(child, max_depth - 1)
            if hint:
                return hint

        return ""

    def _collect_non_placeholder_descendants(self, node: InternalNode) -> List[InternalNode]:
        collected: List[InternalNode] = []

        for child in node.children:
            if _is_placeholder_only(child.text):
                continue

            remaining_children = self._collect_non_placeholder_descendants(child)
            child_copy = child.copy_with(children=remaining_children)

            if child_copy.has_content():
                collected.append(child_copy)

        return collected

    def _convert_nodes_with_placeholder_descendants(self, nodes: List[InternalNode]) -> List[InternalNode]:
        result: List[InternalNode] = []

        for node in nodes:
            if node.node_type.value in CONFIG.SKIP_TYPES:
                if node.has_content():
                    result.append(node)
                continue

            if not node.text.strip():
                if node.has_content():
                    result.append(node)
                continue

            if not self._has_placeholder_descendant(node):
                if node.has_content():
                    result.append(node)
                continue

            hint = self._find_first_placeholder_hint(node)
            result.append(
                _make_question(
                    text=node.text,
                    marker=node.metadata.get("marker"),
                    hint=hint,
                )
            )

            remaining = self._collect_non_placeholder_descendants(node)
            result.extend(remaining)

        return result

    def _group_header_media(self, nodes: List[InternalNode]) -> List[InternalNode]:
        if len(nodes) < 2:
            return [node for node in nodes if node.has_content()]

        result: List[InternalNode] = []
        index = 0

        while index < len(nodes):
            current = nodes[index]

            if current.node_type == NodeType.HEADER:
                if index + 1 < len(nodes) and nodes[index + 1].node_type.value in CONFIG.MEDIA_TYPES:
                    next_node = nodes[index + 1]
                    container = InternalNode(
                        node_id=str(uuid.uuid4()),
                        node_type=NodeType.CONTAINER,
                        metadata={"display_mode": DisplayMode.ALWAYS},
                        children=[current, next_node],
                    )
                    if container.has_content():
                        result.append(container)
                    index += 2
                    continue

                wrapped = self._wrap_header_with_media_child(current)
                if wrapped.has_content():
                    result.append(wrapped)
                index += 1
                continue

            if current.has_content():
                result.append(current)
            index += 1

        return result

    def _wrap_header_with_media_child(self, node: InternalNode) -> InternalNode:
        if node.node_type != NodeType.HEADER or not node.children:
            return node

        first_child = node.children[0]
        if first_child.node_type.value not in CONFIG.MEDIA_TYPES:
            return node

        container_children = [node.copy_with(children=[]), first_child]
        container_children.extend(node.children[1:])

        return InternalNode(
            node_id=str(uuid.uuid4()),
            node_type=NodeType.CONTAINER,
            metadata={"display_mode": DisplayMode.ALWAYS},
            children=container_children,
        )

    def _apply_header_metadata(self, root: InternalNode) -> None:
        preferred_mode = _preferred_display_mode()
        self._apply_header_metadata_recursive(
            nodes=root.children,
            parent_level=0,
            preferred_mode=preferred_mode,
        )

    def _apply_header_metadata_recursive(
            self,
            nodes: List[InternalNode],
            parent_level: int,
            preferred_mode: Optional[DisplayMode],
    ) -> None:
        top_level_headers_seen = 0

        for node in nodes:
            if node.node_type == NodeType.HEADER:
                top_level_headers_seen += 1

                existing_level = node.metadata.get("level")
                if isinstance(existing_level, int) and 1 <= existing_level <= 6:
                    level = existing_level
                elif parent_level == 0 and top_level_headers_seen == 1:
                    level = 1
                elif parent_level == 0:
                    level = 2
                else:
                    level = min(parent_level + 1, 6)

                node.metadata["level"] = level

                if level >= 2 and preferred_mode is not None:
                    node.metadata["display_mode"] = preferred_mode
                else:
                    node.metadata.pop("display_mode", None)

                self._apply_header_metadata_recursive(
                    nodes=node.children,
                    parent_level=level,
                    preferred_mode=preferred_mode,
                )
                continue

            self._apply_header_metadata_recursive(
                nodes=node.children,
                parent_level=parent_level,
                preferred_mode=preferred_mode,
            )

    def _normalize_questions(self, node: InternalNode) -> None:
        for child in node.children:
            self._normalize_questions(child)

        if node.node_type != NodeType.QUESTION:
            return

        hints = [
            child.metadata.get("hint", "")
            for child in node.children
            if child.node_type == NodeType.ANSWER_FIELD and child.metadata.get("hint", "")
        ]
        hint = hints[0] if hints else ""

        node.children = [
            InternalNode(
                node_id=str(uuid.uuid4()),
                node_type=NodeType.ANSWER_FIELD,
                metadata={"hint": hint},
            )
        ]

    def _filter_empty(self, node: InternalNode) -> InternalNode:
        children = [self._filter_empty(child) for child in node.children]
        children = [child for child in children if child.has_content()]
        return node.copy_with(children=children)


class PatchFactory:
    def __init__(self) -> None:
        self._order = 0

    def create_patches(
            self,
            nodes: List[InternalNode],
            parent_id: Optional[str] = None,
    ) -> List[AnyPatch]:
        patches: List[AnyPatch] = []

        for node in nodes:
            if not node.has_content():
                continue

            if _is_placeholder_only(node.text) and node.node_type not in {
                NodeType.ANSWER_FIELD,
                NodeType.QUESTION,
            }:
                continue

            payload = self._to_payload(node, parent_id, self._order)

            if payload is None:
                if node.children:
                    patches.extend(self.create_patches(node.children, parent_id=parent_id))
                continue

            patches.append(
                CreateElementPatch(
                    action=PatchAction.CREATE,
                    payload=payload,
                )
            )
            self._order += 1

            if node.node_type == NodeType.QUESTION:
                answer_children = [
                    child
                    for child in node.children
                    if child.node_type == NodeType.ANSWER_FIELD
                ]
                patches.extend(self.create_patches(answer_children, parent_id=node.node_id))
                continue

            if node.children:
                patches.extend(self.create_patches(node.children, parent_id=node.node_id))

        return patches

    def _to_payload(
            self,
            node: InternalNode,
            parent_id: Optional[str],
            order: int,
    ) -> Optional[AnyElementPayload]:
        try:
            node_uuid = uuid.UUID(node.node_id)
        except ValueError:
            node_uuid = uuid.uuid4()

        parent_uuid = None
        if parent_id:
            try:
                parent_uuid = uuid.UUID(parent_id)
            except ValueError:
                parent_uuid = None

        common: Dict[str, Any] = {
            "id": node_uuid,
            "parent_element_id": parent_uuid,
            "order": order,
            "display_mode": node.metadata.get("display_mode"),
            "marker": node.metadata.get("marker"),
        }

        match node.node_type:
            case NodeType.HEADER:
                return HeaderElementPayload(
                    type=ElementType.HEADER,
                    data=node.text,
                    level=node.metadata.get("level", 2),
                    **common,
                )
            case NodeType.QUESTION:
                return QuestionElementPayload(
                    type=ElementType.QUESTION,
                    data=node.text,
                    max_score=node.metadata.get("max_score", 1.0),
                    **common,
                )
            case NodeType.ANSWER_FIELD:
                return AnswerElementPayload(
                    type=ElementType.ANSWER,
                    data=node.metadata.get("hint", ""),
                    **common,
                )
            case NodeType.TABLE:
                return TableElementPayload(type=ElementType.TABLE, **common)
            case NodeType.ROW:
                return RowElementPayload(type=ElementType.ROW, **common)
            case NodeType.CELL:
                # Передаем rowspan и colspan в Payload ячейки
                cell_kwargs = {"type": ElementType.CELL, **common}
                if "rowspan" in node.metadata:
                    cell_kwargs["rowspan"] = node.metadata["rowspan"]
                if "colspan" in node.metadata:
                    cell_kwargs["colspan"] = node.metadata["colspan"]

                return CellElementPayload(**cell_kwargs)
            case NodeType.IMAGE:
                return ImageElementPayload(
                    type=ElementType.IMAGE,
                    media_key=node.metadata.get("media_key", ""),
                    alt_text=node.text,
                    **common,
                )
            case NodeType.CONTAINER:
                if node.children:
                    return ContainerElementPayload(
                        type=ElementType.CONTAINER,
                        **common,
                    )
                return None
            case _:
                if node.text.strip():
                    return TextElementPayload(
                        type=ElementType.TEXT,
                        data=node.text,
                        **common,
                    )
                return None


class DedocTemplateParser:
    def __init__(
            self,
            storage: Optional[HybridStorage] = None,
            manager: Optional[DedocManager] = None,
            attachments_dir: str = "media",
    ):
        self.manager = manager or DedocManager()
        self.storage = storage
        self.attachments_dir = attachments_dir

    def parse(self, file_path: str) -> List[AnyPatch]:
        document_uuid = str(uuid.uuid4())
        api_data = self._extract(file_path)

        attachments_map = self._process_attachments(
            api_data.get("attachments", []) or [],
            document_uuid,
            )
        tables_map = self._build_tables_map(api_data)

        refiner = TreeRefiner()
        refiner.tables = tables_map
        refiner.attachments = attachments_map

        root_data = api_data.get("content", {}).get("structure") or {
            "text": "",
            "subparagraphs": [],
        }

        tree = self._build_tree(root_data)
        refined_tree = refiner.refine(tree)

        factory = PatchFactory()
        return factory.create_patches(
            [node for node in refined_tree.children if node.has_content()]
        )

    def _build_tree(
            self,
            data: dict,
            depth: int = 0,
            parent_heading_level: int = 0,
    ) -> InternalNode:
        if depth > CONFIG.MAX_TREE_DEPTH:
            logger.warning("max nesting depth %d reached", CONFIG.MAX_TREE_DEPTH)
            return InternalNode(node_id=str(uuid.uuid4()))

        metadata = data.get("metadata", {}) or {}
        annotations = data.get("annotations", []) or []
        paragraph_type = metadata.get("paragraph_type", "raw_text")

        marker, cleaned_text = _clean_text(data.get("text", ""))

        node_metadata: Dict[str, Any] = {}
        if marker:
            node_metadata["marker"] = marker

        node_type = NodeType.RAW_TEXT

        if paragraph_type == "header":
            node_type = NodeType.HEADER
            style_level = _detect_heading_level_by_style(annotations)
            if style_level is not None:
                node_metadata["level"] = style_level
            else:
                node_metadata["level"] = max(parent_heading_level + 1, 2)

        child_heading_level = node_metadata.get("level", parent_heading_level)

        return InternalNode(
            node_id=data.get("node_id", str(uuid.uuid4())),
            text=cleaned_text,
            node_type=node_type,
            metadata=node_metadata,
            annotations=annotations,
            children=[
                self._build_tree(
                    child,
                    depth=depth + 1,
                    parent_heading_level=child_heading_level,
                )
                for child in data.get("subparagraphs", []) or []
            ],
        )

    def _extract(self, file_path: str) -> dict:
        result = self.manager.parse(
            file_path=file_path,
            parameters={
                "document_type": "other",
                "structure_type": "tree",
                "with_attachments": "true",
                "return_base64": "true",
            },
        )
        schema = result.to_api_schema()
        return schema.model_dump() if hasattr(schema, "model_dump") else schema.dict()

    def _process_attachments(
            self,
            attachments: List[dict],
            document_uuid: str,
    ) -> Dict[str, dict]:
        result: Dict[str, dict] = {}

        for attachment in attachments:
            metadata = attachment.get("metadata") or {}
            uid = metadata.get("uid")
            if not uid:
                continue
            self._try_save_image(attachment, document_uuid)
            result[uid] = attachment

        return result

    def _try_save_image(self, attachment: dict, document_uuid: str) -> None:
        metadata = attachment.get("metadata") or {}
        file_type = metadata.get("file_type", "")
        file_name = metadata.get("file_name", "")

        if not _is_image_type(file_type, file_name):
            return

        if not self.storage:
            return

        content_b64 = metadata.get("base64_encode")
        if not content_b64:
            return

        try:
            data = base64.b64decode(content_b64)
            extension = (
                    os.path.splitext(file_name)[-1].lstrip(".")
                    or file_type.split("/")[-1]
                    or "png"
            )
            path = f"{self.attachments_dir}/{document_uuid}/{file_name}"
            saved_path = self.storage.save(path, data, extension)
            if saved_path:
                metadata["storage_path"] = saved_path
        except Exception:
            logger.exception("Failed to save attachment %s", metadata.get("uid", "?"))

    @staticmethod
    def _build_tables_map(api_data: dict) -> Dict[str, dict]:
        tables = api_data.get("content", {}).get("tables", []) or []
        return {
            table["metadata"]["uid"]: table
            for table in tables
            if table.get("metadata", {}).get("uid")
        }