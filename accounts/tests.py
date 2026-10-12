from django.test import TestCase
from django.contrib.auth.models import User
from .models import Audit, log_audit

# Create your tests here.

# CRUD User
class UserTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword")

    def test_create_user(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertTrue(self.user.check_password("testpassword"))

    def test_update_user(self):
        self.user.username = "newusername"
        self.user.save()
        self.assertEqual(self.user.username, "newusername")

    def test_delete_user(self):
        self.user.delete()
        self.assertFalse(User.objects.filter(username="testuser").exists())

# CRUD Audit
class AuditTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword")

    def test_login_audit(self):
        log_audit(
            user=self.user,
            action=Audit.Action.LOGIN,
            table_name="User",
            record_id=self.user.pk,
            description=f"{self.user.username} signed in",
        )
        audit = Audit.objects.filter(user=self.user).first()
        self.assertEqual(audit.action, Audit.Action.LOGIN)

    def test_logout_audit(self):
        log_audit(
            user=self.user,
            action=Audit.Action.LOGOUT,
            table_name="User",
            record_id=self.user.pk,
            description=f"{self.user.username} signed out",
        )
        audit = Audit.objects.filter(user=self.user).first()
        self.assertEqual(audit.action, Audit.Action.LOGOUT)
