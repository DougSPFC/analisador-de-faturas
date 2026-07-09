"""Perfis por banco: permitem sobrescrever regex/exclusões sem tocar no parser genérico.

v1 roda apenas com o perfil genérico. Para dar suporte a um layout específico que o
genérico não cobrir bem, adicione uma nova entrada em PROFILES (antes do genérico).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

GENERIC_LINE_RE = re.compile(
    r"^(?P<date>\d{2}/\d{2}(?:/\d{2,4})?)\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<value>-?\s?R?\$?\s?\d{1,3}(?:\.\d{3})*,\d{2}\s?-?)\s*$"
)

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
