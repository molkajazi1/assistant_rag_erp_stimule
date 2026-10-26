from datetime import timedelta
from decimal import Decimal

import pytest
from freezegun import freeze_time

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_invoices import generate_invoices
from erp_rag.corpus.generate_order_line_items import generate_order_line_items
from erp_rag.corpus.generate_orders import generate_orders
from erp_rag.corpus.generate_products import generate_products
from erp_rag.corpus.schema import CORPUS_REFERENCE_DATE, Invoice, InvoiceStatus


@pytest.fixture
def sample_orders():
    customers = generate_customers(count=10, seed=1)
    return generate_orders(customers, count=10, seed=1)


@pytest.fixture
def sample_line_items(sample_orders):
    products = generate_products(count=10, seed=1)
    return generate_order_line_items(sample_orders, products, seed=1)


def test_generate_invoices_is_deterministic(sample_orders, sample_line_items):
    first_run = generate_invoices(sample_orders, sample_line_items, seed=42)
    second_run = generate_invoices(sample_orders, sample_line_items, seed=42)

    assert first_run == second_run


def test_generate_invoices_one_per_order(sample_orders, sample_line_items):
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1)

    assert len(invoices) == len(sample_orders)


def test_generate_invoices_returns_valid_invoices(sample_orders, sample_line_items):
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1)

    assert all(isinstance(invoice, Invoice) for invoice in invoices)


def test_generate_invoices_ids_are_unique(sample_orders, sample_line_items):
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1)
    ids = [invoice.id for invoice in invoices]

    assert len(ids) == len(set(ids))


def test_generate_invoices_order_ids_reference_real_orders(sample_orders, sample_line_items):
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1)
    valid_order_ids = {order.id for order in sample_orders}

    assert all(invoice.order_id in valid_order_ids for invoice in invoices)


def test_generate_invoices_amount_matches_order_line_items(sample_orders, sample_line_items):
    """Rule 1: amount = sum(quantity * unit_price) over line items with that order_id."""
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1)

    for invoice in invoices:
        expected_amount = sum(
            (
                item.unit_price * item.quantity
                for item in sample_line_items
                if item.order_id == invoice.order_id
            ),
            start=Decimal(0),
        )
        assert invoice.amount == expected_amount


def test_generate_invoices_status_consistent_with_dates(sample_orders, sample_line_items):
    """Rule 2: status must agree with payment_date and due_date, not just be a free label.

    paid -> has a payment_date. overdue -> no payment_date and due_date already passed.
    pending -> no payment_date and due_date has not passed (yet).
    """
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1)
    as_of = CORPUS_REFERENCE_DATE

    for invoice in invoices:
        if invoice.status == InvoiceStatus.PAID:
            assert invoice.payment_date is not None
        elif invoice.status == InvoiceStatus.OVERDUE:
            assert invoice.payment_date is None
            assert invoice.due_date < as_of
        elif invoice.status == InvoiceStatus.PENDING:
            assert invoice.payment_date is None
            assert invoice.due_date >= as_of


def test_generate_invoices_status_follows_as_of(sample_orders, sample_line_items):
    """Moving as_of past every due date turns every unpaid invoice overdue."""
    far_future = CORPUS_REFERENCE_DATE + timedelta(days=3650)
    invoices = generate_invoices(sample_orders, sample_line_items, seed=1, as_of=far_future)

    assert all(invoice.status != InvoiceStatus.PENDING for invoice in invoices)


def test_generate_invoices_ignores_the_real_clock():
    """Same seed on a different day must give the same corpus (ARCHITECTURE.md §4b).

    The plain determinism test can't catch a clock dependency, since both of its
    runs happen on the same day. Here the date Faker sees as "today" jumps a year.
    """

    def build_corpus_slice():
        customers = generate_customers(count=10, seed=1)
        orders = generate_orders(customers, count=10, seed=1)
        line_items = generate_order_line_items(orders, generate_products(count=10, seed=1), seed=1)
        return orders, generate_invoices(orders, line_items, seed=1)

    with freeze_time("2026-10-22"):
        first_run = build_corpus_slice()
    with freeze_time("2027-10-22"):
        second_run = build_corpus_slice()

    assert first_run == second_run
