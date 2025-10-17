
from utils import fmt_currency
from constants import DESP_CATS
from sheets import ws_plan, load_plan_df, salvar_plan

def render(st, spreadsheet, df_desp, sel_ano, sel_mes):
    st.header("📋 Planejamento Financeiro Mensal")
    import pandas as pd
    hoje = pd.to_datetime("today")
    anos = list(range(hoje.year-2, hoje.year+2))

    ano = st.selectbox("Ano", anos, index=anos.index(hoje.year), key="plan_ano")
    mes = st.selectbox("Mês", [(i+1,n) for i,n in enumerate(
        ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    )], index=hoje.month-1, key="plan_mes", format_func=lambda x: x[1])[0]

    df_plan = load_plan_df(st, spreadsheet, DESP_CATS)()
    linha = df_plan[(df_plan["Ano"].astype(int) == ano) & (df_plan["Mês"].astype(int) == mes)].index

    if not linha.empty:
        plan = df_plan.loc[linha[0]]
        r_ric, r_hel, r_ext, r_inv = map(float, (
            plan.get("Salário Ricardo",0), plan.get("Salário Helena",0),
            plan.get("Extras",0), plan.get("Investimentos",0)))
        orc_init = {c: plan.get(c,0) for c in DESP_CATS}
    else:
        r_ric = r_hel = r_ext = r_inv = 0.0
        orc_init = {c: 0.0 for c in DESP_CATS}

    def to_float(s):
        return float(str(s).replace(".","").replace(",",".").replace("R$","").strip() or 0)

    c1,c2,c3,c4 = st.columns(4)
    r_ric = to_float(c1.text_input("Salário Ricardo", fmt_currency(r_ric), key="plan_sal_ric"))
    r_hel = to_float(c2.text_input("Salário Helena", fmt_currency(r_hel), key="plan_sal_hel"))
    r_ext = to_float(c3.text_input("Extras", fmt_currency(r_ext), key="plan_ext"))
    r_inv = to_float(c4.text_input("Investimentos", fmt_currency(r_inv), key="plan_inv"))

    rec_prev = r_ric + r_hel + r_ext + r_inv
    st.markdown(f"**Receita prevista:** {fmt_currency(rec_prev)}")

    st.markdown("#### Orçamento")
    cols = st.columns(4); orc = {}
    for i, cat in enumerate(DESP_CATS):
        with cols[i % 4]:
            orc[cat] = st.number_input(cat, 0.0, value=float(orc_init[cat]), step=50.0, format="%.2f", key=f"orc_{cat}")

    desp_prev = sum(orc.values())
    st.markdown(f"**Gastos previstos:** {fmt_currency(desp_prev)}")
    st.markdown(f"**Saldo previsto:** {fmt_currency(rec_prev - desp_prev)}")

    if st.button("💾 Salvar Planejamento", key="plan_salvar"):
        salvar_plan(ws_plan(spreadsheet, DESP_CATS), linha[0] if not linha.empty else None,
                    [ano, mes, r_ric, r_hel, r_ext, r_inv] + [orc[c] for c in DESP_CATS])
        st.success("Planejamento salvo!")
        load_plan_df(st, spreadsheet, DESP_CATS).clear(); st.rerun()

    st.markdown("---")
    st.markdown("### Comparativo Planejado × Realizado")
    if ano == sel_ano and mes == sel_mes:
        comp = df_desp.groupby("Categoria")["Valor"].sum().abs().reset_index()
        comp["Planejado"] = comp["Categoria"].map(orc)
        comp["Diferença"] = comp["Planejado"] - comp["Valor"]
        for col in ["Planejado","Valor","Diferença"]:
            comp[col] = comp[col].apply(fmt_currency)
        st.dataframe(comp, hide_index=True, use_container_width=True)
    else:
        st.info("Comparativo disponível apenas para o mês corrente.")
