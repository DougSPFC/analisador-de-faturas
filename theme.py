"""Paleta de cores, CSS e componentes visuais do Analisador de Faturas.

Mantido separado de app.py porque é puro "look and feel" (cores, CSS, HTML de
cards) — nenhuma lógica de negócio aqui.
"""
from __future__ import annotations

# Uma cor por categoria (mesma ordem de prioridade das outras telas), usada no
# gráfico de barras. Cores distintas o bastante para não precisar repetir.
CATEGORY_COLORS = {
    "Mercado/Supermercado": "#3987e5",
    "Farmácia/Saúde": "#1baf7a",
    "Posto/Combustível": "#e0a530",
    "Alimentação/Restaurante": "#e0c22e",
    "Transporte": "#9085e9",
    "Assinaturas": "#e66767",
    "Contas/Serviços": "#d55181",
    "Vestuário": "#d95926",
    "Compras online": "#2dd4bf",
    "Encargos/Juros/IOF": "#a78355",
    "Lazer/Entretenimento": "#f472b6",
}
DEFAULT_CATEGORY_COLOR = "#8b90a3"

# Selo emoji ao lado do título de cada categoria expansível — Streamlit não
# permite HTML/CSS dentro do rótulo de um expander, só texto/emoji, então usamos
# os emojis nativos de círculo/quadrado colorido como aproximação visual da cor
# usada no gráfico (mesma família de cor, não é um match exato de hex).
CATEGORY_BADGES = {
    "Mercado/Supermercado": "🟢",
    "Farmácia/Saúde": "🟩",
    "Posto/Combustível": "🟠",
    "Alimentação/Restaurante": "🟡",
    "Transporte": "🔵",
    "Assinaturas": "🔴",
    "Contas/Serviços": "🟣",
    "Vestuário": "🟤",
    "Compras online": "🟦",
    "Encargos/Juros/IOF": "🟧",
    "Lazer/Entretenimento": "🟪",
}
DEFAULT_BADGE = "⚪"
PAGAMENTOS_BADGE = "💳"
OUTROS_BADGE = "❓"


def category_color(label: str) -> str:
    return CATEGORY_COLORS.get(label, DEFAULT_CATEGORY_COLOR)


def category_badge(label: str) -> str:
    if label == "Não identificado/Outros":
        return OUTROS_BADGE
    if label == "Pagamentos e Créditos":
        return PAGAMENTOS_BADGE
    return CATEGORY_BADGES.get(label, DEFAULT_BADGE)


GLOBAL_CSS = """
<style>
h1 {
    font-size: 2.75rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
}
h2, h3 {
    font-weight: 700 !important;
}
[data-testid="stMarkdownContainer"] p {
    font-size: 1.02rem;
}
[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    overflow: hidden;
    margin-bottom: 0.6rem;
}
[data-testid="stExpander"] summary {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    padding: 0.9rem 1.1rem !important;
}
.stButton > button, .stDownloadButton > button {
    border-radius: 999px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
}
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden;
}
[data-testid="stFileUploaderDropzone"] {
    border-radius: 14px !important;
}
</style>
"""


def stat_card(label: str, value: str, accent: str, help_text: str = "") -> str:
    """Card de resumo estilo dashboard financeiro: fundo escuro fixo, faixa e
    rótulo na cor de destaque, valor grande em negrito. Fundo fixo (não
    depende do tema claro/escuro da página) para não ficar ilegível se o
    usuário trocar o tema do Streamlit."""
    subtitle = f'<div style="color:#8b90a3; font-size:0.78rem; margin-top:6px;">{help_text}</div>' if help_text else ""
    return f"""
    <div style="
        background: #141826;
        border: 1px solid {accent}55;
        border-left: 4px solid {accent};
        border-radius: 14px;
        padding: 18px 20px;
        height: 100%;
    ">
        <div style="color:{accent}; font-size:0.75rem; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; margin-bottom:10px;">{label}</div>
        <div style="color:#F2F3F7; font-size:1.9rem; font-weight:800; line-height:1.1;">{value}</div>
        {subtitle}
    </div>
    """
