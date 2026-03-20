from core.files.services.hybrid_storage import HybridStorage
from core.files.services.s3 import S3Storage


def get_file_storage():
    return HybridStorage(backup=S3Storage())