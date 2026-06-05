"""
utils/data_loader.py
Cached loaders for all programme data streams + derived KPI computation.
Data is pulled live from Google Sheets (via gsheets_source) with automatic
fallback to local CSVs when credentials aren't configured.
"""
import pandas as pd
import numpy as np
import streamlit as st
import hashlib, os

from utils.gsheets_source import fetch as _gs_fetch

DATA_DIR = "data"

def anon(raw, pfx="SRV"):
    if pd.isna(raw): return f"{pfx}-UNKNOWN"
    return f"{pfx}-" + hashlib.md5(str(raw).encode()).hexdigest()[:8].upper()

def _col(df, name, default=None):
    """Return df[name] as a Series if it exists, else a Series of `default`
    of the right length. Guards against live sheets missing a column, which
    would otherwise make df.get(name) return a scalar."""
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)

def _split_gps(df):
    """Ensure df has numeric 'lat' and 'lon' columns. SurveyCTO exports a single
    'GPS' column like 'lat lon altitude accuracy'. The old CSVs were pre-split;
    live sheets are not. This handles both, plus hyphenated GPS-Latitude/Longitude."""
    # Already split (old CSV path)
    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        return df
    # Hyphenated form
    if "GPS-Latitude" in df.columns:
        df["lat"] = pd.to_numeric(_col(df, "GPS-Latitude"), errors="coerce")
        df["lon"] = pd.to_numeric(_col(df, "GPS-Longitude"), errors="coerce")
        return df
    # Single 'GPS' string: "lat lon alt acc"
    if "GPS" in df.columns:
        gps = _col(df, "GPS").astype(str).str.strip()
        parts = gps.str.split(r"\s+", expand=True)
        df["lat"] = pd.to_numeric(parts[0], errors="coerce") if parts.shape[1] > 0 else np.nan
        df["lon"] = pd.to_numeric(parts[1], errors="coerce") if parts.shape[1] > 1 else np.nan
        # Keep only valid SW-Uganda-ish coordinates; null out garbage
        bad = ~(df["lat"].between(-2, 0.5) & df["lon"].between(29, 31))
        df.loc[bad, ["lat", "lon"]] = np.nan
    else:
        df["lat"] = np.nan
        df["lon"] = np.nan
    return df

@st.cache_data(ttl=300, show_spinner="Loading survivor data…")
def load_survivors():
    df = _gs_fetch("survivors")
    if not len(df): return pd.DataFrame()
    df = _split_gps(df)
    df["date"] = pd.to_datetime(_col(df, "date").where(_col(df,"date").notna(), _col(df,"date_enrolled")), errors="coerce")
    df["year"]  = df["date"].dt.year.astype("Int64")
    df["month"] = df["date"].dt.month.astype("Int64")
    df["month_label"] = df["date"].dt.to_period("M").astype(str)
    df["quarter"] = "Q" + df["date"].dt.quarter.astype(str) + " " + df["year"].astype(str)
    df["is_child"] = pd.to_numeric(_col(df, "client_age"), errors="coerce") < 18
    df["district"] = _col(df, "district", "Unknown").fillna("Unknown").replace({"Other_District":"Other"})
    df["survivor_token"] = _col(df, "client_id").apply(lambda x: anon(x))
    if "assault_label" in df.columns:
        df["assault_cat"] = df["assault_label"].map({
            "Defilement": "Sexual Violence", "Rape": "Sexual Violence",
            "Sexual assault": "Sexual Violence", "Physical assault": "Physical Violence",
            "Child neglect/abuse": "Child-Related", "Denied resources": "Economic Violence",
            "Early marriage": "Child-Related", "Emotional/Psychological abuse": "Psychological",
        }).fillna("Other")
    return df

