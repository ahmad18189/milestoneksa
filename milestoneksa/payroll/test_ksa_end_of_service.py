# Copyright (c) 2026, ahmed and Contributors

from frappe.tests import IntegrationTestCase

from milestoneksa.payroll.ksa_end_of_service import (
	SEPARATION_CONTRACT_EXPIRY,
	SEPARATION_RESIGNATION,
	compute_article_84_amount,
	compute_years_of_service,
	get_article_85_factor,
)


class TestKSAEndOfService(IntegrationTestCase):
	def test_article_84_three_years(self):
		self.assertEqual(compute_article_84_amount(10000, 3), 15000)

	def test_article_84_seven_years(self):
		self.assertEqual(compute_article_84_amount(10000, 7), 45000)

	def test_article_85_resignation_three_years(self):
		self.assertEqual(get_article_85_factor(3, SEPARATION_RESIGNATION), 1.0 / 3.0)

	def test_article_85_contract_expiry_full(self):
		self.assertEqual(get_article_85_factor(3, SEPARATION_CONTRACT_EXPIRY), 1.0)

	def test_article_85_resignation_under_two_years(self):
		self.assertEqual(get_article_85_factor(1.5, SEPARATION_RESIGNATION), 0.0)

	def test_years_of_service_exact_three_years(self):
		years = compute_years_of_service("2025-03-04", "2028-03-04")
		self.assertEqual(years, 3.0)

	def test_years_of_service_exact_two_years(self):
		years = compute_years_of_service("2025-03-04", "2027-03-04")
		self.assertEqual(years, 2.0)

	def test_years_of_service_deducts_unpaid_leave(self):
		years = compute_years_of_service("2025-01-01", "2026-01-01", unpaid_leave_days=10)
		self.assertAlmostEqual(years, 1.0 - (10 / 365.0), places=3)
