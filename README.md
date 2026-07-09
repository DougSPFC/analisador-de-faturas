# Analisador de Faturas

App web (Streamlit) que lê faturas de cartão de crédito em PDF, separa os gastos
por categoria (Mercado, Farmácia, Posto, Lazer etc.) e mostra o total combinado
de quantas faturas você quiser enviar (útil se você tem mais de um cartão).

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

Abra o endereço mostrado no terminal (normalmente http://localhost:8501) e
envie o PDF da sua fatura.

## Como funciona

1. **Upload**: envie um ou mais PDFs de fatura (`app.py`).
2. **Extração**: `pdf_parser.py` lê o texto do PDF e reconhece linhas de
   transação (data + descrição + valor). Funciona com o layout genérico da
   maioria das faturas; para um banco com layout muito diferente, adicione um
   perfil em `bank_profiles.py`.
3. **Categorização**: `categorizer.py` classifica cada transação por
   palavra-chave, usando as regras em `categories.json` (editável — adicione
   palavras-chave conforme aparecerem estabelecimentos não reconhecidos).
4. **Totais**: `aggregator.py` soma os gastos por categoria, em ordem de
   importância (essenciais primeiro: mercado, farmácia, posto).
5. **Revisão**: toda fatura enviada aparece numa tabela editável — se o parser
   errar uma data, valor ou categoria, corrija direto na tela antes dos totais
   serem calculados.
6. **Múltiplas faturas**: continue enviando mais arquivos a qualquer momento;
   o total combinado é recalculado automaticamente.
7. **Exportação**: baixe o resultado em CSV ou Excel (uma aba por fatura + um
   resumo).

## Limitações conhecidas

- O parser genérico cobre o formato mais comum de fatura (linha com data,
  descrição e valor em `R$`). Bancos com layouts muito diferentes podem
  precisar de um perfil dedicado em `bank_profiles.py` — use a tabela editável
  como rede de segurança enquanto isso.
- Duplicidade só é detectada quando o mesmo arquivo é enviado de novo (mesmo
  hash); lançamentos repetidos em faturas diferentes (ex: mesma anuidade em
  dois cartões do mesmo banco) não são identificados automaticamente.

## Testes

```bash
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tests\fixtures\make_synthetic_pdf.py   # gera o PDF de teste
.venv\Scripts\pytest
```
