from inventory.models import InventoryTransaction


def nav_counts(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "draft_txn_count": InventoryTransaction.objects.filter(status=InventoryTransaction.Status.DRAFT).count(),
    }
