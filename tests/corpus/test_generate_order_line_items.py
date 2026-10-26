import pytest

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_order_line_items import (
    MAX_ITEMS_PER_ORDER,
    MIN_ITEMS_PER_ORDER,
    generate_order_line_items,
)
from erp_rag.corpus.generate_orders import generate_orders
from erp_rag.corpus.generate_products import generate_products
from erp_rag.corpus.schema import OrderLineItem


@pytest.fixture
def sample_orders():
    customers = generate_customers(count=10, seed=1)
    return generate_orders(customers, count=10, seed=1)


@pytest.fixture
def sample_products():
    return generate_products(count=10, seed=1)


def test_generate_order_line_items_is_deterministic(sample_orders, sample_products):
    first_run = generate_order_line_items(sample_orders, sample_products, seed=42)
    second_run = generate_order_line_items(sample_orders, sample_products, seed=42)

    assert first_run == second_run


def test_generate_order_line_items_count_within_bounds(sample_orders, sample_products):
    line_items = generate_order_line_items(sample_orders, sample_products, seed=1)

    min_expected = len(sample_orders) * MIN_ITEMS_PER_ORDER
    max_expected = len(sample_orders) * MAX_ITEMS_PER_ORDER
    assert min_expected <= len(line_items) <= max_expected


def test_generate_order_line_items_returns_valid_line_items(sample_orders, sample_products):
    line_items = generate_order_line_items(sample_orders, sample_products, seed=1)

    assert all(isinstance(line_item, OrderLineItem) for line_item in line_items)


def test_generate_order_line_items_ids_are_unique(sample_orders, sample_products):
    line_items = generate_order_line_items(sample_orders, sample_products, seed=1)
    ids = [line_item.id for line_item in line_items]

    assert len(ids) == len(set(ids))


def test_generate_order_line_items_reference_real_orders_and_products(
    sample_orders, sample_products
):
    line_items = generate_order_line_items(sample_orders, sample_products, seed=1)
    valid_order_ids = {order.id for order in sample_orders}
    valid_product_ids = {product.id for product in sample_products}

    assert all(item.order_id in valid_order_ids for item in line_items)
    assert all(item.product_id in valid_product_ids for item in line_items)
