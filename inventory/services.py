from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import log_audit, Audit

from .models import InventoryTransaction, Stock, StockLedger
from operations.models import InboundLine, InboundReceipt, InboundShipment, OutboundOrder


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
            # receive_stock(txn, user)
            _apply_delta(product=txn.product, warehouse=txn.warehouse, quantity=txn.quantity, txn=txn, user=user)
        elif txn.transaction_type == InventoryTransaction.Type.OUT:
            # pick_stock(txn, user)
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

def receive_inbound_line(*, shipment_id, line_id, quantity, location, user):
    with transaction.atomic():
        shipment = InboundShipment.objects.select_for_update().get(pk=shipment_id)
        line = InboundLine.objects.select_for_update().select_related("product").get(
            pk=line_id, shipment=shipment
        )

        if shipment.status in {InboundShipment.Status.COMPLETED, InboundShipment.Status.CANCELLED}:
            raise ValidationError("This inbound can no longer receive products.")
        if quantity <= 0:
            raise ValidationError("Received quantity must be greater than zero.")
        if quantity > line.remaining():
            raise ValidationError("Cannot receive more than the remaining expected quantity.")
        if location.warehouse_id != shipment.warehouse_id or not location.is_active:
            raise ValidationError("Putaway location must be active and belong to this warehouse.")

        txn = InventoryTransaction.objects.create(
            transaction_type=InventoryTransaction.Type.IN,
            warehouse=shipment.warehouse,
            product=line.product,
            quantity=quantity,
            notes=f"Received against inbound {shipment.number}, line {line.pk}.",
            created_by=user,
        )
        post_inventory_transaction(txn, user)

        receipt = InboundReceipt.objects.create(
            line=line,
            inventory_transaction=txn,
            quantity=quantity,
            putaway_location=location,
            received_by=user,
        )
        line.received_qty += quantity
        line.putaway_location = location
        line.save(update_fields=["received_qty", "putaway_location"])
        if shipment.status == InboundShipment.Status.DRAFT:
            shipment.status = InboundShipment.Status.RECEIVING
            shipment.save(update_fields=["status"])

    return receipt


def create_inbound_transaction(
    warehouse, expected_date, notes, supplier_name, user
):
    inbound, _ = InboundShipment.objects.get_or_create(
        warehouse=warehouse,
        status=InboundShipment.Status.DRAFT,
        expected_date=expected_date,
        notes=notes,
        created_by=user,
        supplier_name=supplier_name,
    )
    
    log_audit(
        user=user,
        action=Audit.Action.CREATE,
        table_name="InboundShipment",
        record_id=inbound.pk,
        description=f"Created {inbound.number}",
    )

def create_outbound_transaction(
    warehouse, required_date, notes, customer_name, user
):
    outbound, _ = OutboundOrder.objects.get_or_create(
        warehouse=warehouse,
        status=OutboundOrder.Status.DRAFT,
        required_date=required_date,
        notes=notes,
        created_by=user,
        customer_name=customer_name,
    )
    
    log_audit(
        user=user,
        action=Audit.Action.CREATE,
        table_name="OutboundOrder",
        record_id=outbound.pk,
        description=f"Created {outbound.number}",
    )