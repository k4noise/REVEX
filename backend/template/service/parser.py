from __future__ import annotations

import re
import uuid
from typing import List, Optional, Dict, Any

from dedoc import DedocManager
from pydantic import BaseModel, Field

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
)


class InternalNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    paragraph_type: str = "raw_text"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    subparagraphs: List[InternalNode] = Field(default_factory=list)
    annotations: List[dict] = Field(default_factory=list)

    @classmethod
    def from_dedoc(cls, data: dict) -> InternalNode:
        return cls(
            node_id=data.get("node_id", str(uuid.uuid4())),
            text=data.get("text", "") or "",
            paragraph_type=data.get("metadata", {}).get("paragraph_type", "raw_text"),
            metadata=data.get("metadata", {}) or {},
            annotations=data.get("annotations", []) or [],
            subparagraphs=[cls.from_dedoc(c) for c in data.get("subparagraphs", []) or []],
        )


class PlaceholderLogic:
    def __init__(self, char: str = "_", min_repeat: int = 3):
        self.pattern = re.compile(rf"{re.escape(char)}{{{min_repeat},}}")

    def find_placeholder(self, text: str):
        return self.pattern.search(text or "")

    def is_placeholder_only(self, text: str) -> bool:
        t = (text or "").strip()
        if not t or not self.find_placeholder(t):
            return False

        clean_text = re.sub(r'^[A-Za-zА-Яа-я0-9_\-()/\.:#\s]*:', '', t).strip()
        return not clean_text or self.find_placeholder(clean_text)


class TreeRefiner:
    def __init__(self, logic: PlaceholderLogic):
        self.logic = logic

    def refine(self, node: InternalNode) -> InternalNode:
        node.subparagraphs = [self.refine(child) for child in node.subparagraphs]
        node.subparagraphs = self._merge_siblings(node.subparagraphs)
        return self._transform_node(node)

    def _merge_siblings(self, nodes: List[InternalNode]) -> List[InternalNode]:
        if not nodes:
            return []

        merged: List[InternalNode] = []
        i = 0
        while i < len(nodes):
            curr = nodes[i]

            if i + 1 < len(nodes):
                nxt = nodes[i + 1]
                if (
                        not self.logic.is_placeholder_only(curr.text)
                        and self.logic.is_placeholder_only(nxt.text)
                ):
                    # Склеиваем "вопрос + поле" в один узел question
                    question_node = InternalNode(
                        paragraph_type="question",
                        subparagraphs=[
                            InternalNode(
                                text=curr.text,
                                paragraph_type="question_text",
                            ),
                            InternalNode(
                                text=nxt.text,
                                paragraph_type="answer_field",
                            ),
                        ],
                    )
                    merged.append(question_node)
                    i += 2
                    continue

            merged.append(curr)
            i += 1

        return merged

    def _transform_node(self, node: InternalNode) -> InternalNode:
        if node.paragraph_type == "header":
            node.metadata["displayMode"] = DisplayMode.ALWAYS
        return node


class PatchFactory:
    def create_patches(
            self,
            nodes: List[InternalNode],
            parent_id: Optional[str] = None,
    ) -> List[AnyPatch]:
        patches: List[AnyPatch] = []
        for i, node in enumerate(nodes):
            element_id = str(uuid.uuid4())

            payload = self._build_payload(node, element_id, parent_id, i)
            if payload:
                patches.append(
                    CreateElementPatch(
                        action=PatchAction.CREATE,
                        payload=payload,
                    )
                )

            if node.subparagraphs:
                patches.extend(
                    self.create_patches(node.subparagraphs, parent_id=element_id)
                )

        return patches

    def _build_payload(
            self,
            node: InternalNode,
            uid: str,
            pid: Optional[str],
            order: int,
    ) -> Optional[AnyElementPayload]:
        common = {
            "id": uid,
            "parentElementId": pid,
            "order": order,
            "displayMode": node.metadata.get("displayMode"),
        }

        match node.paragraph_type:
            case "header":
                return HeaderElementPayload(
                    type=ElementType.HEADER,
                    data=node.text,
                    level=2,
                    **common,
                )

            case "question":
                return QuestionElementPayload(
                    type=ElementType.QUESTION,
                    data="",
                    maxScore=1.0,
                    **common,
                )

            case "question_text":
                return TextElementPayload(
                    type=ElementType.TEXT,
                    data=node.text,
                    **common,
                )

            case "answer_field":
                return AnswerElementPayload(
                    type=ElementType.ANSWER,
                    data=node.text,
                    **common,
                )

            case "image_block":
                return ImageElementPayload(
                    type=ElementType.IMAGE,
                    mediaKey=node.metadata.get("attachment_uid", ""),
                    **common,
                )

            case "container" | "root":
                return ContainerElementPayload(
                    type=ElementType.CONTAINER,
                    **common,
                )

            case _:
                if node.text.strip():
                    return TextElementPayload(
                        type=ElementType.TEXT,
                        data=node.text,
                        **common,
                    )
                return ContainerElementPayload(
                    type=ElementType.CONTAINER,
                    **common,
                )


class DedocTemplateParser:
    def __init__(self, manager: Optional[DedocManager] = None):
        self.logic = PlaceholderLogic()
        self.refiner = TreeRefiner(self.logic)
        self.factory = PatchFactory()
        self.manager = manager or DedocManager()

    def parse(self, file_path: str) -> List[AnyPatch]:
        result = self.manager.parse(file_path=file_path)

        api_schema = result.to_api_schema()
        try:
            api_data = api_schema.model_dump()
        except AttributeError:
            api_data = api_schema.dict()

        root_dict = (
            api_data
            .get("content", {})
            .get("structure", {"text": "", "subparagraphs": []})
        )

        tree = InternalNode.from_dedoc(root_dict)
        refined_tree = self.refiner.refine(tree)

        return self.factory.create_patches(refined_tree.subparagraphs)