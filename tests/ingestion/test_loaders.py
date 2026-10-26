import pytest
from pydantic import ValidationError

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_invoices import generate_invoices
from erp_rag.corpus.generate_order_line_items import generate_order_line_items
from erp_rag.corpus.generate_orders import generate_orders
from erp_rag.corpus.generate_products import generate_products
from erp_rag.corpus.schema import Customer, Invoice, InvoiceStatus
from erp_rag.ingestion.loaders import load_records, load_table


def test_load_records_round_trips_the_committed_corpus():
    """Loading data/raw/ gives back exactly what the generators produce.

    Only possible because the corpus is deterministic by seed and by date
    (ARCHITECTURE.md §4b): the committed CSVs and a fresh in-memory build
    must be the same records, field for field and type for type.
    """
    customers = generate_customers()
    products = generate_products()
    orders = generate_orders(customers)
    line_items = generate_order_line_items(orders, products)
    invoices = generate_invoices(orders, line_items)

    assert load_records() == customers + products + orders + line_items + invoices


def test_load_table_turns_empty_cells_back_into_none(tmp_path):
    path = tmp_path / "invoices.csv"
    path.write_text(
        "id,order_id,invoice_date,due_date,amount,status,payment_date\n"
        "INV-0001,ORD-0001,2026-01-16,2026-02-15,157.50,pending,\n",
        encoding="utf-8",
    )

    [invoice] = load_table(path, Invoice)

    assert invoice.payment_date is None
    assert invoice.status == InvoiceStatus.PENDING


def test_load_table_rejects_a_row_that_breaks_the_schema(tmp_path):
    path = tmp_path / "invoices.csv"
    path.write_text(
        "id,order_id,invoice_date,due_date,amount,status,payment_date\n"
        "INV-0001,ORD-0001,not-a-date,2026-02-15,157.50,pending,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_table(path, Invoice)


def test_load_table_missing_file_points_to_build_script(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_corpus.py"):
        load_table(tmp_path / "customers.csv", Customer)
