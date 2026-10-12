"""Pydantic models for the synthetic ERP corpus.

Five tables, mirroring a normalized ERP export: customers and products are
reference data, orders/order_line_items/invoices are the documents that
reference them. See ARCHITECTURE.md and DevRoadmap.md Phase 1 for the
reasoning behind this shape.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class InvoiceStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class Customer(BaseModel):
    id: str
    name: str
    email: str
    address: str
    city: str
    country: str


class Product(BaseModel):
    id: str
    name: str
    category: str
    unit_price: Decimal
    quantity_in_stock: int = Field(ge=0)
    reorder_threshold: int = Field(ge=0)


class Order(BaseModel):
    id: str
    customer_id: str
    order_date: date
    status: OrderStatus


class OrderLineItem(BaseModel):
    id: str
    order_id: str
    product_id: str
    quantity: int = Field(gt=0)
    unit_price: Decimal


class Invoice(BaseModel):
    id: str
    order_id: str
    invoice_date: date
    due_date: date
    amount: Decimal
    status: InvoiceStatus
    payment_date: date | None = None
