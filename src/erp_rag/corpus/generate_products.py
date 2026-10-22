"""Generate synthetic product (stock) records for the ERP corpus."""

from decimal import Decimal

from faker import Faker

from erp_rag.corpus.schema import Product

DEFAULT_COUNT = 150
DEFAULT_SEED = 42

CATEGORIES: dict[str, list[str]] = {
    "Electronics": [
        "Wireless Mouse",
        "USB-C Hub",
        "Mechanical Keyboard",
        "27-inch Monitor",
        "Webcam",
        "Noise-Cancelling Headphones",
    ],
    "Office Supplies": [
        "Stapler",
        "Printer Paper (Ream)",
        "Ballpoint Pens (Box)",
        "Sticky Notes",
        "Binder Clips",
        "Whiteboard Markers",
    ],
    "Furniture": [
        "Office Chair",
        "Standing Desk",
        "Filing Cabinet",
        "Bookshelf",
        "Desk Lamp",
        "Monitor Stand",
    ],
    "Software Licenses": [
        "Antivirus License",
        "Office Suite License",
        "Cloud Storage Plan",
        "VPN Subscription",
        "Design Software License",
    ],
    "Raw Materials": [
        "Steel Sheet",
        "Aluminum Rod",
        "Plastic Pellets",
        "Copper Wire",
        "Wood Plank",
    ],
}


def generate_products(count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED) -> list[Product]:
    Faker.seed(seed)
    fake = Faker("en_US")

    products = []
    for i in range(1, count + 1):
        category = fake.random_element(elements=list(CATEGORIES))
        name = fake.random_element(elements=CATEGORIES[category])
        brand = fake.company()
        price = Decimal(str(fake.pyfloat(min_value=5, max_value=500, right_digits=2, positive=True)))

        product = Product(
            id=f"PROD-{i:04d}",
            name=name,
            brand=brand,
            category=category,
            unit_price=price,
            quantity_in_stock=fake.random_int(min=0, max=500),
            reorder_threshold=fake.random_int(min=5, max=50),
        )
        products.append(product)

    return products


if __name__ == "__main__":
    for product in generate_products(count=3):
        print(product)
