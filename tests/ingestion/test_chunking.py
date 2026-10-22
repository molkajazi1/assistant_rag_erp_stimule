from datetime import date
from decimal import Decimal

from erp_rag.corpus.schema import (
    Customer,
    Invoice,
    InvoiceStatus,
    Order,
    OrderLineItem,
    OrderStatus,
    Product,
)
from erp_rag.ingestion.chunking import Chunk, fixed_size_chunk, record_level_chunk

# Each customer's str() rendering is exactly 9 whitespace-separated "words" -
# chosen deliberately so chunk boundaries are easy to compute by hand.
CUSTOMER_1 = Customer(
    id="CUST-0001",
    name="Alice Smith",
    email="a@x.com",
    address="1 Main St",
    city="Springfield",
    country="USA",
)
CUSTOMER_2 = Customer(
    id="CUST-0002",
    name="Bob Jones",
    email="b@x.com",
    address="2 Oak Ave",
    city="Lakeside",
    country="Canada",
)


def test_fixed_size_chunk_empty_input_returns_no_chunks():
    assert fixed_size_chunk([], chunk_size=10) == []


def test_fixed_size_chunk_clean_boundary_matches_record_boundary():
    """chunk_size=9 divides evenly: each customer is exactly one chunk, no overlap."""
    chunks = fixed_size_chunk([CUSTOMER_1, CUSTOMER_2], chunk_size=9)

    assert len(chunks) == 2
    assert chunks[0].source_ids == ["CUST-0001"]
    assert chunks[1].source_ids == ["CUST-0002"]
    assert len(chunks[0].text.split()) == 9
    assert len(chunks[1].text.split()) == 9


def test_fixed_size_chunk_cuts_through_record_boundary():
    """chunk_size=10 does not divide evenly: boundary lands mid-record on purpose."""
    chunks = fixed_size_chunk([CUSTOMER_1, CUSTOMER_2], chunk_size=10)

    assert len(chunks) == 2
    # chunk 1: all 9 words of customer 1, plus the first word of customer 2
    assert chunks[0].source_ids == ["CUST-0001", "CUST-0002"]
    assert len(chunks[0].text.split()) == 10
    # chunk 2: the remaining 8 words, all from customer 2
    assert chunks[1].source_ids == ["CUST-0002"]
    assert len(chunks[1].text.split()) == 8


def test_fixed_size_chunk_returns_chunk_instances_tagged_with_strategy():
    chunks = fixed_size_chunk([CUSTOMER_1, CUSTOMER_2], chunk_size=9)

    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    assert all(chunk.strategy == "fixed_size" for chunk in chunks)


# --- record_level_chunk ---

PRODUCT_1 = Product(
    id="PROD-0001",
    name="Wireless Mouse",
    brand="Acme Brand Co",
    category="Electronics",
    unit_price=Decimal("29.99"),
    quantity_in_stock=100,
    reorder_threshold=10,
)
ORDER_1 = Order(
    id="ORD-0001",
    customer_id="CUST-0001",
    order_date=date(2026, 1, 15),
    status=OrderStatus.CONFIRMED,
)
LINE_ITEM_1 = OrderLineItem(
    id="OLI-0001",
    order_id="ORD-0001",
    product_id="PROD-0001",
    quantity=5,
    unit_price=Decimal("31.50"),
)
PAID_INVOICE = Invoice(
    id="INV-0001",
    order_id="ORD-0001",
    invoice_date=date(2026, 1, 16),
    due_date=date(2026, 2, 15),
    amount=Decimal("157.50"),
    status=InvoiceStatus.PAID,
    payment_date=date(2026, 1, 20),
)
UNPAID_INVOICE = Invoice(
    id="INV-0002",
    order_id="ORD-0001",
    invoice_date=date(2026, 1, 16),
    due_date=date(2026, 2, 15),
    amount=Decimal("157.50"),
    status=InvoiceStatus.OVERDUE,
    payment_date=None,
)


def test_record_level_chunk_one_chunk_per_record():
    records = [CUSTOMER_1, CUSTOMER_2, PRODUCT_1]
    chunks = record_level_chunk(records)

    assert len(chunks) == len(records)
    assert [chunk.source_ids for chunk in chunks] == [["CUST-0001"], ["CUST-0002"], ["PROD-0001"]]
    assert all(chunk.strategy == "record_level" for chunk in chunks)


def test_record_level_chunk_customer_includes_all_fields():
    chunk = record_level_chunk([CUSTOMER_1])[0]

    for value in ("CUST-0001", "Alice Smith", "a@x.com", "1 Main St", "Springfield", "USA"):
        assert value in chunk.text


def test_record_level_chunk_product_includes_all_fields():
    chunk = record_level_chunk([PRODUCT_1])[0]

    for value in (
        "PROD-0001",
        "Wireless Mouse",
        "Acme Brand Co",
        "Electronics",
        "29.99",
        "100",
        "10",
    ):
        assert value in chunk.text


def test_record_level_chunk_order_includes_all_fields_and_resolves_customer_name():
    chunk = record_level_chunk([CUSTOMER_1, ORDER_1])[-1]

    for value in ("ORD-0001", "Alice Smith", "CUST-0001", "2026-01-15", "confirmed"):
        assert value in chunk.text


def test_record_level_chunk_order_falls_back_when_customer_missing():
    """The referenced customer isn't in the given records - must not crash."""
    chunk = record_level_chunk([ORDER_1])[0]

    assert "unknown customer" in chunk.text
    assert "CUST-0001" in chunk.text


def test_record_level_chunk_line_item_includes_all_fields_and_resolves_product_name():
    chunk = record_level_chunk([PRODUCT_1, LINE_ITEM_1])[-1]

    for value in ("OLI-0001", "ORD-0001", "5", "Wireless Mouse", "PROD-0001", "31.50"):
        assert value in chunk.text


def test_record_level_chunk_invoice_includes_payment_date_when_paid():
    chunk = record_level_chunk([PAID_INVOICE])[0]

    for value in ("INV-0001", "ORD-0001", "2026-01-16", "2026-02-15", "157.50", "paid", "2026-01-20"):
        assert value in chunk.text


def test_record_level_chunk_invoice_omits_payment_date_when_unpaid():
    chunk = record_level_chunk([UNPAID_INVOICE])[0]

    assert "overdue" in chunk.text
    assert "paid on" not in chunk.text
