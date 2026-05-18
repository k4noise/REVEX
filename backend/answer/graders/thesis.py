import numpy as np
from razdel import sentenize

from answer.graders.base import BaseGrader
from answer.schemas import GradingContext, ErrorDetail, ErrorType
from answer.utils.embedder import TextEmbedder


class ThesisGrader(BaseGrader):
    def __init__(self, embedder: TextEmbedder, **kwargs):
        super().__init__(**kwargs)
        self.embedder = embedder

    def process(self, context: GradingContext) -> None:
        if not context.resolved_reference:
            return

        reference_sentences = self._split_sentences(context.resolved_reference)
        given_sentences = self._split_sentences(context.raw_given)

        if not reference_sentences:
            return

        if not given_sentences:
            context.score = 0.0
            for sentence in reference_sentences:
                context.add_error(ErrorDetail(
                    type=ErrorType.SEMANTIC_MISMATCH,
                    expected=sentence
                ))
            return

        reference_vectors = self.embedder.compute_embeddings(reference_sentences)
        given_vectors = self.embedder.compute_embeddings(given_sentences)

        similarity_matrix = np.dot(reference_vectors, given_vectors.T)
        best_matches_per_reference = np.max(similarity_matrix, axis=1)

        matched_count = 0
        total_count = len(reference_sentences)

        for ref_index, (sentence, match_score) in enumerate(
                zip(reference_sentences, best_matches_per_reference)
        ):
            if match_score >= self.config.semantic_match_threshold:
                matched_count += 1
                continue

            best_given_index = int(np.argmax(similarity_matrix[ref_index]))
            closest_given_sentence = given_sentences[best_given_index]

            if match_score > self.config.semantic_weak_threshold:
                error_type = ErrorType.WEAK_SEMANTIC_MATCH
            else:
                error_type = ErrorType.SEMANTIC_MISMATCH

            context.add_error(ErrorDetail(
                type=error_type,
                expected=sentence,
                actual=closest_given_sentence
            ))

        context.score = round(matched_count / total_count, 3) if total_count > 0 else 0.0

    def _split_sentences(self, text: str) -> list[str]:
        normalized = text.replace('\n', ' ').strip()
        sentences = [segment.text.strip() for segment in sentenize(normalized)]
        return [
            sentence for sentence in sentences
            if len(sentence) >= self.config.min_sentence_length
        ]