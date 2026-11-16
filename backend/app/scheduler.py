import os
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from app.database import SessionLocal
from app.models import Complaint, Status
from app.services.escalation import process_sla_complaint
from app.services.notify import dispatch_pending, retry_failed
from app.services.sla import classify_sla


def run_sla_cycle():
    """Process eligible complaints in bounded, keyset-paginated batches."""

    batch_size = max(50, int(os.getenv("SLA_SCHEDULER_BATCH_SIZE", "500")))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last_id = 0
    processed_count = 0
    warning_count = 0
    escalation_count = 0

    while True:
        db = SessionLocal()
        try:
            batch_ids = [
                row.id
                for row in (
                    db.query(Complaint.id)
                    .filter(
                        Complaint.id > last_id,
                        Complaint.sla_deadline.isnot(None),
                        Complaint.is_archived.is_(False),
                        Complaint.sla_paused_at.is_(None),
                        Complaint.status.notin_([Status.RESOLVED, Status.CLOSED]),
                    )
                    .order_by(Complaint.id.asc())
                    .limit(batch_size)
                    .all()
                )
            ]
            if not batch_ids:
                break

            complaints = (
                db.query(Complaint)
                .filter(Complaint.id.in_(batch_ids))
                .order_by(Complaint.id.asc())
                .all()
            )

            for complaint in complaints:
                complaint.sla_status = classify_sla(
                    complaint.created_at,
                    complaint.sla_deadline,
                    now,
                )
                result = process_sla_complaint(db, complaint, now)
                processed_count += 1
                warning_count += int(result["warning_sent"])
                escalation_count += int(result["escalated"])

            db.commit()
            last_id = batch_ids[-1]
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    print(
        f"[SLA Scheduler] {now} | "
        f"Processed: {processed_count} | "
        f"Warnings: {warning_count} | "
        f"Escalations: {escalation_count} | "
        f"Batch size: {batch_size}"
    )


def run_notification_cycle():
    """Dispatch pending notifications and retry failures whose backoff expired."""
    db = SessionLocal()
    try:
        batch_size = max(1, int(os.getenv("NOTIFICATION_BATCH_SIZE", "100")))
        retried = retry_failed(db, limit=batch_size)
        remaining = max(0, batch_size - retried["attempted"])
        pending = (
            dispatch_pending(db, limit=remaining)
            if remaining
            else {"attempted": 0, "sent": 0, "failed": 0}
        )
        result = {
            key: retried[key] + pending[key] for key in ("attempted", "sent", "failed")
        }
        print(
            f"[Notification Scheduler] Attempted: {result['attempted']} | "
            f"Sent: {result['sent']} | Failed: {result['failed']}"
        )
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_sla_cycle,
        trigger="interval",
        minutes=15,
        next_run_time=datetime.now(timezone.utc),
        id="sla_escalation_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_notification_cycle,
        trigger="interval",
        minutes=1,
        next_run_time=datetime.now(timezone.utc),
        id="notification_outbox_job",
        max_instances=1,
        coalesce=True,
    )
    print("SLA and notification schedulers started. Notification interval: 1 minute.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
