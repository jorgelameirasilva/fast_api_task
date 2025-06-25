import os
import queue
import threading
import time
import logging
from logging.handlers import QueueHandler, QueueListener

from pythonjsonlogger import jsonlogger


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
        self.blob_client = None  # Initialize blob_client attribute

        # Initialize blob client
        self._init_blob_client()

        self._flush_thread = threading.Thread(
            target=self._flush_periodically, daemon=True
        )
        self._flush_thread.start()

    def _init_blob_client(self):
        """Initialize the blob client"""
        try:
            # Import here to avoid circular imports
            from app.core.setup import get_blob_client_for_logging

            blob_container_client = get_blob_client_for_logging()
            self.blob_client = blob_container_client.get_blob_client(self.blob_name)

            try:
                self.blob_client.create_append_blob()
            except Exception:
                # Blob already exists
                pass
        except Exception as e:
            print(f"Failed to initialize blob client: {e}")
            self.blob_client = None

    def emit(self, record):
        msg = self.format(record) + "\n"
        with self._lock:
            self.batch.append(msg)
            if len(self.batch) >= self.batch_size:
                self._flush_batch()

    def _flush_batch(self):
        if self.batch and self.blob_client:
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
    # Configure logging level based on environment (matches old app.py)
    # Level should be one of https://docs.python.org/3/library/logging.html#logging-levels
    default_level = "INFO"  # In development, log more verbosely
    from app.core.config import settings

    if settings.WEBSITE_HOSTNAME:  # In production, don't log as heavily
        default_level = "WARNING"

    # Set up basic logging configuration
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=getattr(logging, default_level),
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

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
