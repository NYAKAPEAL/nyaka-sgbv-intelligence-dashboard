"""
pages/7_Narratives.py
Narratives Intelligence — anonymised case accounts, thematic analysis,
keyword search, survivor follow-up, perpetrator legal timeline.
Real data from assault_narration, crime_scene_description, comments_case_status,
post_mental_comments, post_physical_comments fields.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import C, VIOLENCE_COLORS
from utils.auth import check, sidebar_panel, can_access
from utils.viz import section, page_header, safe_notice

if not check():
    st.warning("Please log in.")
    st.stop()
if not can_access("survivors"):
    st.error("🔒 Access denied.")
    st.stop()

# ── DATA LOADERS ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Loading narrative data…")
def load_narratives():
    # Prefer the LIVE recompute from the perpetrator/survivor sheets (via the
    # shared data layer). Fall back to the pre-built CSVs only if live data
    # isn't available, so the page never goes blank.
    from utils.data_loader import (load_perp_narrative, load_perp_followups,
                                    load_survivor_followups)
    pp_e  = load_perp_narrative()
    pp_fu = load_perp_followups()
    sv_fu = load_survivor_followups()

    if not len(pp_e):
        data_dir = "data"
        def _try(path):
            try:
                return pd.read_csv(path, low_memory=False)
            except Exception:
                return pd.DataFrame()
        pp_e  = _try(f"{data_dir}/perpetrators_narrative.csv")
        pp_fu = _try(f"{data_dir}/perpetrators_followup.csv")
        sv_fu = _try(f"{data_dir}/survivors_followup.csv")

    if len(pp_e):
        if "date" not in pp_e.columns:
            pp_e["date"] = pd.to_datetime(pp_e.get("date_enrolled"), errors="coerce")
        pp_e["date"] = pd.to_datetime(pp_e["date"], errors="coerce")
        pp_e["year"]  = pp_e["date"].dt.year.astype("Int64")
        pp_e["month_label"] = pp_e["date"].dt.to_period("M").astype(str)
        # Ageing fields (pre-computed in data build)
        for dc in ["last_activity_date", "last_followup_date", "date_enrolled_dt"]:
            if dc in pp_e.columns:
                pp_e[dc] = pd.to_datetime(pp_e[dc], errors="coerce")
        if "days_since_update" in pp_e.columns:
            pp_e["days_since_update"] = pd.to_numeric(pp_e["days_since_update"],
                                                        errors="coerce")

    if len(pp_fu):
        pp_fu["date"] = pd.to_datetime(pp_fu.get("follow_up_date",
                                                    pp_fu.get("date")), errors="coerce")

    if len(sv_fu):
        sv_fu["date"] = pd.to_datetime(sv_fu.get("date",
                                                    sv_fu.get("follow_up_date")),
                                        errors="coerce")
    return pp_e, pp_fu, sv_fu


# Reference date for ageing — the most recent activity in the dataset.
# In a live deployment this becomes datetime.now().
def get_reference_date(pp_e):
    if len(pp_e) and "last_activity_date" in pp_e.columns:
        mx = pp_e["last_activity_date"].max()
        if pd.notna(mx):
            return mx
    return pd.Timestamp.now().normalize()


AGEING_BANDS = [
    ("0-30 days (current)",   0,   30,  "green"),
    ("31-60 days",            31,  60,  "teal"),
    ("61-90 days",            61,  90,  "gold"),
    ("91-180 days",           91,  180, "amber"),
    ("180+ days (stale)",     181, 99999, "red"),
]


def compute_ageing(pp_e, ref_date=None):
    """Return pp_e with refreshed ageing band + days_since_update vs ref_date."""
    if not len(pp_e):
        return pp_e
    d = pp_e.copy()
    if ref_date is None:
        ref_date = get_reference_date(d)
    if "last_activity_date" in d.columns:
        d["days_since_update"] = (ref_date - d["last_activity_date"]).dt.days
    if "is_closed" not in d.columns and "last_status" in d.columns:
        d["is_closed"] = d["last_status"].isin(["Won", "Lost", "Transfers"])
    d["is_open"] = ~d.get("is_closed", pd.Series([False] * len(d)))

    def band(row):
        if row.get("is_closed", False):
            return "Closed"
        days = row.get("days_since_update")
        if pd.isna(days):
            return "No date"
        for label, lo, hi, _ in AGEING_BANDS:
            if lo <= days <= hi:
                return label
        return "180+ days (stale)"
    d["ageing_band"] = d.apply(band, axis=1)
    return d


@st.cache_data(ttl=300, show_spinner=False)
def keyword_theme_analysis(df: pd.DataFrame) -> dict:
    """Count narration mentions of key themes from real assault_narration field."""
    if "assault_narration" not in df.columns:
        return {}
    text = df["assault_narration"].fillna("").astype(str).str.lower()
    themes = {
        "At/near home":        ["house", "home", "compound", "room", "door"],
        "Bush / forest":       ["bush", "forest", "garden", "plantation", "shrubs"],
        "School premises":     ["school", "class", "teacher", "lessons"],
        "Water collection":    ["water", "well", "river", "spring", "fetch"],
        "Path / road":         ["path", "road", "walking", "way home", "route"],
        "Night-time incident": ["night", "dark", "evening", "after dark"],
        "Survivor was alone":  ["alone", "by herself", "by himself", "nobody"],
        "Boda boda":           ["boda", "motorcycle", "bicycle", "transport"],
        "Child on errand":     ["sent", "errand", "firewood", "charcoal", "fetch", "collect"],
        "Market / trading":    ["market", "shop", "trading", "selling"],
    }
    return {theme: int(text.apply(lambda n: any(k in str(n) for k in kw)).sum())
            for theme, kw in themes.items()}


@st.cache_data(ttl=300, show_spinner=False)
def top_keywords(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Frequency of meaningful words across all narrations."""
    if "assault_narration" not in df.columns:
        return pd.DataFrame(columns=["word", "count"])
    stop = {"the","a","an","and","or","in","at","of","to","was","is","had","he",
            "she","her","his","their","they","were","with","from","that","this",
            "on","for","not","by","as","it","be","are","have","when","after",
            "before","then","back","got","has","but","so","who","its","all","him"}
    words: dict = {}
    for text in df["assault_narration"].dropna():
        for w in str(text).lower().split():
            w = w.strip(".,;:!?\"'()-")
            if len(w) > 3 and w not in stop:
                words[w] = words.get(w, 0) + 1
    df_w = pd.DataFrame(sorted(words.items(), key=lambda x: -x[1]),
                        columns=["word", "count"])
    return df_w.head(n)


def anon(raw, pfx="SRV"):
    if pd.isna(raw):
        return f"{pfx}-UNKNOWN"
    return pfx + "-" + hashlib.md5(str(raw).encode()).hexdigest()[:8].upper()


