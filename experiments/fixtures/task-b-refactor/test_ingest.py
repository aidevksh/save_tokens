import unittest

from ingest import load_orders, load_products, load_users

USERS = [
    "# id, name, email",
    "1, Ada, ADA@example.com",
    "",
    "2, Grace, grace@example.com",
]

ORDERS = [
    "# id, user_id, sku, qty",
    "10, 1, ab-1, 3",
    "11, 2, cd-2, 1",
]

PRODUCTS = [
    "# sku, title, price",
    "ab-1, Widget, 9.99",
    "cd-2, Gadget, 100",
]


class TestLoaders(unittest.TestCase):
    def test_users(self):
        self.assertEqual(
            load_users(USERS),
            [
                {"id": 1, "name": "Ada", "email": "ada@example.com"},
                {"id": 2, "name": "Grace", "email": "grace@example.com"},
            ],
        )

    def test_orders(self):
        self.assertEqual(
            load_orders(ORDERS),
            [
                {"id": 10, "user_id": 1, "sku": "AB-1", "qty": 3},
                {"id": 11, "user_id": 2, "sku": "CD-2", "qty": 1},
            ],
        )

    def test_products(self):
        self.assertEqual(
            load_products(PRODUCTS),
            [
                {"sku": "AB-1", "title": "Widget", "price_cents": 999},
                {"sku": "CD-2", "title": "Gadget", "price_cents": 10000},
            ],
        )

    def test_wrong_field_count(self):
        with self.assertRaises(ValueError):
            load_users(["1, Ada"])

    def test_empty_field(self):
        with self.assertRaises(ValueError):
            load_users(["1, , ada@example.com"])


if __name__ == "__main__":
    unittest.main()
