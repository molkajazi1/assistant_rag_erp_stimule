from erp_rag.corpus.generate_customers import generate_customers
from erp_rag.corpus.schema import Customer


def test_generate_customers_is_deterministic():
    first_run = generate_customers(count=5, seed=42)
    second_run = generate_customers(count=5, seed=42)

    assert first_run == second_run


def test_generate_customers_respects_count():
    customers = generate_customers(count=7, seed=1)

    assert len(customers) == 7


def test_generate_customers_returns_valid_customers():
    customers = generate_customers(count=3, seed=1)

    assert all(isinstance(customer, Customer) for customer in customers)


def test_generate_customers_ids_are_unique():
    customers = generate_customers(count=50, seed=1)
    ids = [customer.id for customer in customers]

    assert len(ids) == len(set(ids))
