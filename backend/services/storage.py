import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Union, BinaryIO

logger = logging.getLogger("storage")

# Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

class StorageClient:
    """
    Standardized client for file storage.
    Currently wraps AWS S3 via boto3, but interface is designed to be compatible with Supabase Storage.
    """
    
    def __init__(self):
        self.bucket_name = AWS_BUCKET_NAME
        self.region = AWS_REGION
        
        if not self.bucket_name: 
            logger.warning("StorageClient initialized without AWS_BUCKET_NAME.")
            
    def _get_client(self):
        return boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=self.region
        )

    def upload(self, file_path_or_obj: Union[str, BinaryIO], destination_path: str, content_type: str = None) -> bool:
        """
        Upload a file to storage.
        """
        if not self.bucket_name:
            return False
            
        client = self._get_client()
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        try:
            if isinstance(file_path_or_obj, str):
                client.upload_file(file_path_or_obj, self.bucket_name, destination_path, ExtraArgs=extra_args)
            else:
                client.upload_fileobj(file_path_or_obj, self.bucket_name, destination_path, ExtraArgs=extra_args)
                
            logger.info(f"STORAGE: Uploaded to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"STORAGE ERROR: Upload failed - {str(e)}")
            return False

    def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a presigned URL for a file.
        """
        if not self.bucket_name:
            return None
            
        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': path},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"STORAGE ERROR: URL generation failed - {str(e)}")
            return None

# Global Instance
storage_client = StorageClient()

# --- Legacy Adapters for Backward Compatibility ---
def upload_file(file_path: str, object_name: str = None):
    if object_name is None:
        object_name = os.path.basename(file_path)
    return storage_client.upload(file_path, object_name)

def get_presigned_url(object_name: str, expiration=3600):
    return storage_client.get_url(object_name, expiration)

def download_file(object_name: str, file_path: str):
    client = storage_client._get_client()
    try:
        client.download_file(AWS_BUCKET_NAME, object_name, file_path)
        return True
    except ClientError as e:
        logger.error(f"Failed to download file from S3: {e}")
        return False

def get_s3_client():
    """
    Expose the raw boto3 client for advanced operations (like streaming).
    """
    return storage_client._get_client()

