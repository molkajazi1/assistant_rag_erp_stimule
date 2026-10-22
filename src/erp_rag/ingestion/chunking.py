"""Chunking strategies compared in ARCHITECTURE.md §4.

Each strategy is a pure function: list[Record] -> list[Chunk]. No I/O here -
loaders.py handles reading data/raw/, this module only transforms records
already in memory.
"""

from pydantic import BaseModel

from erp_rag.corpus.schema import Customer, Invoice, Order, OrderLineItem, Product

Record = Customer | Product | Order | OrderLineItem | Invoice

DEFAULT_CHUNK_SIZE = 200  # words per chunk, no overlap


class Chunk(BaseModel):
    text: str
    source_ids: list[str]
    strategy: str


def fixed_size_chunk(records: list[Record], chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[Chunk]:
    """Baseline/strawman: render every record as plain text, concatenate, and
    split by word count - ignoring record boundaries entirely. A chunk can cut
    a record in half or straddle two unrelated records. This is the strategy
    strategies 2-4 are meant to beat.
    """
    words: list[str] = []
    word_owner: list[str] = []  # word_owner[i] = id of the record that produced words[i]

    for record in records:
        record_words = str(record).split()
        words.extend(record_words)
        word_owner.extend([record.id] * len(record_words))

    chunks = []
    for start in range(0, len(words), chunk_size):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_owners = word_owner[start:end]

        chunks.append(
            Chunk(
                text=" ".join(chunk_words),
                source_ids=sorted(set(chunk_owners)),
                strategy="fixed_size",
            )
        )

    return chunks


def record_level_chunk(records: list[Record]) -> list[Chunk]:
    """One chunk per record, rendered through a type-specific template.

    Foreign keys to a customer/product are resolved to a human-readable name
    (not just the raw id) so a chunk reads like a sentence an embedding model
    can actually match against a natural-language query. Does NOT embed a
    full line-item breakdown into order/invoice text - that is what strategy 3
    (hierarchical) exists to handle; doing it here would blur the comparison
    between the two strategies.
    """
    customers = {r.id: r for r in records if isinstance(r, Customer)}
    products = {r.id: r for r in records if isinstance(r, Product)}

    return [
        Chunk(
            text=_render_record(record, customers, products),
            source_ids=[record.id],
            strategy="record_level",
        )
        for record in records
    ]


def _render_record(record: Record, customers: dict[str, Customer], products: dict[str, Product]) -> str:
    match record:
        case Customer():
            return (
                f"Customer {record.id}: {record.name}, email {record.email}, "
                f"located at {record.address}, {record.city}, {record.country}."
            )
        case Product():
            return (
                f"Product {record.id}: {record.name} by {record.brand}, category {record.category}, "
                f"unit price ${record.unit_price}, {record.quantity_in_stock} in stock, "
                f"reorder threshold {record.reorder_threshold}."
            )
        case Order():
            customer = customers.get(record.customer_id)
            customer_name = customer.name if customer else "unknown customer"
            return (
                f"Order {record.id} for customer {customer_name} ({record.customer_id}), "
                f"placed on {record.order_date}, status {record.status}."
            )
        case OrderLineItem():
            product = products.get(record.product_id)
            product_name = product.name if product else "unknown product"
            return (
                f"Line item {record.id} on order {record.order_id}: {record.quantity} x "
                f"{product_name} ({record.product_id}) at ${record.unit_price} each."
            )
        case Invoice():
            text = (
                f"Invoice {record.id} for order {record.order_id}, issued {record.invoice_date}, "
                f"due {record.due_date}, amount ${record.amount}, status {record.status}"
            )
            if record.payment_date is not None:
                return text + f", paid on {record.payment_date}."
            return text + "."
