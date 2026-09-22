from decimal import Decimal, DecimalException, ROUND_HALF_UP, localcontext
from math import isfinite


def calculate_payable_amount(supported_amounts: list[object] | None, deductible: object) -> int | float | None:
    """Arithmetic only: finite nonnegative currency, rounded once to cents."""
    if not isinstance(supported_amounts, (list, tuple)):
        return None
    values = [*supported_amounts, deductible]
    if any(type(value) not in (int, float, Decimal) for value in values):
        return None
    try:
        decimals = [Decimal(str(value)) for value in values]
        if any(not value.is_finite() or value < 0 for value in decimals):
            return None
        with localcontext() as context:
            context.prec = 38
            payable = max(sum(decimals[:-1], Decimal(0)) - decimals[-1], Decimal(0))
            payable = payable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result = float(payable)
        if not isfinite(result) or Decimal(str(result)) != payable:
            return None
        return int(payable) if payable == payable.to_integral_value() else result
    except (DecimalException, ValueError, OverflowError):
        return None
