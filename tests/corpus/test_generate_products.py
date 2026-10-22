from erp_rag.corpus.generate_products import CATEGORIES, generate_products
from erp_rag.corpus.schema import Product


def test_generate_products_is_deterministic():
    first_run = generate_products(count=5, seed=42)
    second_run = generate_products(count=5, seed=42)

    assert first_run == second_run


def test_generate_products_respects_count():
    products = generate_products(count=9, seed=1)

    assert len(products) == 9


def test_generate_products_returns_valid_products():
    products = generate_products(count=3, seed=1)

    assert all(isinstance(product, Product) for product in products)


def test_generate_products_ids_are_unique():
    products = generate_products(count=50, seed=1)
    ids = [product.id for product in products]

    assert len(ids) == len(set(ids))


def test_generate_products_name_matches_category():
    products = generate_products(count=50, seed=1)

    for product in products:
        assert product.category in CATEGORIES
        assert product.name in CATEGORIES[product.category]
