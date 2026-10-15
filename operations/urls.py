from django.urls import path

from . import views

urlpatterns = [
    path("inbound/", views.InboundListView.as_view(), name="inbound-list"),
    path("inbound/new/", views.InboundCreateView.as_view(), name="inbound-create"),
    path("inbound/<int:pk>/", views.InboundDetailView.as_view(), name="inbound-detail"),
    path("inbound/<int:pk>/lines/", views.InboundAddLineView.as_view(), name="inbound-add-line"),
    path("inbound/<int:pk>/lines/<int:line_id>/receive/", views.InboundReceiveLineView.as_view(), name="inbound-receive-line"),
    path("inbound/<int:pk>/complete/", views.InboundCompleteView.as_view(), name="inbound-complete"),
    path("outbound/", views.OutboundListView.as_view(), name="outbound-list"),
    path("outbound/new/", views.OutboundCreateView.as_view(), name="outbound-create"),
    path("outbound/<int:pk>/", views.OutboundDetailView.as_view(), name="outbound-detail"),
    path("outbound/<int:pk>/lines/", views.OutboundAddLineView.as_view(), name="outbound-add-line"),
    path("outbound/<int:pk>/lines/<int:line_id>/pick/", views.OutboundPickLineView.as_view(), name="outbound-pick-line"),
    path("outbound/<int:pk>/ship/", views.OutboundShipView.as_view(), name="outbound-ship"),
]