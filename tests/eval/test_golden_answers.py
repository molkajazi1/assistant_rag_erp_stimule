"""Truth tests for the golden dataset: every expected answer is re-derived from the corpus.

test_golden_dataset.py checks the file's *shape*; this module checks that its
*content* is true. Each entry has a verifier below that recomputes, independently
of how the answer was drafted, the exact source records and the key facts
(amounts, dates, counts, ids, names) the answer must state. A corpus change or a
wrong manual edit fails here instead of silently corrupting every benchmark.

Time-relative facts ("overdue", "running low", "since September") are evaluated
as of CORPUS_REFERENCE_DATE, the same date the eval harness passes as as_of.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from erp_rag.corpus.schema import (
    CORPUS_REFERENCE_DATE,
    Customer,
    Invoice,
    InvoiceStatus,
    Order,
    OrderLineItem,
    OrderStatus,
    Product,
)
from erp_rag.ingestion.loaders import load_records

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_dataset" / "qa_pairs.jsonl"


def money(amount: Decimal) -> str:
    return f"${amount:,.2f}"


@dataclass
class Corpus:
    customers: dict[str, Customer] = field(default_factory=dict)
    products: dict[str, Product] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    line_items: list[OrderLineItem] = field(default_factory=list)
    invoices: dict[str, Invoice] = field(default_factory=dict)

    def customer(self, pattern: str) -> list[Customer]:
        return [c for c in self.customers.values() if re.search(pattern, c.name)]

    def product(self, name: str, brand_word: str = "") -> list[Product]:
        return [p for p in self.products.values() if p.name == name and brand_word in p.brand]

    def orders_of(self, customer: Customer) -> list[Order]:
        return [o for o in self.orders.values() if o.customer_id == customer.id]

    def invoice_of(self, order: Order) -> Invoice | None:
        return next((i for i in self.invoices.values() if i.order_id == order.id), None)

    def invoices_of(self, customer: Customer) -> list[Invoice]:
        return [i for o in self.orders_of(customer) if (i := self.invoice_of(o))]

    def lines_of(self, order: Order) -> list[OrderLineItem]:
        return [li for li in self.line_items if li.order_id == order.id]

    def sold_lines(self, product: Product) -> list[OrderLineItem]:
        return [
            li
            for li in self.line_items
            if li.product_id == product.id
            and self.orders[li.order_id].status != OrderStatus.CANCELLED
        ]


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    c = Corpus()
    for record in load_records():
        match record:
            case Customer():
                c.customers[record.id] = record
            case Product():
                c.products[record.id] = record
            case Order():
                c.orders[record.id] = record
            case OrderLineItem():
                c.line_items.append(record)
            case Invoice():
                c.invoices[record.id] = record
    return c


# Each verifier returns (exact expected source ids, facts the answer must contain).
Verified = tuple[set[str], list[str]]


def _unique(items: list) -> object:
    assert len(items) == 1, f"expected exactly one match, got {len(items)}"
    return items[0]


def q001(c: Corpus) -> Verified:
    i = c.invoices["INV-0057"]
    return {i.id}, [i.id, str(i.due_date), i.status.value]


def q002(c: Corpus) -> Verified:
    p = _unique(c.product("Sticky Notes", "Warner"))
    assert p.quantity_in_stock < p.reorder_threshold
    # Numbers are checked with their context: a bare "4" would also match "PROD-0040".
    return {p.id}, [
        p.id,
        f"{p.quantity_in_stock} units left",
        f"threshold is {p.reorder_threshold}",
    ]


def q003(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Elizabeth Riggs"))
    return {cu.id}, [cu.email]


def q004(c: Corpus) -> Verified:
    # Ambiguous: turn 1 only needs the candidates, to see there are several and ask.
    rods = c.product("Aluminum Rod")
    assert len(rods) > 1, "only ambiguous if several products share the name"
    return {p.id for p in rods}, [f"{len(rods)} different products called Aluminum Rod"]


def q005(c: Corpus) -> Verified:
    p = _unique(c.product("Mechanical Keyboard", "Adams-Clark"))
    return {p.id}, [p.id, money(p.unit_price)]


def q006(c: Corpus) -> Verified:
    low = [p for p in c.products.values() if p.quantity_in_stock < p.reorder_threshold]
    facts = [f"{len(low)} products"]
    facts += [f"{p.id} {p.name} by {p.brand} ({p.quantity_in_stock} in stock" for p in low]
    return {p.id for p in low}, facts


def q007(c: Corpus) -> Verified:
    shipped = [o for o in c.orders.values() if o.status == OrderStatus.SHIPPED]
    facts = [f"{len(shipped)} orders"]
    facts += [f"{o.id} ({c.customers[o.customer_id].name}" for o in shipped]
    return {o.id for o in shipped} | {o.customer_id for o in shipped}, facts


def q008(c: Corpus) -> Verified:
    end_of_month = date(CORPUS_REFERENCE_DATE.year, CORPUS_REFERENCE_DATE.month, 31)
    due = [
        i
        for i in c.invoices.values()
        if i.payment_date is None and CORPUS_REFERENCE_DATE <= i.due_date <= end_of_month
    ]
    facts = [f"{len(due)} unpaid invoices"]
    facts += [f"{i.id} ({money(i.amount)}, due {i.due_date})" for i in due]
    return {i.id for i in due}, facts


def q009(c: Corpus) -> Verified:
    pricey = [
        p
        for p in c.products.values()
        if p.category == "Electronics" and p.unit_price > Decimal(450)
    ]
    facts = [f"{len(pricey)} Electronics products"]
    facts += [f"{p.id} {p.name} by {p.brand} ({money(p.unit_price)})" for p in pricey]
    return {p.id for p in pricey}, facts


def q010(c: Corpus) -> Verified:
    cancelled = [
        o
        for o in c.orders.values()
        if o.status == OrderStatus.CANCELLED and o.order_date >= date(2026, 9, 1)
    ]
    facts = [f"{len(cancelled)} orders"]
    facts += [
        f"{o.id} ({c.customers[o.customer_id].name}, placed {o.order_date})" for o in cancelled
    ]
    return {o.id for o in cancelled} | {o.customer_id for o in cancelled}, facts


def q011(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Elizabeth Riggs"))
    orders = c.orders_of(cu)
    n_cancelled = sum(o.status == OrderStatus.CANCELLED for o in orders)
    return {cu.id} | {o.id for o in orders}, [
        f"{len(orders)} orders",
        f"{n_cancelled} of which were cancelled",
    ]


def _overdue(c: Corpus, cu: Customer) -> list[Invoice]:
    return [i for i in c.invoices_of(cu) if i.status == InvoiceStatus.OVERDUE]


def q012(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Jeffrey Cox"))
    overdue = _overdue(c, cu)
    facts = [f"{len(overdue)} overdue invoices", money(sum(i.amount for i in overdue))]
    facts += [i.id for i in overdue]
    return {cu.id} | {i.id for i in overdue} | {i.order_id for i in overdue}, facts


def q013(c: Corpus) -> Verified:
    # Ambiguous: turn 1 only needs the candidate customers, not their invoices.
    lees = c.customer(r"\bLee\b")
    assert len(lees) > 1, "only ambiguous if several customers match"
    return {cu.id for cu in lees}, ["customers are named Lee"]


def q014(c: Corpus) -> Verified:
    p = _unique(c.product("Sticky Notes", "Warner"))
    lines = c.sold_lines(p)
    facts = [f"{sum(li.quantity for li in lines)} units", f"{len(lines)} order lines"]
    facts += [li.id for li in lines]
    return {p.id} | {li.id for li in lines} | {li.order_id for li in lines}, facts


def q015(c: Corpus) -> Verified:
    paid = [
        i
        for i in c.invoices.values()
        if i.payment_date is not None and date(2026, 7, 1) <= i.payment_date <= date(2026, 9, 30)
    ]
    return {i.id for i in paid}, [money(sum(i.amount for i in paid)), f"{len(paid)} invoices"]


def q016(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Lori Clay"))
    latest = max(c.orders_of(cu), key=lambda o: o.order_date)
    lines = c.lines_of(latest)
    facts = [latest.id, str(latest.order_date), latest.status.value]
    facts += [f"{li.quantity} x {c.products[li.product_id].name}" for li in lines]
    sources = {cu.id, latest.id} | {li.id for li in lines} | {li.product_id for li in lines}
    return sources, facts


def q017(c: Corpus) -> Verified:
    i = _unique([i for i in c.invoices.values() if i.amount == Decimal("12636.26")])
    o = c.orders[i.order_id]
    cu = c.customers[o.customer_id]
    return {i.id, o.id, cu.id}, [i.id, cu.name, cu.country]


def q018(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Mark Lloyd"))
    invoices = c.invoices_of(cu)
    unpaid = [i for i in invoices if i.payment_date is None]
    facts = ["No." if unpaid else "Yes.", f"{len(invoices)} invoices"]
    facts += [f"{i.id} ({money(i.amount)}) is {i.status.value}" for i in unpaid]
    return {cu.id} | {i.order_id for i in invoices} | {i.id for i in invoices}, facts


def q019(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Shawn Arroyo"))
    latest = max(c.orders_of(cu), key=lambda o: o.order_date)
    assert latest.status == OrderStatus.SHIPPED, "the question says it just shipped"
    i = c.invoice_of(latest)
    return {cu.id, latest.id, i.id}, [latest.id, i.id, money(i.amount), str(i.due_date)]


def q020(c: Corpus) -> Verified:
    p = _unique(c.product("Sticky Notes", "Warner"))
    assert p.quantity_in_stock < p.reorder_threshold, "the question says it's running low"
    lines = c.sold_lines(p)
    buyers = {c.orders[li.order_id].customer_id for li in lines}
    facts = [f"{len(buyers)} customers"]
    facts += [f"{c.customers[b].name} ({b})" for b in buyers]
    sources = {p.id} | {li.id for li in lines} | {li.order_id for li in lines} | buyers
    return sources, facts


VERIFIERS = {name: fn for name, fn in globals().items() if re.fullmatch(r"q\d{3}", name)}


# --- Ambiguous entries: clarify first, then answer (ARCHITECTURE.md §4c) ---------
#
# Turn 1 is a short explanation plus a clarifying question that offers a few example
# options (never the full list unless the user asks for it). Turn 2 answers the
# user's follow-up, and only then are the detailed records retrieved.

MAX_EXAMPLE_OPTIONS = 3

# All records the ambiguous wording could refer to, as the labels a user would pick from.
CANDIDATES = {
    "q004": lambda c: [p.brand for p in c.product("Aluminum Rod")],
    "q013": lambda c: [cu.name for cu in c.customer(r"\bLee\b")],
}


def q004_follow_up(c: Corpus) -> Verified:
    p = _unique(c.product("Aluminum Rod", "Hancock and Sons"))
    return {p.id}, [
        p.id,
        f"{p.quantity_in_stock} units left",
        f"reorder threshold of {p.reorder_threshold}",
    ]


def q013_follow_up(c: Corpus) -> Verified:
    cu = _unique(c.customer(r"Charles Lee"))
    overdue = _overdue(c, cu)
    facts = [f"{len(overdue)} overdue invoices", money(sum(i.amount for i in overdue))]
    facts += [i.id for i in overdue]
    return {cu.id} | {i.id for i in overdue} | {i.order_id for i in overdue}, facts


FOLLOW_UP_VERIFIERS = {"q004": q004_follow_up, "q013": q013_follow_up}


def _entries() -> list[dict]:
    lines = GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_every_entry_has_a_verifier_and_vice_versa():
    """A new golden entry can't land without a way to prove its answer is true."""
    assert {entry["id"] for entry in _entries()} == set(VERIFIERS)


