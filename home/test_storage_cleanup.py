from django.test import SimpleTestCase

from home.storage_cleanup import StoragePressureError, calculate_storage_pressure


class StoragePressureTests(SimpleTestCase):
    def test_at_or_above_floor_needs_no_cleanup(self):
        result = calculate_storage_pressure(total_bytes=100, free_bytes=20)
        self.assertFalse(result.pressured)
        self.assertEqual(result.cleanup_bytes, 0)

    def test_calculates_only_the_gap_to_the_free_space_floor(self):
        result = calculate_storage_pressure(total_bytes=1000, free_bytes=150)
        self.assertTrue(result.pressured)
        self.assertEqual(result.cleanup_bytes, 50)

    def test_rejects_inconsistent_statistics_without_side_effects(self):
        for total, free in ((0, 0), (100, -1), (100, 101), (True, 1), (100, False)):
            with self.subTest(total=total, free=free):
                with self.assertRaises(StoragePressureError):
                    calculate_storage_pressure(total_bytes=total, free_bytes=free)
