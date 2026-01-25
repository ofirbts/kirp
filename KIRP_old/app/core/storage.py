import os
import boto3 # צריך להוסיף ל-requirements.txt

# במימוש אקדמי נשתמש ב-MinIO (Docker) או ב-S3
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
    aws_access_key_id=os.getenv("S3_KEY", "minioadmin"),
    aws_secret_access_key=os.getenv("S3_SECRET", "minioadmin")
)

def save_large_file(user_id: str, file_name: str, file_data: bytes):
    """
    הוכחת Scale: במקום לחנוק את ה-DB, שומרים ב-Object Storage.
    ב-MongoDB נשמור רק את ה-Reference (הקישור).
    """
    key = f"{user_id}/{file_name}"
    s3_client.put_object(Bucket="kirp-memories", Key=key, Body=file_data)
    return key