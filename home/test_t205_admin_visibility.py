from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from home.admin import MaintenanceJobAdmin
from home.models import MaintenanceJob


class ScheduledTaskAdminVisibilityTests(TestCase):
    def setUp(self):
        self.admin = MaintenanceJobAdmin(MaintenanceJob, django_admin.site)
        self.factory = RequestFactory()
        self.staff = get_user_model().objects.create_user(
            username="scheduled-task-admin",
            password="test-password-123",
            is_staff=True,
            is_active=True,
        )
        permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(MaintenanceJob),
            codename="view_maintenancejob",
        )
        self.staff.user_permissions.add(permission)
        MaintenanceJob.objects.create(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="UTC",
            enabled=False,
        )

    def test_staff_without_explicit_view_permission_cannot_open_surface(self):
        ungranted = get_user_model().objects.create_user(
            username="ungranted-scheduled-task-admin",
            password="test-password-123",
            is_staff=True,
            is_active=True,
        )
        request = self.request_for(ungranted)
        self.assertFalse(self.admin.has_module_permission(request))
        self.assertFalse(self.admin.has_view_permission(request))
        self.assertEqual(self.admin.get_queryset(request).count(), 0)

    def request_for(self, user=None):
        request = self.factory.get("/admin/home/maintenancejob/")
        if user is not None:
            request.user = user
        return request

    def test_active_staff_can_query_existing_records_without_mutation(self):
        request = self.request_for(self.staff)
        self.assertEqual(self.admin.get_queryset(request).count(), 1)
        self.assertFalse(self.admin.has_add_permission(request))
        self.assertFalse(self.admin.has_change_permission(request))
        self.assertFalse(self.admin.has_delete_permission(request))
        self.assertTrue(self.admin.has_module_permission(request))
        self.assertTrue(self.admin.has_view_permission(request))
        self.assertIn("owner", self.admin.list_display)
        self.assertEqual(
            set(self.admin.readonly_fields),
            {field.name for field in MaintenanceJob._meta.fields},
        )

    def test_inactive_or_non_staff_principals_are_hidden_fail_closed(self):
        inactive = get_user_model().objects.create_user(
            username="inactive-scheduled-task-admin",
            password="test-password-123",
            is_staff=True,
            is_active=False,
        )
        ordinary = get_user_model().objects.create_user(
            username="ordinary-scheduled-task-user",
            password="test-password-123",
            is_staff=False,
            is_active=True,
        )
        self.assertEqual(self.admin.get_queryset(self.request_for(inactive)).count(), 0)
        self.assertEqual(self.admin.get_queryset(self.request_for(ordinary)).count(), 0)
        self.assertEqual(self.admin.get_queryset(self.request_for()).count(), 0)
