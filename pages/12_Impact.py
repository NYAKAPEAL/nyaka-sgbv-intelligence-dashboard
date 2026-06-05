"""
pages/12_Impact.py
Programme Impact: survivor wellbeing outcomes (depression, PTSD) at enrollment vs
latest follow-up, recovery rates, trends over time, and justice outcomes.

All outcome figures are descriptive and show ASSOCIATION, not proven causation.
PTSD scores exist only from the new tool's deployment forward, so PTSD panels are
sparse until follow-up data accumulates; they degrade gracefully until then.
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import C
from utils.auth import check, sidebar_panel, can_access
from utils.viz import section, page_header, safe_notice, kpi, grouped_bar, bar_v, donut

if not check():
    st.warning("Please log in.")
    st.stop()
if not can_access("mel"):
    st.error("🔒 Access denied.")
    st.stop()

from utils.data_loader import load_perp_narrative, load_survivor_followups, load_perpetrators

sidebar_panel()
page_header("Programme Impact",
            "Survivor wellbeing outcomes over time · depression & PTSD recovery · justice outcomes",
            "📈")

st.markdown(f"""
<div style='background:{C["amber_lt"]};border-left:4px solid {C["amber"]};
            padding:9px 14px;border-radius:6px;font-size:11px;color:{C["dark"]};
            margin-bottom:14px;'>
  <strong>How to read this page.</strong> Figures describe change recorded between
  enrollment and the latest follow-up. They show association between participation
  and outcomes, not proven causation. PTSD scores begin from the new tool's launch,
  so those panels fill in as follow-up data accumulates. Lower scores are better.
