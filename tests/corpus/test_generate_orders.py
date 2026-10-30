from datetime import date, timedelta

import pytest
from faker.providers.date_time import Provider as FakerDateTimeProvider

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_orders import (
    CONFIRMED_AFTER_DAYS,
    DELIVERED_AFTER_DAYS,
    ORDER_HISTORY_DAYS,
    SHIPPED_AFTER_DAYS,
    generate_orders,
)
from erp_rag.corpus.schema import CORPUS_REFERENCE_DATE, Order, OrderStatus


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


def test_generate_orders_is_identical_on_every_operating_system(sample_customers, monkeypatch):
    """Faker's date_between() draws random seconds with randint on Windows but
    uniform on Linux, so the same seed gave different dates on the CI runner.
    Forcing Faker's other platform path must not change our orders."""
    first_run = generate_orders(sample_customers, count=50, seed=1)

    monkeypatch.setattr(
        FakerDateTimeProvider,
        "_rand_seconds",
        lambda self, start, end: self.generator.random.uniform(start, end),
    )
    second_run = generate_orders(sample_customers, count=50, seed=1)

    assert first_run == second_run


def test_generate_orders_status_follows_order_age(sample_customers):
    """Non-cancelled status is fully determined by how old the order is on as_of,
    so it can never contradict invoicing (orders are invoiced when they ship)."""
    orders = generate_orders(sample_customers, count=300, seed=1)

    for order in orders:
        if order.status == OrderStatus.CANCELLED:
            continue
        age_days = (CORPUS_REFERENCE_DATE - order.order_date).days
        if age_days >= DELIVERED_AFTER_DAYS:
            assert order.status == OrderStatus.DELIVERED
        elif age_days >= SHIPPED_AFTER_DAYS:
            assert order.status == OrderStatus.SHIPPED
        elif age_days >= CONFIRMED_AFTER_DAYS:
            assert order.status == OrderStatus.CONFIRMED
        else:
            assert order.status == OrderStatus.PENDING
