from dataclasses import dataclass


@dataclass(frozen=True)
class GraderConfig:
    review_threshold_low: float = 0.7
    review_threshold_high: float = 0.9

    fuzzy_word_similarity: int = 80
    max_fuzz_reference_length: int = 35

    semantic_match_threshold: float = 0.7
    semantic_weak_threshold: float = 0.5
    min_sentence_length: int = 3

    early_exit_threshold: float = 0.9


DEFAULT_CONFIG = GraderConfig()