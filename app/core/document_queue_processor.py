"""Background document queue processor.

Polls for pending documents and processes them asynchronously.
Can be run as a standalone worker or triggered via API.
"""

import asyncio
import time
from typing import Any
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.db.document_uploads import (
    claim_document_for_processing,
    get_pending_documents,
    update_document_processing,
)
from app.graphs.document_processing_graph import process_document

logger = get_logger(__name__)

# Configuration
DEFAULT_BATCH_SIZE = 5
DEFAULT_POLL_INTERVAL = 5.0  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 30.0  # seconds


class DocumentQueueProcessor:
    """Background processor for document upload queue.

    Polls the database for pending documents and processes them
    through the document processing graph.
    """

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize the processor.

        Args:
            batch_size: Number of documents to fetch per batch
            poll_interval: Seconds between polling for new documents
            max_retries: Maximum retries for failed documents
        """
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self._running = False
        self._processed_count = 0
        self._error_count = 0
        self._start_time: float | None = None

    @property
    def stats(self) -> dict[str, Any]:
        """Get processor statistics."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "uptime_seconds": round(uptime, 1),
        }

    async def process_one(self, document_id: UUID) -> dict[str, Any]:
        """Process a single document.

        Args:
            document_id: Document UUID to process

        Returns:
            Processing result dict
        """
        run_id = uuid4()
        logger.info(
            f"Processing document {document_id}",
            extra={"document_id": str(document_id), "run_id": str(run_id)},
        )

        try:
            result = await process_document(document_id, run_id)

            if result.get("success"):
                self._processed_count += 1
                logger.info(
                    f"Document {document_id} processed successfully",
                    extra={
                        "document_id": str(document_id),
                        "run_id": str(run_id),
                        "signal_id": result.get("signal_id"),
                        "chunks": result.get("chunks_created"),
                    },
                )
            else:
                self._error_count += 1
                logger.error(
                    f"Document {document_id} processing failed: {result.get('error')}",
                    extra={
                        "document_id": str(document_id),
                        "run_id": str(run_id),
                    },
                )

            return result

        except Exception as e:
            self._error_count += 1
            logger.exception(
                f"Unexpected error processing document {document_id}: {e}",
                extra={"document_id": str(document_id), "run_id": str(run_id)},
            )
            return {
                "success": False,
                "document_id": str(document_id),
                "run_id": str(run_id),
                "error": str(e),
            }

    async def process_batch(self) -> list[dict[str, Any]]:
        """Process a batch of pending documents.

        Fetches pending documents and processes them sequentially.
        Uses atomic claim to prevent duplicate processing.

        Returns:
            List of processing results
        """
        # Get pending documents
        pending = get_pending_documents(limit=self.batch_size)

        if not pending:
            return []

        results = []

        for doc in pending:
            document_id = UUID(doc["id"])

            # Atomically claim the document
            claimed = claim_document_for_processing(document_id)

            if not claimed:
                # Already claimed by another worker
                logger.debug(f"Document {document_id} already claimed, skipping")
                continue

            # Process the document
            result = await self.process_one(document_id)
            results.append(result)

            # Small delay between documents to avoid overwhelming resources
            await asyncio.sleep(0.5)

        return results

    async def run_forever(self) -> None:
        """Run the processor continuously.

        Polls for documents and processes them until stopped.
        Call stop() to gracefully shutdown.
        """
        self._running = True
        self._start_time = time.time()

        logger.info(
            f"Starting document queue processor "
            f"(batch_size={self.batch_size}, poll_interval={self.poll_interval}s)"
        )

        while self._running:
            try:
                results = await self.process_batch()

                if results:
                    logger.info(
                        f"Processed batch of {len(results)} documents "
                        f"(total: {self._processed_count}, errors: {self._error_count})"
                    )
                else:
                    # No documents to process, wait before polling again
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.exception(f"Error in processing loop: {e}")
                await asyncio.sleep(self.poll_interval)

        logger.info("Document queue processor stopped")

    def stop(self) -> None:
        """Stop the processor gracefully."""
        logger.info("Stopping document queue processor...")
        self._running = False


# Global processor instance (for API control)
_processor: DocumentQueueProcessor | None = None


def get_processor() -> DocumentQueueProcessor:
    """Get or create the global processor instance."""
    global _processor
    if _processor is None:
        _processor = DocumentQueueProcessor()
    return _processor


async def process_pending_documents(
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Process pending documents (one-shot).

    This is the API-friendly version that processes one batch
    and returns immediately.

    Args:
        batch_size: Number of documents to process

    Returns:
        Dict with processing results
    """
    processor = DocumentQueueProcessor(batch_size=batch_size)
    results = await processor.process_batch()

    return {
        "processed": len(results),
        "successful": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }


async def process_single_document(document_id: UUID) -> dict[str, Any]:
    """Process a single document immediately.

    This bypasses the queue and processes the document directly.
    Useful for priority processing or retries.

    Args:
        document_id: Document UUID to process

    Returns:
        Processing result dict
    """
    processor = DocumentQueueProcessor()

    # Claim the document first
    claimed = claim_document_for_processing(document_id)

    if not claimed:
        return {
            "success": False,
            "document_id": str(document_id),
            "error": "Document is not pending or already claimed",
        }

    return await processor.process_one(document_id)
