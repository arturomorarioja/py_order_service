from app.db import connect


class PaymentService:
    def __init__(self, database_path):
        self.database_path = database_path

    def charge(self, order_id, customer_id, amount_cents):
        with connect(self.database_path) as connection:
            customer = connection.execute(
                "SELECT credit_limit_cents FROM customers WHERE id = ?",
                (customer_id,),
            ).fetchone()

            if customer is None:
                return self._record(
                    connection,
                    order_id,
                    customer_id,
                    amount_cents,
                    "declined",
                    "unknown customer",
                )

            if amount_cents > customer["credit_limit_cents"]:
                return self._record(
                    connection,
                    order_id,
                    customer_id,
                    amount_cents,
                    "declined",
                    "credit limit exceeded",
                )

            return self._record(connection, order_id, customer_id, amount_cents, "charged", None)

    def _record(self, connection, order_id, customer_id, amount_cents, status, reason):
        cursor = connection.execute(
            """
            INSERT INTO payments (order_id, customer_id, amount_cents, status, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, customer_id, amount_cents, status, reason),
        )
        return {
            "ok": status == "charged",
            "payment_id": cursor.lastrowid,
            "status": status,
            "reason": reason,
        }
