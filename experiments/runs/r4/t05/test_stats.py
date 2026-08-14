import unittest

from stats import mean, median, mode, summary, variance


class TestMean(unittest.TestCase):
    def test_integer_average(self):
        self.assertEqual(mean([2, 4, 6]), 4)

    def test_fractional_average(self):
        self.assertAlmostEqual(mean([1, 2]), 1.5)

    def test_negative_values(self):
        self.assertAlmostEqual(mean([-3, 3, 1]), 1 / 3)


class TestMedian(unittest.TestCase):
    def test_unsorted_odd(self):
        self.assertEqual(median([5, 1, 3]), 3)

    def test_even_length(self):
        self.assertAlmostEqual(median([1, 2, 3, 4]), 2.5)

    def test_single(self):
        self.assertEqual(median([7]), 7)


class TestMode(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(mode([1, 1, 2]), 1)

    def test_empty_returns_none(self):
        self.assertIsNone(mode([]))

    def test_tie_returns_smallest(self):
        self.assertEqual(mode([2, 2, 1, 1]), 1)


class TestVariance(unittest.TestCase):
    def test_population_variance(self):
        self.assertAlmostEqual(variance([1, 2, 3, 4]), 1.25)


class TestSummary(unittest.TestCase):
    def test_keys(self):
        s = summary([1, 2, 2, 3])
        self.assertEqual(set(s), {"mean", "median", "mode", "variance"})
        self.assertAlmostEqual(s["mean"], 2.0)
        self.assertAlmostEqual(s["median"], 2.0)


if __name__ == "__main__":
    unittest.main()
