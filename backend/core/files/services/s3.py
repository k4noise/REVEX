import os
import mimetypes
from typing import Optional, Sequence
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from .storage import Storage
from ...core.logger import GlobalLogger


class S3Storage(Storage):
    REQUIRED_ENV_VARS = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET', 'AWS_S3_ENDPOINT_URL']

    def __init__(self):
        self.bucket_name = os.environ.get('AWS_S3_BUCKET')
        self.region_name = os.environ.get('AWS_DEFAULT_REGION', 'eu-north-1')
        self.endpoint_url = os.environ.get('AWS_S3_ENDPOINT_URL')
        self.logger = GlobalLogger().get_logger(__name__)
        self._s3_client = None
        self._initialize()

    @staticmethod
    def can_init() -> bool:
        return all(os.environ.get(key) for key in S3Storage.REQUIRED_ENV_VARS)

    def _initialize(self):
        if not self.can_init():
            self.logger.warning("Переменные окружения для S3 не сконфигурированы. S3Storage будет неактивен")
            return
        try:
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                endpoint_url=self.endpoint_url,
                region_name=self.region_name
            )
            self._s3_client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"S3Storage успешно подключен к бакету '{self.bucket_name}'")
        except (NoCredentialsError, ClientError) as e:
            self._s3_client = None
            self.logger.error(f"Ошибка инициализации S3Storage: {e}")

    def save(self, save_dir: str, file_data: bytes, extension: str, filename: Optional[str] = None) -> Optional[str]:
        if not self._s3_client:
            return None
        filename = self.build_filename(filename, extension)
        s3_key = self._normalize_key(os.path.join(save_dir, filename))
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        try:
            self._s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type
            )
            self.logger.info(f"Файл успешно сохранен в S3: {s3_key}")
            return s3_key
        except ClientError as e:
            self.logger.error(f"Ошибка сохранения в S3: {e}")
            return None

    def get(self, file_path: str) -> Optional[bytes]:
        if not self._s3_client:
            return None
        s3_key = self._normalize_key(file_path)
        try:
            response = self._s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            self.logger.info(f"Файл получен из S3: {s3_key}")
            return response['Body'].read()
        except ClientError as e:
            code = e.response['Error']['Code']
            if code == 'NoSuchKey':
                self.logger.debug(f"Файл не найден в S3: {s3_key}")
            else:
                self.logger.error(f"Ошибка получения из S3: {e}")
            return None

    def remove(self, file_path: str) -> bool:
        if not self._s3_client:
            return False
        s3_key = self._normalize_key(file_path)
        try:
            self._s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            self.logger.info(f"Файл удален из S3: {s3_key}")
            return True
        except ClientError as e:
            code = e.response['Error']['Code']
            if code == 'NoSuchKey':
                self.logger.debug(f"Файл для удаления не найден в S3: {s3_key}")
                return True
            else:
                self.logger.error(f"Ошибка удаления из S3: {e}")
                return False

    def _normalize_key(self, path: str) -> str:
        return os.path.normpath(path).replace("\\", "/")

    def remove_many(self, paths: Sequence[str]) -> Sequence[bool]:
        if not self._s3_client:
            return [False] * len(paths)
        objects = [{'Key': self._normalize_key(p)} for p in paths if p]
        if not objects:
            return []
        try:
            response = self._s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )
            deleted_keys = {d['Key'] for d in response.get('Deleted', [])}
            return [self._normalize_key(p) in deleted_keys for p in paths]
        except ClientError as e:
            self.logger.error(f"Ошибка batch-удаления из S3: {e}")
            return [False] * len(paths)
