
from datetime import datetime
from utils import money_input, modal_or_expander
from constants import METS, ICON_MAP, DEFAULT_ICON

def render(st, df_mes, spreadsheet, dfpm):
    st.header("💸 Pagamentos Mensais")

    from sheets import ws_pm, load_pm_df
    with st.expander("➕ Cadastrar conta recorrente", expanded=False):
        with st.form("pm_add", clear_on_submit=True):
            desc_pm = st.text_input("Descrição")
            dia_pm  = st.number_input("Dia do vencimento", 1, 28, 5, 1)
            from constants import DESP_CATS
            cat_pm  = st.selectbox("Categoria", DESP_CATS,
                                   index=DESP_CATS.index("Moradia") if "Moradia" in DESP_CATS else 0)
            resp_pm = st.selectbox("Responsável", ["Selecione…","Família","Helena","Ricardo"], 0)
            saved = st.form_submit_button("Salvar")
            if saved:
                if resp_pm == "Selecione…":
                    st.warning("Escolha o responsável.")
                else:
                    ws_pm(spreadsheet).append_row([desc_pm,"",dia_pm,cat_pm,resp_pm], value_input_option="USER_ENTERED")
                    st.success("Conta adicionada!"); load_pm_df.clear(); st.rerun()

    if dfpm.empty:
        st.info("Nenhuma conta recorrente cadastrada.")
        return

    sel_ano = st.session_state.get("sel_ano")
    sel_mes = st.session_state.get("sel_mes")

    dfpm_mes = dfpm.copy()
    dfpm_mes["Vencimento"] = [datetime(sel_ano, sel_mes, min(int(d), 28)) for d in dfpm_mes["Dia"]]
    dfpm_mes["chave"] = (dfpm_mes["Descrição"].str.strip()+"|"+
                         dfpm_mes["Categoria"].str.strip()+"|"+
                         dfpm_mes["Responsável"].str.strip())

    ch_lanc = (df_mes[df_mes["Tipo"]=="Despesa"]
               .assign(chave=lambda d:
                       d["Descrição"].str.strip()+"|"+
                       d["Categoria"].str.strip()+"|"+
                       d["Responsável"].str.strip())
               ["chave"].unique())
    dfpm_mes = dfpm_mes[~dfpm_mes["chave"].isin(ch_lanc)].copy()

    if st.session_state.get("pm_modal") and st.session_state.get("pm_idx") not in dfpm_mes.index:
        st.session_state.pop("pm_modal", None); st.session_state.pop("pm_idx", None)

    if dfpm_mes.empty:
        st.success("Todas as contas do mês já foram pagas 🎉")
        return

    st.markdown("#### Contas a pagar")
    cols = st.columns(3)
    for idx, row in dfpm_mes.iterrows():
        with cols[idx % 3]:
            icon = ICON_MAP.get(row["Descrição"], ICON_MAP.get(row["Categoria"], DEFAULT_ICON))
            lbl = (f"{icon} **{row['Descrição']}**  \\n"
                   f"*venc.* {row['Vencimento'].strftime('%d/%m')}")
            if st.button(lbl, key=f"card_{idx}", help="Clique para pagar", use_container_width=True):
                st.session_state["pm_idx"] = idx; st.session_state["pm_modal"] = True; st.rerun()

    if st.session_state.get("pm_modal"):
        conta = dfpm_mes.loc[st.session_state["pm_idx"]]
        with modal_or_expander(f"Pagar {conta['Descrição']}"):
            v_pago = money_input("Valor pago (R$)", 0.0, key="pm_valor_txt")
            metodo = st.selectbox("Método", ["Selecione…"] + METS, key="pm_metodo")
            c_ok, c_cancel = st.columns(2)
            if c_ok.button("Confirmar"):
                if v_pago > 0 and metodo != "Selecione…":
                    existe = (
                        (df_mes["Tipo"] == "Despesa")
                        & (df_mes["Descrição"].str.strip() == conta["Descrição"].strip())
                        & (df_mes["Categoria"].str.strip() == conta["Categoria"].strip())
                        & (df_mes["Responsável"].str.strip() == conta["Responsável"].strip())
                    ).any()
                    if existe:
                        st.warning("Esta conta já foi paga neste mês.")
                        st.session_state.pop("pm_modal"); st.rerun()
                    else:
                        spreadsheet.sheet1.append_row([
                            datetime.today().strftime("%d/%m/%Y"),
                            conta["Responsável"], "Despesa", conta["Descrição"],
                            conta["Categoria"], metodo, f"{-abs(v_pago):.2f}",
                        ], value_input_option="USER_ENTERED")
                        st.success("Pagamento lançado!")
                        st.session_state.pop("pm_modal")
                        st.rerun()
                else:
                    st.warning("Preencha valor e método.")
            if c_cancel.button("Cancelar"):
                st.session_state.pop("pm_modal"); st.rerun()
