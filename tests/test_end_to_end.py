from fixtures.make_synthetic_pdf import build_synthetic_pdf_bytes

from aggregator import invoice_to_dataframe, summary_metrics, totals_by_category
from categorizer import categorize_dataframe, load_categories
from pdf_parser import parse_pdf

rules = load_categories()


def test_full_pipeline_matches_hand_computed_totals():
    invoice = parse_pdf(build_synthetic_pdf_bytes(), filename="synthetic.pdf")
    df = invoice_to_dataframe(invoice)
    df = categorize_dataframe(df, rules)

    metrics = summary_metrics(df, rules, n_invoices=1)

    # Gastos (exclui só o pagamento; o estorno entra e anula a compra cancelada):
    # 350 + 45.90 + 200 + 58.30 + 23.50 + 39.90 + 60 + 99.99 - 58.30
    assert round(metrics["total_gasto"], 2) == 819.29
    # Essenciais: mercado (350) + farmacia (45.90) + posto (200)
    assert round(metrics["total_essencial"], 2) == 595.90
    assert metrics["n_transacoes"] == 9

    totals = totals_by_category(df, rules)
    priorities = list(totals["priority"])
    assert priorities == sorted(priorities)
