# sheets.py — versão robusta (sem oauth2client), credenciais normalizadas
import json
import gspread
from google.oauth2.service_account import Credentials

# Escopos necessários para ler/editar planilhas
_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _coerce_google_credentials(st):
    """
    Lê st.secrets["google"] e devolve um objeto Credentials do google-auth,
    normalizando os campos e tolerando 2 formatos:
      (a) campo "credentials" com o JSON inteiro (string)
      (b) chaves soltas (type, project_id, private_key_id, private_key, etc.)
    """
    if "google" not in st.secrets:
        raise RuntimeError("Segredos do Google ausentes em st.secrets['google'].")

    g = st.secrets["google"]

    # 1) Se vier um JSON bruto em "credentials", tenta parsear
    data = None
    creds_raw = g.get("credentials")
    if isinstance(creds_raw, str) and creds_raw.strip():
        try:
            data = json.loads(creds_raw)
        except Exception as e:
            raise RuntimeError(f"credentials JSON inválido em st.secrets['google.credentials']: {e}")

    # 2) Caso contrário, monta a partir das chaves soltas de [google]
    if data is None:
        data = {
            "type": g.get("type"),
            "project_id": g.get("project_id"),
            "private_key_id": g.get("private_key_id"),
            "private_key": g.get("private_key"),
            "client_email": g.get("client_email"),
            "client_id": g.get("client_id"),
            "auth_uri": g.get("auth_uri"),
            "token_uri": g.get("token_uri"),
            "auth_provider_x509_cert_url": g.get("auth_provider_x509_cert_url"),
            "client_x509_cert_url": g.get("client_x509_cert_url"),
        }

    # 3) Normaliza strings (remove espaços/CR/LF nas extremidades)
    for k, v in list(data.items()):
        if isinstance(v, str):
            data[k] = v.strip()

    # 4) Garante o tipo correto (evita o 'Unexpected credentials type')
    data["type"] = "service_account"

    # 5) Validação mínima e mensagens claras
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
        raise RuntimeError(f"Faltam campos em st.secrets['google']: {', '.join(missing)}")

    try:
        return Credentials.from_service_account_info(data, scopes=_SCOPE)
    except Exception as e:
        # Mensagem mais clara caso a chave quebre por formatação
        raise RuntimeError(
            "Falha ao criar Credentials. Verifique se o bloco private_key está completo "
            "(BEGIN ... END) com QUEBRAS DE LINHA reais e se o e-mail do service account "
            "tem acesso à planilha. Erro original: {}".format(e)
        )


def get_sheet(st):
    """
    Retorna o objeto Spreadsheet já aberto pelo nome definido em st.secrets['google']['sheet_name'].
    Usa cache do Streamlit para não reconectar toda hora.
    """
    @st.cache_resource(show_spinner=False)
    def _get_sheet():
        gsecrets = st.secrets["google"]
        sheet_name = gsecrets.get("sheet_name")
        if not sheet_name:
            raise RuntimeError("Defina google.sheet_name em secrets (é o NOME DO ARQUIVO no Google Sheets).")

        creds = _coerce_google_credentials(st)
        client = gspread.authorize(creds)

        try:
            # Abre pelo nome do ARQUIVO do Google Sheets
            ss = client.open(sheet_name)
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível abrir a planilha '{sheet_name}'. "
                "Confirme o título do arquivo no Google Sheets e compartilhe-o como Editor com "
                f"o service account: {st.secrets['google'].get('client_email')}. "
                f"Erro original: {e}"
            )
        return ss

    return _get_sheet()
