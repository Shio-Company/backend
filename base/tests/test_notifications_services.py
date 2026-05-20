import pytest

from base.models.notifications import EmailLog
from base.services.notifications import NotificationService


@pytest.mark.django_db
def test_send_welcome_email_creates_sent_log():
    log = NotificationService.send(
        "WELCOME", "test@example.com", {"name": "Teste", "email": "test@example.com"}
    )
    assert log.status == EmailLog.Status.SENT
    assert EmailLog.objects.filter(recipient_email="test@example.com").exists()
    assert log.sent_at is not None


@pytest.mark.django_db
def test_send_unknown_template_raises():
    with pytest.raises(ValueError, match="Template desconhecido"):
        NotificationService.send("NONEXISTENT", "x@example.com", {})
