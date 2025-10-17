
from utils import fmt_currency, section

def render(st, df_mes, df_rec, df_desp, df_saldo,
           label_periodo, saldo_inicial, saldo_final, saldo_periodo,
           out_cc, variacao_caixa, saldo_final_caixa):
    st.subheader("📊 Visão Geral")
    tot_rec = df_rec["Valor"].sum()
    tot_desp = df_desp["Valor"].abs().sum()
    saldo_decl = df_saldo["Valor"].sum() if not df_saldo.empty else None

    c0, c1, c2, c3, c4, c5, c6 = st.columns(7)
    c0.metric("Saldo inicial", fmt_currency(saldo_inicial))
    c1.metric("Receitas", fmt_currency(tot_rec))
    c2.metric("Despesas", fmt_currency(tot_desp))
    c3.metric("Saldo do período (resultado)", fmt_currency(saldo_periodo))
    c4.metric("Saída com fatura", fmt_currency(out_cc))
    c5.metric("Variação de caixa", fmt_currency(variacao_caixa))
    c6.metric("Saldo final (caixa)", fmt_currency(saldo_final_caixa))
    if saldo_decl is not None:
        st.caption(f"Saldo declarado neste mês: {fmt_currency(saldo_decl)}")

    st.title(f"Gastos em {label_periodo}")
    if df_mes.empty:
        st.info("Nenhum registro neste período.")
    else:
        cmap_resp = {"Família":"#f4cccc", "Helena":"#b7e1cd", "Ricardo":"#4f81bd"}
        s_cat = df_desp.groupby("Categoria")["Valor"].sum().abs().reset_index()
        c_cat = df_desp.groupby("Categoria")["Valor"].count().reset_index(name="Lançamentos")
        section(st, "Despesas por Categoria", s_cat, "Categoria", "Valor", c_cat, "Lançamentos")

        s_met = df_desp.groupby("Método de Pagamento/Recebimento")["Valor"].sum().abs().reset_index()
        c_met = df_desp.groupby("Método de Pagamento/Recebimento")["Valor"].count().reset_index(name="Lançamentos")
        section(st, "Despesas por Método", s_met, "Método de Pagamento/Recebimento", "Valor", c_met, "Lançamentos")

        s_resp = df_desp.groupby("Responsável")["Valor"].sum().abs().reset_index()
        c_resp = df_desp.groupby("Responsável")["Valor"].count().reset_index(name="Lançamentos")
        section(st, "Despesas por Responsável", s_resp, "Responsável", "Valor", c_resp, "Lançamentos", cmap=cmap_resp)
