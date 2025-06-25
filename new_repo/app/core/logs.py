import os
import queue
import threading
import time
import logging
from logging.handlers import QueueHandler, QueueListener

from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

from pythonjsonlogger import jsonlogger
from .config import settings


class BatchLogHandler(logging.Handler):
    def __init__(
        self, blob_name: str, batch_size: int = 10, flush_interval: float = 3.0
    ):
        super().__init__()
        self.blob_name = blob_name
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._lock = threading.Lock()
        self.batch = []
        self._closed = False

        self._flush_thread = threading.Thread(
            target=self._flush_periodically, daemon=True
        )
        self._flush_thread.start()

    def get_blob_client(self):
        blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
            credential=ClientSecretCredential(
                client_id=settings.AZURE_STORAGE_CLIENT_ID,
                client_secret=settings.AZURE_STORAGE_CLIENT_SECRET,
                tenant_id=settings.AZURE_SEARCH_TENANT_ID,
            ),
        )
        blob_container_client = blob_service_client.get_container_client(
            settings.DIAGNOSTICS_STORAGE_CONTAINER or settings.AZURE_STORAGE_CONTAINER
        )
        blob_client = blob_container_client.get_blob_client(self.blob_name)

        try:
            blob_client.create_append_blob()
        except Exception:
            # Blob already exists
            pass
        return blob_client

    def emit(self, record):
        msg = self.format(record) + "\n"
        with self._lock:
            self.batch.append(msg)
            if len(self.batch) >= self.batch_size:
                self._flush_batch()

    def _flush_batch(self):
        if self.batch:
            logs_to_write = "".join(self.batch)
            try:
                self.blob_client.append_block(logs_to_write.encode("utf-8"))
            except Exception as exc:
                print(f"Failed to write log batch to Azure Blob: {exc}")
            self.batch.clear()

    def _flush_periodically(self):
        while not self._closed:
            time.sleep(self.flush_interval)
            self.flush()

    def flush(self):
        with self._lock:
            self._flush_batch()

    def close(self):
        self._closed = True
        self._flush_thread.join()
        self.flush()
        super().close()


def setup_logging(blob_name):
    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)

    azure_handler = BatchLogHandler(
        blob_name=blob_name,
        batch_size=20,
        flush_interval=2.0,
    )

    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(message)s")
    azure_handler.setFormatter(formatter)

    listener = QueueListener(log_queue, azure_handler, respect_handler_level=True)
    listener.start()

    logger = logging.getLogger("quart.app")
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)

    sio = logging.StreamHandler()
    sio.setFormatter(formatter)
    logger.addHandler(sio)

    return logger, listener, azure_handler
