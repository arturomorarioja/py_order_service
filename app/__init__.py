from pathlib import Path
from tempfile import gettempdir

from flask import Flask, jsonify, request

from app.db import init_db
from app.services.invoice import InvoiceService
from app.services.order import OrderService
from app.services.payment import PaymentService
from app.services.stock import StockService


def create_app(test_config=None, service_overrides=None):
    app = Flask(__name__)
    default_db = Path(gettempdir()) / "flask_integration_testing_example.sqlite"
    app.config.from_mapping(DATABASE=str(default_db), TESTING=False)

    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])

    stock_service = StockService(app.config["DATABASE"])
    payment_service = PaymentService(app.config["DATABASE"])
    invoice_service = InvoiceService(app.config["DATABASE"])

    overrides = service_overrides or {}
    stock_service = overrides.get("stock_service", stock_service)
    payment_service = overrides.get("payment_service", payment_service)
    invoice_service = overrides.get("invoice_service", invoice_service)

    order_service = overrides.get(
        "order_service",
        OrderService(
            app.config["DATABASE"],
            stock_service=stock_service,
            payment_service=payment_service,
            invoice_service=invoice_service,
        ),
    )

    app.extensions["services"] = {
        "stock": stock_service,
        "payment": payment_service,
        "invoice": invoice_service,
        "order": order_service,
    }

    @app.post("/orders")
    def create_order():
        payload = request.get_json(force=True)
        result = order_service.place_order(
            customer_id=payload.get("customer_id"),
            sku=payload.get("sku"),
            quantity=payload.get("quantity"),
        )
        status_code = 201 if result["ok"] else 409
        return jsonify(result), status_code

    @app.get("/orders/<int:order_id>")
    def get_order(order_id):
        order = order_service.get_order(order_id)
        if order is None:
            return jsonify({"error": "order not found"}), 404
        return jsonify(order)

    @app.get("/invoices/<int:invoice_id>")
    def get_invoice(invoice_id):
        invoice = invoice_service.get_invoice(invoice_id)
        if invoice is None:
            return jsonify({"error": "invoice not found"}), 404
        return jsonify(invoice)

    return app