@st.cache_data(ttl=300, show_spinner="Loading perpetrator data…")
def load_perpetrators():
    df = _gs_fetch("perpetrators")
    if not len(df): return pd.DataFrame()
    df = _split_gps(df)
    df["date"] = pd.to_datetime(_col(df, "date").where(_col(df,"date").notna(), _col(df,"survey_date")), errors="coerce")
    df["year"]  = df["date"].dt.year.astype("Int64")
    df["month_label"] = df["date"].dt.to_period("M").astype(str)
    df["perp_token"] = _col(df, "client_id").apply(lambda x: anon(x, "PRP"))
    df["is_enrolled"] = _col(df, "report_category", "") == "enrollment"
    df["is_followup"]  = _col(df, "report_category", "").astype(str).str.contains("followup", na=False)
    df["arrested"] = _col(df, "perpetrator_location_label", "") == "Arrested"
    district = _col(df, "district")
    district = district.where(district.notna(), _col(df, "district_tracking"))
    df["district"] = district.fillna("Unknown")
    df["case_won"]  = _col(df, "case_status_overview", "") == "Won"
    df["case_lost"] = _col(df, "case_status_overview", "") == "Lost"
    df["in_court"]  = _col(df, "case_status_overview", "") == "Court"
    df["date_enrolled_dt"] = pd.to_datetime(_col(df, "date_enrolled"), errors="coerce")
    df["days_to_followup"] = (df["date"] - df["date_enrolled_dt"]).dt.days
    # --- analysis-friendly names (raw SurveyCTO field names are misleading) -------
    # In the PERPETRATOR tool the field 'survivor_id_1' actually holds the
    # PERPETRATOR's own tracking id (used for follow-up preloading), NOT a survivor
    # id; 'survivor_id_again' is its re-entry confirmation. 'pre_survivor_id' is the
    # LINKED survivor's client_id (the cross-sheet key). Expose clear names for
    # analysis. Raw columns are retained so key-resolution keeps working.
    df["linked_survivor_id"]              = _col(df, "pre_survivor_id")
    df["perpetrator_tracking_id"]         = _col(df, "survivor_id_1")
    df["perpetrator_tracking_id_confirm"] = _col(df, "survivor_id_again")
    return df

@st.cache_data(ttl=300, show_spinner="Loading outreach data…")
def load_outreach():
    # Combine the 2025 and 2024 outreach sheets (live), falling back to the CSV.
    parts = []
    for key in ("outreach_2025", "outreach_2024"):
        d = _gs_fetch(key)
        if len(d):
            parts.append(d)
    if parts:
        df = pd.concat(parts, ignore_index=True, sort=False)
        # de-dup any rows that appear in both sheets
        if "KEY" in df.columns:
            df = df.drop_duplicates(subset="KEY")
    else:
        df = pd.DataFrame()
    if not len(df): return pd.DataFrame()
    # Date: live sheets use 'outreach_date'; CSV used 'date'.
    date_src = _col(df, "date")
    date_src = date_src.where(date_src.notna(), _col(df, "outreach_date"))
    date_src = date_src.where(date_src.notna(), _col(df, "entry_date"))
    df["date"] = pd.to_datetime(date_src, errors="coerce")
    df["year"]  = df["date"].dt.year.astype("Int64")
    df["month_label"] = df["date"].dt.to_period("M").astype(str)
    district = _col(df, "district_label")
    district = district.where(district.notna(), _col(df, "district"))
    df["district"] = district.fillna("Unknown")
    # People reached: live sheets use males_attending / females_attending and have
    # no single 'total'. Build males/females/total from whichever names exist.
    males = pd.to_numeric(_col(df, "males"), errors="coerce")
    males = males.where(males.notna(), pd.to_numeric(_col(df, "males_attending"), errors="coerce"))
    females = pd.to_numeric(_col(df, "females"), errors="coerce")
    females = females.where(females.notna(), pd.to_numeric(_col(df, "females_attending"), errors="coerce"))
    df["males"] = males.fillna(0)
    df["females"] = females.fillna(0)
    total = pd.to_numeric(_col(df, "total"), errors="coerce")
    # If no explicit total, sum males + females
    df["total"] = total.where(total.notna(), df["males"] + df["females"]).fillna(0)
    # GPS: live sheets use GPS-Latitude / GPS-Longitude (hyphenated)
    if "lat" not in df.columns:
        df["lat"] = pd.to_numeric(_col(df, "GPS-Latitude"), errors="coerce")
    if "lon" not in df.columns:
        df["lon"] = pd.to_numeric(_col(df, "GPS-Longitude"), errors="coerce")
    if "event_type_label" in df.columns:
        df["event_cat"] = df["event_type_label"].map({
            "OPD Clients (Facility Premises)": "Health Facility",
            "School Sensitization": "School",
            "Public/community/group/event/gathering (at a party/burial/gathering/travelers/etc.)": "Community",
            "Community (Church/Party/Burial/Workers/Market)": "Community",
            "SGBV activism/awareness days": "Awareness Day",
            "SGBV radio talk show": "Radio",
            "SGBV walk/running event": "Awareness Day",
            "SGBV training/induction/orientation/etc": "Training",
            "SGBV seminar/conference/meeting/etc": "Seminar",
            "Boda Boda Riders": "Boda Boda",
            "Grandfathers": "Male Engagement",
        }).fillna("Other")
    return df

