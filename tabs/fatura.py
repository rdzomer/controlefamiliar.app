
import pandas as pd
from utils import fmt_currency, _norm_txt

def render(st, df, label_periodo):
    st.subheader("💳 Resumo de Fatura de Cartão de Crédito")
    c1,c2,c3 = st.columns(3)

    met_norm_all = _norm_txt(df["Método de Pagamento/Recebimento"])
    mask_cc_all = met_norm_all.str.contains(r"\bcartao\s*de\s*credito\b", regex=True, na=False)
    cc_methods = sorted(df.loc[mask_cc_all, "Método de Pagamento/Recebimento"].dropna().unique().tolist())
    cartao = c1.selectbox("Cartão (método)", ["Todos"] + cc_methods, 0, key="fat_cartao")

    data_ini = c2.date_input("Data inicial", format="DD/MM/YYYY",
                             value=pd.to_datetime(label_periodo, format="%m/%Y"), key="fat_data_ini")
    data_fim = c3.date_input("Data final", format="DD/MM/YYYY",
                             value=pd.to_datetime(label_periodo, format="%m/%Y") + pd.offsets.MonthEnd(0), key="fat_data_fim")

    c4, c5, c6 = st.columns(3)
    resp_f_disp = sorted(df["Responsável"].dropna().unique().tolist())
    resp_f_sel  = c4.multiselect("Responsável", ["(todos)"] + resp_f_disp, default="(todos)", key="fat_resp")

    cat_f_disp = sorted(df["Categoria"].dropna().unique().tolist())
    cat_f_sel  = c5.multiselect("Categoria", ["(todas)"] + cat_f_disp, default="(todas)", key="fat_cat")

    inclui_creditos = c6.checkbox("Incluir créditos (estornos) do cartão", value=True, key="fat_creditos")

    busca_f = st.text_input("Busca (Descrição/Categoria/Responsável)", "", key="fat_busca")

    met_norm = _norm_txt(df["Método de Pagamento/Recebimento"])
    is_cc = met_norm.str.contains(r"\bcartao\s*de\s*credito\b", regex=True, na=False)
    if cartao != "Todos":
        is_cc = is_cc & (df["Método de Pagamento/Recebimento"] == cartao)

    base_intervalo = df[
        is_cc & df["Data"].between(pd.to_datetime(data_ini), pd.to_datetime(data_fim))
    ].copy()

    despesas = base_intervalo[base_intervalo["Tipo"] == "Despesa"].copy()

    if inclui_creditos:
        creditos = base_intervalo[
            (base_intervalo["Tipo"] == "Receita") &
            (_norm_txt(base_intervalo["Categoria"]).isin(["estorno","estornos"]))
        ].copy()
    else:
        creditos = base_intervalo.iloc[0:0].copy()

    def _aplica_filtros(dfa):
        if resp_f_sel and "(todos)" not in resp_f_sel:
            dfa = dfa[dfa["Responsável"].isin(resp_f_sel)]
        if cat_f_sel and "(todas)" not in cat_f_sel:
            dfa = dfa[dfa["Categoria"].isin(cat_f_sel)]
        if busca_f.strip():
            pat = _norm_txt(busca_f)
            dfa = dfa[
                _norm_txt(dfa["Descrição"]).str.contains(pat, na=False) |
                _norm_txt(dfa["Categoria"]).str.contains(pat, na=False) |
                _norm_txt(dfa["Responsável"]).str.contains(pat, na=False)
            ]
        return dfa

    despesas = _aplica_filtros(despesas)
    creditos = _aplica_filtros(creditos)

    if despesas.empty and creditos.empty:
        st.info("Nenhum lançamento nesse intervalo com os filtros aplicados.")
        return

    total_gastos = despesas["Valor"].abs().sum()
    total_creditos = creditos["Valor"].sum() if not creditos.empty else 0.0
    total_fatura = max(0.0, float(total_gastos) - float(total_creditos))

    st.write(f"**Total da fatura:** {fmt_currency(total_fatura)}")
    if inclui_creditos and total_creditos:
        st.caption(f"Créditos (estornos) abatidos: {fmt_currency(total_creditos)}")

    res = despesas.groupby("Categoria")["Valor"].sum().abs().sort_values(ascending=False).reset_index()
    res["Valor"] = res["Valor"].apply(fmt_currency)
    st.markdown("**Gastos por categoria:**")
    st.dataframe(res, hide_index=True, use_container_width=True)

    lista_frames = [despesas.assign(__tipo_linha="Despesa")]
    if not creditos.empty:
        lista_frames.append(creditos.assign(__tipo_linha="Crédito"))
    detalhada = pd.concat(lista_frames, ignore_index=True) if len(lista_frames)>1 else despesas.assign(__tipo_linha="Despesa")

    detalhada = detalhada[["Data","Responsável","Descrição","Categoria","Valor","__tipo_linha"]].copy()
    detalhada["Data"] = detalhada["Data"].dt.strftime("%d/%m/%Y")
    detalhada["Valor"] = detalhada["Valor"].apply(fmt_currency)
    detalhada = detalhada.rename(columns={"__tipo_linha":"Tipo do Lançamento"})

    st.markdown("**Lançamentos:**")
    st.dataframe(detalhada, hide_index=True, use_container_width=True)
