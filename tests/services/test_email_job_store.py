import os
import tempfile
import threading
import pytest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from services.email_job_store import EmailJobStore, JobStatus


class TestEmailJobStore:
    @pytest.fixture
    def store(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = EmailJobStore(path)
        yield store
        os.unlink(path)

    def test_create_and_get(self, store):
        job = store.create_job(
            message_id="<msg-1@example.com>",
            sender="client@example.com",
            subject="Disclosure",
            attachment_count=2,
            raw_email_bytes=b"raw-email",
        )
        assert job.status == JobStatus.RECEIVED
        fetched = store.get_job(job.id)
        assert fetched.message_id == "<msg-1@example.com>"
        assert fetched.sender == "client@example.com"
        assert fetched.raw_email_bytes == b"raw-email"

    def test_dedupe_by_message_id(self, store):
        job1 = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        job2 = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        assert job1.id == job2.id

    def test_update_status_and_list(self, store):
        job = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        store.update_status(job.id, JobStatus.COMPLETED, result_path="/tmp/x.docx")
        fetched = store.get_job(job.id)
        assert fetched.status == JobStatus.COMPLETED
        assert fetched.result_path == "/tmp/x.docx"
        jobs = store.list_jobs(status=JobStatus.COMPLETED)
        assert len(jobs) == 1

    def test_increment_retry(self, store):
        job = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        store.increment_retry(job.id, "boom")
        fetched = store.get_job(job.id)
        assert fetched.retry_count == 1
        assert "boom" in fetched.error_message

    def test_reset_for_retry(self, store):
        job = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        store.update_status(job.id, JobStatus.FAILED, error_message="boom")
        store.increment_retry(job.id, "boom")
        fetched = store.get_job(job.id)
        assert fetched.status == JobStatus.FAILED
        assert fetched.retry_count == 1

        store.reset_for_retry(job.id)
        fetched = store.get_job(job.id)
        assert fetched.status == JobStatus.RECEIVED
        assert fetched.retry_count == 0
        assert fetched.error_message is None

    def test_counts_and_sender_limit(self, store):
        today = datetime.now(timezone.utc)
        store.create_job("<m1>", "a@example.com", "X", 0, b"raw")
        store.create_job("<m2>", "a@example.com", "X", 0, b"raw")
        store.create_job("<m3>", "b@example.com", "X", 0, b"raw")
        assert store.get_sender_count_since("a@example.com", today - timedelta(days=1)) == 2
        assert store.get_counts()["total"] == 3

    def test_get_job_missing(self, store):
        assert store.get_job("non-existent-id") is None

    def test_get_job_by_message_id_missing(self, store):
        assert store.get_job_by_message_id("<non-existent>") is None

    def test_list_jobs_since(self, store):
        now = datetime.now(timezone.utc)
        store.create_job("<old>", "a@example.com", "Old", 0, b"raw")
        store.create_job("<new>", "a@example.com", "New", 0, b"raw")
        cutoff = now - timedelta(minutes=1)
        jobs = store.list_jobs(since=cutoff)
        assert len(jobs) == 2
        assert all(j.received_at >= cutoff for j in jobs)

        future_cutoff = now + timedelta(days=1)
        assert store.list_jobs(since=future_cutoff) == []

    def test_list_jobs_pagination(self, store):
        for i in range(5):
            store.create_job(f"<m{i}>", "a@example.com", "X", 0, b"raw")

        all_jobs = store.list_jobs()
        assert len(all_jobs) == 5

        page1 = store.list_jobs(limit=2, offset=0)
        page2 = store.list_jobs(limit=2, offset=2)
        page3 = store.list_jobs(limit=2, offset=4)
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

        ids = [j.id for j in all_jobs]
        assert [j.id for j in page1] == ids[0:2]
        assert [j.id for j in page2] == ids[2:4]
        assert [j.id for j in page3] == ids[4:5]

    def test_counts_initial_and_all_statuses(self, store):
        counts = store.get_counts()
        assert counts["total"] == 0
        for status in JobStatus:
            assert counts[status.value] == 0

        job = store.create_job("<m1>", "a@example.com", "X", 0, b"raw")
        store.update_status(job.id, JobStatus.FAILED)

        counts = store.get_counts()
        assert counts["failed"] == 1
        assert counts["received"] == 0
        assert counts["total"] == 1

    def test_update_status_preserves_result_path(self, store):
        job = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        store.update_status(job.id, JobStatus.COMPLETED, result_path="/tmp/x.docx")
        store.update_status(job.id, JobStatus.FAILED)
        fetched = store.get_job(job.id)
        assert fetched.status == JobStatus.FAILED
        assert fetched.result_path == "/tmp/x.docx"

    def test_update_status_missing_job(self, store):
        with pytest.raises(ValueError, match="not found"):
            store.update_status("non-existent-id", JobStatus.COMPLETED)

    def test_increment_retry_missing_job(self, store):
        with pytest.raises(ValueError, match="not found"):
            store.increment_retry("non-existent-id", "boom")

    def test_list_jobs_negative_limit_or_offset(self, store):
        with pytest.raises(ValueError, match="non-negative"):
            store.list_jobs(limit=-1)
        with pytest.raises(ValueError, match="non-negative"):
            store.list_jobs(offset=-1)

    def test_create_job_dedupe_concurrent(self, store):
        # Each thread tries to create a job with the same message_id.
        results = []
        lock = threading.Lock()

        def create():
            job = store.create_job("<dup>", "a@example.com", "X", 0, b"raw")
            with lock:
                results.append(job.id)

        with ThreadPoolExecutor(max_workers=4) as executor:
            for _ in range(8):
                executor.submit(create)

        unique_ids = set(results)
        assert len(unique_ids) == 1