@st.cache_data(ttl=300, show_spinner="Loading school data…")
def load_school():
    # School Social Work Tool — live Google Sheet with CSV fallback.
    # The live sheet holds the raw SurveyCTO columns and (unlike the old CSV)
    # has no pre-computed date/total/males/females/lat/lon, so derive them here.
    df = _gs_fetch("school_social_work")
    if not len(df): return pd.DataFrame()
    df = _split_gps(df)
    # Date: CSV used 'date'; live sheet uses 'outreach_date' (then entry_date / SubmissionDate)
    date_src = _col(df, "date")
    date_src = date_src.where(date_src.notna(), _col(df, "outreach_date"))
    date_src = date_src.where(date_src.notna(), _col(df, "entry_date"))
    date_src = date_src.where(date_src.notna(), _col(df, "SubmissionDate"))
    df["date"] = pd.to_datetime(date_src, errors="coerce")
    df["year"]  = df["date"].dt.year.astype("Int64")
    df["month_label"] = df["date"].dt.to_period("M").astype(str)
    df["district"] = _col(df, "district", "Unknown").fillna("Unknown")
    # Attendance: live sheet uses males_attending / females_attending and attend_tot.
    males = pd.to_numeric(_col(df, "males"), errors="coerce")
    males = males.where(males.notna(), pd.to_numeric(_col(df, "males_attending"), errors="coerce"))
    females = pd.to_numeric(_col(df, "females"), errors="coerce")
    females = females.where(females.notna(), pd.to_numeric(_col(df, "females_attending"), errors="coerce"))
    df["males"] = males.fillna(0)
    df["females"] = females.fillna(0)
    total = pd.to_numeric(_col(df, "total"), errors="coerce")
    total = total.where(total.notna(), pd.to_numeric(_col(df, "attend_tot"), errors="coerce"))
    df["total"] = total.where(total.notna(), df["males"] + df["females"]).fillna(0)
    df["school_label"] = _col(df, "pre_school").fillna("Unknown School")
    return df

# ── NARRATIVE / FOLLOW-UP ROLLUP (live) ───────────────────────────────────────
# The Narratives and Reports pages used to read pre-built CSVs
# (perpetrators_narrative.csv, perpetrators_followup.csv, survivors_followup.csv)
# that an offline build produced. Those are derived products: one row per case
# with the follow-up history rolled up. The loaders below recompute that rollup
# live from the perpetrator/survivor sheets, where enrollments and follow-ups
# live together and are told apart by `report_category`.
#
# Case linkage: follow-up rows have NO client_id of their own — they reference
# the original case by `survivor_id_1` (the form pulls up the existing case),
# falling back to `pre_survivor_id`. The enrollment's `client_id` is the case id.
_CLOSED_STATUSES = ["Won", "Lost", "Transfers"]
_AGEING_BANDS = [
    ("0-30 days (current)", 0, 30), ("31-60 days", 31, 60),
    ("61-90 days", 61, 90), ("91-180 days", 91, 180),
    ("180+ days (stale)", 181, 10**9),
]