# ── LOOKUPS ───────────────────────────────────────────────────────────────────
LOC_LABELS = {
    "home":               "At / near home",
    "bush_forest":        "Bush / forest",
    "school_premises":    "School premises",
    "water_point":        "Water collection point",
    "path_road":          "Path / road",
    "market":             "Market / trading centre",
    "church":             "Church / gathering",
    "community_gathering":"Community event",
    "boda_transport":     "Boda boda transport",
}
TIME_LABELS = {
    "1": "Morning (5am–12pm)",   "1.0": "Morning (5am–12pm)",
    "2": "Afternoon (12–5pm)",   "2.0": "Afternoon (12–5pm)",
    "3": "Evening (5–9pm)",      "3.0": "Evening (5–9pm)",
    "4": "Night (9pm–5am)",      "4.0": "Night (9pm–5am)",
    "5": "Not sure / unknown",   "5.0": "Not sure / unknown",
}
FACTOR_LABELS = {
    "child_unsupervised":  "Child unsupervised",
    "darkness":            "Darkness / poor lighting",
    "isolated_location":   "Isolated location",
    "caregiver_absent":    "Caregiver absent",
    "school_route":        "On school route",
    "child_errand_alone":  "Child sent on errand",
    "poverty_vulnerability":"Economic vulnerability",
    "trust_exploited":     "Trust / relationship exploited",
    "community_norms":     "Harmful community norms",
    "alcohol_substance":   "Alcohol / substance",
}
RISK_TIME = {
    "Night (9pm–5am)":      ("red",   "HIGH"),
    "Evening (5–9pm)":      ("amber", "MEDIUM"),
    "Morning (5am–12pm)":   ("green", "LOWER"),
    "Afternoon (12–5pm)":   ("green", "LOWER"),
    "Not sure / unknown":   ("grey",  "UNKNOWN"),
}
RISK_COLORS = {"red": C["red"], "amber": C["amber"], "green": C["green"], "grey": C["grey"]}


# ── THEME ICON MAP ────────────────────────────────────────────────────────────
THEME_ICONS = {
    "At/near home":        ("🏠", C["red"]),
    "Bush / forest":       ("🌿", C["green"]),
    "School premises":     ("🏫", C["orange"]),
    "Water collection":    ("💧", C["blue"]),
    "Path / road":         ("🛤️",  C["gold"]),
    "Night-time incident": ("🌙", C["purple"]),
    "Survivor was alone":  ("👤", C["red"]),
    "Boda boda":           ("🏍️",  C["amber"]),
    "Child on errand":     ("📦", C["orange"]),
    "Market / trading":    ("🏪", C["teal"]),
}


# ─────────────────────────────────────────────────────────────────────────────
# PAGE START
# ─────────────────────────────────────────────────────────────────────────────
sidebar_panel()
st.sidebar.markdown("---")

pp_e, pp_fu, sv_fu = load_narratives()
# Refresh ageing against the reference date (latest activity in the dataset;
# in a live deployment this is today's date).
REF_DATE = get_reference_date(pp_e)
pp_e = compute_ageing(pp_e, REF_DATE)

# Sidebar filters
yrs = sorted(pp_e["year"].dropna().unique().astype(int).tolist()) if len(pp_e) else [2022,2023,2024,2025,2026]
sel_yrs  = st.sidebar.multiselect("Year", yrs, default=yrs, key="narr_yr")
sel_dist = st.sidebar.selectbox("District", ["All","Kanungu","Rukungiri","Rubanda"], key="narr_d")
sel_viol = st.sidebar.selectbox("Violence type",
    ["All","Defilement","Rape","Physical assault","Child neglect/abuse",
     "Sexual assault","Denied resources"], key="narr_v")
sel_loc  = st.sidebar.selectbox("Crime scene type",
    ["All"] + list(LOC_LABELS.values()), key="narr_loc")
search   = st.sidebar.text_input("🔍 Keyword search in narrations", "",
                                  placeholder="water, school, boda, night…")

# Apply filters
df = pp_e.copy()
if sel_yrs:
    df = df[df["year"].isin(sel_yrs)]
if sel_dist != "All":
    if "district" in df.columns:
        df = df[df["district"].str.contains(sel_dist, na=False, case=False)]
if sel_viol != "All":
    if "assault_label" in df.columns:
        df = df[df["assault_label"].str.contains(sel_viol[:10], na=False, case=False)]
if sel_loc != "All":
    loc_key = {v: k for k, v in LOC_LABELS.items()}.get(sel_loc, "")
    if loc_key and "incident_location_type" in df.columns:
        df = df[df["incident_location_type"] == loc_key]
if search.strip():
    _q = search.strip()
    def _search_mask(col):
        if col in df.columns:
            return df[col].astype(str).str.contains(_q, case=False, na=False, regex=False)
        return pd.Series(False, index=df.index)
    mask = _search_mask("assault_narration") | _search_mask("crime_scene_description")
    df = df[mask]

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='font-size:10px;color:{C["grey"]};'>
  {len(df):,} matching cases<br>
  {df["assault_narration"].notna().sum():,} narrations<br>
  {df.get("crime_scene_description",pd.Series()).notna().astype(int).sum():,} crime scene descriptions<br>
  {len(pp_fu):,} legal follow-up notes<br>
  {len(sv_fu):,} survivor follow-up notes
</div>""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
page_header("Narratives Intelligence",
            "Case ageing & follow-up tracker · Anonymised accounts · Thematic analysis · "
            "Keyword search · Legal follow-up timeline",
            "📓")

st.markdown(f"""
<div style='background:{C["red_lt"]};border-left:4px solid {C["red"]};
            padding:9px 14px;border-radius:6px;font-size:11px;
            color:{C["red"]};margin-bottom:12px;display:flex;align-items:center;gap:8px;'>
  🔒 <strong>Survivor-safe mode:</strong>
  Real names replaced with tokens (SRV-XXXXXXXX). Exact locations
  omitted. Case managers see only their assigned cases.
  Legal advocates see legal notes only. Admin sees all.
</div>""", unsafe_allow_html=True)

with st.expander("ℹ️ How this data is structured (read before analysing)"):
    st.markdown("""
**Where the narrative comes from.** The assault account (`assault_narration`,
`assault_label`, incident details) is captured at **survivor intake**, not in the
perpetrator tool. So every narrative case here originates from a survivor enrollment.

**What the perpetrator tool contributes.** The perpetrator tool holds the **legal
case notes and status** (`comments_case_status`, case stage, arrest, conviction,
sentence). These are linked back to the survivor's case and shown on the legal
follow-up timeline. There is no separate "perpetrator narrative" stream by design.

**How the two sides link.** A perpetrator record points to its survivor case
through `pre_survivor_id` (shown in analysis as **`linked_survivor_id`**), which
matches the survivor's `client_id`.

**A naming caution for the perpetrator data.** The raw field `survivor_id_1`
(and its confirm `survivor_id_again`) in the perpetrator sheet does **not** hold a
survivor id — it is the **perpetrator's own tracking id**, used to pull up an
existing perpetrator record on follow-up. In this dashboard it is renamed to
**`perpetrator_tracking_id`** for clarity. Use `linked_survivor_id` for the
survivor link and `perpetrator_tracking_id` for the perpetrator's own id.
""")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_age, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⏳ Case ageing & follow-up",
    "📊 Thematic analysis",
    "📋 Case browser",
    "🔍 Case detail viewer",
    "📅 Legal follow-up timeline",
    "💬 Survivor follow-up notes",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB AGE — CASE AGEING & FOLLOW-UP TRACKER
