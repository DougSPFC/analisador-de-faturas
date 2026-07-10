import pandas as pd

from aggregator import summary_metrics, totals_by_category
from categorizer import load_categories
from models import TRANSACTION_COLUMNS

rules = load_categories()


def _make_df():
    rows = [
        {"date": None, "description": "SUPERMERCADO", "amount": 100.0, "category": "Mercado/Supermercado", "needs_review": False, "raw_line": ""},
        {"date": None, "description": "FARMACIA", "amount": 50.0, "category": "Farmácia/Saúde", "needs_review": False, "raw_line": ""},
        {"date": None, "description": "CINEMA", "amount": 30.0, "category": "Lazer/Entretenimento", "needs_review": False, "raw_line": ""},
        {"date": None, "description": "PAGAMENTO EFETUADO", "amount": -100.0, "category": "Pagamentos e Créditos", "needs_review": False, "raw_line": ""},
    ]
    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def test_totals_by_category_orders_by_priority_and_excludes_empty_categories():
    df = _make_df()
    totals = totals_by_category(df, rules)

    assert list(totals["label"]) == [
        "Pagamentos e Créditos",
        "Mercado/Supermercado",
        "Farmácia/Saúde",
        "Lazer/Entretenimento",
    ]
    assert totals.loc[totals["label"] == "Mercado/Supermercado", "total"].iloc[0] == 100.0


def test_totals_by_category_pct_ignores_excluded_category():
    df = _make_df()
    totals = totals_by_category(df, rules)
    # grand_total (gasto) = 100 + 50 + 30 = 180
    mercado_pct = totals.loc[totals["label"] == "Mercado/Supermercado", "pct"].iloc[0]
    assert round(mercado_pct, 2) == round(100 / 180 * 100, 2)


def test_summary_metrics_excludes_payments_from_totals():
    df = _make_df()
    metrics = summary_metrics(df, rules, n_invoices=1)

    assert metrics["total_gasto"] == 180.0
    assert metrics["total_essencial"] == 150.0  # mercado + farmacia
    assert metrics["n_transacoes"] == 3  # payments line excluded
    assert metrics["n_faturas"] == 1
