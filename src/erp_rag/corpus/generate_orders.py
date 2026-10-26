"""Generate synthetic order records for the ERP corpus."""

from datetime import date, timedelta

from faker import Faker

from erp_rag.corpus.schema import CORPUS_REFERENCE_DATE, Customer, Order, OrderStatus

DEFAULT_COUNT = 300
DEFAULT_SEED = 42
ORDER_HISTORY_DAYS = 366  # same window as Faker's "-1y" (365.24 days, applied to a date)


def generate_orders(
    customers: list[Customer],
    count: int = DEFAULT_COUNT,
    seed: int = DEFAULT_SEED,
    as_of: date = CORPUS_REFERENCE_DATE,
) -> list[Order]:
    Faker.seed(seed)
    fake = Faker("en_US")
    history_start = as_of - timedelta(days=ORDER_HISTORY_DAYS)

    orders = []
    for i in range(1, count + 1):
        customer = fake.random_element(elements=customers)
        order = Order(
            id=f"ORD-{i:04d}",
            customer_id=customer.id,
            order_date=fake.date_between(start_date=history_start, end_date=as_of),
            status=fake.random_element(elements=list(OrderStatus)),
        )
        orders.append(order)

    return orders


if __name__ == "__main__":
    from erp_rag.corpus.generate_customers import generate_customers

    sample_customers = generate_customers()
    for order in generate_orders(sample_customers, count=3):
        print(order)
