from __future__ import annotations

import re
import uuid
from typing import List, Optional, Dict, Any

from dedoc import DedocManager
from pydantic import BaseModel, Field

# Импортируем ваши схемы
from template.schemas.template_element import (
    DisplayMode,
    CreateElementPatch,
    PatchAction,
    AnyElementPayload,
    AnyPatch,
    HeaderElementPayload,
    ElementType,
    QuestionElementPayload,
    TextElementPayload,
    AnswerElementPayload,
    ImageElementPayload,
    ContainerElementPayload,
    TableElementPayload,
    RowElementPayload,
    CellElementPayload
)


class TextCleaner:
    # Словарь "лечения" поломанных PDF шрифтов
    PDF_ENCODING_FIXES = {
        '\u0016': 'и',
        '\u0012': 'H',
        '\u0002': 'C',
        '\u0005': 'p',
        '\u0007': 'a',
        '\u000e': 'e',
        '\u0019': 'u'
    }

    @classmethod
    def fix_pdf_encoding(cls, text: str) -> str:
        for bad_char, good_char in cls.PDF_ENCODING_FIXES.items():
            text = text.replace(bad_char, good_char)
        return text

    @classmethod
    def extract_marker_and_clean(cls, raw_text: str) -> tuple[Optional[str], str]:
        """Извлекает маркер списка и возвращает кортеж: (маркер, чистый_текст)"""
        if not raw_text:
            return None, ""

        # 1. Лечим кодировку PDF
        text = cls.fix_pdf_encoding(raw_text.strip())

        # 2. Убиваем колонтитулы PDF (например "Страница 5 из 7")
        text = re.sub(r'Страница \d+ из \d+', '', text).strip()
        if not text:
            return None, ""

        text = re.sub(r'^[●·■]\s*', '• ', text)
        text = re.sub(r'\t', ' ', text)

        marker = None

        match = re.match(r'^((?:\d+(?:\.\d+)*)[\.\)]|[a-zA-Zа-яА-Я][\.\)]|[•\-\*●])(?:[\s\xA0]+|$)', text)

        if match:
            marker = match.group(1)
            text = text[match.end():].strip()
            if marker == '.':
                marker = '•'
        elif text.startswith(". "):
            marker = '•'
            text = text[2:].strip()

        text = re.sub(r' {2,}', ' ', text)
        return marker, text


class MediaProcessor:
    """Обработчик медиа-контента (таблицы, изображения)"""

    @staticmethod
    def extract_table_nodes(table_data: dict) -> List[InternalNode]:
        """Превращает таблицу в иерархию узлов: Строки (row) -> Ячейки (cell) -> Текст"""
        if not table_data or "cells" not in table_data:
            return []

        row_nodes = []
        for row in table_data["cells"]:
            cell_nodes = []
            for cell in row:
                texts = [
                    # Лечим PDF кодировку даже внутри таблиц
                    TextCleaner.fix_pdf_encoding(line.get("text", "").strip())
                    for line in cell.get("lines", [])
                    if line.get("text", "").strip()
                ]
                cell_text = "\n".join(texts).strip()

                content_node = InternalNode(paragraph_type="raw_text", text=cell_text)
                cell_nodes.append(InternalNode(paragraph_type="cell", subparagraphs=[content_node]))

            row_nodes.append(InternalNode(paragraph_type="row", subparagraphs=cell_nodes))

        return row_nodes

    @staticmethod
    def get_table_uid(annotations: List[dict]) -> Optional[str]:
        for ann in annotations:
            if ann.get("name") == "table":
                return ann.get("value")
        return None

    @staticmethod
    def get_attachment_uid(annotations: List[dict]) -> Optional[str]:
        for ann in annotations:
            if ann.get("name") == "attachment":
                return ann.get("value")
        return None

    @staticmethod
    def is_image_attachment(uid: str, attachments_map: Dict[str, dict]) -> bool:
        if not uid or uid not in attachments_map:
            return False
        att = attachments_map.get(uid)
        file_type = att.get("metadata", {}).get("file_type", "")
        return file_type.startswith("image/")


