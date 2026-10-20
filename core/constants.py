from enum import Enum

class MeasurementUnit(Enum):
    
    # in EA or PCS
    EA = ("ea", "Each", 1.0)
    PK = ("pk", "Pack", 6.0)
    CS = ("cs", "Case", 24.0)
    PLT = ("plt", "Pallet", 1200.0)
    
    def __init__(self, symbol, label, to_each):
        self.symbol = symbol
        self.label = label
        self.to_each = to_each

    def convert_to(self, value: float, target_unit: 'MeasurementUnit') -> float:
        # Step 1: Convert the value to the base unit (Each)
        value_in_each = value * self.to_each
        # Step 2: Convert from each to the target unit
        return value_in_each / target_unit.to_each