
import re, unicodedata
import streamlit as st
import pandas as pd

def fmt_currency(x):
    try:
        s = f"{float(x):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return x

def _money_to_float(s: str) -> float:
    if s is None: return 0.0
    s = str(s)
    s = re.sub(r"[^\d,.\-]", "", s)
    s = re.sub(r"\.(?=\d{3}(?:\D|$))", "", s)
    s = s.replace(",", ".")
    try: return float(s) if s else 0.0
    except Exception: return 0.0

def money_input(label: str, value: float = 0.0, key: str | None = None) -> float:
    default = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    raw = st.text_input(label, default, key=key)
    return _money_to_float(raw)

def modal_or_expander(title: str):
    return getattr(st, "modal", lambda t: st.expander(t, expanded=True))(title)

def _norm_txt(s: pd.Series | str):
    if isinstance(s, pd.Series):
        t = s.astype("string").fillna("")
        t = t.str.normalize("NFKD").str.encode("ascii","ignore").str.decode("ascii")
        t = t.str.lower().str.strip().str.replace(r"\s+", " ", regex=True)
        return t
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"\s+"," ", s).strip().lower()
    return s

def parse_data_col(series: pd.Series) -> pd.Series:
    """Converte a coluna Data de forma tolerante a formatos variados e seriais."""
    s = series.astype(str).str.strip()
    d = pd.to_datetime(s, dayfirst=True, errors="coerce", utc=False, infer_datetime_format=True)
    mask_serial = d.isna() & s.str.match(r"^\d+(\.0+)?$")
    if mask_serial.any():
        base = pd.Timestamp("1899-12-30")  # base correta para Excel/Sheets
        d.loc[mask_serial] = base + pd.to_timedelta(s.loc[mask_serial].astype(float), unit="D")
    return d

def _ajusta_sinal(row):
    v = row["Valor"]
    if pd.isna(v): 
        return v
    return -abs(v) if row["Tipo"] in ["Despesa","Transferência"] else abs(v)

def section(st, title, sums_df, name_col, val_col, counts_df, cnt_name, cmap=None):
    import plotly.express as px
    st.subheader(title)
    if sums_df.empty:
        st.info("Sem dados para exibir.")
        return
    palette = ["#4f81bd", "#6fa8dc", "#b7e1cd", "#f4cccc", "#fce5cd"]
    fig = px.pie(sums_df, names=name_col, values=val_col, hole=0.35,
                 color_discrete_sequence=(palette if cmap is None else None),
                 color=name_col if cmap else None, color_discrete_map=cmap)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))

    col_graf, col_tbl = st.columns([3, 2], gap="medium")
    with col_graf: st.plotly_chart(fig, use_container_width=True)

    tbl = sums_df.merge(counts_df, on=name_col).sort_values(val_col, ascending=False)
    total_cnt, total_val = tbl[cnt_name].sum(), tbl[val_col].abs().sum()

    html = ("<table class='tbl'><thead><tr>"
            f"<th>{name_col}</th><th>{cnt_name}</th><th>Total</th>"
            "</tr></thead><tbody>")
    for _, r in tbl.iterrows():
        html += (f"<tr><td>{r[name_col]}</td>"
                 f"<td class='center'>{r[cnt_name]}</td>"
                 f"<td class='right'>{fmt_currency(abs(r[val_col]))}</td></tr>")
    html += (f"<tr><td><strong>Total</strong></td>"
             f"<td class='center'><strong>{total_cnt}</strong></td>"
             f"<td class='right'><strong>{fmt_currency(total_val)}</strong></td></tr>"
             "</tbody></table>")
    with col_tbl: st.markdown(html, unsafe_allow_html=True)
