import os
import numpy as np
from typing import Final, Sequence
from transformers import AutoTokenizer
import onnxruntime as ort

from config.settings import ONNX_MODEL_DIR

MIN_TOKEN_COUNT: Final[int] = 3
MAX_SEQUENCE_LENGTH: Final[int] = 128
VECTOR_DIMENSION: Final[int] = 312


class TextEmbedder:
    def __init__(self, model_dir: str = ONNX_MODEL_DIR):
        self.session = self._load_onnx_session(model_dir)
        self.tokenizer = self._load_tokenizer(model_dir)
        self.vector_size = VECTOR_DIMENSION

    def _load_onnx_session(self, model_dir: str) -> ort.InferenceSession:
        model_path = os.path.join(model_dir, "model.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ONNX model not found: {model_path}")
        return ort.InferenceSession(model_path)

    def _load_tokenizer(self, model_dir: str) -> AutoTokenizer:
        return AutoTokenizer.from_pretrained(model_dir)

    def compute_embeddings(self, sentences: Sequence[str]) -> np.ndarray:
        if not sentences:
            return np.zeros((0, self.vector_size), dtype=np.float32)

        is_valid = [
            isinstance(sentence, str) and len(self.tokenizer.tokenize(sentence)) >= MIN_TOKEN_COUNT
            for sentence in sentences
        ]

        filtered_sentences = [s for s, valid in zip(sentences, is_valid) if valid]

        if not filtered_sentences:
            return np.zeros((len(sentences), self.vector_size), dtype=np.float32)

        inputs = self.tokenizer(
            filtered_sentences,
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=MAX_SEQUENCE_LENGTH,
        )

        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        }

        if "token_type_ids" in inputs:
            onnx_inputs["token_type_ids"] = inputs["token_type_ids"].astype(np.int64)

        outputs = self.session.run(None, onnx_inputs)

        valid_embeddings = self._apply_mean_pooling(outputs[0], inputs["attention_mask"])
        valid_embeddings = self._normalize_vectors(valid_embeddings)

        all_embeddings = np.zeros((len(sentences), self.vector_size), dtype=np.float32)
        valid_idx = 0
        for i, flag in enumerate(is_valid):
            if flag:
                all_embeddings[i] = valid_embeddings[valid_idx]
                valid_idx += 1

        return all_embeddings

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return float(np.dot(vec1, vec2))

    def compute_similarity(self, text1: str, text2: str) -> float:
        embeddings = self.compute_embeddings([text1, text2])
        vec1, vec2 = embeddings[0], embeddings[1]
        return self.cosine_similarity(vec1, vec2)

    def _apply_mean_pooling(self, hidden_states: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        mask = attention_mask[..., None].astype(np.float32)
        masked = hidden_states * mask
        summed = masked.sum(axis=1)
        token_counts = mask.sum(axis=1).clip(min=1e-9)
        return summed / token_counts

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return vectors / norms