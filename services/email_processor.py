"""Process inbound disclosure emails through the AEGIS analysis pipeline."""
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from typing import List, Optional, Tuple

from core.file_parser import FileParser
from services.email_client import SmtpClient, extract_sender_address
from services.email_config import EmailConfig
from services.email_job_store import EmailJobStore, JobStatus

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    success: bool
    should_reply: bool
    body: str
    attachment_bytes: Optional[bytes] = None
    attachment_filename: Optional[str] = None
    error_message: Optional[str] = None
    job_id: Optional[str] = None


class EmailProcessor:
    def __init__(
        self,
        config: EmailConfig,
        store: EmailJobStore,
        analysis_semaphore: asyncio.Semaphore,
    ):
        self.config = config
        self.store = store
        self.semaphore = analysis_semaphore
        self.smtp = SmtpClient(config)

    async def retry_job(self, job_id: str) -> ProcessResult:
        job = self.store.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if not job.raw_email_bytes:
            raise ValueError("Original email not available for retry")
        self.store.reset_for_retry(job_id)
        return await self.process_email(job.raw_email_bytes)

    async def process_email(self, raw_email: bytes) -> ProcessResult:
        msg = message_from_bytes(raw_email)
        message_id = msg.get("Message-ID", "")
        sender = extract_sender_address(raw_email)
        subject = msg.get("Subject", "")

        job = self.store.create_job(
            message_id=message_id,
            sender=sender,
            subject=subject,
            attachment_count=self._count_attachments(msg),
            raw_email_bytes=raw_email,
        )

        if self._sender_over_limit(sender):
            error = f"Daily limit of {self.config.sender_daily_limit} emails exceeded."
            self.store.update_status(job.id, JobStatus.QUARANTINED, error_message=error)
            body = self._failure_body(subject, error)
            if not self.config.dry_run:
                self._send_reply(sender, f"AEGIS Disclosure Analysis: {subject}", body, b"", "")
            else:
                logger.info("[DRY RUN] Would send failure reply to %s: %s", sender, error)
            return ProcessResult(
                success=False,
                should_reply=True,
                body=body,
                error_message=error,
                job_id=job.id,
            )

        try:
            self.store.update_status(job.id, JobStatus.PARSING)
            text, attachments = self._extract_content(msg)

            supported = any(
                Path(filename).suffix.lower() in FileParser.SUPPORTED_TYPES
                for filename, _ in attachments
            )
            if not text.strip() and not supported:
                error = "No usable disclosure content found. Please attach a PDF, DOCX, or paste the disclosure text."
                self.store.update_status(job.id, JobStatus.FAILED, error_message=error)
                body = self._failure_body(subject, error)
                if not self.config.dry_run:
                    self._send_reply(sender, f"AEGIS Disclosure Analysis: {subject}", body, b"", "")
                else:
                    logger.info("[DRY RUN] Would send failure reply to %s: %s", sender, error)
                return ProcessResult(
                    success=False,
                    should_reply=True,
                    body=body,
                    error_message=error,
                    job_id=job.id,
                )

            collection_name = f"temp_session_email_{job.id}"
            try:
                self._ingest_text(text, attachments, collection_name)
            except ValueError as exc:
                if "No parseable disclosure content found" in str(exc):
                    error = "No usable disclosure content found. Please attach a PDF, DOCX, or paste the disclosure text."
                    self.store.update_status(job.id, JobStatus.FAILED, error_message=error)
                    body = self._failure_body(subject, error)
                    if not self.config.dry_run:
                        self._send_reply(sender, f"AEGIS Disclosure Analysis: {subject}", body, b"", "")
                    else:
                        logger.info("[DRY RUN] Would send failure reply to %s: %s", sender, error)
                    return ProcessResult(
                        success=False,
                        should_reply=True,
                        body=body,
                        error_message=error,
                        job_id=job.id,
                    )
                raise

            self.store.update_status(job.id, JobStatus.ANALYSING)
            analysis_result = await self._run_analysis(text, collection_name)

            report_bytes, report_ext = self._build_report(analysis_result, job.id)
            filename = f"AEGIS_Disclosure_Analysis_{job.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{report_ext}"
            result_path = self._save_report(report_bytes, filename)

            reply_body = self._success_body(subject)
            if self.config.dry_run:
                logger.info(
                    "[DRY RUN] Would reply to %s with subject %s and attachment %s",
                    sender,
                    subject,
                    filename,
                )
            else:
                self._send_reply(
                    sender,
                    f"AEGIS Disclosure Analysis: {subject}",
                    reply_body,
                    report_bytes,
                    filename,
                )

            self.store.update_status(
                job.id, JobStatus.COMPLETED, result_path=result_path
            )

            return ProcessResult(
                success=True,
                should_reply=False,
                body=reply_body,
                attachment_bytes=report_bytes,
                attachment_filename=filename,
                job_id=job.id,
            )

        except Exception as exc:
            error = str(exc)
            self.store.increment_retry(job.id, error)
            job = self.store.get_job(job.id)
            if job.retry_count >= self.config.max_retries:
                self.store.update_status(job.id, JobStatus.QUARANTINED, error_message=error)
                user_message = "Analysis failed after multiple attempts. Please try again later or contact support."
                body = self._failure_body(subject, user_message)
                if not self.config.dry_run:
                    self._send_reply(sender, f"AEGIS Disclosure Analysis: {subject}", body, b"", "")
                else:
                    logger.info("[DRY RUN] Would send failure reply to %s", sender)
                return ProcessResult(
                    success=False,
                    should_reply=True,
                    body=body,
                    error_message=error,
                    job_id=job.id,
                )
            return ProcessResult(
                success=False,
                should_reply=False,
                body="",
                error_message=error,
                job_id=job.id,
            )

    def _count_attachments(self, msg: Message) -> int:
        count = 0
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                count += 1
        return count

    def _extract_content(self, msg: Message) -> Tuple[str, List[Tuple[str, bytes]]]:
        body_text = ""
        attachments: List[Tuple[str, bytes]] = []
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                filename = part.get_filename() or f"attachment_{len(attachments)}"
                payload = part.get_payload(decode=True)
                if payload:
                    attachments.append((filename, payload))
            elif content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_text += payload.decode("utf-8", errors="ignore")
            elif content_type == "text/html" and not body_text:
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode("utf-8", errors="ignore")
                    body_text = self._html_to_text(html)
        return body_text, attachments

    @staticmethod
    def _html_to_text(html: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _sender_over_limit(self, sender: str) -> bool:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        count = self.store.get_sender_count_since(sender, since)
        return count > self.config.sender_daily_limit

    def _ingest_text(
        self,
        text: str,
        attachments: List[Tuple[str, bytes]],
        collection_name: str,
    ) -> None:
        from core.rag_engine import NZLegalRAG

        parser = FileParser()
        all_text = [text] if text.strip() else []
        for filename, data in attachments:
            if len(data) > self.config.max_attachment_bytes:
                continue
            try:
                doc = parser.parse_file(data, filename)
                all_text.append(f"=== {filename} ===\n{doc.content}")
            except Exception:
                continue
        combined = "\n\n".join(all_text)
        if not combined.strip():
            raise ValueError("No parseable disclosure content found.")

        db_path = os.getenv("CHROMA_DB_PATH", os.getenv("CHROMADB_PATH", "./chroma_db"))
        embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        llm_model = os.getenv("LLM_MODEL", "deepseek-r1")
        engine = NZLegalRAG(
            db_path=db_path,
            embedding_model=embedding_model,
            llm_model=llm_model,
            use_local_llm=True,
        )
        engine.ingest_text(
            text=combined,
            collection_name=collection_name,
            metadata={"source": "email_bridge"},
        )

    async def _run_analysis(self, text: str, collection_name: str) -> dict:
        from core.rag_engine import NZLegalRAG
        from core.rag_integration import create_swarm_rag

        async with self.semaphore:
            db_path = os.getenv("CHROMA_DB_PATH", os.getenv("CHROMADB_PATH", "./chroma_db"))
            embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
            llm_model = os.getenv("LLM_MODEL", "deepseek-r1")
            engine = NZLegalRAG(
                db_path=db_path,
                embedding_model=embedding_model,
                llm_model=llm_model,
                use_local_llm=True,
            )
            swarm = create_swarm_rag(engine)
            try:
                result = swarm.analyse_disclosure(
                    text, extra_collections=[collection_name]
                )
            finally:
                try:
                    from core.agent_swarm import ollama_unload_model
                    model = getattr(
                        getattr(swarm, "swarm", None), "llm_client", None
                    )
                    model_name = getattr(model, "model", os.getenv("LLM_MODEL", "deepseek-r1"))
                    if ollama_unload_model is not None:
                        await asyncio.to_thread(ollama_unload_model, model_name)
                except Exception:
                    pass
            return result

    def _build_report(self, analysis_result: dict, job_id: str) -> Tuple[bytes, str]:
        from core.report_export import build_docx, build_pdf

        try:
            docx_io = build_docx(analysis_result)
            return docx_io.getvalue(), "docx"
        except Exception as exc:
            try:
                pdf_io = build_pdf(analysis_result)
                return pdf_io.getvalue(), "pdf"
            except Exception:
                text = analysis_result.get("executive_summary", "Analysis complete.")
                return text.encode("utf-8"), "txt"

    def _save_report(self, report_bytes: bytes, filename: str) -> str:
        output_dir = Path("tenant_data/email_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        path.write_bytes(report_bytes)
        return str(path)

    def _send_reply(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> None:
        self.smtp.send_reply(to_address, subject, body, attachment_bytes, attachment_filename)

    def _success_body(self, original_subject: str) -> str:
        return (
            "Thank you for using AEGIS.\n\n"
            f"Your disclosure \"{original_subject}\" has been analysed and the brief is attached.\n\n"
            "DISCLAIMER: This analysis is generated by AI and does not constitute legal advice. "
            "Consult a qualified barrister."
        )

    def _failure_body(self, original_subject: str, reason: str) -> str:
        return (
            "Thank you for using AEGIS.\n\n"
            f"We could not analyse your disclosure \"{original_subject}\": {reason}\n\n"
            "Please ensure you attach a supported file (PDF, DOCX, DOC, TXT, XLSX, HTML, MD, CSV, JSON) "
            "or paste the disclosure text in the email body.\n\n"
            "DISCLAIMER: This message is generated by AI and does not constitute legal advice."
        )

    async def process_batch(self, raw_emails: List[bytes]) -> List[ProcessResult]:
        results = []
        for raw in raw_emails:
            try:
                results.append(await self.process_email(raw))
            except Exception as exc:
                results.append(
                    ProcessResult(
                        success=False,
                        should_reply=False,
                        body="",
                        error_message=str(exc),
                    )
                )
        return results
