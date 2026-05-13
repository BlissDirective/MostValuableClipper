import boto3
from botocore.config import Config
from typing import Optional, BinaryIO
from app.core.config import settings

class R2Service:
    """Cloudflare R2 object storage service."""
    
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
            aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4")
        )
        self.bucket = settings.CLOUDFLARE_R2_BUCKET
    
    async def upload_file(
        self,
        key: str,
        file: BinaryIO,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file to R2."""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        
        self.client.upload_fileobj(
            file,
            self.bucket,
            key,
            ExtraArgs=extra_args
        )
        return f"{settings.CLOUDFLARE_R2_ENDPOINT}/{self.bucket}/{key}"
    
    async def download_file(self, key: str) -> bytes:
        """Download a file from R2."""
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()
    
    async def delete_file(self, key: str) -> bool:
        """Delete a file from R2."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False
    
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a presigned URL for a file."""
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in
        )
        return url
