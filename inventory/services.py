from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import log_audit, Audit

from .models import InventoryTransaction, Stock, StockLedger


def _locked_stock(product, warehouse):
    Stock.objects.get_or_create(product=product, warehouse=warehouse, defaults={"quantity": 0})
    return Stock.objects.select_for_update().get(product=product, warehouse=warehouse)


def _lock_stocks_in_order(*pairs):
    """Acquire row locks in a stable order so opposite transfers cannot deadlock."""
    unique = {(product.pk, warehouse.pk): (product, warehouse) for product, warehouse in pairs}
    for _, (product, warehouse) in sorted(unique.items()):
        _locked_stock(product, warehouse)


def _apply_delta(*, product, warehouse, quantity, txn, user):
    stock = _locked_stock(product, warehouse)
    new_qty = stock.quantity + quantity
    if new_qty < 0:
        raise ValidationError(
            f"Insufficient stock for {product} at {warehouse.code}. Available: {stock.quantity}."
        )
    stock.quantity = new_qty
    stock.save(update_fields=["quantity", "updated_at"])
    StockLedger.objects.create(
        product=product,
        warehouse=warehouse,
        quantity=quantity,
        balance_after=new_qty,
        inventory_transaction=txn,
        created_by=user,
    )
    return stock


def post_inventory_transaction(txn, user):
    # check if transaction already posted
    if txn.status == InventoryTransaction.Status.POSTED:
        raise ValidationError("This transaction is already posted.")
    if txn.status == InventoryTransaction.Status.CANCELLED:
        raise ValidationError("This transaction is cancelled and cannot be posted.")
    # check if warehouse opname is happening at the moment
    warehouse = txn.warehouse
    if warehouse.is_opname and not user.is_superuser:
        raise ValidationError("This transaction belongs to a warehouse undergoing stock opname")
    # check if destination warehouse opname is happening at the moment
    destination_warehouse = txn.destination_warehouse
    if destination_warehouse:
        if destination_warehouse.is_opname and not user.is_superuser:
            raise ValidationError("This transaction belongs to a warehouse undergoing stock opname")
        
    
    txn.clean()
    with transaction.atomic():
        txn = InventoryTransaction.objects.select_for_update().get(pk=txn.pk)
        if txn.status == InventoryTransaction.Status.POSTED:
            raise ValidationError("This transaction is already posted.")

        if txn.transaction_type == InventoryTransaction.Type.IN:
            receive_stock(txn, user)
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.OUT:
            pick_stock(txn, user)
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=-txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.ADJUST:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.TRANSFER:
            _lock_stocks_in_order(
                (txn.product, txn.warehouse),
                (txn.product, txn.destination_warehouse),
            )
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=-txn.quantity, txn=txn, user=user)
            _apply_delta(
                product=txn.product,
                warehouse=txn.destination_warehouse,
                quantity=txn.quantity,
                txn=txn,
                user=user,
            )

        txn.status = InventoryTransaction.Status.POSTED
        txn.posted_at = timezone.now()
        super(InventoryTransaction, txn).save(update_fields=["status", "posted_at"])

    log_audit(
        user=user,
        action=Audit.Action.POST,
        table_name="InventoryTransaction",
        record_id=txn.pk,
        description=f"Posted {txn.number} ({txn.get_transaction_type_display()}) {txn.quantity} {txn.product.unit} of {txn.product.name}",
    )
    return txn

def pick_stock(txn, user):
    pass

def receive_stock(txn, user):
    pass