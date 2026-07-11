"""Extração de transações de faturas em PDF (layouts variados de bancos brasileiros)."""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date

import pdfplumber

from bank_profiles import CARD_SUFFIX_RE, GENERIC_LINE_RE, NOISE_SUBSTRINGS, detect_bank
from models import Invoice, Transaction

VENCIMENTO_RE = re.compile(r"vencimento[:\s]*(\d{2})/(\d{2})/(\d{2,4})", re.IGNORECASE)

MONTH_ABBR = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def is_noise_line(line: str, extra_excludes: list[str] | None = None) -> bool:
    normalized = _strip_accents(line.lower())
    excludes = NOISE_SUBSTRINGS + (extra_excludes or [])
    return any(term in normalized for term in excludes)


def clean_line(line: str) -> str:
    """Remove sufixos de cartão mascarado ('•••• 0985') e colapsa espaços, antes do match."""
    cleaned = CARD_SUFFIX_RE.sub(" ", line)
    return " ".join(cleaned.split())


def parse_brl_value(raw: str) -> float:
    """Converte 'R$ 1.234,56', '−R$ 123,45' (estorno) ou '123,45-' em float com sinal.

    Bancos diferentes colocam o sinal de negativo antes ou depois do valor, e alguns usam
    o sinal matemático '−' (U+2212) em vez do hífen comum — aceitamos os dois.
    """
    raw = raw.strip()
    negative = raw.startswith("-") or raw.startswith("−") or raw.endswith("-") or raw.endswith("−")
    cleaned = raw.replace("R$", "").replace("$", "").replace("-", "").replace("−", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    value = float(cleaned)
    return -value if negative else value


def infer_year(day: int, month: int, reference_date: date | None) -> int:
    """Ancora uma data sem ano na data de vencimento da fatura, tratando virada dez/jan."""
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
    raw = raw.strip()
    if "/" in raw:
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

    # Formato "DD MMM" (ex: "27 MAI"), usado por faturas em estilo "linha do tempo".
    match = re.match(r"(\d{2})\s+([A-Za-z]{3})", raw)
    if not match:
        return None
    day = int(match.group(1))
    month = MONTH_ABBR.get(match.group(2).lower())
    if month is None:
        return None
    year = infer_year(day, month, reference_date)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _extract_lines_from_tables(page) -> list[str]:
    lines = []
    for table in page.extract_tables() or []:
        for row in table:
            cells = [str(c).strip() for c in row if c]
            if cells:
                lines.append(" ".join(cells))
    return lines


def _words_to_lines(words: list[dict], y_tolerance: float = 3.0) -> list[str]:
    """Reagrupa palavras (com posição) em linhas de texto, por proximidade vertical."""
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (round(w["top"] / y_tolerance), w["x0"]))
    lines: list[str] = []
    current_bucket = None
    current_words: list[dict] = []
    for w in ordered:
        bucket = round(w["top"] / y_tolerance)
        if current_bucket is None or bucket != current_bucket:
            if current_words:
                lines.append(" ".join(x["text"] for x in current_words))
            current_words = [w]
            current_bucket = bucket
        else:
            current_words.append(w)
    if current_words:
        lines.append(" ".join(x["text"] for x in current_words))
    return lines


def _find_column_gutter(words: list[dict], page_width: float) -> float | None:
    """Acha o maior espaço vazio horizontal na faixa central da página — o "corredor"
    entre duas colunas de texto lado a lado. Retorna None se não houver um espaço claro
    (página de coluna única), para não dividir texto que não deveria ser dividido."""
    lo, hi = page_width * 0.25, page_width * 0.75
    xs = sorted({round(w["x0"]) for w in words if lo <= w["x0"] <= hi})
    if len(xs) < 2:
        return None
    best_gap, best_mid = 0.0, None
    for a, b in zip(xs, xs[1:]):
        gap = b - a
        if gap > best_gap:
            best_gap, best_mid = gap, (a + b) / 2
    return best_mid if best_gap >= 10 else None


def _extract_lines_two_column(page) -> list[str]:
    """Fallback para faturas em duas colunas lado a lado (ex: Santander), onde
    `extract_text()` intercala o texto das duas colunas na mesma linha visual.
    Detecta o corredor entre as colunas e reconstrói cada lado separadamente antes
    de tentar casar a regex de transação.
    """
    try:
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    except Exception:
        return []
    if len(words) < 20:
        return []
    gutter = _find_column_gutter(words, page.width)
    if gutter is None:
        return []
    left = [w for w in words if w["x0"] < gutter]
    right = [w for w in words if w["x0"] >= gutter]
    return _words_to_lines(left, y_tolerance=2.0) + _words_to_lines(right, y_tolerance=2.0)


def _count_matches(lines: list[str]) -> int:
    count = 0
    for line in lines:
        cleaned = clean_line(line.strip())
        if not cleaned or is_noise_line(cleaned):
            continue
        if GENERIC_LINE_RE.match(cleaned):
            count += 1
    return count


def _best_lines_for_page(page, page_lines: list[str]) -> list[str]:
    """Escolhe, entre a extração simples de texto e dois fallbacks (tabela e duas
    colunas), a que reconhece mais linhas de transação — necessário porque faturas
    diferentes exigem estratégias de extração diferentes.

    Sempre comparamos as três estratégias (mesmo quando a extração simples já
    "acerta" algumas linhas): em layouts de duas colunas, o texto simples pode
    colar linhas de colunas diferentes numa só — o que ainda conta como uma
    correspondência (só que com dados errados) e não pode vencer por padrão.

    Um fallback só é aceito se reconhecer pelo menos 3 transações: páginas sem
    nenhuma transação de verdade (resumo, propaganda) às vezes geram 1 ou 2
    "transações" falsas ao reagrupar palavras por posição, e não queremos que
    esse ruído vença uma extração original correta (mas com poucas transações).
    """
    best_lines, best_count = page_lines, _count_matches(page_lines)

    MIN_ACCEPT = 3
    for candidate in (_extract_lines_from_tables(page), _extract_lines_two_column(page)):
        if not candidate:
            continue
        count = _count_matches(candidate)
        if count > best_count and count >= MIN_ACCEPT:
            best_lines, best_count = candidate, count
    return best_lines


def parse_pdf(file_bytes: bytes, filename: str = "") -> Invoice:
    full_text_parts: list[str] = []
    raw_lines: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text_parts.append(text)
            page_lines = [ln for ln in text.split("\n") if ln.strip()]
            raw_lines.extend(_best_lines_for_page(page, page_lines))

    full_text = "\n".join(full_text_parts)
    profile = detect_bank(full_text)
    reference_date = _find_reference_date(full_text)
    line_regex = profile.line_regex or GENERIC_LINE_RE

    if profile.preprocess:
        raw_lines = [profile.preprocess(ln) for ln in raw_lines]

    transactions: list[Transaction] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        cleaned = clean_line(stripped)
        if not cleaned or is_noise_line(cleaned, profile.extra_excludes):
            continue
        match = line_regex.match(cleaned)
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
