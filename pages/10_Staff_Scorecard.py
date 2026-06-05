"""
pages/10_Staff_Scorecard.py
Staff caseload, workload balance, and follow-up intelligence (computed LIVE).

A SUPPORT and WORKLOAD-BALANCING tool, not a punitive leaderboard. Counts reflect
logged activity, never the difficulty of the work. Restricted to admin / programme / MEL.

Legal advocates work the perpetrator/legal process, which is linked to the survivor
case by the survivor ID. Cases are attributed to an advocate by their jurisdiction
(duty-station district), because individual case assignment is not recorded in the data.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import C, STAFF_ROSTER, STAFF_NAME_MAP, STAFF_DUTY_STATIONS
from utils.auth import check, sidebar_panel, role
from utils.viz import section, page_header, kpi
from utils.data_loader import load_perp_narrative, load_perpetrators

if not check():
    st.warning("Please log in.")
    st.stop()
if role() not in ("admin", "programme", "mel"):
    st.error("🔒 The staff workload view is restricted to programme management and MEL roles.")
    st.stop()
sidebar_panel()

PHOTO_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "staff_photos")
def staff_photo_path(name):
    for cand in (f"{name}.jpg", f"{name.replace(' ', '_')}.jpg",
                 f"{name}.png", f"{name.replace(' ', '_')}.png"):
        p = os.path.join(PHOTO_DIR, cand)
        if os.path.exists(p):
            return p
    return None

page_header("Staff Caseload & Workload",
            "Live caseloads, follow-up needs, arrest tracking · support and balancing, not ranking",
            "🧑🏽‍⚕️")
st.markdown(f"""
<div style='background:{C["amber_lt"]};border-left:4px solid {C["amber"]};padding:9px 14px;
            border-radius:6px;font-size:11px;color:{C["dark"]};margin-bottom:12px;'>
  <strong>How to read this.</strong> A support and balancing view, not a ranking. Active caseload,
  follow-up needs and ageing are current snapshots. Legal cases are grouped by the advocate's
  jurisdiction, since individual assignment is not recorded.
