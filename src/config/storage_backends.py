from storages.backends.s3boto3 import S3Boto3Storage  # type: ignore[import-untyped]


class MediaStorage(S3Boto3Storage):
    location = "media"
