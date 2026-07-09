"""Motor de categorização por palavra-chave, offline e editável via categories.json."""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CATEGORIES_PATH = Path(__file__).parent / "categories.json"


@dataclass
class CategoryRule:
    key: str
    label: str
    priority: int
    keywords: list[str] = field(default_factory=list)
    excluded_from_spend_total: bool = False
    is_default: bool = False


def normalize_text(text: str) -> str:
    """Minúsculas, sem acento, espaços colapsados — usado tanto na descrição quanto nas keywords."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def load_categories(path: Path | str = DEFAULT_CATEGORIES_PATH) -> list[CategoryRule]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = [
        CategoryRule(
            key=c["key"],
            label=c["label"],
            priority=c["priority"],
            keywords=[normalize_text(k) for k in c.get("keywords", [])],
            excluded_from_spend_total=c.get("excluded_from_spend_total", False),
            is_default=c.get("is_default", False),
        )
        for c in data["categories"]
    ]
    rules.sort(key=lambda r: r.priority)
    return rules


def categorize(description: str, rules: list[CategoryRule]) -> str:
    """Retorna o `label` da primeira categoria (em ordem de prioridade) cuja keyword aparece na descrição.

    Usamos o label (em vez da `key` interna) como valor armazenado na coluna `category`
    porque é isso que o usuário vê e edita na tabela do Streamlit (`st.data_editor` com
    um `SelectboxColumn` de opções = labels).
    """
    normalized = normalize_text(description)
    default_label = "Não identificado/Outros"
    for rule in rules:
        if rule.is_default:
            default_label = rule.label
            continue
        for keyword in rule.keywords:
            if keyword and keyword in normalized:
                return rule.label
    return default_label


def categorize_dataframe(df, rules: list[CategoryRule] | None = None):
    """Aplica `categorize` a cada linha de um DataFrame com coluna `description`, preenchendo `category`."""
    if rules is None:
        rules = load_categories()
    df = df.copy()
    df["category"] = df["description"].apply(lambda d: categorize(d, rules))
    return df


def category_labels(rules: list[CategoryRule] | None = None) -> list[str]:
    """Lista de labels na ordem de prioridade — usada como opções do SelectboxColumn."""
    if rules is None:
        rules = load_categories()
    return [r.label for r in rules]
