"""Generate synthetic invoice records for the ERP corpus."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from faker import Faker

from erp_rag.corpus.schema import Invoice, InvoiceStatus, Order, OrderLineItem

DEFAULT_SEED = 42
PAYMENT_TERMS_DAYS = 30
PAID_PROBABILITY = 65  # percent chance an invoice has already been paid


def _order_amount(order: Order, line_items: list[OrderLineItem]) -> Decimal:
    return sum(
        (item.unit_price * item.quantity for item in line_items if item.order_id == order.id),
        start=Decimal(0),
    )


def generate_invoices(
    orders: list[Order], line_items: list[OrderLineItem], seed: int = DEFAULT_SEED
) -> list[Invoice]:
    Faker.seed(seed)
    fake = Faker("en_US")

    invoices = []
    for i, order in enumerate(orders, start=1):
        invoice_date = order.order_date + timedelta(days=fake.random_int(min=0, max=7))
        due_date = invoice_date + timedelta(days=PAYMENT_TERMS_DAYS)

        if fake.boolean(chance_of_getting_true=PAID_PROBABILITY):
            status = InvoiceStatus.PAID
            payment_date = invoice_date + timedelta(days=fake.random_int(min=1, max=40))
        elif due_date < datetime.now(tz=UTC).date():
            status = InvoiceStatus.OVERDUE
            payment_date = None
        else:
            status = InvoiceStatus.PENDING
            payment_date = None

        invoice = Invoice(
            id=f"INV-{i:04d}",
            order_id=order.id,
            invoice_date=invoice_date,
            due_date=due_date,
            amount=_order_amount(order, line_items),
            status=status,
            payment_date=payment_date,
        )
        invoices.append(invoice)

    return invoices


if __name__ == "__main__":
    from erp_rag.corpus.generate_customers import generate_customers
    from erp_rag.corpus.generate_order_line_items import generate_order_line_items
    from erp_rag.corpus.generate_orders import generate_orders
    from erp_rag.corpus.generate_products import generate_products

    sample_customers = generate_customers()
    sample_products = generate_products()
    sample_orders = generate_orders(sample_customers, count=5)
    sample_line_items = generate_order_line_items(sample_orders, sample_products)
    for invoice in generate_invoices(sample_orders, sample_line_items):
        print(invoice)
