"""Modelos de dados compartilhados entre parser, categorizador e agregador."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Transaction:
    date: date | None
    description: str
    amount: float  # positivo = gasto, negativo = crédito/estorno/pagamento
    category: str = "outros"
    source_label: str = ""
    raw_line: str = ""
    needs_review: bool = False


@dataclass
class Invoice:
    label: str
    filename: str
    bank_guess: str | None = None
    reference_month: str | None = None  # "AAAA-MM", inferido do vencimento
    transactions: list[Transaction] = field(default_factory=list)
    raw_text: str = ""


# Ordem única das colunas usada tanto para montar o DataFrame quanto para o
# st.data_editor, evitando divergência entre as duas pontas.
TRANSACTION_COLUMNS = [
    "date",
    "description",
    "amount",
    "category",
    "needs_review",
    "raw_line",
]
