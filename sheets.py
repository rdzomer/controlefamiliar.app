
import json
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from utils import parse_data_col, _ajusta_sinal

def _coerce_google_credentials(st):
    """Accepts both styles of secrets:
    1) [google].credentials as a JSON string (triple-quoted)
    2) [google.credentials] as a TOML table (already a dict)
    3) Or individual keys directly under [google]
    """
    google_secrets = st.secrets["google"]
    creds_raw = google_secrets.get("credentials", {})
    # Case 2: TOML table -> dict
    if isinstance(creds_raw, dict):
        return dict(creds_raw)
    # Case 1: triple-quoted JSON string
    if isinstance(creds_raw, str) and creds_raw.strip():
        return json.loads(creds_raw)
    # Case 3: individual keys under [google]
    keys = ["type","project_id","private_key_id","private_key","client_email","client_id",
            "auth_uri","token_uri","auth_provider_x509_cert_url","client_x509_cert_url","universe_domain"]
    out = {k: google_secrets[k] for k in keys if k in google_secrets}
    if out:
        return out
    raise RuntimeError("Google credentials not found. Provide [google].credentials (string JSON) or [google.credentials] table.")

def get_sheet(st):
    @st.cache_resource(show_spinner=False)
    def _get_sheet():
        creds = _coerce_google_credentials(st)
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        client = gspread.authorize(
            ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
        )
        return client.open(st.secrets["google"]["sheet_name"])
    return _get_sheet()

def load_main_df(st, spreadsheet):
    @st.cache_data(show_spinner=False)
    def _load():
        vals = spreadsheet.sheet1.get_all_values()
        base_cols = ["Data","Responsável","Tipo","Descrição","Categoria",
                    "Método de Pagamento/Recebimento","Valor"]
        if not vals: return pd.DataFrame(columns=base_cols)

        def _norm(s): return str(s).strip().lower()
        wanted = {"data","responsável","responsavel","tipo","descrição","descricao",
                "categoria","valor","método","metodo","forma"}
        header_idx = None
        for i, row in enumerate(vals[:300]):
            tokens = {_norm(c) for c in row if str(c).strip() != ""}
            if len(tokens & wanted) >= 3:
                header_idx = i; break

        if header_idx is None:
            data_rows = []
            for r in vals:
                row = (r + [""]*7)[:7]
                data_rows.append({
                    "Data": row[0], "Responsável": row[1], "Tipo": row[2] or "Despesa",
                    "Descrição": row[3], "Categoria": row[4],
                    "Método de Pagamento/Recebimento": row[5], "Valor": row[6],
                })
            df = pd.DataFrame(data_rows, columns=base_cols)
        else:
            header = [str(c).strip() for c in vals[header_idx]]
            rows   = vals[header_idx+1:]
            df = pd.DataFrame(rows, columns=header)
            ren = {}
            for c in df.columns:
                n = _norm(c)
                if n in {"responsavel","responsável"}: ren[c] = "Responsável"
                elif n in {"descricao","descrição"}:   ren[c] = "Descrição"
                elif n == "categoria":                 ren[c] = "Categoria"
                elif n in {"metodo de pagamento","método de pagamento",
                        "metodo de pagamento/recebimento","método de pagamento/recebimento",
                        "metodo de recebimento","método de recebimento",
                        "forma de pagamento","forma de recebimento","método","metodo"}:
                    ren[c] = "Método de Pagamento/Recebimento"
                elif n.startswith("valor"):            ren[c] = "Valor"
                elif n == "data":                      ren[c] = "Data"
                elif n == "tipo":                      ren[c] = "Tipo"
            if ren: df.rename(columns=ren, inplace=True)
            for c in base_cols:
                if c not in df.columns: df[c] = None
            df = df[base_cols].copy()

        # limpeza
        mask_all_empty = df.apply(lambda r: all(str(x).strip()=="" for x in r), axis=1)
        df = df.loc[~mask_all_empty].copy()

        # tipos
        df["Valor"] = (pd.Series(df["Valor"]).astype(str)
                    .str.replace(r"[^\d,\-\.]", "", regex=True)
                    .str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True)
                    .str.replace(",", ".", regex=False))
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df["Data"]  = parse_data_col(df["Data"])
        df["Valor"] = df.apply(_ajusta_sinal, axis=1)
        for col in ["Categoria","Método de Pagamento/Recebimento","Responsável","Tipo","Descrição"]:
            df[col] = df[col].astype(str).str.strip()
        return df
    return _load()