class PlaceholderLogic:
    def __init__(self):
        self.pattern = re.compile(r'_{3,}')
        self.question_indicators = re.compile(
            r'(\?$|\?["\s]|Успешно ли|Все ли|Какой|Какие|Поясните|В чем|'
            r'Используя.*скопируйте|результат выполнения|Отправьте.*эхо)',
            re.I
        )
        self.instruction_pattern = re.compile(
            r'^[\.\-\•]\s*(Переведите|Имитируйте|Контролируйте|Включите|Выключите)',
            re.I
        )

    def is_placeholder_only(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        without = self.pattern.sub('', t).strip()
        if len(without) == 0:
            return True
        if re.fullmatch(r'\(.*?\)', without):
            return True
        return len(without) <= 5 and not self.question_indicators.search(without)

    def extract_hint(self, text: str) -> str:
        without = self.pattern.sub('', text).strip()
        match = re.match(r'^\((.*?)\)$', without)
        if match:
            return match.group(1).strip()
        return without

    def contains_placeholder(self, text: str) -> bool:
        return bool(self.pattern.search(text or ""))

    def is_question_text(self, text: str) -> bool:
        if not text:
            return False
        text = text.strip()
        if self.instruction_pattern.match(text) and not self.contains_placeholder(text):
            return False
        return bool(self.question_indicators.search(text))

    def split_by_placeholder(self, text: str) -> List[Dict[str, str]]:
        if not text or not self.contains_placeholder(text):
            return [{'type': 'text', 'content': text}] if text else []

        result = []
        last_end = 0
        for match in self.pattern.finditer(text):
            if match.start() > last_end:
                before = text[last_end:match.start()].strip()
                if before:
                    result.append({'type': 'text', 'content': before})
            result.append({'type': 'placeholder', 'content': ''})
            last_end = match.end()

        if last_end < len(text):
            after = text[last_end:].strip()
            if after:
                result.append({'type': 'text', 'content': after})

        return result


class InternalNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    paragraph_type: str = "raw_text"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    annotations: List[dict] = Field(default_factory=list)
    subparagraphs: List[InternalNode] = Field(default_factory=list)

    _processed: bool = False

    @classmethod
    def from_dedoc(cls, data: dict) -> InternalNode:
        metadata = data.get("metadata", {}) or {}
        annotations = data.get("annotations", []) or []
        paragraph_type = metadata.get("paragraph_type", "raw_text")
        raw_text = data.get("text", "")

        marker, clean_text = TextCleaner.extract_marker_and_clean(raw_text)
        if not marker and "list_item" in metadata and isinstance(metadata["list_item"], str):
            marker = metadata["list_item"]

        if marker:
            metadata["marker"] = str(marker).strip()

        if paragraph_type == "header":
            styles = [
                ann.get("value", "").replace(" ", "").lower()
                for ann in annotations if ann.get("name") == "style"
            ]
            level = 2
            if "title" in styles or "heading1" in styles:
                level = 1
            elif "heading2" in styles:
                level = 2
            elif "heading3" in styles:
                level = 3
            elif "heading4" in styles:
                level = 4
            metadata["level"] = level

        return cls(
            node_id=data.get("node_id", str(uuid.uuid4())),
            text=clean_text,
            paragraph_type=paragraph_type,
            metadata=metadata,
            annotations=annotations,
            subparagraphs=[cls.from_dedoc(c) for c in data.get("subparagraphs", []) or []],
        )

    def has_content(self) -> bool:
        if self.text.strip():
            return True
        if self.paragraph_type in ("answer_field", "table", "row", "cell", "image_block"):
            return True
        return any(c.has_content() for c in self.subparagraphs)


class TreeRefiner:
    def __init__(self, logic: PlaceholderLogic, media_processor: MediaProcessor):
        self.logic = logic
        self.media = media_processor
        self.tables_map: Dict[str, dict] = {}
        self.attachments_map: Dict[str, dict] = {}

    def set_media_maps(self, tables: Dict[str, dict], attachments: Dict[str, dict]):
        self.tables_map = tables
        self.attachments_map = attachments

    def _restore_headers(self, nodes: List[InternalNode]) -> List[InternalNode]:
        """Эвристическое восстановление заголовков для плоских PDF"""
        header_keywords = (
            "шаг", "часть", "задачи", "топология", "таблица адресации",
            "исходные данные", "необходимые ресурсы", "вопросы на закрепление", "лабораторная работа"
        )

        for node in nodes:
            # Превращаем текст в заголовок, если он короткий и похож на него
            if node.paragraph_type in ("raw_text", "text", "list_item"):
                text_lower = node.text.lower()
                if len(node.text) < 150 and any(text_lower.startswith(kw) for kw in header_keywords):
                    node.paragraph_type = "header"
                    if text_lower.startswith("шаг"):
                        node.metadata["level"] = 3
                    elif text_lower.startswith("часть"):
                        node.metadata["level"] = 2
                    elif text_lower.startswith("лабораторная работа"):
                        node.metadata["level"] = 1
                    else:
                        node.metadata["level"] = 1

                    node.metadata["displayMode"] = DisplayMode.ALWAYS

        return nodes

    def refine(self, node: InternalNode, depth: int = 0) -> InternalNode:
        if depth > 50 or node._processed:
            return node

        node = self._check_for_media_content(node)

        processed_children = []
        for child in node.subparagraphs:
            if not child._processed:
                processed_children.append(self.refine(child, depth + 1))
            else:
                processed_children.append(child)
        node.subparagraphs = processed_children

        node.subparagraphs = self._convert_nested_labels_to_questions(node.subparagraphs)
        node.subparagraphs = self._split_inline_placeholders(node.subparagraphs)
        node.subparagraphs = self._merge_text_with_placeholder(node.subparagraphs)
        node.subparagraphs = self._detect_questions_by_text(node.subparagraphs)
        node.subparagraphs = self._ensure_answers(node.subparagraphs)
        node.subparagraphs = self._remove_invalid_questions(node.subparagraphs)

        # МАГИЯ PDF: Восстанавливаем плоские заголовки
        node.subparagraphs = self._restore_headers(node.subparagraphs)

        node.subparagraphs = [n for n in node.subparagraphs if n.has_content()]

        if node.paragraph_type == "header":
            node.metadata["displayMode"] = DisplayMode.ALWAYS

        node._processed = True
        return node

    def _check_for_media_content(self, node: InternalNode) -> InternalNode:
        text_lower = node.text.lower()

        table_uid = self.media.get_table_uid(node.annotations)
        if table_uid and table_uid in self.tables_map:
            table_data = self.tables_map[table_uid]
            table_node = InternalNode(
                paragraph_type="table",
                subparagraphs=self.media.extract_table_nodes(table_data)
            )
            node.subparagraphs.insert(0, table_node)

        attachment_uid = self.media.get_attachment_uid(node.annotations)
        if attachment_uid and self.media.is_image_attachment(attachment_uid, self.attachments_map):
            att = self.attachments_map.get(attachment_uid, {})
            image_node = InternalNode(
                paragraph_type="image_block",
                text=node.text,
                metadata={
                    "contains_image": True,
                    "attachment_uid": attachment_uid,
                    "file_name": att.get("metadata", {}).get("file_name", "")
                }
            )
            node.subparagraphs.insert(0, image_node)

        elif any(word in text_lower for word in ["топология", "схема", "диаграмма"]) and node.paragraph_type == "header":
            for att_uid, att_data in self.attachments_map.items():
                if att_data.get("metadata", {}).get("file_type", "").startswith("image/"):
                    image_node = InternalNode(
                        paragraph_type="image_block",
                        text=node.text,
                        metadata={
                            "contains_image": True,
                            "attachment_uid": att_uid,
                            "file_name": att_data.get("metadata", {}).get("file_name", "")
                        }
                    )
                    node.subparagraphs.insert(0, image_node)
                    break

        return node

    def _convert_nested_labels_to_questions(self, nodes: List[InternalNode]) -> List[InternalNode]:
        result = []
        for node in nodes:
            if node.paragraph_type in ("question", "header", "answer_field", "table", "row", "cell", "image_block"):
                result.append(node)
                continue

            questions_from_children = []
            remaining_children = []

            for child in node.subparagraphs:
                if child.text.strip() and self._has_placeholder_child(child):
                    q = self._make_question(child.text, child.metadata.get("marker"))
                    questions_from_children.append(q)
                    for grandchild in child.subparagraphs:
                        if not self.logic.is_placeholder_only(grandchild.text):
                            remaining_children.append(grandchild)
                elif self.logic.is_placeholder_only(child.text):
                    if node.text.strip() and not questions_from_children:
                        hint = self.logic.extract_hint(child.text)
                        q = self._make_question(node.text, node.metadata.get("marker"), hint)
                        questions_from_children.append(q)
                        node.text = ""
                else:
                    remaining_children.append(child)

            if questions_from_children:
                if node.text.strip():
                    result.append(InternalNode(text=node.text, paragraph_type="raw_text", metadata={"marker": node.metadata.get("marker")}))
                result.extend(questions_from_children)
                if remaining_children:
                    node.subparagraphs = remaining_children
                    node.text = ""
                    result.append(node)
            else:
                result.append(node)

        return result

    def _has_placeholder_child(self, node: InternalNode) -> bool:
        return any(self.logic.is_placeholder_only(c.text) for c in node.subparagraphs)

    def _split_inline_placeholders(self, nodes: List[InternalNode]) -> List[InternalNode]:
        result = []
        for node in nodes:
            if node.paragraph_type in ("question", "header", "answer_field", "table", "row", "cell", "image_block"):
                result.append(node)
                continue

            if self.logic.contains_placeholder(node.text) and not self.logic.is_placeholder_only(node.text):
                if '\n' in node.text:
                    for line in node.text.split('\n'):
                        line = line.strip()
                        if not line or self.logic.is_placeholder_only(line):
                            continue
                        if self.logic.contains_placeholder(line):
                            result.append(self._make_inline_question(line, node.metadata.get("marker")))
                        else:
                            result.append(InternalNode(text=line, paragraph_type="raw_text", metadata={"marker": node.metadata.get("marker")}))
                else:
                    result.append(self._make_inline_question(node.text, node.metadata.get("marker")))
            else:
                result.append(node)

        return result

    def _make_inline_question(self, text: str, marker: Optional[str] = None) -> InternalNode:
        segments = self.logic.split_by_placeholder(text)
        children = []
        question_texts = []

        i = 0
        while i < len(segments):
            seg = segments[i]
            if seg['type'] == 'text':
                question_texts.append(seg['content'])
                children.append(InternalNode(text=seg['content'], paragraph_type="question_text"))
                i += 1
            else:
                hint = ""
                if i + 1 < len(segments) and segments[i+1]['type'] == 'text':
                    next_text = segments[i+1]['content']
                    match = re.match(r'^\((.*?)\)(.*)$', next_text)
                    if match:
                        hint = match.group(1).strip()
                        rest_of_text = match.group(2).strip()
                        if rest_of_text:
                            segments[i+1]['content'] = rest_of_text
                        else:
                            i += 1

                children.append(InternalNode(text="", paragraph_type="answer_field", metadata={"hint": hint}))
                i += 1

        full_question_text = " ".join(question_texts)
        meta = {'maxScore': 1.0, 'question_data': full_question_text}
        if marker:
            meta["marker"] = marker

        return InternalNode(
            paragraph_type="question",
            metadata=meta,
            subparagraphs=children,
        )

    def _merge_text_with_placeholder(self, nodes: List[InternalNode]) -> List[InternalNode]:
        if not nodes:
            return []
        result = []
        i = 0
        while i < len(nodes):
            curr = nodes[i]
            if curr.paragraph_type in ("question", "answer_field", "header", "table", "row", "cell", "image_block"):
                result.append(curr)
                i += 1
                continue

            if i + 1 < len(nodes):
                nxt = nodes[i + 1]
                if (curr.text.strip()
                        and not self.logic.contains_placeholder(curr.text)
                        and self.logic.is_placeholder_only(nxt.text)):

                    hint = self.logic.extract_hint(nxt.text)
                    result.append(self._make_question(curr.text, curr.metadata.get("marker"), hint))
                    i += 2
                    continue
            result.append(curr)
            i += 1
        return result

    def _detect_questions_by_text(self, nodes: List[InternalNode]) -> List[InternalNode]:
        result = []
        for node in nodes:
            if node.paragraph_type in ("question", "answer_field", "header", "table", "row", "cell", "image_block"):
                result.append(node)
                continue
            if (self.logic.is_question_text(node.text)
                    and not self.logic.contains_placeholder(node.text)
                    and not node.subparagraphs):
                result.append(self._make_question(node.text, node.metadata.get("marker")))
            else:
                result.append(node)
        return result

    def _ensure_answers(self, nodes: List[InternalNode]) -> List[InternalNode]:
        for node in nodes:
            if node.paragraph_type == "question":
                if not any(c.paragraph_type == "answer_field" for c in node.subparagraphs):
                    node.subparagraphs.append(InternalNode(paragraph_type="answer_field", text=""))
        return nodes

    def _remove_invalid_questions(self, nodes: List[InternalNode]) -> List[InternalNode]:
        result = []
        for node in nodes:
            if node.paragraph_type == "question":
                has_text = any(
                    c.paragraph_type == "question_text" and c.text.strip()
                    for c in node.subparagraphs
                ) or node.metadata.get('question_data', '').strip()
                if has_text:
                    result.append(node)
            else:
                result.append(node)
        return result

    def _make_question(self, text: str, marker: Optional[str] = None, hint: str = "") -> InternalNode:
        meta = {'maxScore': 1.0, 'question_data': text}
        if marker:
            meta["marker"] = marker

        return InternalNode(
            paragraph_type="question",
            metadata=meta,
            subparagraphs=[
                InternalNode(text=text, paragraph_type="question_text"),
                InternalNode(text="", paragraph_type="answer_field", metadata={"hint": hint}),
            ],
        )


class PatchFactory:
    def __init__(self, logic: PlaceholderLogic, media_processor: MediaProcessor):
        self.logic = logic
        self.media = media_processor

    def create_patches(self, nodes: List[InternalNode], parent_id: Optional[str] = None, parent_node: Optional[InternalNode] = None) -> List[AnyPatch]:
        patches = []
        order = 0

        for node in nodes:
            if not node.has_content():
                continue

            if node.paragraph_type == "question_text" and parent_node and parent_node.paragraph_type == "question":
                continue

            if self.logic.is_placeholder_only(node.text) and node.paragraph_type not in ("answer_field", "question"):
                continue

            uid = str(uuid.uuid4())
            payload = self._payload(node, uid, parent_id, order, parent_node)

            if payload:
                patches.append(CreateElementPatch(action=PatchAction.CREATE, payload=payload))
                order += 1

                if node.paragraph_type == "question":
                    answer_children = [c for c in node.subparagraphs if c.paragraph_type == "answer_field"]
                    patches.extend(self.create_patches(answer_children, parent_id=uid, parent_node=node))
                elif node.subparagraphs:
                    patches.extend(self.create_patches(node.subparagraphs, parent_id=uid, parent_node=node))

        return patches

    def _payload(self, node: InternalNode, uid: str, pid: Optional[str], order: int, parent_node: Optional[InternalNode]) -> Optional[AnyElementPayload]:
        common = {
            "id": uuid.UUID(uid),
            "parent_element_id": uuid.UUID(pid) if pid else None,
            "order": order,
            "display_mode": node.metadata.get("displayMode"),
            "marker": node.metadata.get("marker")
        }

        match node.paragraph_type:
            case "header":
                return HeaderElementPayload(
                    type=ElementType.HEADER,
                    data=node.text,
                    level=node.metadata.get("level", 2),
                    **common
                )

            case "question":
                question_text = node.metadata.get('question_data', '')
                if not question_text:
                    question_text = " ".join([c.text.strip() for c in node.subparagraphs if c.paragraph_type == "question_text" and c.text.strip()])

                if not common["marker"] and node.subparagraphs:
                    first_child = node.subparagraphs[0]
                    if first_child.paragraph_type == "question_text" and first_child.metadata.get("marker"):
                        common["marker"] = first_child.metadata.get("marker")

                return QuestionElementPayload(
                    type=ElementType.QUESTION,
                    data=question_text,
                    max_score=node.metadata.get('maxScore', 1.0),
                    **common
                )

            case "question_text":
                if parent_node and parent_node.paragraph_type == "question":
                    return None
                return TextElementPayload(type=ElementType.TEXT, data=node.text, **common)

            case "answer_field":
                return AnswerElementPayload(
                    type=ElementType.ANSWER,
                    data=node.metadata.get("hint", ""),
                    is_correct=False,
                    **common
                )

            case "table":
                return TableElementPayload(type=ElementType.TABLE, **common)

            case "row":
                return RowElementPayload(type=ElementType.ROW, **common)

            case "cell":
                return CellElementPayload(type=ElementType.CELL, **common)

            case "image_block":
                return ImageElementPayload(
                    type=ElementType.IMAGE,
                    media_key=node.metadata.get("attachment_uid") or "",
                    alt_text=node.text,
                    **common
                )

            case "container":
                return ContainerElementPayload(type=ElementType.CONTAINER, **common) if node.subparagraphs else None

            case _:
                if self.logic.is_placeholder_only(node.text):
                    return AnswerElementPayload(type=ElementType.ANSWER, data="", is_correct=False, **common)
                if node.text.strip():
                    return TextElementPayload(type=ElementType.TEXT, data=node.text, **common)
                if node.subparagraphs:
                    return ContainerElementPayload(type=ElementType.CONTAINER, **common)
                return None


class DedocTemplateParser:
    def __init__(self, manager: Optional[DedocManager] = None):
        self.logic = PlaceholderLogic()
        self.media = MediaProcessor()
        self.refiner = TreeRefiner(self.logic, self.media)
        self.factory = PatchFactory(self.logic, self.media)
        self.manager = manager or DedocManager()

    def parse(self, file_path: str) -> List[AnyPatch]:
        result = self.manager.parse(
            file_path=file_path,
            parameters={
                "document_type": "other",
                "structure_type": "tree",
                "with_attachments": "true"
            }
        )

        api_schema = result.to_api_schema()

        try:
            api_data = api_schema.model_dump()
        except AttributeError:
            api_data = api_schema.dict()

        tables = api_data.get("content", {}).get("tables", [])
        tables_map = {t.get("metadata", {}).get("uid"): t for t in tables if t.get("metadata", {}).get("uid")}

        attachments = api_data.get("attachments", [])
        attachments_map = {a.get("metadata", {}).get("uid"): a for a in attachments if a.get("metadata", {}).get("uid")}

        self.refiner.set_media_maps(tables_map, attachments_map)

        root = api_data.get("content", {}).get("structure", {"text": "", "subparagraphs": []})
        tree = InternalNode.from_dedoc(root)
        refined = self.refiner.refine(tree)

        return self.factory.create_patches([n for n in refined.subparagraphs if n.has_content()])