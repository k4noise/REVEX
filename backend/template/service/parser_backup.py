from __future__ import annotations

import re
import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

from dedoc import DedocManager

from template.domain.template_element import DisplayMode, ElementType, GroupedProperties


@dataclass
class BaseElement:
    type: ElementType
    data: Optional[Union[str, Sequence["BaseElement"]]] = None
    display_mode: Optional[DisplayMode] = None
    element_id: uuid.UUID = field(default_factory=uuid.uuid4)
    properties: GroupedProperties = field(default_factory=GroupedProperties)

    def is_container(self) -> bool:
        return isinstance(self.data, Sequence) and not isinstance(self.data, (str, bytes))

    def children(self) -> Sequence["BaseElement"]:
        if self.is_container():
            return list(self.data)  # type: ignore[arg-type]
        return []

    def text_data(self) -> Optional[str]:
        if isinstance(self.data, str):
            return self.data
        return None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": str(self.element_id),
            "type": self.type.value,
        }

        if self.display_mode is not None:
            result["displayMode"] = self.display_mode.value

        grouped = self.properties.to_dict()
        if grouped:
            result["properties"] = grouped

        if self.is_container():
            result["data"] = [child.to_dict() for child in self.children()]
        else:
            result["data"] = self.text_data()

        return result


class DedocTemplateParser:
    PLACEHOLDER_RE = re.compile(r"_{3,}")

    def __init__(
            self,
            placeholder_char: str = "_",
            min_placeholder_repeat: int = 3,
            inline_split_maxlen: int = 400,
            table_block_maxlen: int = 300,
            with_attachments: bool = True,
    ):
        self.placeholder_char = placeholder_char
        self.min_placeholder_repeat = min_placeholder_repeat
        self.inline_split_maxlen = inline_split_maxlen
        self.table_block_maxlen = table_block_maxlen
        self.with_attachments = with_attachments

        escaped = re.escape(self.placeholder_char)
        self.placeholder_re = re.compile(rf"{escaped}{{{self.min_placeholder_repeat},}}")

    def parse(self, path: str) -> list[BaseElement]:
        manager = DedocManager()
        result = manager.parse(
            path,
            parameters={
                "document_type": "other",
                "structure_type": "tree",
                "with_attachments": "true" if self.with_attachments else "false"
            }
        )

        api_schema = result.to_api_schema().model_dump()

        tables = api_schema.get("content", {}).get("tables", [])
        tables_map = {t["metadata"]["uid"]: t for t in tables}

        attachments = api_schema.get("attachments", [])
        attachments_map = {a["metadata"]["uid"]: a for a in attachments}

        structure = api_schema["content"]["structure"]
        normalized_tree = self._process_tree_recursive(structure, tables_map, attachments_map)
        normalized_tree = self._apply_display_mode_root(normalized_tree)

        return self._build_elements_from_root(normalized_tree, attachments_map)

    def _has_placeholder(self, text: str) -> bool:
        return bool(self.placeholder_re.search(text or ""))

    def _first_placeholder_parts(self, text: str) -> Optional[tuple[str, str, str]]:
        if not text:
            return None
        m = self.placeholder_re.search(text)
        if not m:
            return None
        return text[:m.start()], text[m.start():m.end()], text[m.end():]

    def _split_prefix_hint(self, line: str) -> Optional[tuple[str, str]]:
        parts = self._first_placeholder_parts(line)
        if not parts:
            return None

        before, _, after = parts
        prefix = before.strip()

        if after and not after[0].isspace():
            hint = after.strip()
        else:
            hint = ""

        return prefix, hint

    def _is_only_placeholder(self, text: str) -> bool:
        t = (text or "").strip()
        if not t or not self._has_placeholder(t):
            return False

        lines = [line.strip() for line in t.splitlines() if line.strip()]
        if not lines:
            return False

        for line in lines:
            parts = self._first_placeholder_parts(line)
            if not parts:
                return False

            before, _, after = parts
            before = before.strip()

            if after.strip():
                return False

            if before and not re.fullmatch(r'[A-Za-zА-Яа-я0-9_\-()/\.:#\s]*:?', before):
                return False

        return True

    def _convert_table_to_text(self, table_data: dict) -> str:
        if not table_data or "cells" not in table_data:
            return ""

        lines = []

        for row in table_data["cells"]:
            row_text = []

            for cell in row:
                texts = [
                    line.get("text", "").replace("\n", " ").strip()
                    for line in cell.get("lines", [])
                    if line.get("text", "").strip()
                ]
                cell_text = texts[0] if texts else ""
                row_text.append(cell_text)

            lines.append(f"| {' | '.join(row_text)} |")

        return "\n".join(lines)

    def _build_answer_field_node(self, node_id: str, raw_text: str, annotations: List[dict]) -> dict:
        lines = [line.rstrip() for line in (raw_text or "").splitlines() if line.strip()]

        answer_lines = []
        hints = []

        for line in lines:
            parts = self._split_prefix_hint(line)
            if not parts:
                continue

            prefix, hint = parts
            answer_lines.append(prefix)
            if hint:
                hints.append(hint)

        answer_text = "\n".join(answer_lines).strip()
        hint_text = "\n".join(hints).strip()

        return {
            "node_id": node_id,
            "text": answer_text,
            "annotations": annotations,
            "metadata": {
                "paragraph_type": "answer_field",
                "hint": hint_text
            },
            "subparagraphs": []
        }

    @staticmethod
    def _get_table_uid(node: dict) -> Optional[str]:
        for ann in node.get("annotations", []):
            if ann.get("name") == "table":
                return ann.get("value")
        return None

    @staticmethod
    def _get_attachment_uid(node: dict) -> Optional[str]:
        for ann in node.get("annotations", []):
            if ann.get("name") == "attachment":
                return ann.get("value")
        return None

    @staticmethod
    def _is_image_attachment_uid(uid: Optional[str], attachments_map: Dict[str, dict]) -> bool:
        if not uid:
            return False
        att = attachments_map.get(uid)
        if not att:
            return False
        file_type = (att.get("metadata", {}) or {}).get("file_type", "")
        return file_type.startswith("image/")

    def _process_table_blocks(self, node: dict, tables_map: Dict[str, dict]) -> dict:
        table_uid = self._get_table_uid(node)
        if not table_uid:
            return node

        if node.get("metadata", {}).get("paragraph_type") != "header":
            if len(node.get("text", "") or "") > self.table_block_maxlen:
                return node

        table_data = tables_map.get(table_uid)
        table_text = self._convert_table_to_text(table_data)
        if not table_text:
            return node

        new_node = copy.deepcopy(node)
        meta = dict(new_node.get("metadata", {}))
        meta["table_uid"] = table_uid
        meta["contains_table"] = True
        new_node["metadata"] = meta

        current_text = new_node.get("text", "")
        new_node["text"] = f"{current_text}\n\n[TABLE_CONTENT]\n{table_text}\n[/TABLE_CONTENT]"
        return new_node

    def _process_image_attachments(self, node: dict, attachments_map: Dict[str, dict]) -> dict:
        attachment_uid = self._get_attachment_uid(node)
        if not self._is_image_attachment_uid(attachment_uid, attachments_map):
            return node

        new_node = copy.deepcopy(node)
        meta = dict(new_node.get("metadata", {}))
        meta["contains_image"] = True
        meta["attachment_uid"] = attachment_uid
        new_node["metadata"] = meta
        return new_node

    def _build_media_container_from_single_node(self, node: dict, attachments_map: Dict[str, dict]) -> dict:
        meta = node.get("metadata", {})
        contains_table = meta.get("contains_table", False)
        contains_image = meta.get("contains_image", False)

        if not contains_table and not contains_image:
            return node

        media_type = "table" if contains_table else "image"

        container = {
            "node_id": node["node_id"],
            "text": "",
            "annotations": [],
            "metadata": {
                "paragraph_type": "media_container",
                "media_type": media_type
            },
            "subparagraphs": []
        }

        title_text = node.get("text", "")
        if contains_table and "[TABLE_CONTENT]" in title_text:
            title_text = title_text.split("\n\n[TABLE_CONTENT]")[0].strip()

        title_annotations = [
            ann for ann in node.get("annotations", [])
            if ann.get("name") not in {"table", "attachment"}
        ]

        title_node = {
            "node_id": f"{node['node_id']}_title",
            "text": title_text,
            "annotations": title_annotations,
            "metadata": {"paragraph_type": "media_title"},
            "subparagraphs": []
        }

        if contains_table:
            media_text = node.get("text", "")
            if "[TABLE_CONTENT]" in media_text:
                media_text = media_text[media_text.find("[TABLE_CONTENT]"):].strip()

            media_node = {
                "node_id": f"{node['node_id']}_media",
                "text": media_text,
                "annotations": [],
                "metadata": {
                    "paragraph_type": "table_block",
                    "table_uid": meta.get("table_uid")
                },
                "subparagraphs": []
            }
        else:
            att_uid = meta.get("attachment_uid")
            att = attachments_map.get(att_uid, {})
            att_meta = att.get("metadata", {}) if att else {}

            media_node = {
                "node_id": f"{node['node_id']}_media",
                "text": "",
                "annotations": [],
                "metadata": {
                    "paragraph_type": "image_block",
                    "attachment_uid": att_uid,
                    "file_name": att_meta.get("file_name"),
                    "file_type": att_meta.get("file_type")
                },
                "subparagraphs": []
            }

        container["subparagraphs"] = [title_node, media_node]
        return container

    def _split_inline_question(self, node: dict) -> dict:
        text = node.get("text", "") or ""

        if not text or len(text) > self.inline_split_maxlen:
            return node

        if "\n" in text:
            return node

        if "[TABLE_CONTENT]" in text:
            return node

        if self._is_only_placeholder(text):
            return node

        parts = self._first_placeholder_parts(text)
        if not parts:
            return node

        before, _, after = parts
        before = before.rstrip()

        if not before.strip():
            return node

        hint = after.strip() if after and not after[:1].isspace() else ""

        new_node = copy.deepcopy(node)
        new_node["text"] = ""
        meta = dict(new_node.get("metadata", {}))
        meta["paragraph_type"] = "question"
        new_node["metadata"] = meta

        q_text_node = {
            "node_id": f"{node['node_id']}_q",
            "text": before,
            "annotations": node.get("annotations", []),
            "metadata": {"paragraph_type": "question_text"},
            "subparagraphs": []
        }

        ans_node = {
            "node_id": f"{node['node_id']}_a",
            "text": "",
            "annotations": [],
            "metadata": {
                "paragraph_type": "answer_field",
                "hint": hint
            },
            "subparagraphs": []
        }

        old_children = new_node.get("subparagraphs", [])
        new_node["subparagraphs"] = [q_text_node, ans_node] + old_children
        return new_node

    def _process_parent_child_question(self, node: dict) -> dict:
        children = node.get("subparagraphs", [])
        if not children:
            return node

        placeholder_idx = -1
        for i, child in enumerate(children):
            if self._is_only_placeholder(child.get("text", "")):
                placeholder_idx = i
                break

        if placeholder_idx == -1:
            return node

        placeholder_child = children[placeholder_idx]

        new_node = copy.deepcopy(node)
        new_node["text"] = ""
        meta = dict(new_node.get("metadata", {}))
        meta["paragraph_type"] = "question"
        new_node["metadata"] = meta

        q_text_node = {
            "node_id": f"{node['node_id']}_q",
            "text": node.get("text", ""),
            "annotations": node.get("annotations", []),
            "metadata": {"paragraph_type": "question_text"},
            "subparagraphs": []
        }

        ans_node = self._build_answer_field_node(
            node_id=placeholder_child["node_id"],
            raw_text=placeholder_child.get("text", ""),
            annotations=placeholder_child.get("annotations", [])
        )

        other_children = [c for i, c in enumerate(children) if i != placeholder_idx]
        new_node["subparagraphs"] = [q_text_node, ans_node] + other_children
        return new_node

    def _process_question_node(self, node: dict) -> dict:
        if node.get("metadata", {}).get("paragraph_type") in {"question", "question_text", "answer_field"}:
            return node

        node = self._process_parent_child_question(node)
        node = self._split_inline_question(node)
        return node

    @staticmethod
    def _is_media_node(node: dict) -> bool:
        ptype = node.get("metadata", {}).get("paragraph_type")
        return ptype in {"media_container", "table_block", "image_block"}

    def _merge_media_siblings(self, nodes: List[dict]) -> List[dict]:
        if not nodes:
            return []

        result = []
        i = 0

        while i < len(nodes):
            curr = nodes[i]

            if i + 1 < len(nodes):
                nxt = nodes[i + 1]
                curr_type = curr.get("metadata", {}).get("paragraph_type")

                if curr_type == "header" and self._is_media_node(nxt):
                    media_type = nxt.get("metadata", {}).get("media_type")
                    if not media_type:
                        p = nxt.get("metadata", {}).get("paragraph_type")
                        media_type = "table" if p == "table_block" else "image" if p == "image_block" else "media"

                    title_annotations = [
                        ann for ann in curr.get("annotations", [])
                        if ann.get("name") not in {"table", "attachment"}
                    ]

                    container = {
                        "node_id": f"{curr['node_id']}_media_container",
                        "text": "",
                        "annotations": [],
                        "metadata": {
                            "paragraph_type": "media_container",
                            "media_type": media_type
                        },
                        "subparagraphs": [
                            {
                                "node_id": f"{curr['node_id']}_title",
                                "text": curr.get("text", ""),
                                "annotations": title_annotations,
                                "metadata": {"paragraph_type": "media_title"},
                                "subparagraphs": []
                            },
                            copy.deepcopy(nxt)
                        ]
                    }

                    result.append(container)
                    i += 2
                    continue

            result.append(curr)
            i += 1

        return result

    def _merge_siblings(self, nodes: List[dict]) -> List[dict]:
        if not nodes:
            return []

        result = []
        i = 0

        while i < len(nodes):
            curr = nodes[i]

            if i + 1 < len(nodes):
                nxt = nodes[i + 1]

                curr_type = curr.get("metadata", {}).get("paragraph_type")
                nxt_type = nxt.get("metadata", {}).get("paragraph_type")

                if curr_type not in {"question", "question_text", "answer_field"} and nxt_type not in {"question", "question_text", "answer_field"}:
                    if not self._is_only_placeholder(curr.get("text", "")) and self._is_only_placeholder(nxt.get("text", "")):
                        q_container = copy.deepcopy(curr)
                        q_container["text"] = ""

                        meta = dict(q_container.get("metadata", {}))
                        meta["paragraph_type"] = "question"
                        q_container["metadata"] = meta

                        q_text = {
                            "node_id": f"{curr['node_id']}_q",
                            "text": curr.get("text", ""),
                            "annotations": curr.get("annotations", []),
                            "metadata": {"paragraph_type": "question_text"},
                            "subparagraphs": []
                        }

                        ans_field = self._build_answer_field_node(
                            node_id=nxt["node_id"],
                            raw_text=nxt.get("text", ""),
                            annotations=nxt.get("annotations", [])
                        )

                        old_children = q_container.get("subparagraphs", [])
                        q_container["subparagraphs"] = [q_text, ans_field] + old_children
                        result.append(q_container)
                        i += 2
                        continue

            result.append(curr)
            i += 1

        result = self._merge_media_siblings(result)
        return result

    def _process_tree_recursive(self, node: dict, tables_map: Dict[str, dict], attachments_map: Dict[str, dict]) -> dict:
        new_node = copy.deepcopy(node)

        children = new_node.get("subparagraphs", [])
        if children:
            children = [self._process_tree_recursive(child, tables_map, attachments_map) for child in children]
            children = self._merge_siblings(children)
            new_node["subparagraphs"] = children

        new_node = self._process_table_blocks(new_node, tables_map)
        new_node = self._process_image_attachments(new_node, attachments_map)
        new_node = self._process_question_node(new_node)

        if new_node.get("metadata", {}).get("paragraph_type") == "header":
            if new_node.get("metadata", {}).get("contains_table") or new_node.get("metadata", {}).get("contains_image"):
                new_node = self._build_media_container_from_single_node(new_node, attachments_map)

        return new_node

    @staticmethod
    def _get_annotation_values(node: dict, name: str) -> List[str]:
        return [ann.get("value", "") for ann in node.get("annotations", []) if ann.get("name") == name]

    @staticmethod
    def _get_first_float_annotation(node: dict, name: str) -> Optional[float]:
        for ann in node.get("annotations", []):
            if ann.get("name") == name:
                try:
                    return float(str(ann.get("value")).replace(",", "."))
                except Exception:
                    return None
        return None

    def _normalized_style_names(self, node: dict) -> List[str]:
        styles = self._get_annotation_values(node, "style")
        return [re.sub(r"\s+", "", s).lower() for s in styles if s]

    @staticmethod
    def _text_len(node: dict) -> int:
        return len((node.get("text") or "").strip())

    def _is_title_like_header(self, node: dict) -> bool:
        if node.get("metadata", {}).get("paragraph_type") != "header":
            return False

        styles = self._normalized_style_names(node)
        if "title" in styles:
            return True

        size = self._get_first_float_annotation(node, "size")
        if size is not None and size >= 15:
            return True

        return False

    def _is_prefer_list_item(self, node: dict) -> bool:
        if node.get("metadata", {}).get("paragraph_type") != "list_item":
            return False

        styles = self._normalized_style_names(node)
        txt_len = self._text_len(node)

        if "listparagraph" in styles:
            return False

        if txt_len == 0:
            return False

        if txt_len > 350:
            return False

        if styles:
            return True

        return False

    def _node_has_answer_table(self, node: dict) -> bool:
        meta = node.get("metadata", {})

        if meta.get("contains_table") and self._has_placeholder(node.get("text", "")):
            return True

        if meta.get("paragraph_type") == "media_container" and meta.get("media_type") == "table":
            for child in node.get("subparagraphs", []):
                child_meta = child.get("metadata", {})
                if child_meta.get("paragraph_type") == "table_block":
                    if self._has_placeholder(child.get("text", "")):
                        return True

        return False

    def _apply_display_mode(self, node: dict, is_root_child: bool = False) -> dict:
        new_node = copy.deepcopy(node)

        children = new_node.get("subparagraphs", [])
        if children:
            new_node["subparagraphs"] = [
                self._apply_display_mode(child, False) for child in children
            ]

        meta = dict(new_node.get("metadata", {}))
        ptype = meta.get("paragraph_type")

        if self._node_has_answer_table(new_node):
            meta["displayMode"] = "always"
        elif ptype in {"media_container", "question", "question_text", "answer_field"}:
            meta["displayMode"] = "always"
        elif ptype == "header" and is_root_child and self._is_title_like_header(new_node):
            meta["displayMode"] = "always"
        elif ptype == "header":
            meta["displayMode"] = "prefer"
        elif self._is_prefer_list_item(new_node):
            meta["displayMode"] = "prefer"

        new_node["metadata"] = meta
        return new_node

    def _apply_display_mode_root(self, root: dict) -> dict:
        new_root = copy.deepcopy(root)
        children = new_root.get("subparagraphs", [])
        new_root["subparagraphs"] = [self._apply_display_mode(child, True) for child in children]
        return new_root

    def _infer_header_level(self, node: dict) -> int:
        styles = self._normalized_style_names(node)

        if "title" in styles:
            return 1
        if "heading1" in styles:
            return 2
        if "heading2" in styles:
            return 3
        if "heading3" in styles:
            return 4

        return 2

    def _build_text_element(self, text: str, display_mode: Optional[str] = None) -> BaseElement:
        mode = DisplayMode(display_mode) if display_mode else None
        return BaseElement(
            type=ElementType.TEXT,
            data=text,
            display_mode=mode,
            properties=GroupedProperties()
        )

    def _build_header_element(self, text: str, header_level: int, display_mode: Optional[str] = None) -> BaseElement:
        mode = DisplayMode(display_mode) if display_mode else None
        return BaseElement(
            type=ElementType.HEADER,
            data=text,
            display_mode=mode,
            properties=GroupedProperties(render={"headerLevel": header_level})
        )

    def _build_answer_element(self, node: dict) -> BaseElement:
        meta = node.get("metadata", {})
        mode = DisplayMode(meta["displayMode"]) if meta.get("displayMode") else None

        domain = {}
        hint = meta.get("hint")
        if hint:
            domain["hint"] = hint

        return BaseElement(
            type=ElementType.ANSWER,
            data=node.get("text", ""),
            display_mode=mode,
            properties=GroupedProperties(domain=domain)
        )

    def _build_question_element(self, node: dict, attachments_map: Dict[str, dict]) -> BaseElement:
        meta = node.get("metadata", {})
        mode = DisplayMode(meta["displayMode"]) if meta.get("displayMode") else None
        children = [self._build_element(child, attachments_map) for child in node.get("subparagraphs", [])]
        children = [child for child in children if child is not None]

        return BaseElement(
            type=ElementType.QUESTION,
            data=children,
            display_mode=mode,
            properties=GroupedProperties()
        )

    def _build_image_element(self, node: dict) -> BaseElement:
        meta = node.get("metadata", {})
        file_name = meta.get("file_name") or ""
        return BaseElement(
            type=ElementType.IMAGE,
            data=file_name,
            properties=GroupedProperties(
                render={
                    "attachmentUid": meta.get("attachment_uid"),
                    "fileType": meta.get("file_type")
                }
            )
        )

    def _build_table_element(self, node: dict) -> BaseElement:
        meta = node.get("metadata", {})
        mode = DisplayMode(meta["displayMode"]) if meta.get("displayMode") else None
        return BaseElement(
            type=ElementType.TABLE,
            data=node.get("text", ""),
            display_mode=mode,
            properties=GroupedProperties(
                render={
                    "tableUid": meta.get("table_uid")
                }
            )
        )

    def _build_container_element(self, node: dict, attachments_map: Dict[str, dict]) -> BaseElement:
        meta = node.get("metadata", {})
        mode = DisplayMode(meta["displayMode"]) if meta.get("displayMode") else None
        children = [self._build_element(child, attachments_map) for child in node.get("subparagraphs", [])]
        children = [child for child in children if child is not None]

        return BaseElement(
            type=ElementType.CONTAINER,
            data=children,
            display_mode=mode,
            properties=GroupedProperties(
                render={
                    "mediaType": meta.get("media_type")
                } if meta.get("media_type") else {}
            )
        )

    def _build_element(self, node: dict, attachments_map: Dict[str, dict]) -> Optional[BaseElement]:
        meta = node.get("metadata", {})
        ptype = meta.get("paragraph_type")
        text = node.get("text", "") or ""
        display_mode = meta.get("displayMode")

        if ptype == "media_container":
            return self._build_container_element(node, attachments_map)

        if ptype == "media_title":
            return self._build_header_element(
                text=text,
                header_level=2,
                display_mode=None
            )

        if ptype == "image_block":
            return self._build_image_element(node)

        if ptype == "table_block":
            return self._build_table_element(node)

        if ptype == "question":
            return self._build_question_element(node, attachments_map)

        if ptype == "question_text":
            return self._build_text_element(text=text, display_mode=display_mode)

        if ptype == "answer_field":
            return self._build_answer_element(node)

        if ptype == "header":
            return self._build_header_element(
                text=text,
                header_level=self._infer_header_level(node),
                display_mode=display_mode
            )

        if ptype in {"raw_text", "list_item"}:
            return self._build_text_element(text=text, display_mode=display_mode)

        if ptype == "list":
            children = [self._build_element(child, attachments_map) for child in node.get("subparagraphs", [])]
            children = [child for child in children if child is not None]
            if not children:
                return None
            return BaseElement(
                type=ElementType.CONTAINER,
                data=children,
                properties=GroupedProperties()
            )

        if ptype == "root":
            children = [self._build_element(child, attachments_map) for child in node.get("subparagraphs", [])]
            children = [child for child in children if child is not None]
            return BaseElement(
                type=ElementType.CONTAINER,
                data=children,
                properties=GroupedProperties()
            )

        if text.strip():
            return self._build_text_element(text=text, display_mode=display_mode)

        children = [self._build_element(child, attachments_map) for child in node.get("subparagraphs", [])]
        children = [child for child in children if child is not None]
        if children:
            return BaseElement(
                type=ElementType.CONTAINER,
                data=children,
                properties=GroupedProperties()
            )

        return None

    def _build_elements_from_root(self, root: dict, attachments_map: Dict[str, dict]) -> list[BaseElement]:
        result = []
        for child in root.get("subparagraphs", []):
            built = self._build_element(child, attachments_map)
            if built is not None:
                result.append(built)
        return result
