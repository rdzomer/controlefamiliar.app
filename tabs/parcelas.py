
from utils import fmt_currency

def render(st, df):
    st.subheader("📅 Parcelas Futuras")
    futuro = df[df["Data"] > st.session_state.get("__today__", None)]
    if futuro is None or futuro.empty:
        from pandas import to_datetime
        futuro = df[df["Data"] > to_datetime("today")]
    if futuro.empty:
        st.info("Nenhuma parcela futura registrada.")
    else:
        fut = futuro.copy()
        fut["Data"] = fut["Data"].dt.strftime("%d/%m/%Y")
        fut["Valor"] = fut["Valor"].apply(fmt_currency)
        st.dataframe(fut[["Data","Responsável","Descrição","Categoria",
                          "Método de Pagamento/Recebimento","Valor"]],
                     use_container_width=True)