def _split_enroll_followup(df):
    rc = _col(df, "report_category", "").astype(str)
    is_enr = rc.str.contains("enroll", na=False)
    return df[is_enr].copy(), df[~is_enr].copy()

def _survivor_fu_key(fol):
    """Survivor-sheet follow-up -> its survivor case id.
    The follow-up references the enrolment via survivor_id_1 (== client_id by
    value), falling back to pre_survivor_id."""
    k = _col(fol, "survivor_id_1").astype(str).str.strip()
    bad = k.isin(["", "nan", "None", "NaN", "<NA>"])
    return k.where(~bad, _col(fol, "pre_survivor_id").astype(str).str.strip())

def _legal_fu_key(fol):
    """Perpetrator-sheet (legal) follow-up/arrest -> the SURVIVOR case id.
    The legal advocate enters the survivor's ID in pre_survivor_id (col Y), which
    equals the survivor sheet's client_id (col NC). That is the cross-sheet link.
    We do NOT fall back to survivor_id_1 here: in the perpetrator sheet that column
    is the PERPETRATOR's own tracking id, so using it would attach a legal note to
    the wrong (or a non-existent) survivor case. If the survivor link is blank the
    row is left unlinked rather than mis-attached (the safer failure)."""
    k = _col(fol, "linked_survivor_id")
    k = k.where(k.notna(), _col(fol, "pre_survivor_id")).astype(str).str.strip()
    bad = k.isin(["", "nan", "None", "NaN", "<NA>"])
    return k.where(~bad, "")

# Back-compat alias (older callers)
def _resolve_case_key(fol):
    return _survivor_fu_key(fol)

def _followup_date(fol):
    d = _col(fol, "follow_up_date")
    d = d.where(d.notna(), _col(fol, "date"))
    d = d.where(d.notna(), _col(fol, "survey_date"))
    return pd.to_datetime(d, errors="coerce")

