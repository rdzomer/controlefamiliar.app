# sheets.py — versão completa (google-auth, sem oauth2client) + loaders usados no app
from __future__ import annotations
import json
from typing import Dict, Any, List

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd


# Escopos necessários para Google Sheets e Drive (abrir por nome exige Drive)
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Cabeçalhos padrão (mantém compatibilidade com o seu projeto)
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
    "AnoMes",            # ex.: 2025-10
    "FaturaCartao",      # cartão / final
    "DataVencimento",
    "ValorFatura",
    "StatusPagamento",   # Pago | Em aberto
    "Obs",
]


def _load_google_secrets(st) -> Dict[str, Any]:
    """
    Lê st.secrets['google'] e retorna um dicionário com as credenciais.
    Aceita dois formatos:
      (A) google.credentials = "<JSON do service account>"
      (B) chaves soltas em [google] (type, project_id, private_key_id, private_key, etc.)
    Normaliza strings (strip) e garante type="service_account".
    Levanta RuntimeError com mensagem clara se faltar algo.
    """
    if "google" not in st.secrets:
        raise RuntimeError("Segredos do Google não encontrados. Defina a seção [google] em secrets.toml.")

    g = st.secrets["google"]

    # 1) Tenta formato A (JSON em 'credentials')
    data = None
    creds_raw = g.get("credentials")
    if isinstance(creds_raw, str) and creds_raw.strip():
        try:
            data = json.loads(creds_raw)
        except Exception as e:
            raise RuntimeError(
                "O campo google.credentials não contém um JSON válido. "
                f"Erro ao decodificar: {e}"
            )

    # 2) Senão, usa formato B (chaves soltas)
    if data is None:
        data = {
            "type": g.get("type"),
            "project_id": g.get("project_id"),
            "private_key_id": g.get("private_key_id"),
            "private_key": g.get("private_key"),
            "client_email": g.get("client_email"),
            "client_id": g.get("client_id"),
            "auth_uri": g.get("auth_uri") or "https://accounts.google.com/o/oauth2/auth",
            "token_uri": g.get("token_uri") or "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": g.get("auth_provider_x509_cert_url")
                or "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": g.get("client_x509_cert_url"),
        }

    # 3) Normaliza strings
    for k, v in list(data.items()):
        if isinstance(v, str):
            data[k] = v.strip()

    # 4) Garante tipo correto (evita 'Unexpected credentials type')
    data["type"] = "service_account"

    # 5) Validação mínima
    required = [
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "token_uri",
    ]
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise RuntimeError(
            "Faltam campos obrigatórios em [google] no secrets: "
            + ", ".join(missing)
        )

    # 6) Checagem da chave privada (BEGIN/END)
    pk = data.get("private_key", "")
    if "BEGIN PRIVATE KEY" not in pk or "END PRIVATE KEY" not in pk:
        raise RuntimeError(
            "O bloco private_key parece inválido. Cole o conteúdo completo entre "
            'aspas triplas """-----BEGIN PRIVATE KEY----- ... -----END PRIVATE KEY-----""" '
            "com QUEBRAS DE LINHA reais (sem \\n)."
        )

    return data


def _build_google_credentials(st) -> Credentials:
    """
    Constrói um objeto Credentials (google-auth) a partir dos segredos normalizados.
    """
    info = _load_google_secrets(st)
    try:
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    except Exception as e:
        raise RuntimeError(
            "Falha ao criar Credentials a partir dos segredos. "
            "Verifique se todos os campos estão corretos e se a private_key está completa.\n"
            f"Erro original: {e}"
        )
    return creds


from google.auth.transport.requests import AuthorizedSession

def get_sheet(st):
    
    st.write("Service Account:", g.get("client_email"))
try:
    titles = [s.title for s in client.openall()]
    st.write("Planilhas visíveis:", titles)
except Exception as e:
    st.error(f"Erro ao listar planilhas: {e}")
    
    @st.cache_resource(show_spinner=False)
    def _get_sheet():
        g = st.secrets.get("google", {})
        sheet_key  = (g.get("sheet_key") or "").strip()
        sheet_name = (g.get("sheet_name") or "").strip()

        creds = _build_google_credentials(st)

        try:
            # cria sessão HTTP autenticada
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
                f"Não foi possível abrir a planilha.\n"
                f"• ID usado (sheet_key): '{sheet_key}'\n"
                f"• Título usado (sheet_name): '{sheet_name}'\n"
                f"• Service account com permissão: {client_email}\n"
                f"• Verifique se está compartilhado como Editor.\n"
                f"Erro original do gspread: {e}"
            )
        return ss
        return _get_sheet()



def ensure_worksheet(ss: gspread.Spreadsheet, title: str, headers: List[str]) -> gspread.Worksheet:
    """
    Garante que exista uma worksheet com 'title' e, se recém-criada ou vazia,
    escreve a linha de cabeçalhos em A1:Z1 conforme 'headers'.
    """
    try:
        ws = ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=1000, cols=max(10, len(headers)))
        ws.append_row(headers, value_input_option="RAW")
        return ws

    # Se a aba existe mas está vazia (sem cabeçalhos), coloca-os
    values = ws.get_all_values()
    if not values:
        ws.append_row(headers, value_input_option="RAW")
    else:
        first_row = values[0]
        # Se o cabeçalho não bate, não sobrescreve: apenas garante que há algo
        if len(first_row) < len(headers) and first_row == []:
            ws.update(f"A1:{chr(64+len(headers))}1", [headers])

    return ws


def _ws_to_df(ws: gspread.Worksheet, headers: List[str]) -> pd.DataFrame:
    """
    Converte worksheet em DataFrame. Se a aba tiver só cabeçalho ou estiver vazia,
    devolve DF vazio com as colunas padrão 'headers'.
    """
    records = ws.get_all_records(numericise_ignore=["all"])
    if not records:
        return pd.DataFrame(columns=headers)
    df = pd.DataFrame.from_records(records)
    # Garante a ordem/colunas esperadas
    for col in headers:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[headers]
    return df


def load_main_df(st, ss=None) -> pd.DataFrame:
    """Carrega a aba 'Lancamentos' como DataFrame.
    Aceita opcionalmente o Spreadsheet já aberto (ss) para compatibilidade.
    """
    if ss is None:
        ss = get_sheet(st)
    ws = ensure_worksheet(ss, title="Lancamentos", headers=_HEADERS_MAIN)
    return _ws_to_df(ws, _HEADERS_MAIN)


def load_pm_df(st, ss=None) -> pd.DataFrame:
    """Carrega a aba 'PagamentosMensais' como DataFrame.
    Aceita opcionalmente o Spreadsheet já aberto (ss) para compatibilidade.
    """
    if ss is None:
        ss = get_sheet(st)
    ws = ensure_worksheet(ss, title="PagamentosMensais", headers=_HEADERS_PM)
    return _ws_to_df(ws, _HEADERS_PM)

