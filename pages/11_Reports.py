"""
pages/11_Reports.py
Reports Centre — generate and download the monthly programmatic report (Word).
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import C
from utils.auth import check, sidebar_panel, can_access, role
from utils.viz import section, page_header, kpi
from utils.report_generator import build_monthly_report

if not check():
    st.warning("Please log in.")
    st.stop()
if not can_access("reports"):
    st.error("🔒 Access denied. The Reports Centre is for programme and MEL roles.")
    st.stop()

sidebar_panel()
page_header(
    "Reports Centre",
    "Generate the monthly programmatic report as an editable Word document",
    "📄"
)


@st.cache_data(ttl=300, show_spinner="Loading data for reporting…")
def load_report_data():
    # Live data via the shared loaders, with a per-stream CSV fallback so the
    # report always builds even if the live source is briefly unavailable.
    from utils.data_loader import (load_survivors, load_perp_narrative,
                                    load_perp_followups, load_outreach, load_school)
    def _csv(p):
        try:
            return pd.read_csv(p, low_memory=False)
        except Exception:
            return pd.DataFrame()
    def _live_or_csv(live_fn, csv_path):
        try:
            df = live_fn()
        except Exception:
            df = pd.DataFrame()
        return df if len(df) else _csv(csv_path)

    sv  = _live_or_csv(load_survivors,      "data/survivors.csv")
    pp  = _live_or_csv(load_perp_narrative, "data/perpetrators_narrative.csv")
    ppf = _live_or_csv(load_perp_followups, "data/perpetrators_followup.csv")
    ot  = _live_or_csv(load_outreach,       "data/outreach.csv")
    sc  = _live_or_csv(load_school,         "data/school_social_work.csv")
    return {"survivors": sv, "perpetrators": pp, "perp_followup": ppf,
            "outreach": ot, "school": sc, "narrative": pp}


data = load_report_data()

# Determine available months from survivor enrollment dates
sv = data["survivors"]
if len(sv) and "date_enrolled" in sv.columns:
    d = pd.to_datetime(sv["date_enrolled"], errors="coerce")
    months = sorted(d.dropna().dt.to_period("M").unique(), reverse=True)
    month_options = [(p.year, p.month, p.strftime("%B %Y")) for p in months]
else:
    now = datetime.now()
    month_options = [(now.year, now.month, now.strftime("%B %Y"))]

section("Generate monthly report", "purple")

st.markdown(f"""
<div style='background:{C["purple_lt"]};border-left:4px solid {C["purple"]};
            border-radius:8px;padding:11px 16px;font-size:11px;
            color:{C["purple_dk"]};margin-bottom:14px;line-height:1.7;'>
  📝 This produces a <strong>~5-page Word document</strong> you can open, edit,
  and add your programme narrative to before sending to funders. It is a working
  draft built from live data, not a final auto-generated document. The Challenges
  and Recommendations sections are left as prompts for you to complete.
</div>""", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    labels = [m[2] for m in month_options]
    sel_idx = st.selectbox("Reporting month", range(len(labels)),
                           format_func=lambda i: labels[i], key="rpt_month")
    sel_year, sel_month, sel_label = month_options[sel_idx]
with col2:
    prepared_by = st.text_input("Prepared by (optional)",
                                 placeholder="e.g. D. Ainamani, MEAL Manager")

# Preview the month's headline numbers before generating
sv_e = sv[sv.get("report_category","").str.contains("enrollment", na=False)] \
       if "report_category" in sv.columns else sv
d_all = pd.to_datetime(sv_e.get("date_enrolled"), errors="coerce") if len(sv_e) else pd.Series(dtype="datetime64[ns]")
sv_month = sv_e[(d_all.dt.year == sel_year) & (d_all.dt.month == sel_month)] if len(sv_e) else pd.DataFrame()

ot = data["outreach"]
d_ot = pd.to_datetime(ot.get("date"), errors="coerce") if len(ot) else pd.Series(dtype="datetime64[ns]")
ot_month = ot[(d_ot.dt.year == sel_year) & (d_ot.dt.month == sel_month)] if len(ot) else pd.DataFrame()

st.markdown(f"#### Preview — {sel_label}")
p1, p2, p3, p4 = st.columns(4)
with p1: st.markdown(kpi("Survivors", f"{len(sv_month)}", color="purple", icon="👤"),
                     unsafe_allow_html=True)
with p2:
    reach = int(ot_month["total"].sum()) if len(ot_month) and "total" in ot_month.columns else 0
    st.markdown(kpi("Outreach reach", f"{reach:,}", color="teal", icon="🌍"),
                unsafe_allow_html=True)
with p3: st.markdown(kpi("Outreach sessions", f"{len(ot_month)}", color="orange", icon="📣"),
                     unsafe_allow_html=True)
with p4:
    pp_n = data["perpetrators"]
    dpp = pd.to_datetime(pp_n.get("date_enrolled"), errors="coerce") if len(pp_n) else pd.Series(dtype="datetime64[ns]")
    pp_month = pp_n[(dpp.dt.year == sel_year) & (dpp.dt.month == sel_month)] if len(pp_n) else pd.DataFrame()
    st.markdown(kpi("Perpetrator cases", f"{len(pp_month)}", color="red", icon="⚖️"),
                unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

if st.button("📄 Generate Word report", type="primary", use_container_width=True):
    with st.spinner(f"Building the {sel_label} report…"):
        try:
            buf = build_monthly_report(data, sel_year, sel_month, prepared_by)
            fname = f"Nyaka_SGBV_Monthly_Report_{sel_year}_{sel_month:02d}.docx"
            st.success(f"Report for {sel_label} is ready.")
            st.download_button(
                "⬇ Download Word document",
                data=buf,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Report generation failed: {e}")
            st.caption("If this persists, check that python-docx and matplotlib are "
                       "installed (they are in requirements.txt).")

# What's in the report
section("What the report contains", "orange")
st.markdown(f"""
<div style='font-size:12px;color:{C["dark"]};line-height:1.9;'>
  <strong>1. Executive Summary</strong> — auto-drafted narrative + KPI grid<br>
  <strong>2. Survivor Support</strong> — enrollments by district & violence type, with chart<br>
  <strong>3. Justice & Legal Pipeline</strong> — new cases, arrests, case-status activity<br>
  <strong>4. Prevention & Outreach</strong> — sessions, reach, school engagement<br>
  <strong>5. Safeguarding & Case Follow-up</strong> — stale cases, follow-up gaps<br>
  <strong>6. Challenges, Recommendations & Next Steps</strong> — prompts for your narrative
</div>
<div style='background:{C["gold_lt"]};border-left:3px solid {C["gold"]};
            border-radius:4px;padding:9px 14px;font-size:11px;color:#5D4037;
            margin-top:12px;'>
  💡 The figures come straight from the dashboard data. Always verify them against
  your source records, and replace the bracketed prompts with your own programme
  voice before the report goes to a funder.
</div>""", unsafe_allow_html=True)