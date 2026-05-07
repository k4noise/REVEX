from typing import Sequence

import structlog

from files.services.s3 import S3Storage

logger = structlog.get_logger(__name__)


def s3_backup_save_from_file_job(file_path: str, storage_path: str) -> None:
    if not S3Storage.can_init():
        logger.warning(
            "s3_backup_save_from_file_job.s3_not_configured",
            file_path=file_path,
            storage_path=storage_path,
        )
        return

    storage = S3Storage()
    result = storage.save_from_file(file_path, storage_path)

    if result is None:
        logger.error(
            "s3_backup_save_from_file_job.failed",
            file_path=file_path,
            storage_path=storage_path,
        )
    else:
        logger.info(
            "s3_backup_save_from_file_job.ok",
            file_path=file_path,
            storage_path=storage_path,
        )


def s3_backup_delete_job(path: str) -> None:
    if not S3Storage.can_init():
        logger.warning(
            "s3_backup_delete_job.s3_not_configured",
            path=path,
        )
        return

    storage = S3Storage()
    ok = storage.remove(path)
    if ok:
        logger.info("s3_backup_delete_job.ok", path=path)
    else:
        logger.error("s3_backup_delete_job.failed", path=path)


def s3_backup_delete_many_job(paths: Sequence[str]) -> None:
    if not S3Storage.can_init():
        logger.warning(
            "s3_backup_delete_many_job.s3_not_configured",
            count=len(paths),
        )
        return

    storage = S3Storage()
    results = storage.remove_many(list(paths))
    logger.info(
        "s3_backup_delete_many_job.done",
        requested=len(paths),
        deleted=sum(results),
    )