import unittest

from app.services.settlement_calculator import calculate_payable_amount


class SettlementCalculatorTests(unittest.TestCase):
    def test_subtracts_known_deductible_from_all_supported_amounts(self):
        self.assertEqual(
            calculate_payable_amount([30000, 18000, 6000], 5000),
            49000,
        )

    def test_returns_none_when_a_supported_amount_is_unknown(self):
        self.assertIsNone(calculate_payable_amount([30000, None], 5000))

    def test_returns_none_when_deductible_is_unknown(self):
        self.assertIsNone(calculate_payable_amount([30000], None))

