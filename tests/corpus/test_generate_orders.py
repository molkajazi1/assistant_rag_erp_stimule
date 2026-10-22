import pytest

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_orders import generate_orders
from erp_rag.corpus.schema import Order


@pytest.fixture
def sample_customers():
    return generate_customers(count=10, seed=1)


def test_generate_orders_is_deterministic(sample_customers):
    first_run = generate_orders(sample_customers, count=5, seed=42)
    second_run = generate_orders(sample_customers, count=5, seed=42)

    assert first_run == second_run


def test_generate_orders_respects_count(sample_customers):
    orders = generate_orders(sample_customers, count=7, seed=1)

    assert len(orders) == 7


def test_generate_orders_returns_valid_orders(sample_customers):
    orders = generate_orders(sample_customers, count=3, seed=1)

    assert all(isinstance(order, Order) for order in orders)


def test_generate_orders_ids_are_unique(sample_customers):
    orders = generate_orders(sample_customers, count=50, seed=1)
    ids = [order.id for order in orders]

    assert len(ids) == len(set(ids))


def test_generate_orders_customer_ids_reference_real_customers(sample_customers):
    orders = generate_orders(sample_customers, count=50, seed=1)
    valid_customer_ids = {customer.id for customer in sample_customers}

    assert all(order.customer_id in valid_customer_ids for order in orders)
