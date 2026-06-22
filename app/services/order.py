from app.db import connect, row_to_dict


class OrderService:
    def __init__(self, database_path, stock_service, payment_service, invoice_service):
        self.database_path = database_path
        self.stock_service = stock_service
        self.payment_service = payment_service
        self.invoice_service = invoice_service

    def place_order(self, customer_id, sku, quantity):
        if not isinstance(quantity, int) or quantity <= 0:
            return {"ok": False, "reason": "quantity must be a positive integer"}

        product = self.stock_service.get_product(sku)
        if product is None:
            return {"ok": False, "reason": "unknown product"}

        total_cents = product["price_cents"] * quantity
        order_id = self._create_pending_order(customer_id, sku, quantity, total_cents)

        stock_result = self.stock_service.reserve(order_id, sku, quantity)
        if not stock_result["ok"]:
            self._fail_order(order_id, stock_result["reason"])
            return {"ok": False, "order_id": order_id, "reason": stock_result["reason"]}

        payment_result = self.payment_service.charge(order_id, customer_id, total_cents)
        if not payment_result["ok"]:
            self.stock_service.release(order_id)
            self._fail_order(order_id, payment_result["reason"])
            return {"ok": False, "order_id": order_id, "reason": payment_result["reason"]}

        invoice_result = self.invoice_service.create_invoice(order_id, customer_id, total_cents)
        self._complete_order(order_id, invoice_result["invoice_id"])

        return {
            "ok": True,
            "order_id": order_id,
            "invoice_id": invoice_result["invoice_id"],
            "total_cents": total_cents,
        }

    def get_order(self, order_id):
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT id, customer_id, sku, quantity, total_cents, status,
                       failure_reason, invoice_id, created_at
                FROM orders
                WHERE id = ?
                """,
                (order_id,),
            ).fetchone()
            return row_to_dict(row)

    def _create_pending_order(self, customer_id, sku, quantity, total_cents):
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO orders (customer_id, sku, quantity, total_cents, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (customer_id, sku, quantity, total_cents),
            )
            return cursor.lastrowid

    def _complete_order(self, order_id, invoice_id):
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE orders
                SET status = 'completed', invoice_id = ?
                WHERE id = ?
                """,
                (invoice_id, order_id),
            )

    def _fail_order(self, order_id, reason):
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE orders
                SET status = 'failed', failure_reason = ?
                WHERE id = ?
                """,
                (reason, order_id),
            )
