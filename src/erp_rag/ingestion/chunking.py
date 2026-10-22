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
