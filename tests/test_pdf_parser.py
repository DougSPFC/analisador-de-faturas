from datetime import date

from fixtures.make_synthetic_pdf import build_synthetic_pdf_bytes
from pdf_parser import parse_pdf


def test_parse_pdf_extracts_expected_transactions():
    invoice = parse_pdf(build_synthetic_pdf_bytes(), filename="synthetic.pdf")

    assert len(invoice.transactions) == 10
    descriptions = [t.description for t in invoice.transactions]
    assert "SUPERMERCADO BOM PRECO" in descriptions
    assert not any("SALDO ANTERIOR" in d for d in descriptions)
    assert not any("TOTAL DESTA FATURA" in d for d in descriptions)

    first = invoice.transactions[0]
    assert first.date == date(2026, 6, 1)
    assert first.amount == 350.00
    assert first.needs_review is False


def test_parse_pdf_handles_negative_values():
    invoice = parse_pdf(build_synthetic_pdf_bytes(), filename="synthetic.pdf")
    payment = next(t for t in invoice.transactions if "PAGAMENTO EFETUADO" in t.description)
    estorno = next(t for t in invoice.transactions if "ESTORNO" in t.description)

    assert payment.amount == -500.00
    assert estorno.amount == -58.30


def test_parse_pdf_infers_reference_month_from_vencimento():
    invoice = parse_pdf(build_synthetic_pdf_bytes(), filename="synthetic.pdf")
    assert invoice.reference_month == "2026-07"
