import hashlib
import logging
import os

import cv2
from azure.storage.blob import BlockBlobService, ContentSettings

LOGGER = logging.getLogger()

# Azure spams the logs, this will make it quiet.
logging.getLogger("azure").setLevel(logging.CRITICAL)


class WLCAzure:
    def __init__(self):
        self._block_blob_service = self._get_block_blob_service()

    def _get_block_blob_service(self):
        if not os.environ.get('BLOB_ACCOUNT') or not os.environ.get('BLOB_KEY'):
            raise ValueError('BLOB_ACCOUNT and BLOB_KEY environment variables need to be set.')

        account = os.environ.get('BLOB_ACCOUNT')
        key = os.environ.get('BLOB_KEY')

        return BlockBlobService(account_name=account, account_key=key)

    def create_container_not_exists(self, container):
        if not self._block_blob_service.exists(container):
            self._block_blob_service.create_container(container)

    def create_containers_not_exist(self, containers):
        for container in containers:
            self.create_container_not_exists(container)

    def get_data_from_blobs(self, containers, key):
        return list(map(lambda container: self._block_blob_service.get_blob_to_text(container, key), containers))

    def save_image_to_azure(self, container, image):
        """
        Saves image to Azure Blob storage as a jpg. Requires BLOB_ACCOUNT and BLOB_KEY environment variables to be set.
        Uses the hash value of the image to determine if it already exists.

        :param container: Destination container (blob storage uses flat structure)
        :param image: Image which should be saved
        :return: Whether the image was saved and name of the file (hash value)
        """
        self.create_container_not_exists(container)

        hashed = hashlib.md5(image.tobytes()).hexdigest()

        if self._block_blob_service.exists(container, hashed):
            LOGGER.debug('Did not save image, already found one with the same hash.')
            return False, hashed

        img_bytes = cv2.imencode('.jpg', image)[1].tostring()

        self._block_blob_service.create_blob_from_bytes(
            container,
            hashed,
            img_bytes,
            content_settings=ContentSettings(content_type='image/jpg')
        )

        return True, hashed

    def save_template_and_test(self, container, template_file, test_file):
        self.create_container_not_exist(container)

        hashed = hashlib.md5(template_file.tobytes()).hexdigest()

        if self._block_blob_service.exists(container, hashed):
            return '', 1

        template_filename = '{}.py'.format(hashed)
        test_filename = '{}.json'.format(hashed)

        try:
            self._block_blob_service.create_blob_from_text(container, template_filename, template_file)
            self._block_blob_service.create_blob_from_text(container, test_filename, test_file)
        except Exception:
            return '', 2

        return hashed, 0

    def get_tests_from_azure(self, test_key):
        containers = ['template_code', 'test_cases', 'expected_responses']

        self.create_containers_not_exist(containers)
        data = self.get_data_from_blobs(containers, test_key)

        return data[0], data[1], data[2]

    def save_code_to_azure(self, container, image_container, key, code):
        """
        Saves the fixed code to Azure Blob storage as text if the image exists in the pictures container. Will overwrite
        the previous version if if exists.

        :param container: Destination container of the code
        :param image_container: Destination container where images should be found
        :param key: Key under which it should be saves, is the same as the key of the image
        :param code: Fixed code by used
        :return:
        """

        if not self._block_blob_service.exists(image_container, key):
            raise ValueError('Cannot save code for an image which does not exist')

        self.create_container_not_exists(container)
        self._block_blob_service.create_blob_from_text(container, key, code)
