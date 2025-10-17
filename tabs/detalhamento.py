
import pandas as pd
from utils import fmt_currency, _norm_txt

def render(st, df, df_mes, label_periodo, sheet):
    st.subheader("🔍 Detalhamento de lançamentos")
    if df_mes.empty:
        st.info("Nada a detalhar.")
        return

    colf1, colf2, colf3 = st.columns([1,1,1])
    tipos_disponiveis = sorted(df_mes["Tipo"].unique().tolist())
    tipos_sel = colf1.multiselect("Tipo", tipos_disponiveis, default=tipos_disponiveis, key="det_tipos")

    cats_disp = sorted(df_mes["Categoria"].dropna().unique().tolist())
    cats_sel = colf2.multiselect("Categoria", ["(todas)"] + cats_disp, default="(todas)", key="det_cats")

    resp_disp = sorted(df_mes["Responsável"].dropna().unique().tolist())
    resp_sel = colf3.multiselect("Responsável", ["(todos)"] + resp_disp, default="(todos)", key="det_resps")

    colf4, colf5 = st.columns([1,1])
    met_disp = sorted(df_mes["Método de Pagamento/Recebimento"].dropna().unique().tolist())
    met_sel = colf4.multiselect("Método", ["(todos)"] + met_disp, default="(todos)", key="det_mets")
    busca_txt = colf5.text_input("Busca (Descrição/Categoria/Responsável)", "", key="det_busca")

    det = df_mes.copy()
    det = det[det["Tipo"].isin(tipos_sel)]
    if cats_sel and "(todas)" not in cats_sel:
        det = det[det["Categoria"].isin(cats_sel)]
    if resp_sel and "(todos)" not in resp_sel:
        det = det[det["Responsável"].isin(resp_sel)]
    if met_sel and "(todos)" not in met_sel:
        det = det[det["Método de Pagamento/Recebimento"].isin(met_sel)]
    if busca_txt.strip():
        pat = _norm_txt(busca_txt)
        det = det[
            _norm_txt(det["Descrição"]).str.contains(pat, na=False) |
            _norm_txt(det["Categoria"]).str.contains(pat, na=False) |
            _norm_txt(det["Responsável"]).str.contains(pat, na=False)
        ]

    filtros_ativos = (det.shape[0] != df_mes.shape[0])

    det["Data"] = det["Data"].dt.strftime("%d/%m/%Y")
    det.index = range(1, len(det)+1)
    det["Valor"] = det["Valor"].apply(fmt_currency)

    edit = st.data_editor(det, num_rows="dynamic", use_container_width=True, key="det_editor")

    btn_save_full = st.button(
        "💾 Salvar alterações (mês inteiro)",
        disabled=filtros_ativos,
        help="Desative os filtros para salvar o mês inteiro com segurança."
    )

    if btn_save_full:
        df_edit = edit.copy()
        df_edit["Valor"] = (df_edit["Valor"].str.replace(r"[^\d,\-]","",regex=True)
                            .str.replace(",",".").astype(float))
        df_edit["Data"]  = pd.to_datetime(df_edit["Data"], dayfirst=True, format="%d/%m/%Y")

        # Backup simples automático em nova aba
        try:
            bk = sheet.worksheet("_backup_auto")
        except Exception:
            bk = sheet.add_worksheet("_backup_auto", rows=2, cols=10)
            bk.append_row(df.columns.tolist())
        bk.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")

        df_hist = df[df["Data"].dt.strftime("%m/%Y") != label_periodo]
        df_save = pd.concat([df_hist, df_edit.reset_index(drop=True)], ignore_index=True)
        df_save["Data"] = df_save["Data"].dt.strftime("%d/%m/%Y")

        sheet.sheet1.clear()
        sheet.sheet1.append_row(df_save.columns.tolist(), value_input_option="USER_ENTERED")
        sheet.sheet1.append_rows(df_save.astype(str).values.tolist(), value_input_option="USER_ENTERED")
        st.success("Alterações salvas! As tabelas serão recarregadas pelo botão na sidebar.")
