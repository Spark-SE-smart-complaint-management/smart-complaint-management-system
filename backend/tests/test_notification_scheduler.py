from app import scheduler


class FakeSession:
    def __init__(self):
        self.closed = False
        self.rolled_back = False

    def close(self):
        self.closed = True

    def rollback(self):
        self.rolled_back = True


def test_notification_cycle_dispatches_due_rows_and_closes_session(monkeypatch):
    session = FakeSession()
    calls = []

    monkeypatch.setattr(scheduler, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        scheduler,
        "retry_failed",
        lambda db, limit: calls.append(("retry", db, limit))
        or {"attempted": 3, "sent": 2, "failed": 1},
    )
    monkeypatch.setattr(
        scheduler,
        "dispatch_pending",
        lambda db, limit: calls.append(("pending", db, limit))
        or {"attempted": 2, "sent": 2, "failed": 0},
    )
    monkeypatch.setenv("NOTIFICATION_BATCH_SIZE", "25")

    result = scheduler.run_notification_cycle()

    assert result == {"attempted": 5, "sent": 4, "failed": 1}
    assert calls == [("retry", session, 25), ("pending", session, 22)]
    assert session.closed
    assert not session.rolled_back


def test_notification_cycle_rolls_back_and_closes_on_error(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: session)

    def fail(_db, limit):
        raise RuntimeError("temporary database outage")

    monkeypatch.setattr(scheduler, "retry_failed", fail)
    monkeypatch.setattr(
        scheduler,
        "dispatch_pending",
        lambda _db, limit: {"attempted": 0, "sent": 0, "failed": 0},
    )

    try:
        scheduler.run_notification_cycle()
    except RuntimeError as exc:
        assert str(exc) == "temporary database outage"
    else:
        raise AssertionError("Expected notification cycle to propagate the error")

    assert session.rolled_back
    assert session.closed
