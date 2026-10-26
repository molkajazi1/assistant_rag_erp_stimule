"""Load the raw corpus from data/raw/ back into typed records.

The mirror image of scripts/build_corpus.py: that script turns records into
CSV files, this module turns those files back into the same records, so the
chunking strategies in chunking.py receive exactly what the generators
produced. All file I/O for ingestion lives here; chunking stays pure.
"""

import csv
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from erp_rag.corpus.schema import Customer, Invoice, Order, OrderLineItem, Product
from erp_rag.ingestion.chunking import Chunk, Record, get_chunking_strategy

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

# One file per table, same names and order as scripts/build_corpus.py writes them.
CORPUS_FILES: dict[str, type[BaseModel]] = {
    "customers.csv": Customer,
    "products.csv": Product,
    "orders.csv": Order,
    "order_line_items.csv": OrderLineItem,
    "invoices.csv": Invoice,
}

M = TypeVar("M", bound=BaseModel)


def load_table(path: Path, model: type[M]) -> list[M]:
    """Read one CSV file and validate every row against its Pydantic model.

    CSV only stores text, so the model does the conversion back to real types
    (date, Decimal, enum) and rejects any row that doesn't fit the schema.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `poetry run python scripts/build_corpus.py` first."
        )

    with path.open(newline="", encoding="utf-8") as f:
        return [model.model_validate(_empty_cells_to_none(row)) for row in csv.DictReader(f)]


def load_records(data_dir: Path = DEFAULT_DATA_DIR) -> list[Record]:
    """Load all five tables into one list, the input every chunking strategy takes.

    The tables are combined rather than kept apart because chunking needs them
    together, e.g. to resolve an order's customer_id to the customer's name.
    """
    records: list[Record] = []
    for filename, model in CORPUS_FILES.items():
        records.extend(load_table(data_dir / filename, model))
    return records


def load_chunks(strategy: str, data_dir: Path = DEFAULT_DATA_DIR) -> list[Chunk]:
    """Load the corpus and chunk it with the strategy named `strategy`.

    The single entry point later stages (build_index.py, run_eval.py) call, so
    switching strategy is a change of string, not of code.
    """
    chunk = get_chunking_strategy(strategy)  # validate the name before reading any file
    return chunk(load_records(data_dir))


def _empty_cells_to_none(row: dict[str, str]) -> dict[str, str | None]:
    # build_corpus.py writes None (e.g. an unpaid invoice's payment_date) as an
    # empty cell; turn it back into None so optional fields validate.
    return {key: (None if value == "" else value) for key, value in row.items()}
