import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence


class Storage(ABC):
    @staticmethod
    def generate_unique_name() -> str:
        import uuid
        return uuid.uuid4().hex

    @staticmethod
    def build_filename(filename: Optional[str], extension: str) -> str:
        extension = extension if extension.startswith('.') else f'.{extension}'
        filename = filename or Storage.generate_unique_name()
        if not filename.endswith(extension):
            filename += extension
        return filename

    @staticmethod
    @abstractmethod
    def can_init() -> bool:
        pass

    @abstractmethod
    def save(self, save_dir: str, file_data: bytes, extension: str, filename: Optional[str] = None) -> Optional[str]:
        pass

    @abstractmethod
    def get(self, file_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def remove(self, file_path: str) -> bool:
        pass

    def remove_many(self, paths: Sequence[str]) -> Sequence[bool]:
        return [self.remove(path) for path in paths]

    def save_from_file(self, file_path: str, storage_path: str) -> Optional[str]:
        local_file = Path(file_path)

        if not local_file.exists() or not local_file.is_file():
            return None

        try:
            file_data = local_file.read_bytes()
            save_dir = os.path.dirname(storage_path)
            filename = os.path.basename(storage_path)
            extension = local_file.suffix.lstrip('.') or 'bin'

            return self.save(
                save_dir=save_dir,
                file_data=file_data,
                extension=extension,
                filename=filename
            )
        except Exception:
            return None
