from django.urls import path

from . import views

urlpatterns = [
    path("", views.WarehouseListView.as_view(), name="warehouse-list"),
    path("new/", views.WarehouseCreateView.as_view(), name="warehouse-create"),
    path("<int:pk>/", views.WarehouseDetailView.as_view(), name="warehouse-detail"),
    path("<int:pk>/edit/", views.WarehouseUpdateView.as_view(), name="warehouse-update"),
]