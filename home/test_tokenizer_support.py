"""Synthetic counter for tests that exercise other admission boundaries."""


class SyntheticCounter:
    model_id = "synthetic-counter"
    revision = "test-only"

    def count_upper_bound(self, serialized_input):
        return 100
