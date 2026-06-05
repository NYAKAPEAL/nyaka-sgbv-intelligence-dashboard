"""
utils/gsheets_source.py
Live Google Sheets data source for the Nyaka SGBV dashboard.

Design goals:
- FAST: each sheet is fetched once and cached for a refresh window (default 30 min),
  then shared across every page. Page navigation stays 1-3s; only the first load
  after the window expires is slow.
- PRIVATE: uses a Google service account (no public 'publish to web'). The sheets
  are shared privately with the service-account email.
- ROBUST: if credentials are missing or a fetch fails, falls back to the local
  CSVs in data/ so the app never goes blank. The data-source mode is reported in
  the sidebar so the team always knows whether they're seeing live or local data.

Setup is documented in: Nyaka_GoogleSheets_Setup_Guide.docx
"""
import os
import time
import pandas as pd
import streamlit as st

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Refresh window in seconds. 1800 = 30 minutes. Lower = fresher but more slow loads.
REFRESH_SECONDS = 1800

# Records the real reason a live fetch failed, per stream, so it can be shown to
# the user instead of being silently swallowed.
_FETCH_ERRORS = {}
def fetch_errors():
    return dict(_FETCH_ERRORS)

# Path to the service-account key file (you place this in the app folder yourself).
# It is git-ignored and must NEVER be committed or shared.
CREDS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_service_account.json")

