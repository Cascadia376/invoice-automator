import boto3
import os
from botocore.exceptions import ClientError

# Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def upload_file(file_path: str, object_name: str = None):
    """Upload a file to an S3 bucket"""
    if object_name is None:
        object_name = os.path.basename(file_path)

    if not AWS_BUCKET_NAME:
        print("WARNING: AWS_BUCKET_NAME not set. Skipping S3 upload.")
        return False

    s3_client = get_s3_client()
    try:
        s3_client.upload_file(file_path, AWS_BUCKET_NAME, object_name)
        print(f"Successfully uploaded {file_path} to s3://{AWS_BUCKET_NAME}/{object_name}")
        return True
    except ClientError as e:
        print(f"Failed to upload file to S3: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error uploading to S3: {e}")
        return False

def get_presigned_url(object_name: str, expiration=3600):
    """Generate a presigned URL to share an S3 object"""
    print(f"DEBUG: Generating presigned URL for: {object_name}")
    print(f"DEBUG: Bucket: {AWS_BUCKET_NAME}, Region: {AWS_REGION}")
    s3_client = get_s3_client()
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': AWS_BUCKET_NAME,
                                                            'Key': object_name,
                                                            'ResponseContentDisposition': 'inline',
                                                            'ResponseContentType': 'application/pdf'},
                                                    ExpiresIn=expiration)
        print(f"DEBUG: Generated presigned URL: {response[:100]}...")
        return response
    except ClientError as e:
        print(f"ERROR: Failed to generate presigned URL: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error generating presigned URL: {e}")
        return None

def download_file(object_name: str, file_path: str):
    """Download a file from S3"""
    s3_client = get_s3_client()
    try:
        s3_client.download_file(AWS_BUCKET_NAME, object_name, file_path)
        return True
    except ClientError as e:
        print(f"Failed to download file from S3: {e}")
        return False
