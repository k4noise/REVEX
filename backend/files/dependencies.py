from fastapi import Depends

from core.background_service import BackgroundTaskService
from core.dependencies import get_background_task_service
from files.services.hybrid_storage import HybridStorage
from files.services.s3 import S3Storage



def get_file_storage(
        background_service: BackgroundTaskService = Depends(get_background_task_service),
) -> HybridStorage:
    backup = S3Storage() if S3Storage.can_init() else None
    return HybridStorage(backup=backup, background_service=background_service)