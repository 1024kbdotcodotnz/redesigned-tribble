"""Background poller for inbound disclosure emails."""
import asyncio
import logging
from typing import Optional

from services.email_client import ImapClient
from services.email_config import EmailConfig
from services.email_job_store import JobStatus
from services.email_processor import EmailProcessor

logger = logging.getLogger(__name__)


class EmailPoller:
    def __init__(
        self,
        config: EmailConfig,
        processor: EmailProcessor,
        imap_client: Optional[ImapClient] = None,
    ):
        self.config = config
        self.processor = processor
        self.imap_client = imap_client
        self._stop_event = asyncio.Event()

    async def poll_once(self) -> None:
        owns_client = self.imap_client is None
        client = self.imap_client or ImapClient(self.config)
        try:
            client.connect()
            fetched = client.fetch_unseen()
            if fetched:
                logger.info("Fetched %d unseen email(s)", len(fetched))
                raw_emails = [raw for _, raw in fetched]
                results = await self.processor.process_batch(raw_emails)
                if len(results) != len(fetched):
                    logger.error(
                        "process_batch returned %d results for %d emails",
                        len(results),
                        len(fetched),
                    )
                    raise RuntimeError("process_batch result count mismatch")
                for (msg_id, _), result in zip(fetched, results):
                    mark_seen = result.success
                    if (
                        not mark_seen
                        and result.should_reply
                        and result.job_id
                    ):
                        job = self.processor.store.get_job(result.job_id)
                        if job and job.status in (JobStatus.FAILED, JobStatus.QUARANTINED):
                            mark_seen = True
                    if mark_seen:
                        try:
                            client.mark_seen(msg_id)
                        except Exception as mark_exc:
                            logger.error("Failed to mark message %s seen: %s", msg_id, mark_exc)
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("Email poll failed: %s", exc)
        finally:
            if owns_client:
                client.disconnect()

    async def run(self) -> None:
        while not self._stop_event.is_set():
            if self.config.enabled:
                await self.poll_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._stop_event.set()


async def _email_poller_task(
    config: EmailConfig,
    processor: EmailProcessor,
) -> None:
    poller = EmailPoller(config, processor)
    await poller.run()


def start_email_poller(
    config: EmailConfig,
    processor: EmailProcessor,
) -> asyncio.Task:
    return asyncio.create_task(_email_poller_task(config, processor))
