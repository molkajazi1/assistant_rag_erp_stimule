"""Generate synthetic order records for the ERP corpus."""

from faker import Faker

from erp_rag.corpus.schema import Customer, Order, OrderStatus

DEFAULT_COUNT = 300
DEFAULT_SEED = 42


def generate_orders(
    customers: list[Customer], count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED
) -> list[Order]:
    Faker.seed(seed)
    fake = Faker("en_US")

    orders = []
    for i in range(1, count + 1):
        customer = fake.random_element(elements=customers)
        order = Order(
            id=f"ORD-{i:04d}",
            customer_id=customer.id,
            order_date=fake.date_between(start_date="-1y", end_date="today"),
            status=fake.random_element(elements=list(OrderStatus)),
        )
        orders.append(order)

    return orders


if __name__ == "__main__":
    from erp_rag.corpus.generate_customers import generate_customers

    sample_customers = generate_customers()
    for order in generate_orders(sample_customers, count=3):
        print(order)
