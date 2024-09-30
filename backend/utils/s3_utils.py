# utils/s3_utils.py

import os
import uuid
import boto3
from werkzeug.utils import secure_filename
from botocore.exceptions import NoCredentialsError, ClientError


# Configure your AWS credentials (use environment variables or AWS CLI config)
S3_BUCKET = os.getenv('S3_BUCKET')
S3_REGION = os.getenv('S3_REGION')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

# Create an S3 client
s3_client = boto3.client('s3',
                         region_name=S3_REGION,
                         aws_access_key_id=AWS_ACCESS_KEY,
                         aws_secret_access_key=AWS_SECRET_KEY)

def upload_to_s3(file, bucket_name=S3_BUCKET):
    """Upload a file to an S3 bucket and return the file's S3 URL."""
    
    unique_id = str(uuid.uuid4())
    object_name = secure_filename(file.filename)

    # Secure the filename to avoid path traversal attacks
    object_name = f"{unique_id}_{object_name}"

    try:
        # Upload the file
        s3_client.upload_fileobj(file, bucket_name, object_name)
        
        # Generate the file's public URL
        file_url = f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{object_name}"
        return file_url
    
    except Exception as e:
        raise e