</div>""", unsafe_allow_html=True)

# ── helpers ───────────────────────────────────────────────────────────────────
def _pct(v):
    try:
        return float(str(v).strip())
    except Exception:
        return None

def _last_valid(series):
    s = series.apply(_pct).dropna()
    return float(s.iloc[-1]) if len(s) else np.nan

def interpret(meaning, why, sw_uganda, uganda, global_):
    st.markdown(f"""
    <div style='background:{C["purple_xlt"]};border-radius:8px;padding:12px 16px;
                font-size:12px;color:{C["dark"]};line-height:1.7;margin:4px 0 18px;'>
      <div style='font-size:10px;font-weight:600;color:{C["purple"]};
                  text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;'>
        Interpretation</div>
      <p style='margin:2px 0;'><strong>What it means.</strong> {meaning}</p>
      <p style='margin:2px 0;'><strong>Why it matters.</strong> {why}</p>
      <p style='margin:2px 0;'><strong>Southwestern Uganda.</strong> {sw_uganda}</p>
      <p style='margin:2px 0;'><strong>Uganda.</strong> {uganda}</p>
      <p style='margin:2px 0;'><strong>Global relevance.</strong> {global_}</p>
    </div>""", unsafe_allow_html=True)

# ── data ──────────────────────────────────────────────────────────────────────
try:
    narr = load_perp_narrative()
    svfu = load_survivor_followups()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

if not len(narr):
    safe_notice()
    st.info("No case data available yet.")
    st.stop()

narr = narr.copy()
narr["client_id"] = narr["client_id"].astype(str)
narr["enr_dep"]  = narr["depression_percent"].apply(_pct) if "depression_percent" in narr.columns else np.nan
narr["enr_ptsd"] = narr["pre_ptsd_percent"].apply(_pct) if "pre_ptsd_percent" in narr.columns else np.nan

# latest follow-up score per case
lat_dep_map, lat_ptsd_map = {}, {}
if len(svfu) and "client_id" in svfu.columns:
    svfu = svfu.copy()
    svfu["client_id"] = svfu["client_id"].astype(str)
    svfu = svfu.sort_values("date")
    if "post_mental_percent" in svfu.columns:
        lat_dep_map = svfu.groupby("client_id")["post_mental_percent"].apply(_last_valid).to_dict()
    if "fup_ptsd_percent" in svfu.columns:
        lat_ptsd_map = svfu.groupby("client_id")["fup_ptsd_percent"].apply(_last_valid).to_dict()
narr["lat_dep"]  = narr["client_id"].map(lat_dep_map)
narr["lat_ptsd"] = narr["client_id"].map(lat_ptsd_map)

n_cases   = len(narr)
n_with_fu = int((narr["n_followups"] > 0).sum()) if "n_followups" in narr.columns else 0

# matched cohorts (have both enrollment and latest score)
dep_m  = narr[narr["enr_dep"].notna()  & narr["lat_dep"].notna()].copy()
ptsd_m = narr[narr["enr_ptsd"].notna() & narr["lat_ptsd"].notna()].copy()

# ── KPI row ───────────────────────────────────────────────────────────────────
section("Outcome summary", "purple")
k = st.columns(4)
with k[0]:
    st.markdown(kpi("Cases enrolled", f"{n_cases:,}", icon="📋"), unsafe_allow_html=True)
with k[1]:
    pct_fu = (100 * n_with_fu / n_cases) if n_cases else 0
    st.markdown(kpi("Cases with follow-up", f"{n_with_fu:,}", note=f"{pct_fu:.0f}% of enrolled",
                    color="teal", icon="🔁"), unsafe_allow_html=True)
with k[2]:
    if len(dep_m):
        avg_e, avg_l = dep_m["enr_dep"].mean(), dep_m["lat_dep"].mean()
        st.markdown(kpi("Avg depression", f"{avg_l:.0f}%",
                        note=f"enrollment {avg_e:.0f}% → latest {avg_l:.0f}% (n={len(dep_m)})",
                        color="orange", icon="🧠"), unsafe_allow_html=True)
    else:
        st.markdown(kpi("Avg depression", "—", note="awaiting matched follow-ups",
                        color="orange", icon="🧠"), unsafe_allow_html=True)
with k[3]:
    if len(ptsd_m):
        pe, pl = ptsd_m["enr_ptsd"].mean(), ptsd_m["lat_ptsd"].mean()
        st.markdown(kpi("Avg PTSD", f"{pl:.0f}%",
                        note=f"enrollment {pe:.0f}% → latest {pl:.0f}% (n={len(ptsd_m)})",
                        color="purple", icon="💜"), unsafe_allow_html=True)
    else:
        st.markdown(kpi("Avg PTSD", "Collecting", note="PTSD data accrues from new tool",
                        color="purple", icon="💜"), unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ── Depression: enrollment vs latest ──────────────────────────────────────────
section("Depression: enrollment vs latest follow-up", "orange")
if len(dep_m):
    avg_e, avg_l = dep_m["enr_dep"].mean(), dep_m["lat_dep"].mean()
    improved = int((dep_m["lat_dep"] < dep_m["enr_dep"]).sum())
    pct_improved = 100 * improved / len(dep_m)
    # "moved below moderate (50%)" among those who started at/above moderate
    started_high = dep_m[dep_m["enr_dep"] >= 50]
    crossed = int((started_high["lat_dep"] < 50).sum())
    pct_crossed = (100 * crossed / len(started_high)) if len(started_high) else 0

    cc = st.columns([1.1, 1])
    with cc[0]:
        d = pd.DataFrame({"stage": ["Enrollment", "Latest follow-up"], "score": [avg_e, avg_l]})
        st.plotly_chart(bar_v(d, "stage", "score", title="Average depression score (%)",
                              color=C["orange"], text="score"), use_container_width=True)
    with cc[1]:
        st.markdown(kpi("Improved", f"{pct_improved:.0f}%",
                        note=f"{improved} of {len(dep_m)} matched cases scored lower",
                        color="green", icon="✅"), unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(kpi("Moved below moderate", f"{pct_crossed:.0f}%",
                        note=f"of {len(started_high)} who began at moderate+ (≥50%)",
                        color="teal", icon="📉"), unsafe_allow_html=True)
    interpret(
        meaning=(f"Among {len(dep_m)} survivors with both an enrollment and a later score, "
                 f"average recorded depression moved from {avg_e:.0f}% to {avg_l:.0f}%, and "
                 f"{pct_improved:.0f}% scored lower at their latest visit."),
        why=("Depression is a core marker of SGBV harm and of recovery. A downward shift "
             "alongside case-management and psychosocial support is the kind of survivor-level "
             "change donors and evaluators look for, provided it is read as association."),
        sw_uganda=("In Kanungu, Rukungiri and Rubanda, where specialist mental-health services "
                   "are scarce, community-based follow-up appears compatible with improving mood "
                   "symptoms for many survivors."),
        uganda=("It is relevant to Uganda's task-shifting approach to mental health, suggesting "
                "trained community teams can track and support recovery where clinicians are few."),
        global_=("It speaks to the global evidence question of whether community-delivered "
                 "survivor support is associated with measurable psychological recovery in "
                 "low-resource settings."))
else:
    st.info("No cases yet have both an enrollment depression score and a follow-up score. "
            "This panel populates as follow-ups are recorded.")

# ── PTSD: enrollment vs latest ────────────────────────────────────────────────
section("PTSD: enrollment vs latest follow-up", "purple")
if len(ptsd_m):
    pe, pl = ptsd_m["enr_ptsd"].mean(), ptsd_m["lat_ptsd"].mean()
    p_improved = 100 * (ptsd_m["lat_ptsd"] < ptsd_m["enr_ptsd"]).mean()
    below20 = 100 * (ptsd_m["lat_ptsd"] < 20).mean()
    cc = st.columns([1.1, 1])
    with cc[0]:
        d = pd.DataFrame({"stage": ["Enrollment", "Latest follow-up"], "score": [pe, pl]})
        st.plotly_chart(bar_v(d, "stage", "score", title="Average PTSD score (%)",
                              color=C["purple"], text="score"), use_container_width=True)
    with cc[1]:
        st.markdown(kpi("Improved", f"{p_improved:.0f}%", note=f"of {len(ptsd_m)} matched cases",
                        color="green", icon="✅"), unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(kpi("Below 20% (target)", f"{below20:.0f}%",
                        note="programme recovery target", color="teal", icon="🎯"),
                    unsafe_allow_html=True)
    interpret(
        meaning=(f"Among {len(ptsd_m)} survivors with paired PTSD scores, average recorded PTSD "
                 f"moved from {pe:.0f}% to {pl:.0f}%."),
        why=("PTSD measured with validated instruments (CRIES-8 for children, HTQ for adults) is "
             "the most evaluation-credible trauma outcome the programme collects."),
        sw_uganda=("It gives Southwestern Uganda a standardised trauma-recovery signal where none "
                   "previously existed in routine programme data."),
        uganda=("Validated PTSD tracking aligns Nyaka's data with instruments recognised by "
                "Ugandan researchers and the Ministry of Health for trauma assessment."),
        global_=("CRIES-8 and HTQ are used worldwide, so these outcomes can be compared with "
                 "international SGBV and post-conflict recovery literature."))
else:
    st.info("PTSD outcome data is still accumulating. Validated PTSD scores (CRIES-8 for "
            "children, HTQ for adults) begin from the new tool's deployment, and this panel "
            "will populate as survivors are re-assessed at follow-up.")

# ── Trend over time (enrollment cohorts) ──────────────────────────────────────
section("Trend over time", "gold")
if "date_enrolled_dt" in narr.columns and len(dep_m):
    dm = dep_m.copy()
    dm["q"] = pd.to_datetime(dm["date_enrolled_dt"], errors="coerce").dt.to_period("Q").astype(str)
    dm = dm[dm["q"] != "NaT"]
    if len(dm):
        agg = dm.groupby("q").agg(Enrollment=("enr_dep", "mean"),
                                   Latest=("lat_dep", "mean")).reset_index()
        agg = agg.sort_values("q")
        st.plotly_chart(
            grouped_bar(agg, "q", ["Enrollment", "Latest"],
                        ["Enrollment", "Latest follow-up"], [C["orange"], C["green"]],
                        title="Average depression by enrollment cohort (%)"),
            use_container_width=True)
        interpret(
            meaning=("Each quarter's cohort shows its average depression at enrollment next to its "
                     "latest recorded average. A widening gap in favour of lower latest scores "
                     "indicates recovery within cohorts over time."),
            why=("Cohort trends separate genuine programme effect from changes in who enrolls, and "
                 "are more robust for donor reporting than a single before/after pair."),
            sw_uganda=("It lets district teams see whether more recent cohorts are recovering as "
                       "well as earlier ones, flagging where support may need strengthening."),
            uganda=("Cohort-based outcome tracking is the standard expected by national MEAL "
                    "frameworks and by Uganda's results-based donor reporting."),
            global_=("Cohort comparison is the backbone of credible impact evaluation worldwide, "
                     "and positions Nyaka's data for external study."))
    else:
        st.info("Not enough dated cohorts yet for a trend.")
else:
    st.info("Trend populates once matched follow-up scores accumulate across enrollment cohorts.")

# ── Justice outcomes ──────────────────────────────────────────────────────────
section("Justice outcomes", "teal")
try:
    pp = load_perpetrators()
except Exception:
    pp = pd.DataFrame()
if len(pp) and "case_status_overview" in pp.columns and "perpetrator_tracking_id" in pp.columns:
    # Count distinct CASES, not follow-up visits (status is logged on each follow-up).
    _tid = pp["perpetrator_tracking_id"].astype(str)
    _ov = pp["case_status_overview"].astype(str).str.strip().str.lower()
    _jr = pd.DataFrame({"_tid": _tid.values, "_stat": _ov.values})
    won = int(_jr.loc[_jr["_stat"] == "won", "_tid"].nunique())
    lost = int(_jr.loc[_jr["_stat"] == "lost", "_tid"].nunique())
    at_court = int(_jr.loc[_jr["_stat"] == "court", "_tid"].nunique())
    decided = won + lost
    conv_rate = (100 * won / decided) if decided else 0
    cc = st.columns([1, 1.1])
    with cc[0]:
        st.markdown(kpi("Conviction rate", f"{conv_rate:.0f}%",
                        note=f"{won} won of {decided} decided cases", color="green", icon="⚖️"),
                    unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(kpi("Ever reached court", f"{at_court:,}", note="distinct cases (not visits)",
                        color="amber", icon="🏛️"), unsafe_allow_html=True)
    with cc[1]:
        if won or lost or at_court:
            st.plotly_chart(donut(["Won", "Lost", "Reached court"], [won, lost, at_court],
                                  title="Legal case outcomes (distinct cases)",
                                  colors=[C["green"], C["red"], C["amber"]]),
                            use_container_width=True)
    interpret(
        meaning=(f"Of cases with a decided outcome, {conv_rate:.0f}% resulted in a conviction "
                 f"({won} of {decided}), with {at_court} still progressing through court."),
        why=("Justice outcomes are a distinct impact dimension from wellbeing: they measure "
             "accountability and deterrence, central to SGBV prevention."),
        sw_uganda=("Conviction tracking shows whether survivors in these districts are reaching "
                   "justice, a known challenge in rural Uganda where cases often stall."),
        uganda=("It contributes evidence to national debates on SGBV case attrition and the "
                "effectiveness of survivor legal support."),
        global_=("Case-to-conviction tracking responds to a global SGBV gap: most programmes "
                 "cannot follow cases through the justice chain, and this data can."))
else:
    st.info("Justice outcome data will display once perpetrator case statuses are available.")

st.caption("All outcome figures are descriptive associations recorded in routine programme data, "
           "not causal estimates. PTSD panels populate as the new tool's follow-up data accrues.")