from erp_rag.corpus.schema import Customer
from erp_rag.ingestion.chunking import Chunk, fixed_size_chunk

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
