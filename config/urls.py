from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts.views import AuditListView, DashboardView, UserListView

admin.site.site_header = "Harbor WMS"
admin.site.site_title = "Harbor WMS"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", DashboardView.as_view(), name="dashboard"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("audit/", AuditListView.as_view(), name="audit-list"),
    path("warehouses/", include("warehouse.urls")),
    path("catalog/", include("catalog.urls")),
    path("inventory/", include("inventory.urls")),
]