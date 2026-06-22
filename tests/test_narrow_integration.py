"""
Happy path. The order-to-invoice integration is successful:
- The order ends up as completed
- A real invoice is issued for the order total
- Stock and payment are mocked and called with the expected values
"""
def test_narrow_order_to_invoice_happy_path_issues_the_invoice(service_bundle_factory, mocker):
    # Arrange
    quantity = 3
    unit_price_cents = 1500
    expected_total_cents = 4500
    mocked_stock = mocker.Mock()
    mocked_payment = mocker.Mock()
    mocked_stock.get_product.return_value = {
        "sku": "NARROW-SKU",
        "name": "Narrow Test Product",
        "stock_on_hand": 999,
        "price_cents": unit_price_cents,
    }
    mocked_stock.reserve.return_value = {"ok": True}
    mocked_payment.charge.return_value = {
        "ok": True,
        "status": "charged",
        "payment_id": 999,
    }
    services = service_bundle_factory(
        stock_service=mocked_stock,
        payment_service=mocked_payment,
    )
    customer_id = services.data.customer(credit_limit_cents=10000)
    sku = services.data.product(stock_on_hand=1, price_cents=999)

    # Act
    result = services.order.place_order(customer_id=customer_id, sku=sku, quantity=quantity)
    order = services.order.get_order(result["order_id"])

    # Assert

    # The order is completed
    assert result["ok"] is True
    assert order["status"] == "completed"

    # The real invoice service issues an invoice for the mocked order total
    assert result["total_cents"] == expected_total_cents
    assert services.invoice.get_invoice(result["invoice_id"]) == {
        "id": result["invoice_id"],
        "order_id": result["order_id"],
        "customer_id": customer_id,
        "amount_cents": expected_total_cents,
        "status": "issued",
    }

    # Mocked collaborators are called at the integration boundary.
    # The following lines are shown for didactic purposes only.
    # Avoid including them in production
    mocked_stock.get_product.assert_called_once_with(sku)
    mocked_stock.reserve.assert_called_once_with(result["order_id"], sku, quantity)
    mocked_payment.charge.assert_called_once_with(
        result["order_id"],
        customer_id,
        expected_total_cents,
    )


"""
Negative test. Mocked stock service rejects the reservation:
- The order is rejected
- The order is marked as failed because of insufficient stock
- Payment and invoice are not used
"""
def test_narrow_does_not_invoice_when_mocked_stock_rejects_the_order(service_bundle_factory, mocker):
    # Arrange
    quantity = 2
    mocked_stock = mocker.Mock()
    mocked_payment = mocker.Mock()
    mocked_stock.get_product.return_value = {
        "sku": "NARROW-SKU",
        "name": "Narrow Test Product",
        "stock_on_hand": 1,
        "price_cents": 750,
    }
    mocked_stock.reserve.return_value = {
        "ok": False,
        "reason": "insufficient stock",
    }
    services = service_bundle_factory(
        stock_service=mocked_stock,
        payment_service=mocked_payment,
    )
    customer_id = services.data.customer(credit_limit_cents=10000)
    sku = services.data.product(stock_on_hand=1, price_cents=999)

    # Act
    result = services.order.place_order(customer_id=customer_id, sku=sku, quantity=quantity)
    order = services.order.get_order(result["order_id"])

    # Assert

    # The order is rejected
    assert result == {
        "ok": False,
        "order_id": result["order_id"],
        "reason": "insufficient stock",
    }

    # The order is marked as failed without an invoice
    assert {
        "status": order["status"],
        "failure_reason": order["failure_reason"],
        "invoice_id": order["invoice_id"],
    } == {
        "status": "failed",
        "failure_reason": "insufficient stock",
        "invoice_id": None,
    }

    # Downstream mocked collaborators are not called after stock rejection.
    # The following lines are shown for didactic purposes only.
    # Avoid including them in production
    mocked_stock.reserve.assert_called_once_with(result["order_id"], sku, quantity)
    mocked_payment.charge.assert_not_called()


"""
Negative test. Mocked payment service declines the charge:
- The order is rejected
- The order is marked as failed because of the payment failure
- The real invoice service is not used and mocked stock is released
"""
def test_narrow_does_not_invoice_when_mocked_payment_declines(service_bundle_factory, mocker):
    # Arrange
    quantity = 1
    unit_price_cents = 1200
    mocked_stock = mocker.Mock()
    mocked_payment = mocker.Mock()
    mocked_stock.get_product.return_value = {
        "sku": "NARROW-SKU",
        "name": "Narrow Test Product",
        "stock_on_hand": 999,
        "price_cents": unit_price_cents,
    }
    mocked_stock.reserve.return_value = {"ok": True}
    mocked_stock.release.return_value = {"ok": True, "released": True}
    mocked_payment.charge.return_value = {
        "ok": False,
        "status": "declined",
        "reason": "fake payment failure",
    }
    services = service_bundle_factory(
        stock_service=mocked_stock,
        payment_service=mocked_payment,
    )
    customer_id = services.data.customer(credit_limit_cents=10000)
    sku = services.data.product(stock_on_hand=1, price_cents=999)

    # Act
    result = services.order.place_order(customer_id=customer_id, sku=sku, quantity=quantity)
    order = services.order.get_order(result["order_id"])

    # Assert

    # The order is rejected
    assert {
        "ok": result["ok"],
        "reason": result["reason"],
    } == {
        "ok": False,
        "reason": "fake payment failure",
    }

    # The order is marked as failed without an invoice
    assert {
        "status": order["status"],
        "failure_reason": order["failure_reason"],
        "invoice_id": order["invoice_id"],
    } == {
        "status": "failed",
        "failure_reason": "fake payment failure",
        "invoice_id": None,
    }

    # The stock reservation is released and no invoice is issued.
    # The following lines are shown for didactic purposes only.
    # Avoid including them in production
    mocked_stock.release.assert_called_once_with(result["order_id"])
    assert order["invoice_id"] is None
