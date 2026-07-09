"""Extração de transações de faturas em PDF (layouts variados de bancos brasileiros)."""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date

import pdfplumber

from bank_profiles import GENERIC_LINE_RE, NOISE_SUBSTRINGS, detect_bank
from models import Invoice, Transaction

VENCIMENTO_RE = re.compile(r"vencimento[:\s]*(\d{2})/(\d{2})/(\d{2,4})", re.IGNORECASE)


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def is_noise_line(line: str, extra_excludes: list[str] | None = None) -> bool:
    normalized = _strip_accents(line.lower())
    excludes = NOISE_SUBSTRINGS + (extra_excludes or [])
    return any(term in normalized for term in excludes)


def parse_brl_value(raw: str) -> float:
    """Converte '1.234,56', 'R$ 123,45', '123,45-' (estorno) etc. em float com sinal."""
    raw = raw.strip()
    negative = raw.startswith("-") or raw.endswith("-")
    cleaned = raw.replace("R$", "").replace("$", "").replace("-", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    value = float(cleaned)
    return -value if negative else value


def infer_year(day: int, month: int, reference_date: date | None) -> int:
    """Ancora um DD/MM sem ano na data de vencimento da fatura, tratando virada dez/jan."""
    if reference_date is None:
        return date.today().year
    year = reference_date.year
    # Se o mês da transação é bem maior que o mês de referência (ex: transação em 12,
    # vencimento em 01), a transação é do ano anterior.
    if month - reference_date.month > 6:
        year -= 1
    elif reference_date.month - month > 6:
        year += 1
    return year


def _find_reference_date(text: str) -> date | None:
    match = VENCIMENTO_RE.search(text)
    if not match:
        return None
    day, month, year = match.groups()
    year_int = int(year)
    if year_int < 100:
        year_int += 2000
    try:
        return date(year_int, int(month), int(day))
    except ValueError:
        return None


def _parse_date(raw: str, reference_date: date | None) -> date | None:
    parts = raw.split("/")
    try:
        day, month = int(parts[0]), int(parts[1])
        if len(parts) == 3:
            year = int(parts[2])
            if year < 100:
                year += 2000
        else:
            year = infer_year(day, month, reference_date)
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _extract_lines_from_tables(page) -> list[str]:
    lines = []
    for table in page.extract_tables() or []:
        for row in table:
            cells = [str(c).strip() for c in row if c]
            if cells:
                lines.append(" ".join(cells))
    return lines


def parse_pdf(file_bytes: bytes, filename: str = "") -> Invoice:
    full_text_parts: list[str] = []
    raw_lines: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text_parts.append(text)
            page_lines = [ln for ln in text.split("\n") if ln.strip()]

            matches_on_page = sum(1 for ln in page_lines if GENERIC_LINE_RE.match(ln.strip()))
            if matches_on_page < 3:
                table_lines = _extract_lines_from_tables(page)
                if len(table_lines) > len(page_lines):
                    page_lines = table_lines

            raw_lines.extend(page_lines)

    full_text = "\n".join(full_text_parts)
    profile = detect_bank(full_text)
    reference_date = _find_reference_date(full_text)
    line_regex = profile.line_regex or GENERIC_LINE_RE

    if profile.preprocess:
        raw_lines = [profile.preprocess(ln) for ln in raw_lines]

    transactions: list[Transaction] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped or is_noise_line(stripped, profile.extra_excludes):
            continue
        match = line_regex.match(stripped)
        if not match:
            continue
        parsed_date = _parse_date(match.group("date"), reference_date)
        try:
            amount = parse_brl_value(match.group("value"))
        except ValueError:
            continue
        description = match.group("desc").strip()
        transactions.append(
            Transaction(
                date=parsed_date,
                description=description,
                amount=amount,
                raw_line=stripped,
                needs_review=parsed_date is None,
            )
        )

    reference_month = f"{reference_date.year:04d}-{reference_date.month:02d}" if reference_date else None

    return Invoice(
        label=f"{profile.name} - {reference_month or filename}",
        filename=filename,
        bank_guess=profile.name,
        reference_month=reference_month,
        transactions=transactions,
        raw_text=full_text,
    )
