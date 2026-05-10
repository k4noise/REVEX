import numpy as np
from razdel import sentenize
from typing import Sequence

from answer.schemas import GradingContext, ErrorDetail, ErrorType
from answer.utils.embedder import TextEmbedder

SIMILARITY_THRESHOLD: float = 0.7
SIMILARITY_CLOSE_THRESHOLD: float = 0.5
MIN_SENTENCE_LENGTH: int = 3


class ThesisAnswerGrader:
    def __init__(self, embedder: TextEmbedder):
        self.embedder = embedder

    def process(self, ctx: GradingContext) -> None:
        if not ctx.resolved_reference:
            return

        user_sentences = self._split_sentences(ctx.original_given)
        reference_theses = self._split_sentences(ctx.resolved_reference)

        if not reference_theses:
            return

        if not user_sentences:
            ctx.final_score = 0.0
            for thesis in reference_theses:
                ctx.add_error(ErrorDetail(type=ErrorType.SEMANTIC_MISMATCH, expected=thesis))
                if ctx.should_stop:
                    return
            return

        ref_vectors = self.embedder.compute_embeddings(reference_theses)
        user_vectors = self.embedder.compute_embeddings(user_sentences)

        similarity_matrix = np.dot(ref_vectors, user_vectors.T)
        match_scores = np.max(similarity_matrix, axis=1)

        ctx.final_score = round(float(np.mean(match_scores)), 3)

        if ctx.final_score < 1.0:
            for i, (thesis, score) in enumerate(zip(reference_theses, match_scores)):
                if score >= SIMILARITY_THRESHOLD:
                    continue

                best_idx = int(np.argmax(similarity_matrix[i]))
                best_similarity = float(similarity_matrix[i, best_idx])
                best_sentence = user_sentences[best_idx] if user_sentences else ""

                error_type = ErrorType.WEAK_SEMANTIC_MATCH if best_similarity > SIMILARITY_CLOSE_THRESHOLD else ErrorType.SEMANTIC_MISMATCH

                ctx.add_error(ErrorDetail(
                    type=error_type,
                    expected=thesis,
                    actual=best_sentence
                ))

                if ctx.should_stop:
                    return

    @staticmethod
    def _split_sentences(text: str) -> Sequence[str]:
        normalized = text.replace("\n", " ").strip()
        sentences = [s.text.strip() for s in sentenize(normalized)]
        return [s for s in sentences if len(s) >= MIN_SENTENCE_LENGTH]