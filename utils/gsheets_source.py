"""
utils/gsheets_source.py
Live Google Sheets data source for the Nyaka SGBV dashboard.
"""

import os
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────

REFRESH_SECONDS = 1800  # 30 minutes cache

_FETCH_ERRORS = {}

def fetch_errors():
    return dict(_FETCH_ERRORS)

CREDS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "google_service_account.json"
)

SHEETS = {
    "survivors": {
        "sheet_id": "1ZHIGtVHf0GPa8h7K3OSwZ5B14DwYAq1ZlvCyvUrLM3g",
        "worksheet": None,
        "fallback_csv": "survivors.csv",
    },
    "perpetrators": {
        "sheet_id": "1GxBJwu1YKipqi5i6n7dlkzTg6_uWiK8x4eGOGZu_9Cw",
        "worksheet": None,
        "fallback_csv": "perpetrators.csv",
    },
    "outreach_2025": {
        "sheet_id": "1UyQN0fXKXj-evXhlAIJg6WVqm8NHqIW4ERtj6U8sE44",
        "worksheet": None,
        "fallback_csv": "outreach.csv",
    },
    "outreach_2024": {
        "sheet_id": "1Eh6ifKOloAp-vbelN6jNKHKPgNG0uZzRbt8XkeFr9RY",
        "worksheet": None,
        "fallback_csv": "outreach.csv",
    },
    "school_social_work": {
        "sheet_id": "1BPYwpaQMZMDPQzfonJOYFtk5pbWFTjvQEW1Jlr1PP8Y",
        "worksheet": None,
        "worksheet_gid": 1549751163,
        "fallback_csv": "school_social_work.csv",
    },
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# ─────────────────────────────────────────────────────────
# DEBUG CONTROL (NEW CLEAN SYSTEM)
# ─────────────────────────────────────────────────────────

DEBUG_MODE = st.sidebar.checkbox("Show debug info", value=False)

def debug_log(stream_key, df, source):
    if DEBUG_MODE:
        st.sidebar.write(
            f"[DEBUG] {stream_key} → rows={df.shape[0]}, cols={df.shape[1]}, source={source}"
        )


# ─────────────────────────────────────────────────────────
# CREDENTIALS
# ─────────────────────────────────────────────────────────

def _creds_from_secrets():
    try:
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    return None


def credentials_available() -> bool:
    return os.path.exists(CREDS_PATH) or _creds_from_secrets() is not None


@st.cache_resource(show_spinner=False)
def _get_gspread_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]

        sec = _creds_from_secrets()

        if sec:
            creds = Credentials.from_service_account_info(sec, scopes=scopes)
        elif os.path.exists(CREDS_PATH):
            creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
        else:
            return None

        return gspread.authorize(creds)

    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# CORE FETCH
# ─────────────────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def _fetch_sheet(stream_key: str):
    cfg = SHEETS.get(stream_key)

    if not cfg:
        return pd.DataFrame(), "empty"

    # ── LIVE GOOGLE SHEETS ──────────────────────────────
    if credentials_available():
        try:
            client = _get_gspread_client()

            if client is not None:
                sh = client.open_by_key(cfg["sheet_id"])

                if cfg.get("worksheet_gid") is not None:
                    ws = sh.get_worksheet_by_id(cfg["worksheet_gid"])
                else:
                    ws = sh.get_worksheet(0)

                vals = ws.get_all_values()

                if vals and len(vals) > 1:
                    header = vals[0]
                    seen, clean = {}, []

                    for i, h in enumerate(header):
                        h = str(h).strip() or f"col_{i}"
                        if h in seen:
                            seen[h] += 1
                            h = f"{h}_{seen[h]}"
                        else:
                            seen[h] = 0
                        clean.append(h)

                    df = pd.DataFrame(vals[1:], columns=clean)
                    df = df.replace("", pd.NA)

                    if len(df):
                        _FETCH_ERRORS.pop(stream_key, None)
                        return df, "live"

                _FETCH_ERRORS[stream_key] = "Empty or invalid sheet"

        except Exception as e:
            _FETCH_ERRORS[stream_key] = f"{type(e).__name__}: {str(e)[:300]}"

    # ── FALLBACK CSV ────────────────────────────────────
    fallback = os.path.join(DATA_DIR, cfg["fallback_csv"])

    if os.path.exists(fallback):
        try:
            return pd.read_csv(fallback, low_memory=False), "local"
        except Exception:
            pass

    return pd.DataFrame(), "empty"


# ─────────────────────────────────────────────────────────
# PUBLIC FETCH
# ─────────────────────────────────────────────────────────

def fetch(stream_key: str) -> pd.DataFrame:
    df, source = _fetch_sheet(stream_key)

    # Controlled debug output
    debug_log(stream_key, df, source)

    # Track mode for dashboard
    modes = st.session_state.setdefault("_data_source_modes", {})
    modes[stream_key] = source

    return df


# ─────────────────────────────────────────────────────────
# STATUS HELPERS
# ─────────────────────────────────────────────────────────

def data_source_summary():
    modes = st.session_state.get("_data_source_modes", {})

    if not modes:
        return {
            "mode": "live" if credentials_available() else "local",
            "detail": {},
            "configured": credentials_available(),
        }

    vals = set(modes.values())

    if vals == {"live"}:
        mode = "live"
    elif "live" in vals:
        mode = "mixed"
    else:
        mode = "local"

    return {
        "mode": mode,
        "detail": dict(modes),
        "configured": credentials_available(),
    }


def force_refresh():
    _fetch_sheet.clear()
    st.session_state.pop("_data_source_modes", None)


def render_data_status(st_module, C):
    st = st_module
    summ = data_source_summary()
    mode = summ["mode"]

    if mode == "live":
        label, sub = "● LIVE DATA", "Google Sheets"
    elif mode == "mixed":
        label, sub = "● PARTLY LIVE", "some CSV fallback"
    else:
        label, sub = "● LOCAL DATA", "fallback mode"

    st.sidebar.markdown(f"**{label}**  \n{sub}")

    if st.sidebar.button("🔄 Refresh data"):
        force_refresh()
        st.rerun()

    errs = fetch_errors()
    if errs:
        with st.sidebar.expander("Data issues"):
            for k, v in errs.items():
                st.write(k, v)