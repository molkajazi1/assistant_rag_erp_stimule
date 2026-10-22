"""Generate synthetic order line item records for the ERP corpus."""

from decimal import Decimal

from faker import Faker

from erp_rag.corpus.schema import Order, OrderLineItem, Product

DEFAULT_SEED = 42
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 3
PRICE_VARIATION = 0.10  # +/- 10% vs. the product's current price


def generate_order_line_items(
    orders: list[Order], products: list[Product], seed: int = DEFAULT_SEED
) -> list[OrderLineItem]:
    Faker.seed(seed)
    fake = Faker("en_US")

    line_items = []
    item_id = 1
    for order in orders:
        item_count = fake.random_int(min=MIN_ITEMS_PER_ORDER, max=MAX_ITEMS_PER_ORDER)
        for _ in range(item_count):
            product = fake.random_element(elements=products)
            variation = fake.pyfloat(min_value=-PRICE_VARIATION, max_value=PRICE_VARIATION, right_digits=4)
            price_at_order_time = product.unit_price * (Decimal(1) + Decimal(str(variation)))

            line_item = OrderLineItem(
                id=f"OLI-{item_id:04d}",
                order_id=order.id,
                product_id=product.id,
                quantity=fake.random_int(min=1, max=10),
                unit_price=round(price_at_order_time, 2),
            )
            line_items.append(line_item)
            item_id += 1

    return line_items


if __name__ == "__main__":
    from erp_rag.corpus.generate_customers import generate_customers
    from erp_rag.corpus.generate_orders import generate_orders
    from erp_rag.corpus.generate_products import generate_products

    sample_customers = generate_customers()
    sample_products = generate_products()
    sample_orders = generate_orders(sample_customers, count=3)
    for line_item in generate_order_line_items(sample_orders, sample_products):
        print(line_item)
