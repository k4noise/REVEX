from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import timedelta
from typing import Sequence, Dict, List, Optional, Type, TypeVar, Any

import numpy as np
import structlog
from pydantic import BaseModel, Field

from answer.services.pre_grader import PreGraderService
from answer.schemas import AnswerResponse, ErrorType
from answer.utils.embedder import TextEmbedder
from core.auth.user_model import User
from core.ttl_cache import RedisCache
from report.exceptions import NotOwnerAccessDeniedException
from report.schemas.hint import NewHintRequest, HintGenerationRequest
from template.schemas.template import FullWorkResponse
from template.schemas.template_element import (
    ElementUpdatePayload,
    ElementType,
    TemplateElementResponse,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class AnswerHintContextCache(BaseModel):
    reference: Optional[str] = None
    question_id: Optional[str] = None
    question_text: str = ""
    similar_theory_ids: list[str] = Field(default_factory=list)


class TemplateHintSnapshotCache(BaseModel):
    template_id: uuid.UUID
    fingerprint: str
    answers: dict[str, AnswerHintContextCache] = Field(default_factory=dict)
    theory: dict[str, str] = Field(default_factory=dict)
    static_params: dict[str, str] = Field(default_factory=dict)
    tables: dict[str, str] = Field(default_factory=dict)


class ReportHintMetaCache(BaseModel):
    report_id: uuid.UUID
    template_id: uuid.UUID
    template_snapshot_key: str
    author_id: str
    status: str


class HintContextService:
    TEMPLATE_SNAPSHOT_TTL = timedelta(hours=6)
    REPORT_META_TTL = timedelta(hours=1)

    def __init__(self, embedder: TextEmbedder):
        self.embedder = embedder

    def cache(self, report: FullWorkResponse, cache: RedisCache) -> None:
        elements_tree: Sequence[TemplateElementResponse] = report.template.elements or []
        elements = self._flatten_elements(elements_tree)

        if not elements:
            logger.info("hint.cache.skip_empty_template", report_id=str(report.id))
            return

        reference_by_element_id: Dict[str, Optional[str]] = {
            str(answer.element_id): answer.reference
            for answer in (report.answers or [])
            if getattr(answer, "element_id", None)
        }

        template_id = report.template.id
        fingerprint = self._build_template_fingerprint(elements)
        snapshot_key = self._template_snapshot_key(template_id, fingerprint)

        snapshot = self._cache_get_model(cache, snapshot_key, TemplateHintSnapshotCache)
        if snapshot is None:
            snapshot = self._build_template_snapshot(
                template_id=template_id,
                fingerprint=fingerprint,
                elements=elements,
                reference_by_element_id=reference_by_element_id,
            )
            cache.set(snapshot_key, snapshot.model_dump(mode="json"), ttl=self.TEMPLATE_SNAPSHOT_TTL)

        meta = ReportHintMetaCache(
            report_id=report.id,
            template_id=template_id,
            template_snapshot_key=snapshot_key,
            author_id=str(report.author_id),
            status=str(getattr(report.status, "value", report.status)),
        )
        cache.set(self._report_meta_key(report.id), meta.model_dump(mode="json"), ttl=self.REPORT_META_TTL)

        logger.info(
            "hint.cache.ok",
            report_id=str(report.id),
            template_id=str(template_id),
            snapshot_key=snapshot_key,
            answers=len(snapshot.answers),
            theory_count=len(snapshot.theory),
            static_params=len(snapshot.static_params),
            tables=len(snapshot.tables),
        )

    def get_from_cache(
            self,
            hint_request: NewHintRequest,
            user: User,
            report_id: uuid.UUID,
            cache: RedisCache,
    ) -> HintGenerationRequest | None:
        meta = self._cache_get_model(cache, self._report_meta_key(report_id), ReportHintMetaCache)
        if meta is None:
            logger.info("hint.get_from_cache.no_report_meta", report_id=str(report_id))
            return None

        if str(meta.author_id) != str(user.id):
            logger.warning(
                "hint.get_from_cache.not_owner",
                report_id=str(report_id),
                user_id=str(user.id),
                author_id=str(meta.author_id),
            )
            raise NotOwnerAccessDeniedException()

        snapshot = self._cache_get_model(cache, meta.template_snapshot_key, TemplateHintSnapshotCache)
        if snapshot is None:
            logger.info(
                "hint.get_from_cache.no_template_snapshot",
                report_id=str(report_id),
                snapshot_key=meta.template_snapshot_key,
            )
            return None

        answer_ctx = snapshot.answers.get(str(hint_request.current.element_id))
        if answer_ctx is None:
            logger.info(
                "hint.get_from_cache.no_answer_context",
                report_id=str(report_id),
                element_id=str(hint_request.current.element_id),
            )
            return None

        hint_request.current.reference = answer_ctx.reference

        live_answers = list(hint_request.params or [])
        parameters = self._build_runtime_parameters(
            live_answers=live_answers,
            static_params=snapshot.static_params,
        )

        logger.info(
            "hint.get_from_cache.pregrade_input",
            report_id=str(report_id),
            element_id=str(hint_request.current.element_id),
            has_reference=bool(hint_request.current.reference),
            has_data=bool(hint_request.current.data),
            params_count=len(live_answers),
        )

        pre_grader = PreGraderService(live_answers, embedder=self.embedder, parameters=parameters)
        pre_graded = pre_grader.grade(hint_request.current)

        if pre_graded is None:
            logger.info(
                "hint.get_from_cache.no_pregrade_result",
                report_id=str(report_id),
                element_id=str(hint_request.current.element_id),
            )
            return None

        grade_dict = getattr(pre_graded, "pre_grade", {}) or {}
        errors = grade_dict.get("errors", [])
        score = grade_dict.get("score", 1.0)

        if score == 1.0 or not errors:
            logger.info(
                "hint.get_from_cache.no_hint_needed",
                report_id=str(report_id),
                element_id=str(hint_request.current.element_id),
                score=score,
                errors_count=len(errors),
            )
            return None

        first_error_dict = errors[0]
        actual_value = first_error_dict.get("actual")

        error_detail = {
            "type": first_error_dict.get("type", ErrorType.SEMANTIC_MISMATCH.value),
            "expected": first_error_dict.get("expected", ""),
            "actual": actual_value,
        }

        theory_data: list[str] = []
        for theory_id in answer_ctx.similar_theory_ids:
            text = snapshot.theory.get(theory_id)
            if isinstance(text, str) and text.strip():
                theory_data.append(text.strip())

        if not theory_data:
            if answer_ctx.question_text:
                theory_data.append(f"[Контекст вопроса]: {answer_ctx.question_text}")

            for tid, text in snapshot.theory.items():
                if text and text.strip():
                    theory_data.append(text.strip())
                if len(theory_data) >= 5:
                    break

            if len(theory_data) < 3:
                for cell_id, cell_text in snapshot.static_params.items():
                    if cell_text and cell_text.strip():
                        theory_data.append(f"[Данные из таблицы]: {cell_text.strip()}")
                    if len(theory_data) >= 8:
                        break

        param_context = self._resolve_param_context(answer_ctx, snapshot)
        if param_context:
            theory_data.append(f"[Параметры задания]: {param_context}")

        referenced_tables = self._find_referenced_tables(answer_ctx, snapshot)
        for table_text in referenced_tables:
            theory_data.append(f"[Таблица задания]:\n{table_text}")

        if actual_value:
            distractor_theory = self._find_distractor_theory(
                wrong_value=str(actual_value),
                theory_map=snapshot.theory,
                ignore_ids=answer_ctx.similar_theory_ids,
            )
            if distractor_theory:
                theory_data.append(
                    f"[ИСТОЧНИК ОШИБКИ СТУДЕНТА (взял значение отсюда)]: {distractor_theory}"
                )

        logger.info(
            "hint.get_from_cache.ok",
            report_id=str(report_id),
            element_id=str(hint_request.current.element_id),
            theory_count=len(theory_data),
            score=score,
            has_params=bool(param_context),
            referenced_tables=len(referenced_tables),
        )

        return HintGenerationRequest(
            answer=(hint_request.current.data or {}).get("text") or "",
            question=answer_ctx.question_text or "",
            theory=theory_data,
            error_detail=error_detail,
            pre_score=score,
        )

    def analyze(
            self,
            template_elements: Sequence[TemplateElementResponse],
    ) -> Sequence[ElementUpdatePayload]:
        elements = self._flatten_elements(template_elements)
        if not elements:
            return []

        by_id = {element.id: element for element in elements}
        children = self._build_children_index(elements)

        questions = [el for el in elements if el.type == ElementType.QUESTION]
        theory = [el for el in elements if self._is_theory_element(el, by_id)]

        if not questions or not theory:
            return []

        q_ids: List[uuid.UUID] = []
        q_texts: List[str] = []
        question_texts: Dict[uuid.UUID, str] = {}

        for question in questions:
            q_text = self._get_question_text(question, children)
            if q_text:
                q_ids.append(question.id)
                q_texts.append(q_text)
                question_texts[question.id] = q_text

        if not q_texts:
            return []

        q_embeddings = self.embedder.compute_embeddings(q_texts)
        question_embeddings_map: Dict[uuid.UUID, np.ndarray] = {
            qid: vec for qid, vec in zip(q_ids, q_embeddings)
        }

        theory_embeddings_map = self._create_embedding_map(theory)

        results: List[ElementUpdatePayload] = []
        for question in questions:
            question_vector = question_embeddings_map.get(question.id)
            if question_vector is None:
                continue

            top_similar_ids = self._find_top_similar_ids(
                question_vector=question_vector,
                candidates_map=theory_embeddings_map,
                top_k=3,
            )

            results.append(ElementUpdatePayload(id=question.id, similar_theory=top_similar_ids))

            q_text = question_texts.get(question.id)
            nested_answers = self._collect_descendant_answers(question.id, children)

            for answer_element in nested_answers:
                results.append(
                    ElementUpdatePayload(
                        id=answer_element.id,
                        similar_theory=top_similar_ids,
                        question_id=str(question.id),
                        question_text=q_text,
                    )
                )

        logger.info("hint.analyze.ok", questions=len(questions), theory=len(theory), updates=len(results))
        return results

    def _cache_get_model(self, cache: RedisCache, key: str, model_cls: Type[T]) -> Optional[T]:
        raw = cache.get(key)
        if raw is None:
            return None
        if isinstance(raw, model_cls):
            return raw
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except Exception:
                logger.warning("hint.cache.invalid_bytes", key=key)
                return None
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("hint.cache.invalid_json", key=key)
                return None
        if isinstance(raw, dict):
            try:
                return model_cls.model_validate(raw)
            except Exception:
                logger.exception("hint.cache.invalid_model", key=key, model=model_cls.__name__)
                return None
        logger.warning("hint.cache.unsupported_raw_type", key=key, raw_type=type(raw).__name__)
        return None

    def _build_template_snapshot(
            self,
            template_id: uuid.UUID,
            fingerprint: str,
            elements: Sequence[TemplateElementResponse],
            reference_by_element_id: Dict[str, Optional[str]],
    ) -> TemplateHintSnapshotCache:
        by_id = {element.id: element for element in elements}
        children = self._build_children_index(elements)

        analysis_updates = self.analyze(elements)
        updates_by_id: dict[uuid.UUID, ElementUpdatePayload] = {u.id: u for u in analysis_updates}

        answers = self._build_answer_contexts(elements, by_id, children, updates_by_id, reference_by_element_id)
        theory = self._build_theory_map(elements, by_id)
        static_params = self._build_static_params(elements, by_id)
        tables = self._build_table_texts(elements, by_id)

        return TemplateHintSnapshotCache(
            template_id=template_id,
            fingerprint=fingerprint,
            answers=answers,
            theory=theory,
            static_params=static_params,
            tables=tables,
        )

    def _build_answer_contexts(
            self,
            elements: Sequence[TemplateElementResponse],
            by_id: Dict[uuid.UUID, TemplateElementResponse],
            children: Dict[uuid.UUID, List[TemplateElementResponse]],
            updates_by_id: Dict[uuid.UUID, ElementUpdatePayload],
            reference_by_element_id: Dict[str, Optional[str]],
    ) -> dict[str, AnswerHintContextCache]:
        result: dict[str, AnswerHintContextCache] = {}

        for element in elements:
            if element.type != ElementType.ANSWER:
                continue

            question = self._find_nearest_ancestor_of_type(element.id, ElementType.QUESTION, by_id)

            answer_update = updates_by_id.get(element.id)
            question_update = updates_by_id.get(question.id) if question else None

            question_text = (
                    (answer_update.question_text if answer_update else None)
                    or (question_update.question_text if question_update else None)
                    or self._get_question_text(question, children)
                    or ""
            )

            similar_theory_ids = (
                    (answer_update.similar_theory if answer_update else None)
                    or (question_update.similar_theory if question_update else None)
                    or []
            )

            result[str(element.id)] = AnswerHintContextCache(
                reference=reference_by_element_id.get(str(element.id)),
                question_id=str(question.id) if question else None,
                question_text=question_text,
                similar_theory_ids=[str(x) for x in similar_theory_ids],
            )

        return result

    def _build_theory_map(
            self,
            elements: Sequence[TemplateElementResponse],
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for element in elements:
            if not self._is_theory_element(element, by_id):
                continue
            text = (element.data or "").strip()
            if text:
                result[str(element.id)] = text
        return result

    def _build_static_params(
            self,
            elements: Sequence[TemplateElementResponse],
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> dict[str, str]:
        table_meta = self._build_table_meta(elements, by_id)
        grouped: dict[str, list[tuple[int, uuid.UUID, str]]] = {}

        for element in elements:
            if element.type != ElementType.TEXT:
                continue
            text_value = (element.data or "").strip()
            if not text_value:
                continue

            cell = self._find_nearest_ancestor_of_type(element.id, ElementType.CELL, by_id)
            if cell is None:
                continue

            has_table = self._has_ancestor_of_type(element.id, ElementType.TABLE, by_id)
            has_container = self._has_ancestor_of_type(element.id, ElementType.CONTAINER, by_id)
            if not (has_table and has_container):
                continue

            key = str(cell.id)
            grouped.setdefault(key, []).append((element.order, element.id, text_value))

        result: dict[str, str] = {}
        for cell_id, chunks in grouped.items():
            chunks.sort(key=lambda item: (item[0], str(item[1])))
            merged_text = " ".join(chunk for _, _, chunk in chunks).strip()
            if not merged_text:
                continue

            meta = table_meta.get(cell_id)
            if meta:
                result[cell_id] = f"{meta['row_label']} / {meta['col_label']} = {merged_text}"
            else:
                result[cell_id] = merged_text

        return result

    def _build_table_meta(
            self,
            elements: Sequence[TemplateElementResponse],
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> Dict[str, Dict[str, str]]:
        result: Dict[str, Dict[str, str]] = {}
        tables = [el for el in elements if el.type == ElementType.TABLE]

        for table in tables:
            if not self._has_ancestor_of_type(table.id, ElementType.CONTAINER, by_id):
                continue

            rows = [c for c in (table.children or []) if c.type == ElementType.ROW]
            if not rows:
                continue

            header_row = rows[0]
            header_texts = [
                self._cell_text(c)
                for c in (header_row.children or [])
                if c.type == ElementType.CELL
            ]

            for row_idx, row in enumerate(rows):
                cells = [c for c in (row.children or []) if c.type == ElementType.CELL]
                row_label = self._cell_text(cells[0]) if cells else f"Строка {row_idx + 1}"

                for col_idx, cell in enumerate(cells):
                    col_label = (
                        header_texts[col_idx]
                        if col_idx < len(header_texts)
                        else f"Столбец {col_idx + 1}"
                    )
                    result[str(cell.id)] = {"row_label": row_label, "col_label": col_label}

        return result

    def _build_table_texts(
            self,
            elements: Sequence[TemplateElementResponse],
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        tables = [el for el in elements if el.type == ElementType.TABLE]

        for table in tables:
            if not self._has_ancestor_of_type(table.id, ElementType.CONTAINER, by_id):
                continue

            rows = [c for c in (table.children or []) if c.type == ElementType.ROW]
            if not rows:
                continue

            lines: list[str] = []
            all_element_ids: list[str] = []

            for row in rows:
                cells = [c for c in (row.children or []) if c.type == ElementType.CELL]
                cell_texts = [self._cell_text(c) or "-" for c in cells]
                lines.append(" | ".join(cell_texts))

                for cell in cells:
                    all_element_ids.append(str(cell.id))
                    self._collect_all_ids(cell, all_element_ids)

            if lines:
                table_id = str(table.id)
                table_text = "\n".join(lines)
                result[table_id] = table_text

                for eid in all_element_ids:
                    if eid != table_id:
                        result[eid] = table_id

        return result

    @staticmethod
    def _collect_all_ids(node: TemplateElementResponse, ids: list[str]) -> None:
        for child in node.children or []:
            ids.append(str(child.id))
            HintContextService._collect_all_ids(child, ids)

    def _build_runtime_parameters(
            self,
            live_answers: Sequence[AnswerResponse],
            static_params: Dict[str, str],
    ) -> Dict[str, AnswerResponse]:
        result: Dict[str, AnswerResponse] = {
            str(answer.element_id): answer
            for answer in live_answers or []
            if answer.element_id
        }

        for element_id_str, text_value in static_params.items():
            if not text_value or element_id_str in result:
                continue

            raw_value = text_value
            eq_pos = text_value.rfind("= ")
            if eq_pos >= 0:
                raw_value = text_value[eq_pos + 2:].strip()

            element_uuid = uuid.UUID(element_id_str)
            result[element_id_str] = AnswerResponse(
                id=element_uuid,
                element_id=element_uuid,
                score=1.0,
                data={"text": raw_value},
                weight=None,
                reference=None,
                root_id=None,
            )

        return result

    def _resolve_param_context(
            self,
            answer_ctx: AnswerHintContextCache,
            snapshot: TemplateHintSnapshotCache,
    ) -> Optional[str]:
        ref = answer_ctx.reference
        if not ref:
            return None

        param_ids = re.findall(r"\{([0-9a-fA-F-]{36})(?:\|[^}]*)?\}", ref)
        if not param_ids:
            return None

        seen = set()
        parts = []
        for pid in param_ids:
            if pid in seen:
                continue
            seen.add(pid)

            value = snapshot.static_params.get(pid)
            if value:
                parts.append(value)
            else:
                for ans_id, ans_ctx in snapshot.answers.items():
                    if ans_id == pid and ans_ctx.question_text:
                        parts.append(f"ответ студента на: {ans_ctx.question_text}")
                        break

        if not parts:
            return None

        return "; ".join(parts)

    def _find_referenced_tables(
            self,
            answer_ctx: AnswerHintContextCache,
            snapshot: TemplateHintSnapshotCache,
    ) -> list[str]:
        ref = answer_ctx.reference
        if not ref:
            return []

        param_ids = re.findall(r"\{([0-9a-fA-F-]{36})(?:\|[^}]*)?\}", ref)
        if not param_ids:
            return []

        table_ids_seen = set()
        table_texts = []

        for pid in param_ids:
            table_ref = snapshot.tables.get(pid)
            if not table_ref:
                continue

            if table_ref in snapshot.tables and table_ref != pid:
                table_id = table_ref
            else:
                table_id = pid

            if table_id in table_ids_seen:
                continue
            table_ids_seen.add(table_id)

            table_text = snapshot.tables.get(table_id)
            if table_text and "\n" in table_text:
                table_texts.append(table_text)

        return table_texts

    def _template_snapshot_key(self, template_id: uuid.UUID, fingerprint: str) -> str:
        return f"template_hint_ctx:{template_id}:{fingerprint}"

    def _report_meta_key(self, report_id: uuid.UUID) -> str:
        return f"report_hint_meta:{report_id}"

    def _build_template_fingerprint(self, elements: Sequence[TemplateElementResponse]) -> str:
        payload: list[dict[str, Any]] = []
        for element in sorted(elements, key=lambda x: (x.order, str(x.id))):
            dumped = element.model_dump(mode="json", exclude_none=True)
            dumped.pop("children", None)
            payload.append(dumped)
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _find_distractor_theory(
            self,
            wrong_value: str,
            theory_map: Dict[str, str],
            ignore_ids: List[str],
    ) -> Optional[str]:
        val_str = str(wrong_value).strip()
        if not val_str:
            return None
        pattern = re.compile(rf"\b{re.escape(val_str)}\b", re.IGNORECASE)
        for theory_id, text in theory_map.items():
            if theory_id in ignore_ids:
                continue
            if isinstance(text, str) and pattern.search(text):
                return text
        return None

    @staticmethod
    def _flatten_elements(elements: Sequence[TemplateElementResponse]) -> list[TemplateElementResponse]:
        result: list[TemplateElementResponse] = []
        seen: set[uuid.UUID] = set()

        def walk(node: TemplateElementResponse) -> None:
            if node.id in seen:
                return
            seen.add(node.id)
            result.append(node)
            for child in node.children or []:
                walk(child)

        for element in elements or []:
            walk(element)
        return result

    @staticmethod
    def _build_children_index(
            elements: Sequence[TemplateElementResponse],
    ) -> Dict[uuid.UUID, List[TemplateElementResponse]]:
        children: Dict[uuid.UUID, List[TemplateElementResponse]] = {}
        for el in elements:
            if el.parent_element_id:
                children.setdefault(el.parent_element_id, []).append(el)
        return children

    @staticmethod
    def _get_question_text(
            question: Optional[TemplateElementResponse],
            children_index: Dict[uuid.UUID, List[TemplateElementResponse]],
    ) -> Optional[str]:
        if not question:
            return None
        if question.data and question.data.strip():
            return question.data.strip()
        for child in children_index.get(question.id, []):
            if child.type == ElementType.TEXT and child.data and child.data.strip():
                return child.data.strip()
        return None

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

    @staticmethod
    def _collect_descendant_answers(
            root_id: uuid.UUID,
            children_index: Dict[uuid.UUID, List[TemplateElementResponse]],
    ) -> List[TemplateElementResponse]:
        result: List[TemplateElementResponse] = []
        stack = list(children_index.get(root_id, []))
        while stack:
            current = stack.pop()
            if current.type == ElementType.ANSWER:
                result.append(current)
            stack.extend(children_index.get(current.id, []))
        return result

    @staticmethod
    def _is_theory_element(
            element: TemplateElementResponse,
            by_id: Dict[uuid.UUID, TemplateElementResponse],
    ) -> bool:
        if element.type not in (ElementType.TEXT, ElementType.HEADER):
            return False
        if HintContextService._has_ancestor_of_type(element.id, ElementType.QUESTION, by_id):
            return False
        if HintContextService._has_ancestor_of_type(element.id, ElementType.TABLE, by_id):
            return False
        return bool((element.data or "").strip())

    @staticmethod
    def _cell_text(cell: TemplateElementResponse) -> str:
        texts: list[str] = []

        def walk(node: TemplateElementResponse) -> None:
            if node.type == ElementType.ANSWER:
                return
            if node.data and node.data.strip():
                texts.append(node.data.strip())
            for child in node.children or []:
                walk(child)

        walk(cell)
        return " ".join(texts) or ""

    def _create_embedding_map(
            self,
            elements: Sequence[TemplateElementResponse],
    ) -> Dict[uuid.UUID, np.ndarray]:
        ids: List[uuid.UUID] = []
        texts: List[str] = []
        for element in elements:
            if element.data and element.data.strip():
                ids.append(element.id)
                texts.append(element.data.strip())
        if not texts:
            return {}
        embeddings = self.embedder.compute_embeddings(texts)
        return {el_id: vec for el_id, vec in zip(ids, embeddings)}

    def _find_top_similar_ids(
            self,
            question_vector: np.ndarray,
            candidates_map: Dict[uuid.UUID, np.ndarray],
            top_k: int,
    ) -> List[str]:
        scores = []
        for candidate_id, candidate_vector in candidates_map.items():
            similarity = self.embedder.cosine_similarity(question_vector, candidate_vector)
            scores.append((candidate_id, similarity))
        sorted_scores = sorted(scores, key=lambda item: item[1], reverse=True)
        return [str(item[0]) for item in sorted_scores[:top_k]]