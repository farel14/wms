from inventory.models import InventoryTransaction


def nav_counts(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "draft_txn_count": InventoryTransaction.objects.filter(status=InventoryTransaction.Status.DRAFT).count(),
    }

def user_group_names(request):
    if request.user.is_authenticated:
        group_names = ", ".join(
            request.user.groups.values_list("name", flat=True)
        )
    else:
        group_names = ""

    return {"user_group_names": group_names}