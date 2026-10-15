from django.urls import path

from . import views

urlpatterns = [
    path("stock/", views.StockListView.as_view(), name="stock-list"),
    path("ledger/", views.LedgerListView.as_view(), name="ledger-list"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction-list"),
    path("transactions/new/", views.TransactionCreateView.as_view(), name="transaction-create"),
    path("transactions/<int:pk>/", views.TransactionDetailView.as_view(), name="transaction-detail"),
    path("transactions/<int:pk>/post/", views.TransactionPostView.as_view(), name="transaction-post"),
]