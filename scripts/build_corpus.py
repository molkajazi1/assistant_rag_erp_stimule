"""Build the full synthetic ERP corpus and write it to data/raw/ as CSV files."""

import csv
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.generate_invoices import generate_invoices
from erp_rag.corpus.generate_order_line_items import generate_order_line_items
from erp_rag.corpus.generate_orders import generate_orders
from erp_rag.corpus.generate_products import generate_products

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _write_csv(records: Iterable[BaseModel], path: Path) -> None:
    records = list(records)
    if not records:
        return

    fieldnames = list(records[0].model_dump().keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {
                key: ("" if value is None else value) for key, value in record.model_dump().items()
            }
            writer.writerow(row)


def build_corpus() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    customers = generate_customers()
    products = generate_products()
    orders = generate_orders(customers)
    line_items = generate_order_line_items(orders, products)
    invoices = generate_invoices(orders, line_items)

    _write_csv(customers, DATA_DIR / "customers.csv")
    _write_csv(products, DATA_DIR / "products.csv")
    _write_csv(orders, DATA_DIR / "orders.csv")
    _write_csv(line_items, DATA_DIR / "order_line_items.csv")
    _write_csv(invoices, DATA_DIR / "invoices.csv")

    print(
        f"Wrote {len(customers)} customers, {len(products)} products, "
        f"{len(orders)} orders, {len(line_items)} order line items, "
        f"{len(invoices)} invoices to {DATA_DIR}"
    )


if __name__ == "__main__":
    build_corpus()
