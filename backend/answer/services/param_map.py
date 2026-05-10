from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Dict, List, Sequence, Optional

from answer.schemas import AnswerResponse
from template.schemas.template_element import TemplateElementResponse, ElementType


class ParameterMapBuilder:
    @staticmethod
    def build(
            answers: Sequence[AnswerResponse],
            template_elements: Sequence[TemplateElementResponse] | None,
    ) -> Dict[str, AnswerResponse]:
        result: Dict[str, AnswerResponse] = {}

        for answer in answers or []:
            if answer.element_id:
                result[str(answer.element_id)] = answer

        if not template_elements:
            return result

        all_elements = ParameterMapBuilder._flatten_elements(template_elements)
        by_id: Dict[uuid.UUID, TemplateElementResponse] = {
            element.id: element for element in all_elements
        }

        texts_by_cell_id: dict[uuid.UUID, list[tuple[int, uuid.UUID, str]]] = defaultdict(list)

        for element in all_elements:
            if element.type != ElementType.TEXT:
                continue

            text_value = (element.data or "").strip()
            if not text_value:
                continue

            cell = ParameterMapBuilder._find_nearest_ancestor_of_type(
                element.id,
                ElementType.CELL,
                by_id,
            )
            if not cell:
                continue

            has_table = ParameterMapBuilder._has_ancestor_of_type(
                element.id,
                ElementType.TABLE,
                by_id,
            )
            has_container = ParameterMapBuilder._has_ancestor_of_type(
                element.id,
                ElementType.CONTAINER,
                by_id,
            )

            if not (has_table and has_container):
                continue

            texts_by_cell_id[cell.id].append(
                (element.order, element.id, text_value)
            )

        for cell_id, chunks in texts_by_cell_id.items():
            chunks.sort(key=lambda item: (item[0], str(item[1])))
            merged_text = " ".join(chunk_text for _, _, chunk_text in chunks).strip()
            if not merged_text:
                continue

            synthetic = AnswerResponse(
                id=cell_id,
                element_id=cell_id,
                score=1.0,
                data={"text": merged_text},
                weight=None,
                reference=None,
                root_id=None,
            )

            result[str(cell_id)] = synthetic

            for _, text_element_id, _ in chunks:
                result[str(text_element_id)] = synthetic

        return result

    @staticmethod
    def _flatten_elements(
            elements: Sequence[TemplateElementResponse],
    ) -> list[TemplateElementResponse]:
        result: list[TemplateElementResponse] = []

        def walk(node: TemplateElementResponse) -> None:
            result.append(node)
            for child in node.children or []:
                walk(child)

        for element in elements or []:
            walk(element)

        return result

    @staticmethod
    def _find_nearest_ancestor_of_type(
            element_id: uuid.UUID,
            target_type: ElementType,
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> Optional[TemplateElementResponse]:
        current = by_id.get(element_id)
        visited: set[uuid.UUID] = set()

        while current and current.parent_element_id:
            parent_id = current.parent_element_id
            if parent_id in visited:
                break

            visited.add(parent_id)
            parent = by_id.get(parent_id)
            if not parent:
                break

            if parent.type == target_type:
                return parent

            current = parent

        return None

    @staticmethod
    def _has_ancestor_of_type(
            element_id: uuid.UUID,
            target_type: ElementType,
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> bool:
        current = by_id.get(element_id)
        visited: set[uuid.UUID] = set()

        while current and current.parent_element_id:
            parent_id = current.parent_element_id
            if parent_id in visited:
                break

            visited.add(parent_id)
            parent = by_id.get(parent_id)
            if not parent:
                break

            if parent.type == target_type:
                return True

            current = parent

        return False