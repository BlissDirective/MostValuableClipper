import boto3
from botocore.config import Config
import requests
from typing import Optional, BinaryIO
from app.core.config import settings

class R2Service:
    """Cloudflare R2 object storage service.
    
    Supports two auth methods:
    1. S3-style Access Key ID + Secret Access Key (preferred for boto3)
    2. Cloudflare API Token (falls back to REST API for uploads/downloads)
    """
    
    def __init__(self):
        self.bucket = settings.CLOUDFLARE_R2_BUCKET
        self.endpoint = settings.CLOUDFLARE_R2_ENDPOINT
        self.account_id = settings.CLOUDFLARE_ACCOUNT_ID
        self.api_token = settings.CLOUDFLARE_R2_API_TOKEN
        
        # Check if we have S3-style keys
        has_s3_keys = (
            settings.CLOUDFLARE_R2_ACCESS_KEY_ID
            and settings.CLOUDFLARE_R2_ACCESS_KEY_ID != "your-access-key"
            and settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY
            and settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY != "your-secret-key"
        )
        
        if has_s3_keys:
            self.client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4")
            )
            self._use_s3 = True
        elif self.api_token:
            # Use API Token with boto3 (Cloudflare supports this)
            self.client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.account_id,
                aws_secret_access_key=self.api_token,
                config=Config(signature_version="s3v4")
            )
            self._use_s3 = True
        else:
            self.client = None
            self._use_s3 = False
    
    async def upload_file(
        self,
        key: str,
        file: BinaryIO,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file to R2."""
        if not self._use_s3:
            raise RuntimeError("R2 not configured: need S3 keys or API token")
        
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        
        self.client.upload_fileobj(
            file,
            self.bucket,
            key,
            ExtraArgs=extra_args
        )
        return f"{self.endpoint}/{self.bucket}/{key}"
    
    async def download_file(self, key: str) -> bytes:
        """Download a file from R2."""
        if not self._use_s3:
            raise RuntimeError("R2 not configured: need S3 keys or API token")
        
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()
    
    async def delete_file(self, key: str) -> bool:
        """Delete a file from R2."""
        if not self._use_s3:
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False
    
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a presigned URL for a file."""
        if not self._use_s3:
            raise RuntimeError("R2 not configured: need S3 keys or API token")
        
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in
        )
        return url
    
    async def list_objects(self, prefix: Optional[str] = None) -> list:
        """List objects in the bucket."""
        if not self._use_s3:
            raise RuntimeError("R2 not configured: need S3 keys or API token")
        
        kwargs = {"Bucket": self.bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        
        response = self.client.list_objects_v2(**kwargs)
        return response.get("Contents", [])
