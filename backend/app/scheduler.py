from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from app.database import SessionLocal
from app.models import Complaint, SLAStatus, Status
from app.services.escalation import process_sla_complaint
from app.services.sla import classify_sla


def run_sla_cycle():
    """Process all eligible complaints for SLA warnings and escalation."""

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        complaints = (
            db.query(Complaint)
            .filter(
                Complaint.sla_deadline.isnot(None),
                Complaint.is_archived.is_(False),
                Complaint.sla_paused_at.is_(None),
                Complaint.status.notin_(
                    [Status.RESOLVED, Status.CLOSED]
                ),
            )
            .all()
        )

        warning_count = 0
        escalation_count = 0

        for complaint in complaints:
            complaint.sla_status = classify_sla(
                complaint.created_at,
                complaint.sla_deadline,
                now,
            )

            result = process_sla_complaint(
                db,
                complaint,
                now,
            )

            if result["warning_sent"]:
                warning_count += 1

            if result["escalated"]:
                escalation_count += 1

        db.commit()

        print(
            f"[SLA Scheduler] {now} | "
            f"Processed: {len(complaints)} | "
            f"Warnings: {warning_count} | "
            f"Escalations: {escalation_count}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":

    scheduler = BlockingScheduler(timezone="UTC")

    # Run once immediately, then every 15 minutes.
    scheduler.add_job(
        run_sla_cycle,
        trigger="interval",
        minutes=15,
        next_run_time=datetime.now(timezone.utc),
        id="sla_escalation_job",
        max_instances=1,
        coalesce=True,
    )

    print("SLA Scheduler started. Interval: 15 minutes.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()