@st.cache_data(ttl=300, show_spinner="Loading narrative data…")
def load_perp_narrative():
    """NARRATIVE CASE rows = SURVIVOR INTAKE enrollments.

    The assault narrative (assault_narration, assault_label, etc.) is captured at
    survivor intake, so the narrative case universe is the survivor sheet's
    enrollment rows — NOT the perpetrator sheet. (The perpetrator sheet is a
    separate case universe used for the legal-tracking timeline; its IDs do not
    overlap survivor case IDs.)

    The follow-up rollup (last_status, last_activity_date, n_followups, is_closed,
    ageing_band) is computed from SURVIVOR follow-ups — the case-management visits
    on the survivor — linked by matching the follow-up's survivor_id_1 to the
    enrollment's client_id. IDs are matched by VALUE: the two row-types use
    different column names (survivor_id_1 vs client_id) for the same case id.

    Conservative by design: a follow-up is attributed only on a real ID match, so
    a missed link makes a case look *staler*, never falsely current."""
    sv = load_survivors()
    if not len(sv): return pd.DataFrame()
    enr, sv_fol = _split_enroll_followup(sv)
    if not len(enr): return pd.DataFrame()

    # Two follow-up streams keyed to the SAME survivor case id (client_id):
    #   • survivor case-management follow-ups  (survivor sheet, via survivor_id_1)
    #   • legal advocate follow-ups / arrests  (perpetrator sheet, via pre_survivor_id)
    sv_fol = sv_fol.assign(_fdate=_followup_date(sv_fol), _case=_survivor_fu_key(sv_fol),
                           _src="survivor")
    try:
        pp = load_perpetrators()
        _, pp_fol = _split_enroll_followup(pp) if len(pp) else (None, pd.DataFrame())
    except Exception:
        pp_fol = pd.DataFrame()
    if len(pp_fol):
        pp_fol = pp_fol.assign(_fdate=_followup_date(pp_fol), _case=_legal_fu_key(pp_fol),
                               _src="legal")

    keep = ["_case", "_fdate", "_src", "case_status_overview", "case_status_label",
            "comments_case_status"]
    def _slim(d):
        if not len(d): return pd.DataFrame(columns=keep)
        for c in keep:
            if c not in d.columns: d[c] = np.nan
        return d[keep]
    allfu = pd.concat([_slim(sv_fol), _slim(pp_fol)], ignore_index=True)
    allfu = allfu[allfu["_case"].notna() & ~allfu["_case"].astype(str).isin(["", "nan", "None"])]
    allfu = allfu.sort_values("_fdate")

    n_fu       = allfu.groupby("_case").size()
    last_fdate = allfu.groupby("_case")["_fdate"].max()
    # Latest status prefers the most recent LEGAL follow-up (authoritative case
    # outcome); falls back to the most recent of any follow-up.
    legal = allfu[allfu["_src"] == "legal"].dropna(subset=["_fdate"])
    last_legal = legal.groupby("_case").tail(1).set_index("_case")
    last_any   = allfu.dropna(subset=["_fdate"]).groupby("_case").tail(1).set_index("_case")

    cid = _col(enr, "client_id").astype(str).str.strip()
    def _status_for(case_id):
        if case_id in last_legal.index: return last_legal.at[case_id, "case_status_overview"]
        if case_id in last_any.index:   return last_any.at[case_id, "case_status_overview"]
        return np.nan

    if "survivor_token" not in enr.columns:
        enr["survivor_token"] = _col(enr, "client_id").apply(lambda x: anon(x, "SRV"))
    enr["n_followups"]        = cid.map(n_fu).fillna(0).astype(int)
    enr["last_followup_date"] = pd.to_datetime(cid.map(last_fdate))
    has_fu = enr["n_followups"] > 0
    enr["last_status"]        = cid.map(_status_for).where(has_fu, "No follow-up yet")
    enr["last_status"]        = enr["last_status"].fillna("Follow-up (status not recorded)")
    enr["last_comment"]       = cid.map(
        lambda c: last_any.at[c, "comments_case_status"] if c in last_any.index else np.nan
    ).where(has_fu, _col(enr, "comments_case_status"))

    enr_date = pd.to_datetime(
        _col(enr, "date_enrolled").where(_col(enr, "date_enrolled").notna(), _col(enr, "survey_date")),
        errors="coerce")
    enr["date_enrolled_dt"]  = enr_date
    enr["last_activity_date"] = enr["last_followup_date"].where(has_fu, enr_date)
    enr["is_closed"] = enr["last_status"].isin(_CLOSED_STATUSES)
    enr["is_open"]   = ~enr["is_closed"]

    ref = pd.Timestamp.now().normalize()
    enr["days_since_update"] = (ref - pd.to_datetime(enr["last_activity_date"])).dt.days
    def _band(r):
        if r["is_closed"]: return "Closed"
        d = r["days_since_update"]
        if pd.isna(d): return "No date"
        for lbl, lo, hi in _AGEING_BANDS:
            if lo <= d <= hi: return lbl
        return "180+ days (stale)"
    enr["ageing_band"] = enr.apply(_band, axis=1)
    return enr

@st.cache_data(ttl=300, show_spinner=False)
def load_perp_followups():
    """Perpetrator/legal follow-up rows (live) for the legal-notes timeline.
    `date` is set to the follow-up date and `client_id` is resolved to the parent
    perpetrator case. Note: these belong to the perpetrator case universe and do
    not share IDs with survivor cases, so they feed the all-notes legal view."""
    pp = load_perpetrators()
    if not len(pp): return pd.DataFrame()
    _, fol = _split_enroll_followup(pp)
    if not len(fol): return pd.DataFrame()
    fol = fol.copy()
    fol["date"] = _followup_date(fol)
    fol["client_id"] = _legal_fu_key(fol)   # SURVIVOR case id (pre_survivor_id, col Y)
    return fol