# ════════════════════════════════════════════════════════════════════════════
with tab_age:
    from utils.viz import kpi as _kpi

    section("Case ageing report — which cases need follow-up?", "red")
    st.markdown(f"""
    <div style='background:{C["amber_lt"]};border-left:4px solid {C["amber"]};
                padding:9px 14px;border-radius:6px;font-size:11px;
                color:#5A3000;margin-bottom:12px;'>
      ⏱ <strong>How this works:</strong> "Days since update" is measured from each
      case's most recent activity (enrollment or last follow-up) to the
      reference date <strong>{REF_DATE:%d %b %Y}</strong> (the latest activity in
      the current data). In the live system this is measured against today, so
      the report continuously surfaces cases that have gone quiet. Closed cases
      (Won / Lost / Transferred) are excluded from ageing.
    </div>""", unsafe_allow_html=True)

    age_df = pp_e.copy()
    open_df = age_df[age_df.get("is_open", True)]
    closed_n = int(age_df.get("is_closed", pd.Series([False]*len(age_df))).sum())
    no_fu = int(age_df["last_followup_date"].isna().sum()) if "last_followup_date" in age_df.columns else 0

    # KPI strip
    stale_n  = int((open_df["ageing_band"] == "180+ days (stale)").sum())
    aging_91 = int(open_df["ageing_band"].isin(["91-180 days","180+ days (stale)"]).sum())
    current_n= int((open_df["ageing_band"] == "0-30 days (current)").sum())
    med_days = open_df["days_since_update"].median()

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(_kpi("Open cases", f"{len(open_df):,}", color="purple",
                              icon="📂", note=f"{closed_n} closed (excluded)"),
                         unsafe_allow_html=True)
    with k2: st.markdown(_kpi("Stale (180+ days)", f"{stale_n:,}", color="red",
                              icon="🚨", note="No update in 6+ months"),
                         unsafe_allow_html=True)
    with k3: st.markdown(_kpi("Need attention (90+ days)", f"{aging_91:,}", color="amber",
                              icon="⚠️", note="Overdue for follow-up"),
                         unsafe_allow_html=True)
    with k4: st.markdown(_kpi("No follow-up yet", f"{no_fu:,}", color="orange",
                              icon="📭", note="Enrolled, never followed up"),
                         unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Ageing band distribution
    col1, col2 = st.columns([3,2])
    with col1:
        band_order = ["0-30 days (current)","31-60 days","61-90 days",
                      "91-180 days","180+ days (stale)"]
        band_colors = {"0-30 days (current)":C["green"],"31-60 days":C["teal"],
                       "61-90 days":C["gold"],"91-180 days":C["amber"],
                       "180+ days (stale)":C["red"]}
        band_cnt = open_df["ageing_band"].value_counts().reindex(band_order).fillna(0).reset_index()
        band_cnt.columns = ["Band","Cases"]
        fig_band = px.bar(band_cnt, x="Band", y="Cases", color="Band",
                          color_discrete_map=band_colors, height=300,
                          template="plotly_white",
                          title="Open cases by time since last update",
                          text="Cases")
        fig_band.update_traces(textposition="outside")
        fig_band.update_layout(margin=dict(l=36,r=16,t=48,b=60), showlegend=False,
                               xaxis_tickangle=-20)
        st.plotly_chart(fig_band, use_container_width=True)
    with col2:
        # By district — where are the stale cases?
        if "district" in open_df.columns:
            stale_by_dist = open_df[open_df["ageing_band"]=="180+ days (stale)"]
            sd = stale_by_dist["district"].value_counts().reset_index()
            sd.columns = ["District","Stale cases"]
            fig_sd = px.bar(sd, x="Stale cases", y="District", orientation="h",
                            color_discrete_sequence=[C["red"]], height=300,
                            template="plotly_white",
                            title="Stale cases by district")
            fig_sd.update_layout(margin=dict(l=90,r=16,t=48,b=36))
            st.plotly_chart(fig_sd, use_container_width=True)

    # Stale cases needing action — priority worklist
    section("Priority worklist — oldest open cases first", "red")
    st.caption("Sorted by days since last update. These are the survivors whose "
               "cases have gone quiet and may need re-contact.")

    work_cols = [c for c in ["survivor_token","assault_label","district",
                              "subcounty_label","last_status","days_since_update",
                              "last_activity_date","n_followups","SGBV_staff_label"]
                 if c in open_df.columns]
    worklist = open_df[open_df["days_since_update"] >= 90].sort_values(
        "days_since_update", ascending=False)[work_cols].head(60)

    if len(worklist):
        disp = worklist.rename(columns={
            "survivor_token":"Case token","assault_label":"Violence type",
            "district":"District","subcounty_label":"Subcounty",
            "last_status":"Last status","days_since_update":"Days quiet",
            "last_activity_date":"Last activity","n_followups":"# follow-ups",
            "SGBV_staff_label":"Assigned officer",
        })
        if "Last activity" in disp.columns:
            disp["Last activity"] = pd.to_datetime(disp["Last activity"]).dt.strftime("%d %b %Y")
        disp["Days quiet"] = disp["Days quiet"].round(0).astype("Int64")

        def highlight_age(row):
            d = row.get("Days quiet", 0)
            if pd.isna(d): return [""]*len(row)
            if d > 365: return ["background-color:#FCE4E4"]*len(row)
            if d > 180: return ["background-color:#FFF0E0"]*len(row)
            return [""]*len(row)
        st.dataframe(disp.style.apply(highlight_age, axis=1),
                     use_container_width=True, hide_index=True, height=420)
        st.caption(f"Showing {len(worklist)} cases 90+ days without update "
                   f"(of {(open_df['days_since_update']>=90).sum()} total). "
                   "Red = over 1 year quiet; orange = over 180 days.")
    else:
        st.success("No open cases over 90 days without an update. Follow-up is current.")

    # Cases with no follow-up at all
    if no_fu > 0:
        section("Enrolled but never followed up", "orange")
        nofu_df = age_df[age_df["last_followup_date"].isna()]
        nofu_cols = [c for c in ["survivor_token","assault_label","district",
                                  "date_enrolled_dt","perpetrator_location_label",
                                  "SGBV_staff_label"] if c in nofu_df.columns]
        nofu_disp = nofu_df[nofu_cols].copy().rename(columns={
            "survivor_token":"Case token","assault_label":"Violence type",
            "district":"District","date_enrolled_dt":"Enrolled",
            "perpetrator_location_label":"Perpetrator status",
            "SGBV_staff_label":"Assigned officer",
        })
        if "Enrolled" in nofu_disp.columns:
            nofu_disp["Enrolled"] = pd.to_datetime(nofu_disp["Enrolled"]).dt.strftime("%d %b %Y")
        st.dataframe(nofu_disp.head(40), use_container_width=True, hide_index=True)
        st.caption(f"{no_fu} enrolled cases have no recorded follow-up visit. "
                   "These need a first follow-up scheduled.")




# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — THEMATIC ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    section("Theme distribution across narrations", "purple")
    st.caption(f"Automatic text-mining across {len(df):,} case narrations. "
               "Each case may match multiple themes.")

    themes = keyword_theme_analysis(df)
    if not themes:
        st.info("No narration data in current filter.")
    else:
        total_narr = len(df)
        cols = st.columns(5)
        for i, (theme, count) in enumerate(sorted(themes.items(), key=lambda x: -x[1])):
            icon, color = THEME_ICONS.get(theme, ("📌", C["grey"]))
            pct = round(100 * count / max(total_narr, 1))
            with cols[i % 5]:
                st.markdown(f"""
                <div style='background:{C["white"]};border:0.5px solid {C["purple_lt"]};
                            border-top:3px solid {color};border-radius:8px;
                            padding:10px 12px;text-align:center;margin-bottom:8px;
                            box-shadow:0 1px 4px rgba(0,0,0,0.05);'>
                  <div style='font-size:20px;margin-bottom:3px;'>{icon}</div>
                  <div style='font-size:22px;font-weight:700;color:{color};'>{count:,}</div>
                  <div style='font-size:10px;color:{C["grey"]};margin-top:2px;'>{theme}</div>
                  <div style='height:4px;background:#EEE;border-radius:2px;margin-top:6px;'>
                    <div style='height:4px;background:{color};width:{pct}%;border-radius:2px;'></div>
                  </div>
                  <div style='font-size:9px;color:{C["grey"]};margin-top:2px;'>{pct}% of cases</div>
                </div>""", unsafe_allow_html=True)

    section("Keyword frequency heatmap", "orange")
    kw_df = top_keywords(df)
    if not kw_df.empty:
        max_cnt = kw_df["count"].max()
        # Colour scale: high = red, mid = amber, low = green
        def kw_color(cnt):
            pct = cnt / max_cnt
            if pct > 0.6: return ("#FCEBEB", "#791F1F")
            if pct > 0.35: return ("#FAEEDA", "#633806")
            return ("#EAF3DE", "#27500A")

        cols5 = st.columns(5)
        for i, row in kw_df.iterrows():
            bg, fg = kw_color(row["count"])
            with cols5[i % 5]:
                st.markdown(f"""
                <div style='background:{bg};border-radius:6px;padding:7px 9px;
                            text-align:center;margin-bottom:6px;cursor:pointer;'>
                  <div style='font-size:12px;font-weight:500;color:{fg};'>{row["word"]}</div>
                  <div style='font-size:10px;color:{fg};opacity:0.75;'>{int(row["count"])}</div>
                </div>""", unsafe_allow_html=True)

    section("Crime scene type distribution", "teal")
    if "incident_location_type" in df.columns:
        loc_cnt = df["incident_location_type"].map(LOC_LABELS).fillna("Other").value_counts().reset_index()
        loc_cnt.columns = ["Location Type", "Cases"]
        fig = px.bar(loc_cnt.sort_values("Cases"), x="Cases", y="Location Type",
                     orientation="h", color="Cases",
                     color_continuous_scale="Purples", height=320,
                     template="plotly_white",
                     title="Incident location — from V3 crime scene type field")
        fig.update_layout(margin=dict(l=180, r=16, t=48, b=36), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    section("Contributing factors", "red")
    if "contributing_factors" in df.columns:
        all_factors = []
        for factors_str in df["contributing_factors"].dropna():
            for f in str(factors_str).split():
                lbl = FACTOR_LABELS.get(f.strip())
                if lbl:
                    all_factors.append(lbl)
        if all_factors:
            factor_cnt = pd.Series(all_factors).value_counts().reset_index()
            factor_cnt.columns = ["Factor", "Count"]
            fig2 = px.bar(factor_cnt.sort_values("Count"),
                          x="Count", y="Factor", orientation="h",
                          color_discrete_sequence=[C["red"]], height=280,
                          template="plotly_white",
                          title="Contributing factors (from V3 structured field)")
            fig2.update_layout(margin=dict(l=220, r=16, t=48, b=36))
            st.plotly_chart(fig2, use_container_width=True)

    section("Time-of-day risk profile", "amber")
    if "incident_time_of_day" in df.columns:
        time_cnt = df["incident_time_of_day"].map(TIME_LABELS).fillna("Not recorded").value_counts()
        c1, c2 = st.columns([2, 1])
        with c1:
            time_df = time_cnt.reset_index()
            time_df.columns = ["Time", "Count"]
            clr_map = {
                "Night (20–05h)": C["red"], "Evening (17–20h)": C["amber"],
                "Early morning (05–08h)": C["gold"], "Morning (08–12h)": C["green"],
                "Afternoon (12–17h)": C["green_lt"], "Not known": C["grey"],
            }
            fig3 = px.bar(time_df, x="Time", y="Count",
                          color="Time", color_discrete_map=clr_map,
                          height=280, template="plotly_white",
                          title="Incident time of day (V3 new field)")
            fig3.update_layout(margin=dict(l=36, r=16, t=48, b=36), showlegend=False)
            fig3.update_xaxes(tickangle=-20)
            st.plotly_chart(fig3, use_container_width=True)
        with c2:
            for time_lbl, cnt in time_cnt.items():
                color_key, risk_lbl = RISK_TIME.get(str(time_lbl), ("grey", "?"))
                clr = RISK_COLORS.get(color_key, C["grey"])
                lt  = clr.replace(")", ", 0.1)").replace("rgb", "rgba") if "rgb" in clr else clr + "1A"
                bg  = {"red": C["red_lt"], "amber": C["amber_lt"],
                       "green": C["green_lt"], "grey": "#F5F5F5"}.get(color_key, "#F5F5F5")
                st.markdown(f"""
                <div style='background:{bg};border-left:3px solid {clr};
                            border-radius:4px;padding:5px 10px;
                            margin-bottom:5px;display:flex;
                            align-items:center;justify-content:space-between;'>
                  <span style='font-size:10px;color:{clr};font-weight:500;'>{time_lbl}</span>
                  <span style='font-size:10px;font-weight:700;color:{clr};'>
                    {int(cnt)} · {risk_lbl}
                  </span>
                </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — CASE BROWSER
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    section(f"Case browser — {len(df):,} matching records", "purple")

    # Sort options
    sort_col = st.selectbox("Sort by", ["Date (newest)", "Most overdue (days quiet)",
                                         "Date (oldest)", "Violence type", "Location type"],
                            key="sort_cases")
    df_sorted = df.copy()
    if sort_col == "Most overdue (days quiet)" and "days_since_update" in df_sorted.columns:
        # Open cases first, oldest update first; closed cases last
        df_sorted["_open_rank"] = (~df_sorted.get("is_closed", False)).astype(int)
        df_sorted = df_sorted.sort_values(
            ["_open_rank", "days_since_update"], ascending=[False, False], na_position="last")
    elif sort_col == "Date (newest)":
        df_sorted = df_sorted.sort_values("date", ascending=False, na_position="last")
    elif sort_col == "Date (oldest)":
        df_sorted = df_sorted.sort_values("date", ascending=True, na_position="last")
    elif sort_col == "Violence type" and "assault_label" in df_sorted.columns:
        df_sorted = df_sorted.sort_values("assault_label")
    elif sort_col == "Location type" and "incident_location_type" in df_sorted.columns:
        df_sorted = df_sorted.sort_values("incident_location_type")

    if df_sorted.empty:
        st.info("No cases match the current filter combination.")
    else:
        # Show 20 per page
        page_size = 20
        total_pages = max(1, (len(df_sorted) - 1) // page_size + 1)
        page_num = st.number_input("Page", min_value=1, max_value=total_pages,
                                    value=1, step=1) - 1
        page_df = df_sorted.iloc[page_num * page_size:(page_num + 1) * page_size]

        st.caption(f"Showing {page_num*page_size+1}–{min((page_num+1)*page_size, len(df_sorted))} "
                   f"of {len(df_sorted):,} cases")

        for _, row in page_df.iterrows():
            token  = row.get("survivor_token", anon(row.get("client_id", "?")))
            vtype  = str(row.get("assault_label", "Unknown"))
            date_e = str(row.get("date", ""))[:10]
            district = str(row.get("district", ""))
            subcounty = str(row.get("subcounty_label", ""))
            loc_lbl = LOC_LABELS.get(str(row.get("incident_location_type", "")), "Unknown")
            time_lbl = TIME_LABELS.get(str(row.get("incident_time_of_day", "")), "Not recorded")
            narr = str(row.get("assault_narration", ""))[:220]
            alone = "Yes" if str(row.get("incident_survivor_alone","")).lower()=="yes" else "No"
            perp_loc = str(row.get("perpetrator_location_label", ""))

            # Colour for violence type
            vt_bg = {"Defilement": "#F7C1C1", "Rape": "#FCEBEB",
                     "Physical assault": "#FAEEDA"}.get(vtype, "#EDE7F6")
            vt_fg = {"Defilement": "#501313", "Rape": "#791F1F",
                     "Physical assault": "#412402"}.get(vtype, "#3C3489")

            legal_color = C["green"] if "Arrested" in perp_loc or "Convicted" in perp_loc \
                else C["red"] if "run" in perp_loc.lower() \
                else C["grey"]

            # Ageing indicator for the expander title
            age_band = str(row.get("ageing_band", ""))
            days_q   = row.get("days_since_update")
            if age_band == "Closed":
                age_tag = "✅ closed"
            elif age_band == "180+ days (stale)":
                age_tag = f"🔴 {int(days_q)}d quiet" if pd.notna(days_q) else "🔴 stale"
            elif age_band in ("91-180 days",):
                age_tag = f"🟠 {int(days_q)}d quiet" if pd.notna(days_q) else "🟠 ageing"
            elif age_band in ("61-90 days", "31-60 days"):
                age_tag = f"🟡 {int(days_q)}d" if pd.notna(days_q) else "🟡"
            elif age_band == "0-30 days (current)":
                age_tag = "🟢 current"
            else:
                age_tag = ""

            with st.expander(f"🔒 {token}  ·  {vtype}  ·  {district} {subcounty}  ·  {date_e}  ·  {age_tag}"):
                c_meta, c_narr = st.columns([1, 2])
                with c_meta:
                    last_act = row.get("last_activity_date")
                    last_act_str = pd.to_datetime(last_act).strftime("%d %b %Y") if pd.notna(last_act) else "—"
                    n_fu = int(row.get("n_followups", 0)) if pd.notna(row.get("n_followups")) else 0
                    days_q_str = f"{int(days_q)} days ago" if pd.notna(days_q) else "—"
                    age_color = (C["red"] if age_band == "180+ days (stale)"
                                 else C["amber"] if age_band == "91-180 days"
                                 else C["green"] if age_band in ("0-30 days (current)","Closed")
                                 else C["gold"])
                    st.markdown(f"""
                    <div style='font-size:11px;line-height:2;'>
                      <strong>Token:</strong>
                      <code style='font-size:10px;'>{token}</code><br>
                      <strong>Survivor ID (for follow-up):</strong>
                      <code style='font-size:10px;color:{C["orange"]};font-weight:600;'>{row.get("client_id","—") or "—"}</code><br>
                      <strong>Violence:</strong> {vtype}<br>
                      <strong>District:</strong> {district}<br>
                      <strong>Subcounty:</strong> {subcounty}<br>
                      <strong>Enrolled:</strong> {date_e}<br>
                      <strong>Last update:</strong>
                      <span style='color:{age_color};font-weight:600;'>{last_act_str}</span>
                      ({days_q_str})<br>
                      <strong>Follow-ups recorded:</strong> {n_fu}<br>
                      <strong>Location:</strong> {loc_lbl}<br>
                      <strong>Time of day:</strong> {time_lbl}<br>
                      <strong>Survivor alone:</strong> {alone}<br>
                      <strong>Perpetrator status:</strong>
                      <span style='color:{legal_color};font-weight:500;'>
                        {perp_loc}
                      </span>
                    </div>""", unsafe_allow_html=True)

                    factors_raw = str(row.get("contributing_factors", ""))
                    factor_labels = [FACTOR_LABELS.get(f.strip(), f.strip())
                                     for f in factors_raw.split() if f.strip()]
                    if factor_labels:
                        st.markdown("**Contributing factors:**")
                        for fl in factor_labels:
                            st.markdown(
                                f"<span style='background:{C['red_lt']};color:{C['red']};"
                                f"font-size:9px;padding:1px 7px;border-radius:8px;"
                                f"margin-right:3px;display:inline-block;margin-bottom:3px;'>"
                                f"{fl}</span>", unsafe_allow_html=True)

                with c_narr:
                    # Incident narration
                    st.markdown(f"""
                    <div style='font-size:10px;font-weight:500;color:{C['purple']};
                                text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;'>
                      Incident narration (from intake)
                    </div>
                    <div style='font-size:11px;color:{C['dark']};line-height:1.8;
                                background:{C['purple_xlt']};padding:9px 12px;
                                border-left:3px solid {C['purple']};border-radius:4px;'>
                      {narr}{"…" if len(str(row.get("assault_narration","")))<220 else ""}
                    </div>""", unsafe_allow_html=True)

                    # Crime scene
                    scene = str(row.get("crime_scene_description", ""))
                    if scene and scene not in ("", "nan"):
                        st.markdown(f"""
                        <div style='font-size:10px;font-weight:500;color:{C['gold']};
                                    text-transform:uppercase;letter-spacing:.05em;
                                    margin:8px 0 5px;'>
                          Crime scene description (V3)
                        </div>
                        <div style='font-size:11px;color:{C['dark']};line-height:1.8;
                                    background:{C['gold_lt']};padding:9px 12px;
                                    border-left:3px solid {C['gold']};border-radius:4px;'>
                          {scene}
                        </div>""", unsafe_allow_html=True)

                    # Context
                    ctx = str(row.get("incident_context", ""))
                    if ctx and ctx not in ("", "nan"):
                        st.caption(f"📌 Context: {ctx}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — CASE DETAIL VIEWER
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    section("Case detail viewer", "purple")
    st.caption("Select a case to view all narrative layers: "
               "incident account · crime scene · context · legal timeline · HIV status.")

    if df.empty:
        st.info("No cases match the current filter.")
    else:
        # Build display labels for the selector
        df_labeled = df.copy()
        df_labeled["_label"] = (
            df_labeled.get("survivor_token", pd.Series(dtype=str)).fillna("?")
            + " · " +
            df_labeled.get("assault_label", pd.Series(dtype=str)).fillna("")
            + " · " +
            df_labeled.get("district", pd.Series(dtype=str)).fillna("")
            + " · " +
            df_labeled["date"].dt.strftime("%d %b %Y").fillna("?")
        )
        labels = df_labeled["_label"].tolist()
        selected_label = st.selectbox("Select case", labels, key="detail_select")
        row = df_labeled[df_labeled["_label"] == selected_label].iloc[0]

        token    = row.get("survivor_token", anon(row.get("client_id", "?")))
        vtype    = str(row.get("assault_label", ""))
        district = str(row.get("district", ""))
        sub      = str(row.get("subcounty_label", ""))
        parish   = str(row.get("parish", ""))
        village  = str(row.get("village", ""))
        date_str = str(row.get("date", ""))[:10]
        loc_lbl  = LOC_LABELS.get(str(row.get("incident_location_type", "")), "Not recorded")
        time_lbl = TIME_LABELS.get(str(row.get("incident_time_of_day", "")), "Not recorded")
        alone    = "Yes" if str(row.get("incident_survivor_alone","")).lower()=="yes" else "No"
        context  = str(row.get("incident_context", ""))
        narr     = str(row.get("assault_narration", "No narration recorded."))
        scene    = str(row.get("crime_scene_description", ""))
        perp_loc = str(row.get("perpetrator_location_label", ""))
        relation = str(row.get("perpetrator_relation_label", ""))
        hiv_res  = str(row.get("perp_hiv_result", ""))
        days_arr = row.get("days_to_apprehension", "")
        challenges = str(row.get("apprehension_challenges", ""))
        client_id  = str(row.get("client_id", ""))

        st.markdown("---")

        # Case header bar
        st.markdown(f"""
        <div style='background:{C["purple_lt"]};border-radius:8px;padding:12px 16px;
                    display:flex;gap:16px;flex-wrap:wrap;align-items:center;'>
          <div>
            <div style='font-size:9px;color:{C["grey"]};text-transform:uppercase;'>Survivor token</div>
            <div style='font-family:monospace;font-size:13px;font-weight:500;color:{C["purple"]};'>{token}</div>
          </div>
          <div>
            <div style='font-size:9px;color:{C["grey"]};text-transform:uppercase;'>Survivor ID · for follow-up</div>
            <div style='font-family:monospace;font-size:13px;font-weight:600;color:{C["orange"]};'>{client_id or "—"}</div>
          </div>
          <div>
            <div style='font-size:9px;color:{C["grey"]};text-transform:uppercase;'>Violence type</div>
            <div style='font-size:12px;font-weight:500;color:{C["dark"]};'>{vtype}</div>
          </div>
          <div>
            <div style='font-size:9px;color:{C["grey"]};text-transform:uppercase;'>Location</div>
            <div style='font-size:12px;color:{C["dark"]};'>{village} · {parish} · {sub} · {district}</div>
          </div>
          <div>
            <div style='font-size:9px;color:{C["grey"]};text-transform:uppercase;'>Enrolled</div>
            <div style='font-size:12px;color:{C["dark"]};'>{date_str}</div>
          </div>
          <div style='margin-left:auto;'>
            <div style='background:{C["purple"]};color:white;font-size:10px;
                        padding:4px 12px;border-radius:6px;cursor:pointer;'>
              🔒 Role-restricted view
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ---- Wellbeing & recovery: depression + PTSD, enrollment vs latest ----
        def _pct(v):
            try:
                return float(str(v).strip())
            except Exception:
                return None
        enr_dep  = _pct(row.get("depression_percent"))
        enr_ptsd = _pct(row.get("pre_ptsd_percent"))
        enr_dep_band = next((str(row.get(b)) for b in
            ["depression_severe_label", "depression_moderate_label",
             "depression_mild_label", "normal_depression_label"]
            if str(row.get(b, "")).strip() not in ("", "nan", "None")), "")
        if len(sv_fu) and "client_id" in sv_fu.columns:
            case_sv = sv_fu[sv_fu["client_id"].astype(str) == str(client_id)].copy().sort_values("date")
        else:
            case_sv = sv_fu.iloc[0:0]
        def _latest(col):
            if not len(case_sv) or col not in case_sv.columns:
                return None
            s = case_sv[col].apply(_pct).dropna()
            return float(s.iloc[-1]) if len(s) else None
        lat_dep  = _latest("post_mental_percent")
        lat_ptsd = _latest("fup_ptsd_percent")

        st.markdown(f"<div style='font-size:11px;font-weight:600;color:{C['purple']};"
                    f"text-transform:uppercase;letter-spacing:.05em;margin:10px 0 2px;'>"
                    f"📈 Wellbeing &amp; recovery (recorded)</div>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        def _render_metric(col, title, enr, lat):
            with col:
                if enr is None and lat is None:
                    st.metric(title, "Not yet measured")
                    st.caption("No score recorded for this case.")
                elif lat is None:
                    st.metric(title, f"{enr:.0f}%")
                    st.caption("Enrollment baseline · no follow-up score yet.")
                elif enr is None:
                    st.metric(title, f"{lat:.0f}%")
                    st.caption("Latest follow-up · enrollment score not recorded.")
                else:
                    st.metric(title, f"{lat:.0f}%", delta=round(lat - enr), delta_color="inverse")
                    st.caption(f"Enrollment {enr:.0f}% → latest {lat:.0f}% · lower is better "
                               f"({len(case_sv)} follow-up(s) recorded).")
        _render_metric(m1, "Depression level", enr_dep, lat_dep)
        _render_metric(m2, "PTSD level", enr_ptsd, lat_ptsd)
        if enr_dep_band:
            st.caption(f"Depression band at enrollment: {enr_dep_band}.")

        with st.expander(f"🤝 Follow-up actions & services recorded ({len(case_sv)})"):
            if not len(case_sv):
                st.caption("No follow-up visits recorded for this case yet.")
            else:
                def _val(fr, c):
                    v = str(fr.get(c, "")).strip()
                    return "" if v.lower() in ("", "nan", "none", "<na>") else v
                for _, fr in case_sv.iterrows():
                    dt = str(fr.get("date", ""))[:10]
                    bits = []
                    for c, lbl in [("case_management_support", "Case mgmt"),
                                   ("post_social_support_label", "Social support"),
                                   ("post_mental_percent", "Depression %"),
                                   ("fup_ptsd_percent", "PTSD %"),
                                   ("relief_items_label", "Relief items")]:
                        v = _val(fr, c)
                        if v:
                            bits.append(f"**{lbl}:** {v}")
                    note = _val(fr, "post_mental_comments")
                    line = f"**{dt}** — " + (" · ".join(bits) if bits else "visit recorded")
                    if note:
                        line += f"  \n  _{note[:200]}_"
                    st.markdown(line)
            st.caption("Services shown are those recorded between assessments. This indicates "
                       "association with any score change, not proven causation.")

        st.markdown("<br/>", unsafe_allow_html=True)
        c_left, c_right = st.columns(2)

        with c_left:
            # Incident narration
            st.markdown(f"""
            <div style='font-size:10px;font-weight:500;color:{C['purple']};
                        text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>
              📓 Incident narration — from intake form
            </div>
            <div style='font-size:12px;color:{C['dark']};line-height:1.8;
                        background:{C['purple_xlt']};padding:12px 14px;
                        border-left:3px solid {C['purple']};border-radius:4px;
                        min-height:80px;'>
              {narr}
            </div>""", unsafe_allow_html=True)
            st.markdown("<br/>", unsafe_allow_html=True)

            if scene and scene not in ("", "nan"):
                st.markdown(f"""
                <div style='font-size:10px;font-weight:500;color:{C['gold']};
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>
                  📍 Crime scene description — V3 new field
                </div>
                <div style='font-size:12px;color:{C['dark']};line-height:1.8;
                            background:{C['gold_lt']};padding:12px 14px;
                            border-left:3px solid {C['gold']};border-radius:4px;'>
                  {scene}
                </div>""", unsafe_allow_html=True)
                st.markdown("<br/>", unsafe_allow_html=True)

            if context and context not in ("", "nan"):
                st.markdown(f"""
                <div style='font-size:11px;color:{C['teal']};
                            background:{C['teal_lt']};padding:9px 12px;
                            border-left:3px solid {C['teal']};border-radius:4px;'>
                  <strong>What survivor was doing before incident:</strong><br>{context}
                </div>""", unsafe_allow_html=True)

        with c_right:
            # Incident metadata
            st.markdown(f"""
            <div style='font-size:10px;font-weight:500;color:{C['orange']};
                        text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>
              ⚡ Incident details
            </div>
            <div style='background:{C['orange_lt']};border-radius:6px;padding:10px 14px;
                        font-size:11px;line-height:2;'>
              <strong>Crime scene type:</strong> {loc_lbl}<br>
              <strong>Time of day:</strong> {time_lbl}<br>
              <strong>Survivor alone:</strong> {alone}<br>
              <strong>Perpetrator relation:</strong> {relation}<br>
              <strong>Perpetrator status:</strong> {perp_loc}
            </div>""", unsafe_allow_html=True)
            st.markdown("<br/>", unsafe_allow_html=True)

            # Factors
            factors_raw = str(row.get("contributing_factors", ""))
            factor_labels = [FACTOR_LABELS.get(f.strip(), f.strip())
                             for f in factors_raw.split() if f.strip()]
            if factor_labels:
                st.markdown(f"""
                <div style='font-size:10px;font-weight:500;color:{C['red']};
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>
                  ⚠ Contributing factors (V3)
                </div>""", unsafe_allow_html=True)
                tags_html = "".join(
                    f"<span style='background:{C['red_lt']};color:{C['red']};"
                    f"font-size:10px;padding:2px 9px;border-radius:8px;"
                    f"margin-right:5px;margin-bottom:5px;display:inline-block;'>"
                    f"{fl}</span>" for fl in factor_labels)
                st.markdown(tags_html, unsafe_allow_html=True)
                st.markdown("<br/>", unsafe_allow_html=True)

            # HIV + apprehension
            hiv_color = {"positive": C["red"], "negative": C["green"],
                         "inconclusive": C["amber"]}.get(hiv_res.lower(), C["grey"])
            hiv_bg    = {"positive": C["red_lt"], "negative": C["green_lt"],
                         "inconclusive": C["amber_lt"]}.get(hiv_res.lower(), "#F5F5F5")

            st.markdown(f"""
            <div style='font-size:10px;font-weight:500;color:{C['blue']};
                        text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>
              🧬 HIV & apprehension (V3 fields)
            </div>
            <div style='background:{hiv_bg};border-left:3px solid {hiv_color};
                        border-radius:4px;padding:9px 12px;font-size:11px;line-height:1.9;'>
              <strong>HIV test result:</strong>
              <span style='font-weight:500;color:{hiv_color};'>
                {hiv_res.upper() if hiv_res else "Not yet tested"}
              </span><br>
              <strong>Days to arrest:</strong>
              {int(float(days_arr)) if str(days_arr) not in ("","nan") else "Not arrested yet"}<br>
              {f"<strong>Arrest challenges:</strong> {challenges}<br>" if challenges and challenges not in ("","nan") else ""}
            </div>""", unsafe_allow_html=True)

        # Follow-up legal notes for this case
        st.markdown("<br/>", unsafe_allow_html=True)
        section("Legal follow-up timeline", "teal")

        if len(pp_fu) and "client_id" in pp_fu.columns:
            case_fu = pp_fu[pp_fu["client_id"].astype(str) == str(client_id)].copy()
            case_fu = case_fu.sort_values("date", ascending=False, na_position="last")
        else:
            case_fu = pd.DataFrame()

        if case_fu.empty:
            st.info("No follow-up records linked to this case in the current data. "
                    "Follow-up notes appear here as legal advocates enter updates "
                    "in SurveyCTO.")
        else:
            for i, (_, fu_row) in enumerate(case_fu.iterrows()):
                fu_date   = str(fu_row.get("date", ""))[:10]
                fu_status = str(fu_row.get("case_status_label", ""))
                fu_comment= str(fu_row.get("comments_case_status", ""))
                fu_by     = str(fu_row.get("SGBV_staff_label", "Legal Advocate"))
                fu_days   = fu_row.get("days_to_apprehension", "")
                fu_perp_id = str(fu_row.get("perpetrator_tracking_id", "")).strip()
                if fu_perp_id in ("", "nan", "None", "<NA>"): fu_perp_id = "—"
                dot_color = [C["purple"], C["blue"], C["teal"], C["orange"],
                             C["green"]][i % 5]

                st.markdown(f"""
                <div style='display:flex;gap:12px;padding:8px 0;
                            border-bottom:0.5px dashed {C["border"] if hasattr(C,"border") else "#EEE"};'>
                  <div style='display:flex;flex-direction:column;align-items:center;'>
                    <div style='width:10px;height:10px;border-radius:50%;
                                background:{dot_color};flex-shrink:0;margin-top:3px;'></div>
                  </div>
                  <div style='flex:1;'>
                    <div style='font-size:10px;color:{C["grey"]};margin-bottom:2px;'>
                      {fu_date}
                    </div>
                    <div style='font-size:11px;font-weight:500;color:{C["dark"]};
                                margin-bottom:3px;'>{fu_status}</div>
                    <div style='font-size:11px;color:{C["grey"]};line-height:1.6;
                                background:{C["purple_xlt"]};padding:6px 10px;
                                border-radius:4px;'>
                      {fu_comment if fu_comment not in ("","nan") else "No comment recorded."}
                    </div>
                    <div style='font-size:10px;color:{C["dark"]};margin-top:3px;'>
                      Perpetrator ID (for follow-up):
                      <code style='color:{C["orange"]};font-weight:600;'>{fu_perp_id}</code>
                    </div>
                    <div style='font-size:10px;color:{C["grey"]};margin-top:3px;'>
                      Entered by: {fu_by}
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — LEGAL FOLLOW-UP TIMELINE (ALL CASES)
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    section("Legal follow-up notes — all cases", "teal")
    st.caption("Showing actual field notes entered by legal advocates during follow-up visits.")

    if pp_fu.empty:
        st.info("No follow-up data available.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            fu_status_opts = ["All"] + sorted(
                pp_fu["case_status_overview"].dropna().unique().tolist())
            sel_fu_status = st.selectbox("Case status", fu_status_opts, key="fu_stat")
        with col_f2:
            fu_dist_opts = ["All"] + sorted(
                pp_fu.get("district", pd.Series(dtype=str)).dropna().unique().tolist())
            sel_fu_dist = st.selectbox("District", fu_dist_opts, key="fu_dist")
        with col_f3:
            fu_search = st.text_input("Search in notes", "", placeholder="arrested, court, remanded…",
                                       key="fu_search")

        fu_df = pp_fu.copy()
        if sel_fu_status != "All":
            fu_df = fu_df[fu_df["case_status_overview"] == sel_fu_status]
        if sel_fu_dist != "All" and "district" in fu_df.columns:
            fu_df = fu_df[fu_df["district"].astype(str).str.contains(sel_fu_dist, na=False, regex=False)]
        if fu_search.strip():
            fu_df = fu_df[fu_df["comments_case_status"].astype(str).str.contains(
                fu_search.strip(), case=False, na=False, regex=False)]
        fu_df = fu_df.sort_values("date", ascending=False, na_position="last")

        st.markdown(f"**{len(fu_df):,} follow-up notes** match current filters")
        st.markdown("---")

        # Status summary
        status_cnt = pp_fu["case_status_overview"].value_counts().head(8)
        fig_status = px.bar(status_cnt.reset_index(), x="case_status_overview", y="count",
                            title="Case status distribution across all follow-up records",
                            color_discrete_sequence=[C["teal"]], height=240,
                            template="plotly_white")
        fig_status.update_layout(margin=dict(l=36, r=16, t=48, b=36),
                                  xaxis_title="", yaxis_title="Follow-up records")
        st.plotly_chart(fig_status, use_container_width=True)

        # Notes table (paginated)
        display_cols = [c for c in ["date", "case_status_label", "comments_case_status",
                                     "perpetrator_tracking_id", "linked_survivor_id",
                                     "district", "case_status_overview"] if c in fu_df.columns]
        st.dataframe(
            fu_df[display_cols].head(50).rename(columns={
                "date": "Follow-up Date",
                "case_status_label": "Status Detail",
                "comments_case_status": "Field Note",
                "perpetrator_tracking_id": "Perpetrator ID",
                "linked_survivor_id": "Survivor ID",
                "district": "District",
                "case_status_overview": "Status",
            }),
            use_container_width=True,
            hide_index=True,
        )
        if len(fu_df) > 50:
            st.caption(f"Showing first 50 of {len(fu_df):,} matching records. Use filters to narrow.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — SURVIVOR FOLLOW-UP NOTES
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    section("Survivor follow-up notes — case manager records", "orange")
    st.caption("Mental health, physical status, and case progress notes entered "
               "by case managers at each follow-up visit.")

    if sv_fu.empty:
        st.info("No survivor follow-up data available.")
    else:
        # Overview metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Follow-up records", f"{len(sv_fu):,}")
        m2.metric("With mental health notes",
                  f"{sv_fu['post_mental_comments'].notna().sum():,}")
        m3.metric("With physical notes",
                  f"{sv_fu.get('post_physical_comments', pd.Series()).notna().sum():,}")
        m4.metric("With case status notes",
                  f"{sv_fu.get('comments_case_status', pd.Series()).notna().sum():,}")

        st.markdown("---")

        # Search
        sv_search = st.text_input("Search in survivor notes",
                                    placeholder="improving, hospital, trauma, school…",
                                    key="sv_narr_search")

        sv_df = sv_fu.sort_values("date", ascending=False, na_position="last")
        if sv_search.strip():
            def _sv_mask(col):
                if col in sv_df.columns:
                    return sv_df[col].astype(str).str.contains(sv_search, case=False, na=False, regex=False)
                return pd.Series(False, index=sv_df.index)
            mask = (_sv_mask("post_mental_comments") | _sv_mask("post_physical_comments")
                    | _sv_mask("comments_case_status"))
            sv_df = sv_df[mask]

        st.markdown(f"**{len(sv_df):,} survivor follow-up records**")

        for _, row in sv_df.head(30).iterrows():
            sv_tok  = str(row.get("survivor_token", anon(row.get("client_id","?"))))
            sv_date = str(row.get("date",""))[:10]
            mh_note = str(row.get("post_mental_comments",""))
            ph_note = str(row.get("post_physical_comments",""))
            cs_note = str(row.get("comments_case_status",""))
            try: _dpf=float(str(row.get("depression_percent","")).strip())
            except Exception: _dpf=None
            mh_cat  = ("" if _dpf is None else ("Normal" if _dpf<25 else "Mild" if _dpf<50
                       else "Moderate" if _dpf<75 else "Severe"))
            district= str(row.get("district",""))

            if all(n in ("","nan") for n in [mh_note, ph_note, cs_note]):
                continue

            with st.expander(f"🔒 {sv_tok}  ·  {mh_cat}  ·  {district}  ·  {sv_date}"):
                n1, n2, n3 = st.columns(3)
                with n1:
                    if mh_note and mh_note not in ("","nan"):
                        st.markdown(f"""
                        <div style='font-size:10px;font-weight:500;color:{C['purple']};
                                    margin-bottom:4px;'>MENTAL HEALTH NOTE</div>
                        <div style='font-size:11px;background:{C['purple_xlt']};
                                    padding:8px;border-left:3px solid {C['purple']};
                                    border-radius:4px;line-height:1.6;'>{mh_note}</div>
                        """, unsafe_allow_html=True)
                with n2:
                    if ph_note and ph_note not in ("","nan"):
                        st.markdown(f"""
                        <div style='font-size:10px;font-weight:500;color:{C['teal']};
                                    margin-bottom:4px;'>PHYSICAL STATUS NOTE</div>
                        <div style='font-size:11px;background:{C['teal_lt']};
                                    padding:8px;border-left:3px solid {C['teal']};
                                    border-radius:4px;line-height:1.6;'>{ph_note}</div>
                        """, unsafe_allow_html=True)
                with n3:
                    if cs_note and cs_note not in ("","nan"):
                        st.markdown(f"""
                        <div style='font-size:10px;font-weight:500;color:{C['orange']};
                                    margin-bottom:4px;'>CASE STATUS NOTE</div>
                        <div style='font-size:11px;background:{C['orange_lt']};
                                    padding:8px;border-left:3px solid {C['orange']};
                                    border-radius:4px;line-height:1.6;'>{cs_note}</div>
                        """, unsafe_allow_html=True)

        if len(sv_df) > 30:
            st.caption(f"Showing first 30 of {len(sv_df):,} matching records.")