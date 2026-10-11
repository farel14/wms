from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import log_audit


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    log_audit(user=user, action="LOGIN", table_name="User", record_id=user.pk, description=f"{user.username} signed in")


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    log_audit(
        user=user,
        action="LOGOUT",
        table_name="User",
        record_id=getattr(user, "pk", ""),
        description=f"{getattr(user, 'username', 'unknown')} signed out",
    )


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", "")
    log_audit(user=None, action="LOGIN_FAILED", table_name="User", description=f"Failed sign-in for {username}")
