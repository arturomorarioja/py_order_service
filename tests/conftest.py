import shutil
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db import SCHEMA, connect
from app.services.invoice import InvoiceService
from app.services.order import OrderService
from app.services.payment import PaymentService
from app.services.stock import StockService
from tests.data_builder import TestData


@pytest.fixture
def service_bundle_factory(request):
    test_run_directory = Path(__file__).resolve().parents[1] / ".test-runs" / uuid4().hex
    test_run_directory.mkdir(parents=True)
    request.addfinalizer(lambda: shutil.rmtree(test_run_directory, ignore_errors=True))

    service_count = 0

    def _make_services(stock_service=None, payment_service=None, invoice_service=None):
        nonlocal service_count
        service_count += 1
        database_path = test_run_directory / f"test-{service_count}.sqlite"

        with connect(database_path) as connection:
            connection.executescript(SCHEMA)

        stock = stock_service or StockService(database_path)
        payment = payment_service or PaymentService(database_path)
        invoice = invoice_service or InvoiceService(database_path)
        order = OrderService(
            database_path,
            stock_service=stock,
            payment_service=payment,
            invoice_service=invoice,
        )

        return SimpleNamespace(
            database_path=database_path,
            data=TestData(database_path),
            order=order,
            stock=stock,
            payment=payment,
            invoice=invoice,
        )

    return _make_services


@pytest.fixture
def services(service_bundle_factory):
    return service_bundle_factory()
