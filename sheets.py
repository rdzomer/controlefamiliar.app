# sheets.py — versão estável p/ gspread>=6 e Streamlit
from __future__ import annotations
import json
from typing import Any, Dict, List

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_HEADERS_MAIN: List[str] = [
    "Titular",
    "Cartao (Final)",
    "Data",
    "Estabelecimento",
    "Parcela",
    "Valor (R$)",
    "Categoria",
]

_HEADERS_PM: List[str] = [
    "AnoMes",
    "FaturaCartao",
    "DataVencimento",
    "ValorFatura",
    "StatusPagamento",
    "Obs",
]

# ------------------------- Credenciais ------------------------- #
def _load_google_secrets(st) -> Dict[str, Any]:
    if "google" not in st.secrets:
        raise RuntimeError("Falta a seção [google] no secrets.toml.")

    g = st.secrets["google"]
    # Se veio um JSON inteiro em google.credentials, parseia.
    creds_raw = g.get("credentials")
    if isinstance(creds_raw, str) and creds_raw.strip():
        try:
            data = json.loads(creds_raw)
        except Exception as e:
            raise RuntimeError(f"google.credentials não é JSON válido: {e}")
    else:
        # Monta a partir dos campos individuais
        data = {
            "type": "service_account",
            "project_id": g.get("project_id"),
            "private_key_id": g.get("private_key_id"),
            "private_key": g.get("private_key"),
            "client_email": g.get("client_email"),
            "client_id": g.get("client_id"),
            "auth_uri": g.get("auth_uri") or "https://accounts.google.com/o/oauth2/auth",
            "token_uri": g.get("token_uri") or "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": g.get("auth_provider_x509_cert_url") or "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": g.get("client_x509_cert_url"),
        }

    req = ["project_id", "private_key_id", "private_key", "client_email", "client_id", "token_uri"]
    falta = [k for k in req if not data.get(k)]
    if falta:
        raise RuntimeError("Faltam campos em [google]: " + ", ".join(falta))

    pk = data.get("private_key", "")
    if "BEGIN PRIVATE KEY" not in pk or "END PRIVATE KEY" not in pk:
        raise RuntimeError("private_key inválida. Cole o bloco completo entre aspas triplas.")

    return data


def _build_google_credentials(st) -> Credentials:
    info = _load_google_secrets(st)
    try:
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    except Exception as e:
        raise RuntimeError(f"Falha ao criar Credentials: {e}")

# ------------------------- Spreadsheet ------------------------- #
def get_sheet(st):
    @st.cache_resource(show_spinner=False)
    def _get_sheet():
        g = st.secrets.get("google", {})
        sheet_key  = (g.get("sheet_key") or "").strip()
        sheet_name = (g.get("sheet_name") or "").strip()

        creds = _build_google_credentials(st)
        try:
            authed_session = AuthorizedSession(creds)
            client = gspread.Client(auth=creds, session=authed_session)
        except Exception as e:
            raise RuntimeError(f"Falha ao iniciar gspread: {e}")

        try:
            if sheet_key:
                ss = client.open_by_key(sheet_key)
            elif sheet_name:
                ss = client.open(sheet_name)
            else:
                raise RuntimeError("Defina google.sheet_key (recomendado) ou google.sheet_name no secrets.")
        except Exception as e:
            client_email = g.get("client_email", "<service-account>")
            raise RuntimeError(
                "Não foi possível abrir a planilha.\n"
                f"• sheet_key: '{sheet_key}'\n"
                f"• sheet_name: '{sheet_name}'\n"
                f"• Verifique se o arquivo está compartilhado como Editor com: {client_email}\n"
                f"• Erro do gspread: {e}"
            )
        return ss

    return _get_sheet()

# ------------------------- Worksheets / DataFrames ------------------------- #
def ensure_worksheet(ss: gspread.Spreadsheet, title: str, headers: List[str]) -> gspread.Worksheet:
    try:
        ws = ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=1000, cols=max(10, len(headers)))
        ws.append_row(headers, value_input_option="RAW")
        return ws

    values = ws.get_all_values()
    if not values:
        ws.append_row(headers, value_input_option="RAW")
    return ws


def _ws_to_df(ws: gspread.Worksheet, headers: List[str]) -> pd.DataFrame:
    records = ws.get_all_records(numericise_ignore=["all"])
    if not records:
        return pd.DataFrame(columns=headers)
    df = pd.DataFrame.from_records(records)
    for col in headers:
        if col not in df.columns:
            df[col] = pd.NA
    return df[headers]


def load_main_df(st, ss=None) -> pd.DataFrame:
    """Compatível com load_main_df(st) e load_main_df(st, spreadsheet)."""
    if ss is None:
        ss = get_sheet(st)
    ws = ensure_worksheet(ss, "Lancamentos", _HEADERS_MAIN)
    return _ws_to_df(ws, _HEADERS_MAIN)


def load_pm_df(st, ss=None) -> pd.DataFrame:
    """Compatível com load_pm_df(st) e load_pm_df(st, spreadsheet)."""
    if ss is None:
        ss = get_sheet(st)
    ws = ensure_worksheet(ss, "PagamentosMensais", _HEADERS_PM)
    return _ws_to_df(ws, _HEADERS_PM)

# ---- Funções usadas pela aba de Planejamento (compat) ---- #
def ws_plan(st):
    ss = get_sheet(st)
    return ensure_worksheet(ss, "Planejamento", ["Categoria", "Meta (R$)", "Observações"])

def load_plan_df(st):
    ws = ws_plan(st)
    return _ws_to_df(ws, ["Categoria", "Meta (R$)", "Observações"])

def salvar_plan(st, df: pd.DataFrame):
    ws = ws_plan(st)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option="USER_ENTERED")
