"""
AWS S3 client for presigned URL generation and file operations.
"""
import boto3
from botocore.exceptions import ClientError
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class S3Client:
    """Client for S3 operations."""

    def __init__(self):
        """Initialize S3 client with credentials from config."""
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS credentials must be configured")
        if not settings.AWS_S3_BUCKET:
            raise ValueError("AWS_S3_BUCKET must be configured")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.AWS_S3_BUCKET

    def generate_presigned_upload_url(
        self, file_id: str, expires_in: int = 3600
    ) -> str:
        """
        Generate a presigned PUT URL for uploading a file to S3.

        Args:
            file_id: Unique file identifier (UUID)
            expires_in: Expiration time in seconds (default: 1 hour)

        Returns:
            Presigned PUT URL string

        Raises:
            ClientError: If presigned URL generation fails
        """
        s3_key = f"uploads/{file_id}.pdf"

        try:
            url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": "application/pdf",
                },
                ExpiresIn=expires_in,
            )
            logger.info(f"Generated presigned PUT URL for {s3_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned PUT URL: {e}")
            raise

    def generate_presigned_url(
        self, s3_key: str, expires_in: int = 3600
    ) -> str:
        """
        Generate a presigned GET URL for downloading a file from S3.

        Args:
            s3_key: S3 object key (e.g., uploads/{file_id}.pdf)
            expires_in: Expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL string

        Raises:
            ClientError: If presigned URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
            logger.info(f"Generated presigned GET URL for {s3_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned GET URL: {e}")
            raise

    def download_file(self, s3_key: str) -> bytes:
        """
        Download a file from S3.

        Args:
            s3_key: S3 object key

        Returns:
            File content as bytes

        Raises:
            ClientError: If download fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"Error downloading file {s3_key}: {e}")
            raise


# Global S3 client instance (lazy initialization)
_s3_client: Optional[S3Client] = None


def get_s3_client() -> S3Client:
    """Get or create the global S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client

