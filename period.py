
import pandas as pd

def _ultimo_mes_existente(dframe: pd.DataFrame):
    hoje = pd.Timestamp.today().normalize()
    d = dframe.copy()
    d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    valid_hoje = d[d["Data"].notna() & (d["Data"] <= hoje)]
    if not valid_hoje.empty:
        ult = valid_hoje["Data"].max()
        return int(ult.year), int(ult.month)
    if d["Data"].notna().any():
        ult = d.loc[d["Data"].notna(), "Data"].max()
        return int(ult.year), int(ult.month)
    return int(hoje.year), int(hoje.month)

def obter_df_periodo(st, dframe: pd.DataFrame):
    import pandas as pd
    from utils import _norm_txt
    dframe = dframe.copy()
    dframe["Data"] = pd.to_datetime(dframe["Data"], errors="coerce")

    ano_padrao, mes_padrao = _ultimo_mes_existente(dframe)

    anos_existentes = sorted(dframe.loc[dframe["Data"].notna(), "Data"].dt.year.unique(), reverse=True)
    if ano_padrao not in anos_existentes: anos_existentes.insert(0, ano_padrao)
    if not anos_existentes: anos_existentes = [ano_padrao]

    MESES = [(i+1, n) for i, n in enumerate(
        ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    )]

    with st.sidebar.expander("📅 Escolher período"):
        sel_ano  = st.selectbox("Ano", anos_existentes,
                                index=anos_existentes.index(ano_padrao) if ano_padrao in anos_existentes else 0,
                                key="periodo_ano_selector")
        sel_nome = st.selectbox("Mês", [m[1] for m in MESES], index=max(0, mes_padrao-1),
                                key="periodo_mes_selector")

    sel_mes = next(m for m, n in MESES if n == sel_nome)

    mask_mes = (dframe["Data"].dt.year == sel_ano) & (dframe["Data"].dt.month == sel_mes)
    dfm = dframe.loc[mask_mes].copy()

    primeiro_dia = pd.Timestamp(sel_ano, sel_mes, 1)
    prev = dframe[(dframe["Tipo"] == "Saldo") & (dframe["Data"] < primeiro_dia)].copy()
    if prev.empty:
        saldo_inicial = 0.0
    else:
        prev["__cta"] = _norm_txt(prev["Descrição"])
        ultimos = (prev.sort_values(["__cta","Data"]).groupby("__cta", as_index=False).tail(1))
        saldo_inicial = float(ultimos["Valor"].sum())

    df_rec   = dfm[dfm["Tipo"] == "Receita"].copy()
    df_desp  = dfm[dfm["Tipo"] == "Despesa"].copy()
    df_saldo = dfm[dfm["Tipo"] == "Saldo"].copy()

    saldo_periodo = df_rec["Valor"].sum() - df_desp["Valor"].abs().sum()
    saldo_final   = saldo_inicial + saldo_periodo

    out_cc = dframe[
        (dframe["Tipo"] == "Transferência") &
        (dframe["Categoria"].str.strip() == "Pagamento Cartão") &
        (dframe["Data"].dt.year == sel_ano) &
        (dframe["Data"].dt.month == sel_mes)
    ]["Valor"].abs().sum()

    variacao_caixa = saldo_periodo - out_cc
    saldo_final_caixa = saldo_inicial + variacao_caixa

    return (dfm, df_rec, df_desp, df_saldo,
            sel_mes, sel_ano, f"{sel_mes:02d}/{sel_ano}",
            saldo_inicial, saldo_final, saldo_periodo,
            out_cc, variacao_caixa, saldo_final_caixa)
