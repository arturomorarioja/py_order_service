from app.db import connect


class TestData:
    def __init__(self, database_path):
        self.database_path = database_path

    def customer(self, customer_id=1, name="Test Customer", credit_limit_cents=10000):
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO customers (id, name, credit_limit_cents)
                VALUES (?, ?, ?)
                """,
                (customer_id, name, credit_limit_cents),
            )
        return customer_id

    def product(self, sku="TEST-SKU", name="Test Product", stock_on_hand=10, price_cents=1200):
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO products (sku, name, stock_on_hand, price_cents)
                VALUES (?, ?, ?, ?)
                """,
                (sku, name, stock_on_hand, price_cents),
            )
        return sku
