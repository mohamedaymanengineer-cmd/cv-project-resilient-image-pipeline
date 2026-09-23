import os
import sys
import json
import logging
import time
from io import BytesIO
from urllib.parse import unquote_plus

import boto3
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("worker")

QUEUE_URL = os.environ["SQS_QUEUE_URL"]
PROCESSED_BUCKET = os.environ["PROCESSED_BUCKET"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

THUMBNAIL_SIZE = (200, 200)
POLL_WAIT_SECONDS = 20

sqs = boto3.client("sqs", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def poll_and_process():
    logger.info("Worker started. Polling queue: %s", QUEUE_URL)
    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=POLL_WAIT_SECONDS,
        )

        messages = response.get("Messages", [])
        if not messages:
            continue

        message = messages[0]
        process_message(message)


def process_message(message):
    receipt_handle = message["ReceiptHandle"]

    try:
        body = json.loads(message["Body"])
        record = body["Records"][0]["s3"]
        bucket_name = record["bucket"]["name"]
        object_key = unquote_plus(record["object"]["key"])

        logger.info("Processing s3://%s/%s", bucket_name, object_key)

        image_bytes = download_image(bucket_name, object_key)
        thumbnail_bytes, metadata = create_thumbnail(image_bytes)
        thumb_key = build_thumbnail_key(object_key)
        upload_thumbnail(thumbnail_bytes, thumb_key)
        write_status(object_key, thumb_key, metadata, status="SUCCESS")

        sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
        logger.info("Successfully processed and deleted message for %s", object_key)

    except Exception as exc:
        logger.exception("Failed to process message: %s", exc)


def download_image(bucket_name, object_key):
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    return response["Body"].read()


def create_thumbnail(image_bytes):
    image = Image.open(BytesIO(image_bytes))
    original_format = image.format
    original_size = image.size

    image.thumbnail(THUMBNAIL_SIZE)

    output = BytesIO()
    image.save(output, format=original_format)
    output.seek(0)

    metadata = {
        "original_width": str(original_size[0]),
        "original_height": str(original_size[1]),
        "thumbnail_width": str(image.size[0]),
        "thumbnail_height": str(image.size[1]),
        "format": original_format,
    }
    return output.read(), metadata


def build_thumbnail_key(object_key):
    name, ext = os.path.splitext(object_key)
    return f"{name}_thumb{ext}"


def upload_thumbnail(thumbnail_bytes, thumb_key):
    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=thumb_key,
        Body=thumbnail_bytes,
    )


def write_status(object_key, thumb_key, metadata, status):
    item = {
        "image_id": object_key,
        "status": status,
        "thumbnail_key": thumb_key,
        "processed_at": str(int(time.time())),
    }
    item.update(metadata)
    table.put_item(Item=item)


if __name__ == "__main__":
    poll_and_process()