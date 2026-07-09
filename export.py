"""Geração de bytes CSV/Excel para os botões de download do app."""
from __future__ import annotations

import io

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(invoices: dict[str, dict], resumo: pd.DataFrame) -> bytes:
    """Gera um Excel com uma aba `Resumo` + uma aba por fatura."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
        for info in invoices.values():
            sheet_name = info["label"][:31] or "Fatura"
            info["df"].to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()
