"""Generate synthetic customer records for the ERP corpus."""

from faker import Faker

from erp_rag.corpus.schema import Customer

DEFAULT_COUNT = 50
DEFAULT_SEED = 42


def generate_customers(count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED) -> list[Customer]:
    Faker.seed(seed)
    fake = Faker("en_US")

    customers = []
    for i in range(1, count + 1):
        customer = Customer(
            id=f"CUST-{i:04d}",
            name=fake.name(),
            email=fake.email(),
            address=fake.street_address(),
            city=fake.city(),
            country=fake.country(),
        )
        customers.append(customer)

    return customers


if __name__ == "__main__":
    for customer in generate_customers(count=3):
        print(customer)
