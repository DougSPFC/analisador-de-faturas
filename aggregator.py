"""Totais por categoria/fatura/combinado — pandas puro, sem dependência de Streamlit."""
from __future__ import annotations

import pandas as pd

from categorizer import CategoryRule
from models import TRANSACTION_COLUMNS, Invoice

ESSENTIAL_KEYS = {"mercado", "farmacia", "posto"}


def _essential_labels(rules: list[CategoryRule]) -> set[str]:
    return {r.label for r in rules if r.key in ESSENTIAL_KEYS}


def invoice_to_dataframe(invoice: Invoice) -> pd.DataFrame:
    rows = [
        {
            "date": t.date,
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "needs_review": t.needs_review,
            "raw_line": t.raw_line,
        }
        for t in invoice.transactions
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def combine_invoices(invoices: dict[str, dict]) -> pd.DataFrame:
    """`invoices` é um dict {chave: {"label": str, "df": DataFrame}}; retorna tudo empilhado com coluna `fatura`."""
    frames = []
    for info in invoices.values():
        df = info["df"].copy()
        df["fatura"] = info["label"]
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=[*TRANSACTION_COLUMNS, "fatura"])
    return pd.concat(frames, ignore_index=True)


def totals_by_category(df: pd.DataFrame, rules: list[CategoryRule]) -> pd.DataFrame:
    excluded_labels = {r.label for r in rules if r.excluded_from_spend_total}
    spend_df = df[~df["category"].isin(excluded_labels)]
    grand_total = spend_df["amount"].sum()

    rows = []
    for rule in rules:
        subset = df[df["category"] == rule.label]
        total = subset["amount"].sum()
        rows.append(
            {
                "key": rule.key,
                "label": rule.label,
                "priority": rule.priority,
                "total": total,
                "pct": (total / grand_total * 100) if grand_total and not rule.excluded_from_spend_total else 0.0,
                "n_transacoes": len(subset),
                "excluded_from_spend_total": rule.excluded_from_spend_total,
            }
        )
    result = pd.DataFrame(rows).sort_values("priority").reset_index(drop=True)
    return result[result["n_transacoes"] > 0].reset_index(drop=True)


def summary_metrics(df: pd.DataFrame, rules: list[CategoryRule], n_invoices: int) -> dict:
    excluded_labels = {r.label for r in rules if r.excluded_from_spend_total}
    spend_df = df[~df["category"].isin(excluded_labels)]
    essential_df = spend_df[spend_df["category"].isin(_essential_labels(rules))]
    return {
        "total_gasto": spend_df["amount"].sum(),
        "total_essencial": essential_df["amount"].sum(),
        "n_transacoes": len(spend_df),
        "n_faturas": n_invoices,
    }
