from core.background_service import BackgroundTaskService
from files.services.hybrid_storage import HybridStorage
from files.services.s3 import S3Storage


def get_file_storage():
    return HybridStorage(backup=S3Storage(), background_service=BackgroundTaskService())