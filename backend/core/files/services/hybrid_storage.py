import os
from typing import Optional, Sequence
from pathlib import Path
from .local import LocalStorage
from .storage import Storage
from ...configs.config import FILES_STORAGE_DIR
from ...core.logger import GlobalLogger
from ...services.background_task import BackgroundTaskService


class HybridStorage:
    def __init__(
            self,
            base_path: str = FILES_STORAGE_DIR,
            backup: Optional[Storage] = None,
            background_service: Optional[BackgroundTaskService] = None
    ):
        self.local_storage = LocalStorage(base_path)
        self.backup_storage = backup
        self.background_service = background_service
        self.logger = GlobalLogger().get_logger(__name__)
        self.base_path = Path(base_path)

    def save(self, path: str, file_data: bytes, extension: str) -> Optional[str]:
        """Сохранить файл"""
        save_dir = os.path.dirname(path)
        local_relative_path = self.local_storage.save(save_dir, file_data, extension)
        if local_relative_path is None:
            self.logger.error(f"Ошибка локального сохранения: {path}")
            return None

        if self._can_backup() and self.background_service is not None:
            backup_storage = self.backup_storage
            full_path = self._get_full_path(local_relative_path)

            def save_to_backup():
                try:
                    result = backup_storage.save_from_file(
                        file_path=str(full_path),
                        storage_path=local_relative_path
                    )
                    if result:
                        self.logger.info(f"Файл сохранен в backup: {local_relative_path}")
                    else:
                        self.logger.error(f"Не удалось сохранить в backup: {local_relative_path}")
                except Exception as e:
                    self.logger.error(f"Ошибка backup сохранения: {e}", exc_info=True)

            self.background_service.enqueue(save_to_backup)
            self.logger.debug(f"Задача сохранения в backup добавлена в очередь")

        return local_relative_path

    def get(self, path: str) -> Optional[bytes]:
        """Получить файл"""
        data = self.local_storage.get(path)
        if data:
            self.logger.debug(f"Файл получен из локального хранилища: {path}")
            return data
        if not self._can_backup():
            self.logger.warning(f"Файл не найден локально, бэкап не настроен: {path}")
            return None
        try:
            self.logger.info(f"Файл не найден локально, ищем в бэкапе: {path}")
            data = self.backup_storage.get(path)
            if data:
                save_dir = os.path.dirname(path)
                filename = os.path.basename(path)
                name, ext = os.path.splitext(filename)
                extension = ext.lstrip('.') if ext else 'bin'
                self.local_storage.save(save_dir, data, extension, filename=filename)
                return data
        except Exception as e:
            self.logger.error(f"Ошибка при обращении к резервному хранилищу: {path} - {e}", exc_info=True)
        self.logger.warning(f"Файл не найден нигде: {path}")
        return None

    def delete(self, path: str) -> bool:
        """Удалить файл"""
        if self.local_storage.remove(path):
            self._enqueue_backup_operation("remove", file_path=path)
            return True
        return False

    def delete_many(self, paths: Sequence[str], max_files: int = 1000) -> int:
        """Удалить много файлов одновременно"""
        if len(paths) > max_files:
            raise ValueError(f"Превышен лимит: {len(paths)} > {max_files}")
        deleted = self.local_storage.remove_many(paths)

        successful_paths = [p for p, success in zip(paths, deleted) if success]
        if self._can_backup() and successful_paths:
            self._enqueue_backup_operation("remove_many", successful_paths)

        return sum(deleted)

    def _can_backup(self) -> bool:
        """Проверка, доступно ли резервное хранилище"""
        return self.backup_storage is not None

    def _get_full_path(self, relative_path: str) -> Path:
        """Получение полного пути к файлу в локальном хранилище"""
        return (self.base_path / Path(relative_path)).resolve()

    def _enqueue_backup_operation(self, operation_name: str, *args, **kwargs) -> None:
        """Ставим операцию в фон"""
        if not self._can_backup() or self.background_service is None:
            return
        func = getattr(self.backup_storage, operation_name, None)
        if not func:
            self.logger.error(f"Метод {operation_name} не найден в резервном хранилище")
            return

        def wrapped_operation():
            try:
                result = func(*args, **kwargs)
                self.logger.debug(f"Операция '{operation_name}' выполнена в резерве: {result or 'OK'}")
            except Exception as e:
                self.logger.error(f"Ошибка при '{operation_name}' в резерве: {e}", exc_info=True)

        self.background_service.enqueue(wrapped_operation)
        self.logger.debug(f"Задача '{operation_name}' добавлена в очередь")
