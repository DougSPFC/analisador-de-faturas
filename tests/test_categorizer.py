from categorizer import categorize, load_categories, normalize_text

rules = load_categories()


def test_normalize_text_strips_accents_and_case():
    assert normalize_text("SUPERMERCADO Preço") == "supermercado preco"


def test_categorize_matches_regardless_of_accent_or_case():
    assert categorize("supermercado preco baixo", rules) == "Mercado/Supermercado"
    assert categorize("SUPERMERCADO PREÇO BAIXO", rules) == "Mercado/Supermercado"


def test_categorize_essentials():
    assert categorize("DROGARIA SAO PAULO", rules) == "Farmácia/Saúde"
    assert categorize("POSTO SHELL CENTRO", rules) == "Posto/Combustível"


def test_categorize_falls_back_to_outros():
    assert categorize("LOJA COMPLETAMENTE DESCONHECIDA", rules) == "Não identificado/Outros"


def test_categorize_payments_excluded_category():
    rule = next(r for r in rules if r.key == "pagamentos")
    assert rule.excluded_from_spend_total is True
    assert categorize("PAGAMENTO EFETUADO", rules) == "Pagamentos e Créditos"
