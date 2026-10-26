from datetime import date, timedelta

import pytest

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_orders import ORDER_HISTORY_DAYS, generate_orders
from erp_rag.corpus.schema import CORPUS_REFERENCE_DATE, Order


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


@pytest.mark.parametrize("as_of", [CORPUS_REFERENCE_DATE, date(2030, 1, 15)])
def test_generate_orders_dates_fall_in_the_year_before_as_of(sample_customers, as_of):
    orders = generate_orders(sample_customers, count=50, seed=1, as_of=as_of)
    history_start = as_of - timedelta(days=ORDER_HISTORY_DAYS)

    assert all(history_start <= order.order_date <= as_of for order in orders)