@st.cache_data(ttl=300, show_spinner=False)
def load_survivor_followups():
    """Survivor case-management follow-up rows (live): mental-health, physical and
    case-status notes. `client_id` resolved to the parent survivor case so the
    per-case views can join, and `date` set to the follow-up date."""
    sv = load_survivors()
    if not len(sv): return pd.DataFrame()
    _, fol = _split_enroll_followup(sv)
    if not len(fol): return pd.DataFrame()
    fol = fol.copy()
    fol["date"] = _followup_date(fol)
    fol["client_id"] = _survivor_fu_key(fol)   # parent survivor-case id
    if "survivor_token" not in fol.columns:
        fol["survivor_token"] = fol["client_id"].apply(lambda x: anon(x, "SRV"))
    return fol

def load_all():
    return {
        "survivors":   load_survivors(),
        "perpetrators":load_perpetrators(),
        "outreach":    load_outreach(),
        "school":      load_school(),
    }

def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    d = df.copy()
    if f.get("district") and f["district"] != "All":
        dcol = next((c for c in ["district","district_label","district_tracking"] if c in d.columns), None)
        if dcol: d = d[d[dcol].str.contains(f["district"], na=False, case=False)]
    if f.get("years") and len(f["years"]) > 0:
        if "year" in d.columns: d = d[d["year"].isin(f["years"])]
    if f.get("violence") and f["violence"] != "All":
        vcol = next((c for c in ["assault_label","pre_survivor_assault","assault_tracking"] if c in d.columns), None)
        if vcol: d = d[d[vcol] == f["violence"]]
    if f.get("gender") and f["gender"] != "All":
        gcol = next((c for c in ["client_gender","gender_tracking"] if c in d.columns), None)
        if gcol: d = d[d[gcol].isin([f["gender"][0], f["gender"]])]
    return d

def compute_kpis(sv, pp, ot, sc) -> dict:
    sv_e = sv[sv.get("report_category","").str.contains("enrollment",na=False)] if len(sv) else sv
    pp_e = pp[pp["is_enrolled"]] if "is_enrolled" in pp.columns and len(pp) else pp
    pp_f = pp[pp.get("is_followup", pd.Series(dtype=bool))] if "is_followup" in pp.columns and len(pp) else pp

    total   = len(sv_e)
    arrested= int(pp_e["arrested"].sum()) if "arrested" in pp_e.columns else 0
    won     = int(pp_f["case_won"].sum()) if "case_won" in pp_f.columns else 0
    ot_r    = int(ot["total"].sum()) if "total" in ot.columns else 0
    sc_r    = int(sc["total"].sum()) if "total" in sc.columns else 0

    return {
        "total_survivors":   total,
        "active_cases":      int((~sv_e.get("case_status_clean", pd.Series(["Active"]*total)).isin(["Closed"])).sum()),
        "crisis_cases":      int(sv_e.get("has_crisis", pd.Series(dtype=bool)).sum()),
        "children":          int(sv_e.get("is_child", pd.Series(dtype=bool)).sum()),
        "perpetrators":      len(pp_e),
        "arrested":          arrested,
        "arrest_rate":       round(100 * arrested / max(len(pp_e), 1), 1),
        "convicted":         won,
        "conviction_rate":   round(100 * won / max(len(pp_e), 1), 1),
        "outreach_sessions": len(ot),
        "outreach_reach":    ot_r,
        "school_sessions":   len(sc),
        "school_reach":      sc_r,
        "total_reach":       ot_r + sc_r,
        "districts":         sv_e.get("district", pd.Series(dtype=str)).nunique(),
    }