</div>""", unsafe_allow_html=True)

# ── helpers ───────────────────────────────────────────────────────────────────
def _norm(s):
    return STAFF_NAME_MAP.get(str(s).strip(), str(s).strip())
def _days_since(series):
    return (pd.Timestamp.now().normalize() - pd.to_datetime(series, errors="coerce")).dt.days
TODAY_YEAR = pd.Timestamp.now().year

try:
    narr = load_perp_narrative().copy()
    pp = load_perpetrators().copy()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

narr["staff"]      = narr.get("SGBV_staff_label", "").map(_norm)
narr["enr_dt"]     = pd.to_datetime(narr.get("date_enrolled_dt"), errors="coerce")
narr["days_since"] = _days_since(narr.get("last_activity_date"))
narr["active"]     = ~narr.get("is_closed", False).fillna(False)
narr["sid"]        = narr["client_id"].astype(str)

# ── legal case-state rollup (per survivor case, from linked perpetrator records) ─
link = "linked_survivor_id" if "linked_survivor_id" in pp.columns else "pre_survivor_id"
pp["sid"] = pp[link].astype(str)
pp["arr"] = pp.get("arrested", False).fillna(False).astype(bool)
_dcol = next((c for c in ["follow_up_date", "date_enrolled", "survey_date", "date"] if c in pp.columns), None)
pp["_d"] = pd.to_datetime(pp[_dcol], errors="coerce") if _dcol else pd.NaT
arr_any   = pp.groupby("sid")["arr"].max()
last_legal = pp.sort_values("_d").groupby("sid").tail(1).set_index("sid")
last_state = last_legal.get("perpetrator_location_label", pd.Series(dtype=str))
last_ldate = pp.groupby("sid")["_d"].max()

narr["has_perp"]      = narr["sid"].isin(set(pp["sid"]))
narr["perp_arrested"] = narr["sid"].map(arr_any).fillna(False).astype(bool)
narr["perp_state"]    = narr["sid"].map(last_state)
narr["legal_days"]    = _days_since(narr["sid"].map(last_ldate))

# ── staff selector + PROFILE HEADER (photo, role, station, status) ────────────
section("Individual profile", "purple")
pp["staff"] = pp.get("SGBV_staff_label", "").map(_norm)
active_staff = [n for n, v in STAFF_ROSTER.items() if v.get("status") == "active"]
legal_in_data = [n for n in pp["staff"].dropna().unique()
                 if STAFF_ROSTER.get(n, {}).get("role") == "Legal Advocate" and n not in active_staff]
sel = st.selectbox("Select a staff member", active_staff + legal_in_data)
info  = STAFF_ROSTER.get(sel, {})
srole = info.get("role", "")
sstat = info.get("status", "")
duty  = STAFF_DUTY_STATIONS.get(sel, {})

hc1, hc2 = st.columns([1, 5])
with hc1:
    ph = staff_photo_path(sel)
    if ph:
        st.image(ph, width=96)
    else:
        st.markdown(f"<div style='width:96px;height:96px;border-radius:50%;background:{C['purple_xlt']};"
                    f"display:flex;align-items:center;justify-content:center;font-size:30px;'>👤</div>",
                    unsafe_allow_html=True)
with hc2:
    station = duty.get("base", "Station not recorded")
    juris   = duty.get("jurisdiction", "")
    badge   = ("" if sstat == "active"
               else f"<span style='background:{C['grey']};color:white;border-radius:4px;"
                    f"padding:1px 7px;font-size:10px;margin-left:8px;'>former staff</span>")
    st.markdown(f"""
      <div style='font-size:20px;font-weight:700;color:{C["purple"]};'>{sel}{badge}</div>
      <div style='font-size:13px;color:{C["dark"]};margin-top:2px;'>{srole}</div>
      <div style='font-size:12px;color:{C["grey"]};margin-top:6px;'>
        📍 {station}{(' · jurisdiction: ' + juris) if juris else ''}</div>
    """, unsafe_allow_html=True)
st.markdown("<br/>", unsafe_allow_html=True)

def _contact_table(df, id_col, extra=None):
    spec = [(id_col, "Case ID"), ("district_label", "District"), ("subcounty_label", "Subcounty"),
            ("village", "Village"), ("assault_label", "Case type")]
    if extra:
        spec += extra
    spec += [("client_contact", "Survivor contact"), ("next_kin_name", "Next of kin"),
             ("next_kin_contact", "Next of kin contact")]
    cols = {label: df[src] for src, label in spec if src in df.columns}
    return pd.DataFrame(cols)

# ===== CASE MANAGER PROFILE =====
if srole.startswith("Case Manager"):
    mine = narr[narr["staff"] == sel].copy()
    active = mine[mine["active"]]
    need_fu = active[active["days_since"] > 90]
    urgent = active[(active["days_since"] > 180) & (active["n_followups"].fillna(0) == 0)]
    k = st.columns(4)
    k[0].markdown(kpi("Active cases", f"{len(active):,}", icon="📁"), unsafe_allow_html=True)
    k[1].markdown(kpi("Need follow-up", f"{len(need_fu):,}", note="no activity in 90+ days",
                      color="amber", icon="🔔"), unsafe_allow_html=True)
    k[2].markdown(kpi("Urgent", f"{len(urgent):,}", note="180+ days, no follow-up logged",
                      color="red", icon="⏰"), unsafe_allow_html=True)
    k[3].markdown(kpi("Total ever", f"{len(mine):,}", color="teal", icon="📊"), unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    tabs = st.tabs([f"🔔 Need follow-up ({len(need_fu)})", f"⏰ Urgent ({len(urgent)})",
                    f"📁 All active ({len(active)})"])
    for tab, d, empty in [(tabs[0], need_fu, "None."),
                          (tabs[1], urgent, "None — nothing 180+ days unattended."),
                          (tabs[2], active, "No active cases.")]:
        with tab:
            t = _contact_table(d.sort_values("days_since", ascending=False), "client_id")
            st.dataframe(t, use_container_width=True, hide_index=True) if len(t) else st.caption(empty)
    st.caption("Contacts shown to support follow-up; this view is access-restricted and audited.")

# ===== LEGAL ADVOCATE PROFILE (jurisdiction-based, arrest + perpetrator follow-up) =====
elif srole == "Legal Advocate":
    juris = duty.get("jurisdiction", "")
    if juris and juris.lower() not in ("all districts", ""):
        cases = narr[narr["district"].astype(str).str.contains(juris, case=False, na=False)].copy()
        scope_note = f"survivor cases in {juris} jurisdiction"
    else:
        cases = narr.copy()
        scope_note = "all survivor cases (no single jurisdiction)"
    ongoing = cases[cases["active"]]
    not_started  = ongoing[~ongoing["has_perp"]]
    arrest_pend  = ongoing[ongoing["has_perp"] & ~ongoing["perp_arrested"]]
    arrested_act = ongoing[ongoing["has_perp"] & ongoing["perp_arrested"]]
    no_arrest    = ongoing[~ongoing["perp_arrested"]]            # not started + pending
    at_risk      = ongoing[ongoing["has_perp"] & (ongoing["legal_days"] > 180)]

    st.caption(f"Scope: {scope_note}. Cases link to perpetrators by survivor ID.")
    k = st.columns(4)
    k[0].markdown(kpi("Open cases", f"{len(ongoing):,}", icon="⚖️"), unsafe_allow_html=True)
    k[1].markdown(kpi("Perpetrator NOT arrested", f"{len(no_arrest):,}",
                      note="needs arrest (incl. not yet started)", color="red", icon="🚓"),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Arrested, in process", f"{len(arrested_act):,}", note="arrest done, case ongoing",
                      color="teal", icon="📁"), unsafe_allow_html=True)
    k[3].markdown(kpi("At risk", f"{len(at_risk):,}", note="180+ days, no legal activity",
                      color="amber", icon="⏰"), unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    # perpetrator follow-up state breakdown
    states = cases[cases["has_perp"]]["perp_state"].fillna("State not recorded").astype(str)
    if len(states):
        sc = states.value_counts().reset_index()
        sc.columns = ["Perpetrator status", "Cases"]
        fig = px.bar(sc.sort_values("Cases"), x="Cases", y="Perpetrator status", orientation="h",
                     template="plotly_white", height=300, text="Cases",
                     color_discrete_sequence=[C["purple"]])
        fig.update_layout(margin=dict(l=170, r=16, t=30, b=30),
                          title="Perpetrator follow-up status (linked cases)")
        st.plotly_chart(fig, use_container_width=True)

    tabs = st.tabs([f"🚓 Need arrest ({len(no_arrest)})",
                    f"📁 Arrested, in process ({len(arrested_act)})",
                    f"⏰ At risk ({len(at_risk)})",
                    f"🆕 Not yet started ({len(not_started)})"])
    extra = [("perp_state", "Perpetrator status")]
    for tab, d in [(tabs[0], no_arrest), (tabs[1], arrested_act), (tabs[2], at_risk), (tabs[3], not_started)]:
        with tab:
            t = _contact_table(d.sort_values("legal_days", ascending=False), "client_id", extra)
            st.dataframe(t, use_container_width=True, hide_index=True) if len(t) else st.caption("None.")
    st.caption("Cases grouped by jurisdiction, not individual assignment. 'Not yet started' means no "
               "perpetrator record is linked to the survivor case, so the legal process (arrest) has "
               "not begun. Contacts shown for follow-up only; access is audited.")

else:
    st.info(f"{sel} is a {srole}. Detailed caseload metrics are tracked for case managers and legal advocates.")

# ── WORKLOAD BALANCE (period-filtered) — now AFTER the profile ─────────────────
st.markdown("<hr style='border:none;border-top:1px solid #eee;margin:18px 0;'/>", unsafe_allow_html=True)
section("Workload balance · new cases enrolled", "orange")
years = sorted([int(y) for y in narr["enr_dt"].dt.year.dropna().unique()])
fc = st.columns([1, 1, 3])
with fc[0]:
    yr = st.selectbox("Year", ["All"] + years[::-1],
                      index=(1 + years[::-1].index(TODAY_YEAR)) if TODAY_YEAR in years else 0)
with fc[1]:
    months = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    mo = st.selectbox("Month", months, index=0)
period = narr.copy()
if yr != "All":
    period = period[period["enr_dt"].dt.year == int(yr)]
if mo != "All":
    period = period[period["enr_dt"].dt.month == months.index(mo)]
period_lbl = (f"{mo} {yr}" if mo != "All" and yr != "All" else (str(yr) if yr != "All" else "all time"))

cm_names = [n for n, v in STAFF_ROSTER.items() if v["role"].startswith("Case Manager")]
wl = (period[period["staff"].isin(cm_names)].groupby("staff")["client_id"].count()
      .reindex(cm_names).fillna(0).sort_values(ascending=False).reset_index())
wl.columns = ["Staff", "New cases"]
if wl["New cases"].sum() > 0:
    fig = px.bar(wl, x="New cases", y="Staff", orientation="h", template="plotly_white",
                 height=260, color_discrete_sequence=[C["orange"]], text="New cases")
    fig.update_layout(margin=dict(l=160, r=16, t=20, b=30))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Active case managers, new survivor enrollments in {period_lbl}. A lighter bar is not "
               "'less work' — newer staff and leave periods show here too, which is why the period filter matters.")
else:
    st.info(f"No new case-manager enrollments recorded in {period_lbl}.")