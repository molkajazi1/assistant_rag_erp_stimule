"""Chunking strategies compared in ARCHITECTURE.md §4.

Each strategy is a pure function: list[Record] -> list[Chunk]. No I/O here -
loaders.py handles reading data/raw/, this module only transforms records
already in memory.
"""

from collections.abc import Callable

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
    strategies 2-3 are meant to beat.
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


def hierarchical_chunk(records: list[Record]) -> list[Chunk]:
    """Header/summary chunk per order plus separate, enriched line-item
    chunks, linked back to their parent order both in text and in
    source_ids. Only orders get this treatment - they are the one entity
    with "many line items" this strategy exists for. Everything else
    (customer, product, invoice) renders exactly like record_level_chunk,
    since there's no hierarchy to represent for those.
    """
    customers = {r.id: r for r in records if isinstance(r, Customer)}
    products = {r.id: r for r in records if isinstance(r, Product)}
    line_items_by_order: dict[str, list[OrderLineItem]] = {}
    for record in records:
        if isinstance(record, OrderLineItem):
            line_items_by_order.setdefault(record.order_id, []).append(record)

    consumed_line_item_ids: set[str] = set()
    chunks: list[Chunk] = []

    for record in records:
        if isinstance(record, OrderLineItem):
            continue  # handled alongside its parent order below, or as a fallback after this loop

        if isinstance(record, Order):
            header_text = _render_record(record, customers, products)
            children = line_items_by_order.get(record.id, [])
            if children:
                child_ids = ", ".join(item.id for item in children)
                header_text += f" Has {len(children)} line item(s): {child_ids}."
            chunks.append(Chunk(text=header_text, source_ids=[record.id], strategy="hierarchical"))

            customer = customers.get(record.customer_id)
            customer_name = customer.name if customer else "unknown customer"
            for item in children:
                chunks.append(
                    Chunk(
                        text=_render_line_item_with_order_context(
                            item, record, customer_name, products
                        ),
                        source_ids=[item.id, record.id],
                        strategy="hierarchical",
                    )
                )
                consumed_line_item_ids.add(item.id)
            continue

        chunks.append(
            Chunk(
                text=_render_record(record, customers, products),
                source_ids=[record.id],
                strategy="hierarchical",
            )
        )

    # Line items whose parent order wasn't in the given records - fall back to
    # a standalone rendering rather than silently dropping them.
    for record in records:
        if isinstance(record, OrderLineItem) and record.id not in consumed_line_item_ids:
            chunks.append(
                Chunk(
                    text=_render_record(record, customers, products),
                    source_ids=[record.id],
                    strategy="hierarchical",
                )
            )

    return chunks


ChunkingStrategy = Callable[[list[Record]], list[Chunk]]

# Name -> strategy, so a strategy can be chosen by a plain string (CLI flag,
# config file, or a benchmark loop over every name) instead of by editing code.
# Each key is the same string the strategy stamps on Chunk.strategy.
CHUNKING_STRATEGIES: dict[str, ChunkingStrategy] = {
    "fixed_size": fixed_size_chunk,
    "record_level": record_level_chunk,
    "hierarchical": hierarchical_chunk,
}


def get_chunking_strategy(name: str) -> ChunkingStrategy:
    """Look a strategy up by name, failing loudly on an unknown one (e.g. a typo
    in a config value) rather than silently falling back to a default."""
    try:
        return CHUNKING_STRATEGIES[name]
    except KeyError:
        valid = ", ".join(CHUNKING_STRATEGIES)
        raise ValueError(f"Unknown chunking strategy {name!r}. Valid names: {valid}.") from None


def _render_line_item_with_order_context(
    item: OrderLineItem, order: Order, customer_name: str, products: dict[str, Product]
) -> str:
    product = products.get(item.product_id)
    product_name = product.name if product else "unknown product"
    return (
        f"Line item {item.id} for order {order.id} "
        f"(customer {customer_name}, placed {order.order_date}): "
        f"{item.quantity} x {product_name} ({item.product_id}) at ${item.unit_price} each."
    )


def _render_record(
    record: Record, customers: dict[str, Customer], products: dict[str, Product]
) -> str:
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