# Map each logical data stream to its Google Sheet ID and the worksheet/tab name.
# The Sheet ID is the long string in the URL between /d/ and /edit.
# Worksheet name: the tab name at the bottom of the Google Sheet. If your data is
# on a single tab, set it; if unsure, leave as None to read the FIRST tab.
SHEETS = {
    "survivors": {
        # CURRENTLY ACTIVE intake tool (SGBV Intake Tracking Tool V1.2022).
        # New survivor enrollments land here today. When the redesigned
        # SGBV_Data_Migrated_Master_June_2026 is launched and the old tool is
        # deactivated, swap sheet_id to "1JBQZCW-csmCBOB6Z8VPIKciK2lNbFGE7rT4hWtBZeKI".
        "sheet_id":  "1ZHIGtVHf0GPa8h7K3OSwZ5B14DwYAq1ZlvCyvUrLM3g",
        "worksheet": None,
        "fallback_csv": "survivors.csv",
    },
    "perpetrators": {
        "sheet_id":  "1GxBJwu1YKipqi5i6n7dlkzTg6_uWiK8x4eGOGZu_9Cw",
        "worksheet": None,   # SGBV Perpetrator Intake & Tracking Tool 2022
        "fallback_csv": "perpetrators.csv",
    },
    "outreach_2025": {
        "sheet_id":  "1UyQN0fXKXj-evXhlAIJg6WVqm8NHqIW4ERtj6U8sE44",
        "worksheet": None,   # 2025 SGBV Community outreaches tool
        "fallback_csv": "outreach.csv",
    },
    "outreach_2024": {
        "sheet_id":  "1Eh6ifKOloAp-vbelN6jNKHKPgNG0uZzRbt8XkeFr9RY",
        "worksheet": None,   # SGBV Outreach Reporting tool V.2024
        "fallback_csv": "outreach.csv",
    },
    "school_social_work": {
        # School Social Work Tool 2022.1 — School Social Worker activity reports.
        # The data tab is selected by gid (from the sheet URL) rather than by name,
        # so a renamed tab won't silently break the fetch.
        "sheet_id":      "1BPYwpaQMZMDPQzfonJOYFtk5pbWFTjvQEW1Jlr1PP8Y",
        "worksheet":     None,
        "worksheet_gid": 1549751163,
        "fallback_csv":  "school_social_work.csv",
    },
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# ── CREDENTIAL / CLIENT HANDLING ──────────────────────────────────────────────
def _creds_from_secrets():
    """Service-account info from Streamlit secrets (used on Streamlit Cloud,
    where no local key file exists). Returns a dict or None."""
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
    """Build an authorised gspread client from the service-account key.
    Prefers Streamlit secrets (cloud), falls back to a local key file (dev).
    Cached as a resource so we authenticate once per app run, not per fetch."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
                  "https://www.googleapis.com/auth/drive.readonly"]
        sec = _creds_from_secrets()
        if sec:
            creds = Credentials.from_service_account_info(sec, scopes=scopes)
        elif os.path.exists(CREDS_PATH):
            creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
        else:
            return None
        return gspread.authorize(creds)
    except Exception as e:
        # Surface nothing here; callers handle the fallback.
        return None


# ── CORE FETCH (cached for the refresh window) ────────────────────────────────
@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def _fetch_sheet(stream_key: str) -> tuple:
    """Return (DataFrame, source_label). Tries Google Sheets, falls back to CSV.
    Cached for REFRESH_SECONDS so repeated page loads are instant."""
    cfg = SHEETS.get(stream_key)
    fallback = os.path.join(DATA_DIR, cfg["fallback_csv"]) if cfg else None

    # 1. Try live Google Sheets if credentials exist
    if cfg and credentials_available():
        try:
            client = _get_gspread_client()
            if client is not None:
                sh = client.open_by_key(cfg["sheet_id"])
                if cfg.get("worksheet_gid") is not None:
                    ws = sh.get_worksheet_by_id(cfg["worksheet_gid"])
                elif cfg.get("worksheet"):
                    ws = sh.worksheet(cfg["worksheet"])
                else:
                    ws = sh.get_worksheet(0)
                # get_all_records() raises on sheets with duplicate or blank
                # headers (common in wide SurveyCTO tools). Parse values manually
                # so such sheets still load: keep first-seen header names, make
                # later collisions and blanks unique instead of failing.
                vals = ws.get_all_values()
                if vals and len(vals) > 1:
                    header = vals[0]
                    seen, clean = {}, []
                    for i, h in enumerate(header):
                        h = (str(h).strip() or f"col_{i}")
                        if h in seen:
                            seen[h] += 1
                            h = f"{h}_{seen[h]}"
                        else:
                            seen[h] = 0
                        clean.append(h)
                    df = pd.DataFrame(vals[1:], columns=clean)
                    # blank cells come back as "" — treat as missing
                    df = df.replace("", pd.NA)
                    if len(df):
                        _FETCH_ERRORS.pop(stream_key, None)
                        return df, "live"
                _FETCH_ERRORS[stream_key] = "Live sheet returned no rows (empty worksheet or wrong tab)."
        except Exception as e:
            _FETCH_ERRORS[stream_key] = f"{type(e).__name__}: {str(e)[:400]}"

    # 2. Fallback: local CSV
    # TEMP DEBUG: disable fallback
# if fallback and os.path.exists(fallback):
#     return pd.read_csv(fallback), "local"
        except Exception:
            pass
    return pd.DataFrame(), "empty"


def fetch(stream_key: str) -> pd.DataFrame:
    """Public fetch — returns just the DataFrame and records the source mode."""
    
    df, source = _fetch_sheet(stream_key)

    # DEBUG LINE (temporary - remove later)
    st.write(f"[DEBUG] {stream_key} -> rows={df.shape[0]}, cols={df.shape[1]}, source={source}")

    # Track which sources are live vs local for the sidebar indicator
    modes = st.session_state.setdefault("_data_source_modes", {})
    modes[stream_key] = source

    return df


def data_source_summary() -> dict:
    """Return {'mode': 'live'|'local'|'mixed', 'detail': {...}, 'last_refresh': ts}."""
    modes = st.session_state.get("_data_source_modes", {})
    if not modes:
        # Determine likely mode without forcing a fetch
        return {"mode": "live" if credentials_available() else "local",
                "detail": {}, "configured": credentials_available()}
    vals = set(modes.values())
    if vals == {"live"}:
        mode = "live"
    elif "live" in vals:
        mode = "mixed"
    else:
        mode = "local"
    return {"mode": mode, "detail": dict(modes),
            "configured": credentials_available()}


def force_refresh():
    """Clear the cached fetches so the next load pulls fresh from Google."""
    _fetch_sheet.clear()
    st.session_state.pop("_data_source_modes", None)


def render_data_status(st_module, C):
    """Prominent sidebar banner: LIVE vs LOCAL, with a manual refresh button."""
    st = st_module
    summ = data_source_summary()
    mode = summ["mode"]
    if mode == "live":
        bg, label, sub = C["green"], "● LIVE", "Google Sheets"
    elif mode == "mixed":
        bg, label, sub = C["amber"], "● PARTLY LIVE", "some streams on local CSV"
    else:
        bg, label, sub = C["grey"], "● LOCAL CSV", (
            "no key file — not live" if not summ.get("configured")
            else "live fetch failed — using CSV (check sharing)")
    st.sidebar.markdown(
        f"<div style='background:{bg};color:#FFFFFF;padding:8px 12px;border-radius:8px;"
        f"margin:8px 0 6px;text-align:center;line-height:1.3;'>"
        f"<div style='font-size:13px;font-weight:700;letter-spacing:0.3px;'>{label} DATA SOURCE</div>"
        f"<div style='font-size:10px;opacity:0.9;margin-top:2px;'>{sub}</div></div>",
        unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh data now", use_container_width=True,
                          key="force_refresh_btn"):
        force_refresh()
        st.rerun()
    # Surface the real reason a live fetch failed, so it isn't silently hidden.
    errs = fetch_errors()
    if errs:
        with st.sidebar.expander("⚠ Data source details", expanded=(mode != "live")):
            for stream, msg in errs.items():
                st.markdown(f"**{stream}**: {msg}")