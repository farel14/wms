from .models import Product

def convert_to_unit(value: float, source_unit: Product.MeasurementUnit, target_unit: Product.MeasurementUnit) -> float:
    # Step 1: Convert the value to the base unit (Each)
    value_in_each = value * Product.UNIT_TO_EACH.get(source_unit, 1.0)
    # Step 2: Convert from each to the target unit
    return value_in_each / Product.UNIT_TO_EACH.get(target_unit, 1.0)
