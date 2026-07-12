"""Analisador de Faturas — app Streamlit.

Só orquestra UI e st.session_state; toda a lógica de negócio vive em
pdf_parser.py, categorizer.py, aggregator.py e export.py.
"""
from __future__ import annotations

import hashlib

import plotly.graph_objects as go
import streamlit as st

from aggregator import combine_invoices, invoice_to_dataframe, summary_metrics, totals_by_category
from categorizer import categorize_dataframe, category_labels, load_categories, normalize_text
from export import to_csv_bytes, to_excel_bytes
from pdf_parser import parse_pdf
from theme import GLOBAL_CSS, category_badge, category_color, stat_card

THEME_COLORS = {
    "light": {"bar": "#2a78d6", "text": "#52514e", "grid": "#e1e0d9", "surface": "#fcfcfb"},
    "dark": {"bar": "#3987e5", "text": "#c3c2b7", "grid": "#2c2c2a", "surface": "#1a1a19"},
}


def _theme_colors() -> dict:
    try:
        theme_type = st.context.theme.type
    except Exception:
        theme_type = "light"
    return THEME_COLORS.get(theme_type, THEME_COLORS["light"])

st.set_page_config(page_title="Analisador de Faturas", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.session_state.setdefault("invoices", {})
st.session_state.setdefault("removed_hashes", set())

rules = load_categories()
category_options = category_labels(rules)

st.markdown(
    """
    <div style="display:flex; align-items:center; gap:16px; margin-bottom:4px;">
        <div style="
            width:52px; height:52px; border-radius:14px; flex-shrink:0;
            background: linear-gradient(135deg, #7C6FEA, #5B4FD1);
            display:flex; align-items:center; justify-content:center;
            font-size:1.6rem;
        ">🧾</div>
        <div style="font-size:2.3rem; font-weight:800; color:#F2F3F7; line-height:1.1;">Analisador de Faturas</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write(
    "Envie o PDF da sua fatura de cartão de crédito para separar os gastos por "
    "categoria (mercado, farmácia, posto, lazer etc.) e ver o total combinado, "
    "incluindo quantos cartões você quiser."
)

uploaded_files = st.file_uploader(
    "Envie sua fatura (PDF)", type="pdf", accept_multiple_files=True
)

if uploaded_files:
    for uploaded in uploaded_files:
        file_bytes = uploaded.getvalue()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        if file_hash in st.session_state.removed_hashes:
            continue
        if file_hash not in st.session_state.invoices:
            invoice = parse_pdf(file_bytes, filename=uploaded.name)
            df = invoice_to_dataframe(invoice)
            df = categorize_dataframe(df, rules)
            st.session_state.invoices[file_hash] = {
                "label": invoice.label,
                "filename": uploaded.name,
                "df": df,
            }

if st.session_state.invoices:
    st.info(
        "Você tem outras faturas para incluir? Envie mais arquivos acima para "
        "atualizar o total combinado — útil se você tem mais de um cartão."
    )
else:
    st.stop()

st.divider()
st.subheader("Faturas enviadas")

column_config = {
    "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
    "description": st.column_config.TextColumn("Descrição", width="large"),
    "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
    "category": st.column_config.SelectboxColumn("Categoria", options=category_options),
    "needs_review": st.column_config.CheckboxColumn("Revisar?", disabled=True),
    "raw_line": st.column_config.TextColumn("Linha original (depuração)", width="large"),
}

for file_hash, info in list(st.session_state.invoices.items()):
    with st.expander(info["label"], expanded=False):
        new_label = st.text_input("Nome da fatura", value=info["label"], key=f"label_{file_hash}")
        info["label"] = new_label

        edited_df = st.data_editor(
            info["df"],
            key=f"editor_{file_hash}",
            num_rows="dynamic",
            column_config=column_config,
            use_container_width=True,
        )
        info["df"] = edited_df

        invoice_totals = totals_by_category(edited_df, rules)
        st.caption("Subtotal desta fatura")
        st.dataframe(
            invoice_totals[["label", "total", "n_transacoes"]].rename(
                columns={"label": "Categoria", "total": "Total (R$)", "n_transacoes": "Transações"}
            ),
            hide_index=True,
            use_container_width=True,
        )

        if st.button("Remover fatura", key=f"remove_{file_hash}"):
            del st.session_state.invoices[file_hash]
            st.session_state.removed_hashes.add(file_hash)
            st.rerun()

st.divider()
st.subheader("Total combinado")

combined_df = combine_invoices(st.session_state.invoices)
metrics = summary_metrics(combined_df, rules, n_invoices=len(st.session_state.invoices))

col1, col2, col3, col4 = st.columns(4)
col1.markdown(stat_card("Total gasto", f"R$ {metrics['total_gasto']:,.2f}", "#7C6FEA"), unsafe_allow_html=True)
col2.markdown(
    stat_card("Essenciais", f"R$ {metrics['total_essencial']:,.2f}", "#F4A52A", "mercado + farmácia + posto"),
    unsafe_allow_html=True,
)
col3.markdown(stat_card("Transações", str(metrics["n_transacoes"]), "#2dd4bf"), unsafe_allow_html=True)
col4.markdown(stat_card("Faturas incluídas", str(metrics["n_faturas"]), "#34D399"), unsafe_allow_html=True)
st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

detail_column_config = {
    "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
    "description": st.column_config.TextColumn("Descrição", width="large"),
    "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
    "category": st.column_config.TextColumn("Categoria"),
    "fatura": st.column_config.TextColumn("Fatura"),
}

st.divider()
st.subheader("Buscar uma compra específica")
search_term = st.text_input(
    "Buscar por descrição (ex: nome do estabelecimento) — soma só as transações encontradas",
    key="search_term",
)
if search_term.strip():
    normalized_search = normalize_text(search_term)
    matches = combined_df[
        combined_df["description"].apply(normalize_text).str.contains(normalized_search, na=False)
    ].sort_values("amount", ascending=False)
    if matches.empty:
        st.write(f'Nenhuma transação encontrada para "{search_term}".')
    else:
        st.markdown(
            stat_card(
                f'Total para "{search_term}"',
                f"R$ {matches['amount'].sum():,.2f}",
                "#2dd4bf",
                f"{len(matches)} transação(ões) encontrada(s), em qualquer categoria ou fatura",
            ),
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        st.dataframe(
            matches[["date", "description", "amount", "category", "fatura"]],
            hide_index=True,
            use_container_width=True,
            column_config=detail_column_config,
        )

st.divider()

totals = totals_by_category(combined_df, rules)
spend_totals = totals[~totals["excluded_from_spend_total"]].reset_index(drop=True)
other_totals = totals[totals["excluded_from_spend_total"]].reset_index(drop=True)

if not spend_totals.empty:
    colors = _theme_colors()
    bar_colors = [category_color(label) for label in spend_totals["label"]]
    fig = go.Figure(
        go.Bar(
            x=spend_totals["total"],
            y=spend_totals["label"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"R$ {v:,.2f}" for v in spend_totals["total"]],
            textposition="outside",
            textfont=dict(color=colors["text"]),
            hovertemplate="%{y}<br>R$ %{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Gasto por categoria (essenciais primeiro)",
        yaxis=dict(autorange="reversed", title=None, color=colors["text"]),
        xaxis=dict(title="R$", gridcolor=colors["grid"], zeroline=False, color=colors["text"]),
        plot_bgcolor=colors["surface"],
        paper_bgcolor=colors["surface"],
        font_color=colors["text"],
        margin=dict(l=10, r=60, t=50, b=10),
        height=90 + 40 * len(spend_totals),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Clique numa categoria para ver as transações que compõem o total")
    for _, row in spend_totals.iterrows():
        cat_label = row["label"]
        cat_df = combined_df[combined_df["category"] == cat_label].sort_values(
            "amount", ascending=False
        )
        with st.expander(
            f"{category_badge(cat_label)} {cat_label} — R$ {row['total']:,.2f} ({row['n_transacoes']} transações)"
        ):
            if cat_label == "Não identificado/Outros":
                st.caption(
                    "Nenhuma palavra-chave bateu com essas descrições. Você pode corrigir a "
                    "categoria diretamente na tabela da fatura (acima) ou adicionar uma "
                    "palavra-chave em categories.json para que apareçam classificadas nas "
                    "próximas faturas."
                )
            st.dataframe(
                cat_df[["date", "description", "amount", "fatura"]],
                hide_index=True,
                use_container_width=True,
                column_config=detail_column_config,
            )
else:
    st.write("Nenhuma transação classificada como gasto ainda.")

if not other_totals.empty:
    for _, row in other_totals.iterrows():
        cat_label = row["label"]
        cat_df = combined_df[combined_df["category"] == cat_label].sort_values(
            "amount", ascending=False
        )
        with st.expander(
            f"{category_badge(cat_label)} {cat_label} — R$ {row['total']:,.2f} "
            f"({row['n_transacoes']} — não entra no total de gastos)"
        ):
            st.dataframe(
                cat_df[["date", "description", "amount", "fatura"]],
                hide_index=True,
                use_container_width=True,
                column_config=detail_column_config,
            )

st.divider()
st.subheader("Exportar")
col_csv, col_xlsx = st.columns(2)
col_csv.download_button(
    "Baixar CSV combinado",
    data=to_csv_bytes(combined_df),
    file_name="faturas_combinadas.csv",
    mime="text/csv",
)
col_xlsx.download_button(
    "Baixar Excel (resumo + faturas)",
    data=to_excel_bytes(st.session_state.invoices, totals),
    file_name="faturas_combinadas.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
