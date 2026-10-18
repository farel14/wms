from django.urls import path

from . import views

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/new/", views.ProductCreateView.as_view(), name="product-create"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product-update"),
    path("products/<int:pk>/deactivate/", views.ProductDeactivateView.as_view(), name="product-deactivate"),
    path("products/<int:pk>/activate/", views.ProductActivateView.as_view(), name="product-activate"),
]