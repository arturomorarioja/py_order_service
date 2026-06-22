from app.db import connect, row_to_dict


class StockService:
    def __init__(self, database_path):
        self.database_path = database_path

    def get_product(self, sku):
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT sku, name, stock_on_hand, price_cents FROM products WHERE sku = ?",
                (sku,),
            ).fetchone()
            return row_to_dict(row)

    def reserve(self, order_id, sku, quantity):
        with connect(self.database_path) as connection:
            product = connection.execute(
                "SELECT stock_on_hand FROM products WHERE sku = ?",
                (sku,),
            ).fetchone()

            if product is None:
                return {"ok": False, "reason": "unknown product"}
            if product["stock_on_hand"] < quantity:
                return {"ok": False, "reason": "insufficient stock"}

            connection.execute(
                "UPDATE products SET stock_on_hand = stock_on_hand - ? WHERE sku = ?",
                (quantity, sku),
            )
            connection.execute(
                """
                INSERT INTO stock_reservations (order_id, sku, quantity, status)
                VALUES (?, ?, ?, 'reserved')
                """,
                (order_id, sku, quantity),
            )
            return {"ok": True}

    def release(self, order_id):
        with connect(self.database_path) as connection:
            reservation = connection.execute(
                """
                SELECT id, sku, quantity
                FROM stock_reservations
                WHERE order_id = ? AND status = 'reserved'
                """,
                (order_id,),
            ).fetchone()

            if reservation is None:
                return {"ok": True, "released": False}

            connection.execute(
                "UPDATE products SET stock_on_hand = stock_on_hand + ? WHERE sku = ?",
                (reservation["quantity"], reservation["sku"]),
            )
            connection.execute(
                "UPDATE stock_reservations SET status = 'released' WHERE id = ?",
                (reservation["id"],),
            )
            return {"ok": True, "released": True}
