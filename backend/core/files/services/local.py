import os
from pathlib import Path
from typing import Optional
from .storage import Storage
from ...core.logger import GlobalLogger


class LocalStorage(Storage):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.logger = GlobalLogger().get_logger(__name__)

    @staticmethod
    def can_init(base_path: Optional[str] = None) -> bool:
        from ...configs.config import FILES_STORAGE_DIR
        path = Path(base_path or FILES_STORAGE_DIR)
        return path.exists() and os.access(path, os.W_OK)

    def save(self, save_dir: str, file_data: bytes, extension: str, filename: Optional[str] = None) -> Optional[str]:
        filename = self.build_filename(filename, extension)
        relative_path = str(Path(save_dir) / filename)
        full_path = self._get_full_path(relative_path)
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(file_data)
            self.logger.info(f"Файл сохранен локально: {full_path}")
            return relative_path
        except Exception as e:
            self.logger.error(f"Ошибка сохранения локального файла {full_path}: {e}")
            return None

    def get(self, file_path: str) -> Optional[bytes]:
        full_path = self._get_full_path(file_path)
        if not full_path.exists():
            self.logger.debug(f"Локальный файл не найден: {full_path}")
            return None
        try:
            return full_path.read_bytes()
        except Exception as e:
            self.logger.error(f"Ошибка чтения локального файла {full_path}: {e}")
            return None

    def remove(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        if not full_path.exists():
            self.logger.debug(f"Файл для удаления не существует: {full_path}")
            return True
        try:
            full_path.unlink()
            self.logger.info(f"Файл удален локально: {full_path}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления локального файла {full_path}: {e}")
            return False

    def _get_full_path(self, relative_path: str) -> Path:
        return (self.base_path / Path(relative_path)).resolve()
