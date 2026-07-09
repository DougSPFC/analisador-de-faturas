"""Gera um PDF sintético de fatura para testes automatizados e smoke test manual.

Roda como script (`python tests/fixtures/make_synthetic_pdf.py`) para regravar
`synthetic_fatura.pdf`, ou é importado pelos testes via `build_synthetic_pdf_bytes()`.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

LINES = [
    "FATURA CARTAO DE CREDITO - BANCO GENERICO",
    "Vencimento: 10/07/2026",
    "SALDO ANTERIOR 0,00",
    "01/06 SUPERMERCADO BOM PRECO 350,00",
    "02/06 FARMACIA DROGA RAIA 45,90",
    "03/06 POSTO IPIRANGA COMBUSTIVEL 200,00",
    "04/06 IFOOD DELIVERY 58,30",
    "05/06 UBER TRIP 23,50",
    "06/06 NETFLIX.COM 39,90",
    "07/06 CINEMA SHOPPING 60,00",
    "08/06 LOJA DESCONHECIDA XYZ 99,99",
    "09/06 PAGAMENTO EFETUADO 500,00-",
    "10/06 ESTORNO COMPRA CANCELADA 58,30-",
    "TOTAL DESTA FATURA 918,79",
    "PAGINA 1 DE 1",
]

OUTPUT_PATH = Path(__file__).parent / "synthetic_fatura.pdf"


def build_synthetic_pdf_bytes(lines: list[str] = LINES) -> bytes:
    import io

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    text_obj = c.beginText(40, height - 60)
    text_obj.setFont("Helvetica", 10)
    for line in lines:
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.showPage()
    c.save()
    return buffer.getvalue()


if __name__ == "__main__":
    OUTPUT_PATH.write_bytes(build_synthetic_pdf_bytes())
    print(f"PDF sintético gravado em {OUTPUT_PATH}")
