"""Generate synthetic order records for the ERP corpus."""

from datetime import date, timedelta

from faker import Faker

from erp_rag.corpus.schema import CORPUS_REFERENCE_DATE, Customer, Order, OrderStatus

DEFAULT_COUNT = 300
DEFAULT_SEED = 42
ORDER_HISTORY_DAYS = 366  # same window as Faker's "-1y" (365.24 days, applied to a date)

# Order lifecycle: status follows from the order's age on the as_of date, so it can
# never contradict invoicing (an order is invoiced when it ships, see
# generate_invoices.py). Cancellation can happen at any age.
CANCELLED_PROBABILITY = 8  # percent
CONFIRMED_AFTER_DAYS = 2
SHIPPED_AFTER_DAYS = 7
DELIVERED_AFTER_DAYS = 14


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
        order_date = fake.date_between(start_date=history_start, end_date=as_of)
        cancelled = fake.boolean(chance_of_getting_true=CANCELLED_PROBABILITY)
        order = Order(
            id=f"ORD-{i:04d}",
            customer_id=customer.id,
            order_date=order_date,
            status=OrderStatus.CANCELLED if cancelled else _status_by_age(order_date, as_of),
        )
        orders.append(order)

    return orders


def _status_by_age(order_date: date, as_of: date) -> OrderStatus:
    age_days = (as_of - order_date).days
    if age_days >= DELIVERED_AFTER_DAYS:
        return OrderStatus.DELIVERED
    if age_days >= SHIPPED_AFTER_DAYS:
        return OrderStatus.SHIPPED
    if age_days >= CONFIRMED_AFTER_DAYS:
        return OrderStatus.CONFIRMED
    return OrderStatus.PENDING


if __name__ == "__main__":
    from erp_rag.corpus.generate_customers import generate_customers

    sample_customers = generate_customers()
    for order in generate_orders(sample_customers, count=3):
        print(order)
