from app.db import connect, row_to_dict


class InvoiceService:
    def __init__(self, database_path):
        self.database_path = database_path

    def create_invoice(self, order_id, customer_id, amount_cents):
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO invoices (order_id, customer_id, amount_cents, status)
                VALUES (?, ?, ?, 'issued')
                """,
                (order_id, customer_id, amount_cents),
            )
            return {
                "ok": True,
                "invoice_id": cursor.lastrowid,
                "status": "issued",
            }

    def get_invoice(self, invoice_id):
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT id, order_id, customer_id, amount_cents, status
                FROM invoices
                WHERE id = ?
                """,
                (invoice_id,),
            ).fetchone()
            return row_to_dict(row)
