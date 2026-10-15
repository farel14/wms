from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import log_audit, Audit

from .models import InventoryTransaction, Stock, StockLedger


def _locked_stock(product, warehouse):
    Stock.objects.get_or_create(product=product, warehouse=warehouse, defaults={"quantity": 0})
    return Stock.objects.select_for_update().get(product=product, warehouse=warehouse)


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
    if txn.status == InventoryTransaction.Status.POSTED:
        raise ValidationError("This transaction is already posted.")
    txn.clean()
    with transaction.atomic():
        txn = InventoryTransaction.objects.select_for_update().get(pk=txn.pk)
        if txn.status == InventoryTransaction.Status.POSTED:
            raise ValidationError("This transaction is already posted.")

        if txn.transaction_type == InventoryTransaction.Type.IN:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.OUT:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=-txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.ADJUST:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.TRANSFER:
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


def pick_stock(product, location, quantity, user, reference):
    # TODO fix pick_stock and receive_stock flow
    """product=line.product,
                    location=location,
                    quantity=qty,
                    user=request.user,
                    reference=order.number
                    
    _apply_delta -> inventory_transaction
    """
    
    if txn.status == InventoryTransaction.Status.POSTED:
        raise ValidationError("This transaction is already posted.")
    txn.clean()
    with transaction.atomic():
        txn = InventoryTransaction.objects.select_for_update().get(pk=txn.pk)
        if txn.status == InventoryTransaction.Status.POSTED:
            raise ValidationError("This transaction is already posted.")

        if txn.transaction_type == InventoryTransaction.Type.IN:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.OUT:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=-txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.ADJUST:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.TRANSFER:
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

def receive_stock(product, location, quantity, user, reference):
    """product=line.product,
                    location=location,
                    quantity=qty,
                    user=request.user,
                    reference=order.number"""
                    
    """
    update inboundshipment -> 
        change status to [RECEIVING = "RECEIVING", "Receiving"], received_at, 
    create inboundline -> 
        shipment = models.ForeignKey(InboundShipment, on_delete=models.CASCADE, related_name="lines")
        product = models.ForeignKey(Product, on_delete=models.PROTECT)
        expected_qty = models.PositiveIntegerField()
        received_qty = models.PositiveIntegerField(default=0)
        putaway_location = models.CharField(max_length=100, blank=True)
        
        def remaining(self):
            return max(self.expected_qty - self.received_qty, 0)
    add to inventory stock

    
    """
    
    
    
    # !==============
    
    if txn.status == InventoryTransaction.Status.POSTED:
        raise ValidationError("This transaction is already posted.")
    txn.clean()
    with transaction.atomic():
        txn = InventoryTransaction.objects.select_for_update().get(pk=txn.pk)
        if txn.status == InventoryTransaction.Status.POSTED:
            raise ValidationError("This transaction is already posted.")

        if txn.transaction_type == InventoryTransaction.Type.IN:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.OUT:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=-txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.ADJUST:
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.TRANSFER:
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