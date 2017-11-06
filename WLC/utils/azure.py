import hashlib
import logging
import os

import cv2
from azure.storage.blob import BlockBlobService, ContentSettings

LOGGER = logging.getLogger()

# Azure spams the logs, this will make it quiet.
logging.getLogger("azure").setLevel(logging.CRITICAL)


def get_block_blob_service():
    if not os.environ.get('BLOB_ACCOUNT') or not os.environ.get('BLOB_KEY'):
        raise ValueError('BLOB_ACCOUNT and BLOB_KEY environment variables need to be set.')

    account = os.environ.get('BLOB_ACCOUNT')
    key = os.environ.get('BLOB_KEY')

    return BlockBlobService(account_name=account, account_key=key)


def create_container_not_exists(block_blob_service, container):
    if not block_blob_service.exists(container):
        block_blob_service.create_container(container)


def save_image_to_azure(container, image):
    """
    Saves image to Azure Blob storage as a jpg. Requires BLOB_ACCOUNT and BLOB_KEY environment variables to be set.
    Uses the hash value of the image to determine if it already exists.

    :param container: Destination container (blob storage uses flat structure)
    :param image: Image which should be saved
    :return: Whether the image was saved and name of the file (hash value)
    """
    block_blob_service = get_block_blob_service()
    create_container_not_exists(block_blob_service, container)

    hashed = hashlib.md5(image.tobytes()).hexdigest()

    if block_blob_service.exists(container, hashed):
        LOGGER.debug('Did not save image, already found one with the same hash.')
        return False, ""

    img_bytes = cv2.imencode('.jpg', image)[1].tostring()

    block_blob_service.create_blob_from_bytes(
        container,
        hashed,
        img_bytes,
        content_settings=ContentSettings(content_type='image/jpg')
    )

    return True, hashed


def save_code_to_azure(container, image_container, key, code):
    """
    Saves the fixed code to Azure Blob storage as text if the image exists in the pictures container. Will overwrite
    the previous version if if exists.

    :param container: Destination container of the code
    :param image_container: Destination container where images should be found
    :param key: Key under which it should be saves, is the same as the key of the image
    :param code: Fixed code by used
    :return:
    """
    block_blob_service = get_block_blob_service()

    if not block_blob_service.exists(image_container, key):
        raise ValueError('Cannot save code for an image which does not exist')

    create_container_not_exists(block_blob_service, container)
    block_blob_service.create_blob_from_text(container, key, code)
