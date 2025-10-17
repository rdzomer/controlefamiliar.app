
import streamlit as st
import pandas as pd
from datetime import date as dt_date
import calendar

from constants import DESP_CATS, REC_CATS, METS, TIPOS, ACCOUNTS
from utils import fmt_currency, money_input
from sheets import get_sheet, load_main_df, load_pm_df
from period import obter_df_periodo
from tabs import visao, receitas, detalhamento, fatura, parcelas, pagamentos, planejamento

st.set_page_config(page_title="Controle de Despesas", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# CSS
st.markdown("""
<style>
div.block-container{max-width:none;padding-left:2rem;padding-right:2rem;}
.stTabs [data-baseweb="tab-list"]{flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{padding:6px 12px;}
.tbl th{background:#4f81bd;color:#fff;text-align:left}
.tbl tr:nth-child(even){background:#f2f2f2}
.tbl td.center{text-align:center}.tbl td.right{text-align:right}
</style>
""", unsafe_allow_html=True)

spreadsheet = get_sheet(st)
df = load_main_df(st, spreadsheet)

(df_mes, df_rec, df_desp, df_saldo, sel_mes, sel_ano, label_periodo,
 saldo_inicial, saldo_final, saldo_periodo,
 out_cc, variacao_caixa, saldo_final_caixa) = obter_df_periodo(st, df)

# persist for other tabs
st.session_state["sel_mes"] = sel_mes
st.session_state["sel_ano"] = sel_ano

abas = ["📊 Visão Geral","💰 Receitas","🔍 Detalhamento",
        "💳 Resumo de Fatura","📅 Parcelas Futuras",
        "💸 Pagamentos Mensais","📋 Planejamento"]
(tab_visao, tab_rec, tab_det, tab_fat, tab_parc, tab_pag, tab_plan) = st.tabs(abas)

# Sidebar utils
if st.sidebar.button("🔄 Atualizar dados"):
    load_main_df.clear(); st.rerun()

# Novo registro
st.sidebar.header("➕ Lançar novo registro")
with st.sidebar.form("novo_reg", clear_on_submit=True):
    dt   = st.date_input("Data", format="DD/MM/YYYY")
    resp = st.selectbox("Responsável", ["Selecione…", "Família", "Helena", "Ricardo"], 0)
    tipo = st.selectbox("Tipo", ["Selecione…"] + TIPOS, 0)
    desc = st.text_input("Descrição")

    if tipo == "Receita":         cat_lst = ["Selecione…"] + REC_CATS
    elif tipo == "Transferência": cat_lst = ["Pagamento Cartão"]
    else:                         cat_lst = ["Selecione…"] + DESP_CATS

    cat     = st.selectbox("Categoria", cat_lst, 0)
    cat_new = st.text_input("Se 'Outra', digite categoria", key="cat_new")
    met     = st.selectbox("Método de Pagamento/Recebimento", ["Selecione…"] + METS, 0)
    met_new = st.text_input("Se 'Outra', digite método", key="met_new")

    val      = money_input("Valor (R$)", 0.0, key="novo_valor")
    parcelas = st.number_input("Parcelas (1× à vista)", 1, 36, 1)
    salvar   = st.form_submit_button("Salvar")

    if salvar:
        obrig = (resp == "Selecione…" or tipo == "Selecione…" or
                 (cat == "Selecione…" and tipo != "Transferência") or
                 met == "Selecione…" or abs(val) <= 0)
        if obrig:
            st.error("Preencha todos os campos obrigatórios.")
        else:
            categoria = cat_new.strip() if cat == "Outra" else cat
            metodo    = met_new.strip() if met == "Outra" else met
            if tipo == "Transferência":
                categoria, metodo = "Pagamento Cartão", "Transferência Bancária"
            valor = val if tipo == "Receita" else -abs(val)

            registros = []
            import dateutil.relativedelta
            if metodo == "Cartão de Crédito" and parcelas > 1 and tipo != "Transferência":
                v_parc = round(valor / parcelas, 2)
                for i in range(parcelas):
                    dt_parc = dt + dateutil.relativedelta.relativedelta(months=i)
                    registros.append([
                        dt_parc.strftime("%d/%m/%Y"), resp, tipo,
                        f"{desc} ({i+1}/{parcelas})", categoria, metodo, f"{v_parc:.2f}"
                    ])
            else:
                registros.append([
                    dt.strftime("%d/%m/%Y"), resp, tipo, desc, categoria, metodo, f"{valor:.2f}"
                ])

            for reg in registros:
                spreadsheet.sheet1.append_row(reg, value_input_option="USER_ENTERED")
            st.success("Registro salvo!")
            load_main_df.clear(); st.rerun()

# Sidebar saldo manual
st.sidebar.markdown("---")
st.sidebar.header("💼 Registrar saldo de cada conta")
ultimo_dia = dt_date(sel_ano, sel_mes, calendar.monthrange(sel_ano, sel_mes)[1])
with st.sidebar.form("form_saldo", clear_on_submit=True):
    from constants import ACCOUNTS
    conta     = st.selectbox("Conta", ACCOUNTS, 0)
    conta_new = st.text_input("Se 'Outro', nome da conta", key="conta_new")
    nome_cta  = conta_new.strip() if conta == "Outro" else conta
    dt_saldo  = st.date_input("Data do saldo", value=ultimo_dia, format="DD/MM/YYYY")
    val_saldo = money_input("Valor em caixa (R$)", 0.0, key="saldo_valor")
    btn_saldo = st.form_submit_button("Salvar saldo")

    if btn_saldo and nome_cta:
        spreadsheet.sheet1.append_row(
            [dt_saldo.strftime("%d/%m/%Y"), "Sistema", "Saldo",
             nome_cta, "Saldo", nome_cta, f"{val_saldo:.2f}"],
            value_input_option="USER_ENTERED"
        )
        st.success("Saldo registrado!"); load_main_df.clear(); st.rerun()
    elif btn_saldo:
        st.error("Informe o nome da conta.")

# Tabs rendering
with tab_visao:
    visao.render(st, df_mes, df_rec, df_desp, df_saldo,
                 label_periodo, saldo_inicial, saldo_final, saldo_periodo,
                 out_cc, variacao_caixa, saldo_final_caixa)

with tab_rec:
    receitas.render(st, df_rec)

with tab_det:
    detalhamento.render(st, df, df_mes, label_periodo, spreadsheet)

with tab_fat:
    fatura.render(st, df, label_periodo)

with tab_parc:
    import pandas as pd
    st.session_state["__today__"] = pd.to_datetime("today")
    parcelas.render(st, df)

with tab_pag:
    from sheets import ws_pm, load_pm_df
    dfpm = load_pm_df(st, spreadsheet)()
    pagamentos.render(st, df_mes, spreadsheet, dfpm)

with tab_plan:
    from tabs import planejamento as plan
    plan.render(st, spreadsheet, df_desp, sel_ano, sel_mes)
