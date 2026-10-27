from inventory.models import InventoryTransaction
from operations.models import OutboundOrder, InboundShipment


def nav_counts(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "draft_txn_count": InventoryTransaction.objects.filter(status=InventoryTransaction.Status.DRAFT).count(),
        "draft_inbound_count": InboundShipment.objects.filter(status=InboundShipment.Status.DRAFT).count(),
        "draft_outbound_count": OutboundOrder.objects.filter(status=OutboundOrder.Status.DRAFT).count(),
    }

def user_group_names(request):
    if request.user.is_authenticated:
        group_names = ", ".join(
            request.user.groups.values_list("name", flat=True)
        )
    else:
        group_names = ""

    return {"user_group_names": group_names}