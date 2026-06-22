"""
Happy path. The purchase order is successful:
- The order ends up as completed
- An invoice is issued for the order total
- The stock is reduced according to the item quantity ordered
"""
def test_broad_happy_path_completes_the_order_and_issues_the_invoice(services):
    # Arrange
    initial_stock = 10
    quantity = 2
    customer_id = services.data.customer(credit_limit_cents=10000)
    sku = services.data.product(stock_on_hand=initial_stock, price_cents=1200)

    # Act
    result = services.order.place_order(customer_id=customer_id, sku=sku, quantity=quantity)

    # Assert
    order = services.order.get_order(result["order_id"])

    # The order is completed
    assert result["ok"] is True
    assert order["status"] == "completed"

    # The invoice is issued for the order total
    assert result["total_cents"] == 2400
    assert services.invoice.get_invoice(result["invoice_id"]) == {
        "id": result["invoice_id"],
        "order_id": result["order_id"],
        "customer_id": customer_id,
        "amount_cents": 2400,
        "status": "issued",
    }

    # Stock is properly reduced
    assert services.stock.get_product(sku)["stock_on_hand"] == initial_stock - quantity


"""
Negative test. Product stock is unavailable:
- The order is rejected
- The order is marked as failed because of insufficient stock
- Stock remains unchanged
"""
def test_broad_rejects_order_when_stock_is_unavailable(services):
    # Arrange
    initial_stock = 1
    customer_id = services.data.customer(credit_limit_cents=10000)
    sku = services.data.product(stock_on_hand=initial_stock, price_cents=750)

    # Act
    result = services.order.place_order(customer_id=customer_id, sku=sku, quantity=2)
    order = services.order.get_order(result["order_id"])

    # Assert

    # Order is rejected
    assert result == {
        "ok": False,
        "order_id": result["order_id"],
        "reason": "insufficient stock",
    }

    # Stock check marks order as failed
    assert {
        "status": order["status"],
        "failure_reason": order["failure_reason"],
        "invoice_id": order["invoice_id"],
    } == {
        "status": "failed",
        "failure_reason": "insufficient stock",
        "invoice_id": None,
    }

    # Stock stays unchanged
    assert services.stock.get_product(sku)["stock_on_hand"] == initial_stock


"""
Negative test. Payment is declined:
- The order is rejected
- The order is marked as failed because of credit limit exceeded
- The reserved stock gets released
"""
def test_broad_rejects_order_when_payment_is_declined(services):
    # Arrange
    initial_stock = 10
    customer_id = services.data.customer(credit_limit_cents=500)
    sku = services.data.product(stock_on_hand=initial_stock, price_cents=1200)

    # Act
    result = services.order.place_order(customer_id=customer_id, sku=sku, quantity=1)
    order = services.order.get_order(result["order_id"])

    # Assert

    # Order rejected
    assert {
        "ok": result["ok"],
        "reason": result["reason"],
    } == {
        "ok": False,
        "reason": "credit limit exceeded",
    }

    # Order marked as failed
    assert {
        "status": order["status"],
        "failure_reason": order["failure_reason"],
        "invoice_id": order["invoice_id"],
    } == {
        "status": "failed",
        "failure_reason": "credit limit exceeded",
        "invoice_id": None,
    }

    # Reserved stock released
    assert services.stock.get_product(sku)["stock_on_hand"] == initial_stock