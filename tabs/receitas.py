
from utils import section

def render(st, df_rec):
    st.subheader("💰 Receitas")
    if df_rec.empty:
        st.info("Nenhuma receita neste período.")
    else:
        r_cat_s = df_rec.groupby("Categoria")["Valor"].sum().reset_index()
        r_cat_c = df_rec.groupby("Categoria")["Valor"].count().reset_index(name="Lançamentos")
        section(st, "Receitas por Categoria", r_cat_s, "Categoria", "Valor", r_cat_c, "Lançamentos")

        r_met_s = df_rec.groupby("Método de Pagamento/Recebimento")["Valor"].sum().reset_index()
        r_met_c = df_rec.groupby("Método de Pagamento/Recebimento")["Valor"].count().reset_index(name="Lançamentos")
        section(st, "Receitas por Método", r_met_s, "Método de Pagamento/Recebimento", "Valor", r_met_c, "Lançamentos")

        r_resp_s = df_rec.groupby("Responsável")["Valor"].sum().reset_index()
        r_resp_c = df_rec.groupby("Responsável")["Valor"].count().reset_index(name="Lançamentos")
        section(st, "Receitas por Responsável", r_resp_s, "Responsável", "Valor", r_resp_c, "Lançamentos",
                cmap={"Família": "#f4cccc", "Helena": "#b7e1cd", "Ricardo": "#4f81bd"})
