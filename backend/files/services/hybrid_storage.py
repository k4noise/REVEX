import os
from pathlib import Path
from typing import Optional, Sequence

import structlog

from config.settings import FILES_STORAGE_DIR
from core.background_service import BackgroundTaskService
from files.jobs import (
    s3_backup_save_from_file_job,
    s3_backup_delete_job,
    s3_backup_delete_many_job,
)
from files.services.local import LocalStorage
from files.services.s3 import S3Storage
from files.services.storage import Storage


class HybridStorage:
    def __init__(
            self,
            base_path: str = FILES_STORAGE_DIR,
            backup: Optional[Storage] = None,
            background_service: Optional[BackgroundTaskService] = None,
            logger=structlog.get_logger(__name__),
    ):
        self.local_storage = LocalStorage(base_path)
        self.backup_storage = backup
        self.background_service = background_service
        self.logger = logger
        self.base_path = Path(base_path)

    def save(self, path: str, file_data: bytes, extension: str) -> Optional[str]:
        save_dir = os.path.dirname(path)
        local_relative_path = self.local_storage.save(save_dir, file_data, extension)

        if local_relative_path is None:
            self.logger.error("Ошибка локального сохранения", path=path)
            return None

        if self._can_backup() and self.background_service:
            full_path = self._get_full_path(local_relative_path)
            self.background_service.enqueue(
                s3_backup_save_from_file_job,
                str(full_path),
                local_relative_path,
            )
            self.logger.debug(
                "hybrid_storage.backup_save.enqueued",
                local_path=local_relative_path,
            )

        return local_relative_path

    def get(self, path: str) -> Optional[bytes]:
        data = self.local_storage.get(path)
        if data:
            self.logger.debug("hybrid_storage.get.local", path=path)
            return data

        if not self._can_backup():
            self.logger.warning("hybrid_storage.get.miss_no_backup", path=path)
            return None

        try:
            self.logger.info("hybrid_storage.get.from_backup", path=path)
            storage = S3Storage()
            data = storage.get(path)
            if data:
                save_dir = os.path.dirname(path)
                filename = os.path.basename(path)
                name, ext = os.path.splitext(filename)
                extension = ext.lstrip(".") if ext else "bin"
                self.local_storage.save(save_dir, data, extension, filename=filename)
                return data
        except Exception as e:
            self.logger.error(
                "hybrid_storage.get.backup_error",
                path=path,
                error=str(e),
                exc_info=True,
            )

        self.logger.warning("hybrid_storage.get.not_found", path=path)
        return None

    def delete(self, path: str) -> bool:
        if self.local_storage.remove(path):
            if self._can_backup() and self.background_service:
                self.background_service.enqueue(
                    s3_backup_delete_job,
                    path,
                )
            return True
        return False

    def delete_many(self, paths: Sequence[str], max_files: int = 1000) -> int:
        if len(paths) > max_files:
            raise ValueError(f"Превышен лимит: {len(paths)} > {max_files}")

        deleted_flags = self.local_storage.remove_many(paths)
        successful_paths = [p for p, ok in zip(paths, deleted_flags) if ok]

        if self._can_backup() and successful_paths and self.background_service:
            self.background_service.enqueue(
                s3_backup_delete_many_job,
                successful_paths,
            )

        return sum(deleted_flags)

    def _can_backup(self) -> bool:
        return bool(self.backup_storage) or S3Storage.can_init()

    def _get_full_path(self, relative_path: str) -> Path:
        return (self.base_path / Path(relative_path)).resolve()