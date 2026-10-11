from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Audit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_entries"
    )
    action = models.CharField(max_length=64)
    table_name = models.CharField(max_length=64, blank=True)
    record_id = models.CharField(max_length=64, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit"
        ordering = ["-created_at"]
        verbose_name = "audit"
        verbose_name_plural = "audit"

    def __str__(self):
        who = self.user.username if self.user else "system"
        return f"{self.created_at:%Y-%m-%d %H:%M} {who} {self.action}"

    def save(self, *args, **kwargs):
        if self.pk and Audit.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit history cannot be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit history cannot be deleted.")


def log_audit(*, user, action, description, table_name="", record_id=""):
    Audit.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        table_name=table_name,
        record_id=str(record_id) if record_id != "" else "",
        description=description,
    )