@pytest.mark.parametrize("entry", _entries(), ids=lambda entry: entry["id"])
def test_expected_answer_is_true_against_the_corpus(entry, corpus):
    expected_sources, facts = VERIFIERS[entry["id"]](corpus)

    assert set(entry["expected_source_ids"]) == expected_sources
    missing = [fact for fact in facts if fact not in entry["expected_answer"]]
    assert not missing, f"answer is missing or contradicts: {missing}"


def test_every_ambiguous_entry_has_candidates_and_a_follow_up_verifier():
    ambiguous_ids = {entry["id"] for entry in _entries() if entry["ambiguous"]}

    assert ambiguous_ids == set(CANDIDATES) == set(FOLLOW_UP_VERIFIERS)


@pytest.mark.parametrize("entry", _entries(), ids=lambda entry: entry["id"])
def test_only_ambiguous_entries_ask_a_question(entry):
    assert ("?" in entry["expected_answer"]) == entry["ambiguous"]


@pytest.mark.parametrize(
    "entry", [e for e in _entries() if e["ambiguous"]], ids=lambda entry: entry["id"]
)
def test_clarifying_question_offers_a_few_options_not_the_full_list(entry, corpus):
    candidates = CANDIDATES[entry["id"]](corpus)
    offered = [label for label in candidates if label in entry["expected_answer"]]

    assert offered, "the clarifying question should suggest at least one real option"
    if len(candidates) > MAX_EXAMPLE_OPTIONS:
        assert len(offered) <= MAX_EXAMPLE_OPTIONS, "list examples, not every option"


@pytest.mark.parametrize(
    "entry", [e for e in _entries() if e["ambiguous"]], ids=lambda entry: entry["id"]
)
def test_follow_up_answer_is_true_against_the_corpus(entry, corpus):
    expected_sources, facts = FOLLOW_UP_VERIFIERS[entry["id"]](corpus)

    assert set(entry["follow_up_source_ids"]) == expected_sources
    missing = [fact for fact in facts if fact not in entry["follow_up_answer"]]
    assert not missing, f"follow-up answer is missing or contradicts: {missing}"
