"""Perfis por banco: permitem sobrescrever regex/exclusões sem tocar no parser genérico.

v1 roda apenas com o perfil genérico. Para dar suporte a um layout específico que o
genérico não cobrir bem, adicione uma nova entrada em PROFILES (antes do genérico).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

# Data numérica (21/06, 21/06/2026) ou por extenso abreviado (21 JUN) — os dois formatos
# aparecem em faturas reais (bancos com layout tabular vs. layout "timeline" tipo Nubank).
DATE_PATTERN = r"(?:\d{2}/\d{2}(?:/\d{2,4})?|\d{2}\s+(?:JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ))"

# Sinal negativo pode ser o hífen comum OU o sinal matemático "−" (U+2212) que alguns
# bancos usam para estornos/pagamentos, aparecendo antes OU depois do valor.
GENERIC_LINE_RE = re.compile(
    r"^(?:\d+\s+)?(?P<date>" + DATE_PATTERN + r")\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<value>[-−]?\s?R?\$?\s?\d{1,3}(?:\.\d{3})*,\d{2}\s?[-−]?)\s*$",
    re.IGNORECASE,
)

# Sufixo de cartão mascarado (ex: "•••• 0985", "**** 1234") que aparece entre a data e a
# descrição em algumas faturas — removido antes do match para não poluir a descrição.
CARD_SUFFIX_RE = re.compile(r"[•*]{3,}\s*\d{3,4}\b")

# Linhas que nunca são transação, mesmo que casem com a regex por acidente.
NOISE_SUBSTRINGS = [
    "saldo anterior",
    "saldo atual",
    "total desta fatura",
    "total da fatura",
    "limite disponivel",
    "limite disponível",
    "limite de credito",
    "limite de crédito",
    "central de atendimento",
    "ouvidoria",
    "sac ",
    "vencimento da fatura",
    "fatura fechada",
    "pagina ",
    "página ",
]


@dataclass
class BankProfile:
    name: str
    detect: Callable[[str], bool]
    line_regex: re.Pattern | None = None
    preprocess: Callable[[str], str] | None = None
    extra_excludes: list[str] = field(default_factory=list)


GENERIC_PROFILE = BankProfile(name="Genérico", detect=lambda text: True)

PROFILES: list[BankProfile] = [GENERIC_PROFILE]


def detect_bank(text: str) -> BankProfile:
    normalized = text.lower()
    for profile in PROFILES:
        if profile is GENERIC_PROFILE:
            continue
        if profile.detect(normalized):
            return profile
    return GENERIC_PROFILE
