"""
pages/9_Cost_of_Impact.py
Financial Intelligence Module — Investment efficiency for donor decision-making.
"If I invest in Nyaka, what exactly does it cost to deliver justice,
 and what happens if we scale to Rubanda?"
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import C
from utils.auth import check, sidebar_panel, can_access
from utils.data_loader import load_survivors, load_outreach, load_school
from utils.viz import section, page_header, kpi, progress
from utils.cost_model import (
    survivor_cost, arrest_cost, justice_outcome_cost, juvenile_cost,
    outreach_cost, healing_center_cost,
    expansion_cost, cost_drivers_breakdown, workshop_cost_for_n, format_ugx,
    WORKSHOP_PER_PARTICIPANT, ANNUAL_SURVIVORS, ANNUAL_ARRESTS,
    ANNUAL_OUTREACH_SESS, ANNUAL_SCHOOL_SESS, N_CENTRES,
    LEGAL_ADVOCATE_SALARY, MOTORCYCLE_PURCHASE,
)

if not check():
    st.warning("Please log in.")
    st.stop()
if not can_access("mel"):
    st.error("🔒 Access denied.")
    st.stop()

sidebar_panel()
page_header(
    "Cost of Impact",
    "Investment efficiency · unit economics · scale intelligence · "
    "donor decision-making framework",
    "💰"
)

# Investment philosophy notice
st.markdown(f"""
<div style='background:{C["purple_lt"]};border-left:4px solid {C["purple"]};
            border-radius:8px;padding:12px 18px;font-size:12px;
            color:{C["purple_dk"]};margin-bottom:14px;'>
  <strong>📐 This is an investment intelligence tool, not an accounting system.</strong>
  Costs are range-based to reflect real variability. Shared programme costs
  (salaries, vehicles, management) are allocated proportionally across outputs
  to avoid double-counting. All figures in UGX.
</div>""", unsafe_allow_html=True)

# Load live data for context (actual throughput numbers)
try:
    sv = load_survivors()
    sv_e = sv[sv.get("report_category","").str.contains("enrollment", na=False)]
    ot = load_outreach()
    sc = load_school()
    actual_survivors  = len(sv_e)
    actual_outreach   = len(ot)
    actual_school     = len(sc)
    actual_reach      = int(ot["total"].sum()) if "total" in ot.columns else 0
    actual_students   = int(sc["total"].sum()) if "total" in sc.columns else 0
except Exception:
    actual_survivors  = ANNUAL_SURVIVORS
    actual_outreach   = ANNUAL_OUTREACH_SESS
    actual_school     = ANNUAL_SCHOOL_SESS
    actual_reach      = 463953
    actual_students   = 16464

# Pre-compute all cost models
sv_model = survivor_cost(include_shared=True)
arr_model = arrest_cost()
just_model = justice_outcome_cost()
juv_model  = juvenile_cost()
ot_comm   = outreach_cost("community")
ot_wkshp  = outreach_cost("workshop")
ot_radio  = outreach_cost("radio")
ot_school = outreach_cost("school")
hc_model  = healing_center_cost()
exp_model = expansion_cost("Rubanda")
drivers   = cost_drivers_breakdown()

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TOP KPI STRIP
# ════════════════════════════════════════════════════════════════════════════
section("💰 Executive Investment Summary", "purple")

c1,c2,c3,c4,c5 = st.columns(5)
with c1:
    st.markdown(kpi("Cost per survivor",
                    format_ugx(sv_model["avg"], short=True),
                    color="purple", icon="👤",
                    note=f"Range: {format_ugx(sv_model['min'],True)} – "
                         f"{format_ugx(sv_model['max'],True)}"),
                unsafe_allow_html=True)
with c2:
    arr_cps = arr_model["avg"]
    st.markdown(kpi("Cost per arrest",
                    format_ugx(arr_cps, short=True),
                    color="red", icon="🔒",
                    note="Flat 60K (30K police + 30K transport)"),
                unsafe_allow_html=True)
with c3:
    st.markdown(kpi("Cost per justice outcome",
                    format_ugx(just_model["avg"], short=True),
                    color="orange", icon="⚖️",
                    note=f"Range: {format_ugx(just_model['min'],True)} – "
                         f"{format_ugx(just_model['max'],True)} · excl. juveniles"),
                unsafe_allow_html=True)
with c4:
    ot_session_cost = ot_comm["avg"]
    st.markdown(kpi("Cost per outreach session",
                    format_ugx(ot_session_cost, short=True),
                    color="teal", icon="🌍",
                    note="Community session (transport + lunch)"),
                unsafe_allow_html=True)
with c5:
    st.markdown(kpi("Cost per workshop participant",
                    format_ugx(WORKSHOP_PER_PARTICIPANT, short=True),
                    color="gold", icon="📚",
                    note="Fixed rate · UGX 100,000"),
                unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ── SCALE HEADLINE ────────────────────────────────────────────────────────────
total_drivers = drivers["total"]
col_h1, col_h2, col_h3 = st.columns(3)
with col_h1:
    st.markdown(kpi("Estimated annual programme cost",
                    format_ugx(total_drivers, short=True),
                    color="purple", icon="📊",
                    note="All cost categories combined"), unsafe_allow_html=True)
with col_h2:
    st.markdown(kpi("Survivors supported",
                    f"{actual_survivors:,}",
                    color="teal", icon="👥",
                    note="All-time enrolled 2022–2026"), unsafe_allow_html=True)
with col_h3:
    # USD equivalent at Bank of Uganda rate ~3,750 UGX/USD
    usd_per_survivor = round(sv_model["avg"] / 3750)
    st.markdown(kpi("Cost per survivor (USD equiv.)",
                    f"~${usd_per_survivor}",
                    color="green", icon="💵",
                    note="At BOU rate ~3,750 UGX/USD"),
                unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SURVIVOR JUSTICE PATHWAY
# ════════════════════════════════════════════════════════════════════════════
section("🏥 Survivor Justice Pathway Cost Model", "purple")

col1, col2 = st.columns([3, 2])

with col1:
    # Waterfall / staged cost breakdown
    stages = [
        ("Intake & medical exam",     sv_model["stages"]["Intake & medical exam"],            C["teal"]),
        ("Follow-ups (min, 4 visits)", sv_model["stages"]["Case-manager follow-ups (min, 4 visits)"], C["blue"]),
        ("Follow-ups (max, 10 visits)",sv_model["stages"]["Case-manager follow-ups (max, 10 visits)"],C["purple"]),
        ("Medication / drugs",         sv_model["stages"]["Medication / drugs"],               C["orange"]),
        ("Medical extra (scans, labs)",sv_model["stages"]["Medical care extra (scans, labs)"], C["amber"]),
        ("Sanitary supplies",          sv_model["stages"]["Sanitary supplies (pads, knickers)"], C["gold"]),
        ("Other aid materials",        sv_model["stages"]["Other aid materials"],              C["green"]),
        ("Shared system (allocated)",  sv_model["stages"]["Shared system (allocated)"],        C["grey"]),
    ]
    stage_df = pd.DataFrame(stages, columns=["Stage","Cost (UGX)","Color"])

    fig_stages = go.Figure(go.Bar(
        x=stage_df["Stage"], y=stage_df["Cost (UGX)"],
        marker_color=stage_df["Color"],
        text=[format_ugx(v, True) for v in stage_df["Cost (UGX)"]],
        textposition="outside"
    ))
    fig_stages.update_layout(
        template="plotly_white", height=340,
        margin=dict(l=36, r=16, t=48, b=100),
        title="Cost breakdown by pathway stage (average survivor)",
        xaxis_tickangle=-30, yaxis_title="UGX", showlegend=False
    )
    st.plotly_chart(fig_stages, use_container_width=True)

with col2:
    st.markdown(f"""
    <div style='background:{C["purple_lt"]};border-radius:8px;padding:14px 16px;'>
      <div style='font-size:12px;font-weight:600;color:{C["purple"]};
                  margin-bottom:10px;'>Per-survivor pathway cost</div>
      <div style='display:flex;justify-content:space-between;
                  border-bottom:1px solid {C["border"] if hasattr(C,"border") else "#DDD"};
                  padding-bottom:8px;margin-bottom:8px;'>
        <span style='font-size:11px;color:{C["grey"]};'>Minimum pathway</span>
        <span style='font-weight:500;color:{C["green"]};'>
          {format_ugx(sv_model["min"])}
        </span>
      </div>
      <div style='display:flex;justify-content:space-between;
                  border-bottom:1px solid #EEE;padding-bottom:8px;margin-bottom:8px;'>
        <span style='font-size:11px;color:{C["grey"]};'>Average pathway</span>
        <span style='font-weight:600;font-size:14px;color:{C["purple"]};'>
          {format_ugx(sv_model["avg"])}
        </span>
      </div>
      <div style='display:flex;justify-content:space-between;
                  padding-bottom:8px;'>
        <span style='font-size:11px;color:{C["grey"]};'>Maximum pathway</span>
        <span style='font-weight:500;color:{C["red"]};'>
          {format_ugx(sv_model["max"])}
        </span>
      </div>
    </div>
    <br>
    <div style='background:{C["gold_lt"]};border-left:3px solid {C["gold"]};
                border-radius:4px;padding:9px 12px;font-size:11px;
                color:#5D4037;line-height:1.8;'>
      <strong>How this is computed:</strong><br>
      Covers a survivor from intake until their PTSD score falls below 20%:
      the medical exam, all case-manager follow-up visits (4–10 depending on
      trauma severity), medication and medical care (drugs, scans, lab tests),
      sanitary supplies (pads, knickers) and other aid materials.
      Court and justice costs are <em>not</em> included here — they are counted
      under Cost per Justice Outcome to avoid double counting.
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — LEGAL & ENFORCEMENT
# ════════════════════════════════════════════════════════════════════════════
section("⚖️ Legal & Enforcement Costs", "orange")

# --- Arrest cost (flat) + Justice outcome (range) side by side ---
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div style='background:{C["red_lt"]};border-radius:8px;padding:14px 16px;height:100%;'>
      <div style='font-size:12px;font-weight:600;color:{C["red"]};margin-bottom:10px;'>
        🔒 Cost per arrest — flat {format_ugx(arr_model["avg"])}
      </div>
      <table style='width:100%;font-size:11px;border-collapse:collapse;'>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Police facilitation to arrest</td>
            <td style='text-align:right;font-weight:500;'>UGX 30,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Transport suspect (local post → CPS)</td>
            <td style='text-align:right;font-weight:500;border-top:0.5px solid #EEE;'>UGX 30,000</td></tr>
        <tr><td style='padding:6px 0;font-weight:600;color:{C["red"]};border-top:1px solid #DDD;'>
              Total per arrest</td>
            <td style='text-align:right;font-weight:600;color:{C["red"]};border-top:1px solid #DDD;'>
              {format_ugx(arr_model["avg"])}</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>{ANNUAL_ARRESTS} arrests × 60K</td>
            <td style='text-align:right;font-weight:500;color:{C["purple"]};'>
              {format_ugx(arr_model["avg"] * ANNUAL_ARRESTS, True)} / yr</td></tr>
      </table>
      <div style='margin-top:8px;font-size:10px;color:{C["grey"]};line-height:1.6;'>
        Every arrest is a flat 60K. Juveniles cost more (remand transport) and are
        shown separately below so they don't inflate this average.
      </div>
    </div>""", unsafe_allow_html=True)

with col2:
    adv_range = just_model["components"]["Legal advocate follow-up (2–6 months)"]
    court_range = just_model["components"]["Survivor court facilitation (2–3 trips)"]
    st.markdown(f"""
    <div style='background:{C["orange_lt"]};border-radius:8px;padding:14px 16px;height:100%;'>
      <div style='font-size:12px;font-weight:600;color:{C["orange"]};margin-bottom:10px;'>
        ⚖️ Cost per justice outcome — {format_ugx(just_model["min"])}–{format_ugx(just_model["max"])}
      </div>
      <table style='width:100%;font-size:11px;border-collapse:collapse;'>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Arrest (police + transport)</td>
            <td style='text-align:right;font-weight:500;'>UGX 60,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Police reports (scene + medical/PF3)</td>
            <td style='text-align:right;font-weight:500;border-top:0.5px solid #EEE;'>UGX 60,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Legal advocate follow-up (2–6 mo)</td>
            <td style='text-align:right;font-weight:500;border-top:0.5px solid #EEE;'>UGX {adv_range}</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Survivor court facilitation (2–3 trips)</td>
            <td style='text-align:right;font-weight:500;border-top:0.5px solid #EEE;'>UGX {court_range}</td></tr>
        <tr><td style='padding:6px 0;font-weight:600;color:{C["orange"]};border-top:1px solid #DDD;'>
              Average per justice outcome</td>
            <td style='text-align:right;font-weight:600;color:{C["orange"]};border-top:1px solid #DDD;'>
              {format_ugx(just_model["avg"])}</td></tr>
      </table>
      <div style='margin-top:8px;font-size:10px;color:{C["grey"]};line-height:1.6;'>
        Excludes juveniles. This is the cost to pursue an adult case all the way
        to court, including facilitating the survivor to testify.
      </div>
    </div>""", unsafe_allow_html=True)

# --- Juvenile cases: separate box ---
st.markdown("<br/>", unsafe_allow_html=True)
section("Juvenile suspects — costed separately", "red")
jc1, jc2 = st.columns([1, 1.6])
with jc1:
    st.markdown(kpi("Cost per juvenile case",
                    format_ugx(juv_model["per_juvenile_case"], short=True),
                    color="red", icon="🧒",
                    note=f"~{juv_model['estimated_count']} cases/yr (assumed "
                         f"{int(juv_model['assumed_share']*100)}%)"),
                unsafe_allow_html=True)
with jc2:
    st.markdown(f"""
    <div style='background:{C["red_lt"]};border-left:3px solid {C["red"]};
                border-radius:4px;padding:10px 14px;font-size:11px;color:#5D2020;
                line-height:1.7;'>
      <strong>Why juveniles are separated:</strong> a juvenile suspect incurs the
      standard UGX 60,000 arrest cost <em>plus</em> UGX 200,000 to transport them
      to the Kabale remand home — UGX 260,000 in total. Because juveniles are a
      small share of cases, averaging this into every arrest would badly overstate
      the typical cost. The {int(juv_model['assumed_share']*100)}% share here is an
      assumption — replace it with the real juvenile count from your records for a
      precise figure.
    </div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style='background:{C["light"]};border-left:4px solid {C["purple"]};
            border-radius:6px;padding:10px 16px;font-size:11px;color:{C["dark"]};
            margin-top:12px;line-height:1.7;'>
  <strong>📐 How these legal costs are computed:</strong>
  Cost per arrest is a flat UGX 60,000 (UGX 30,000 paid to the police to effect
  the arrest at the local post + UGX 30,000 to transport the suspect to the
  Central Police Station). Cost per justice outcome adds the police scene-of-crime
  and medical (PF3) reports, the legal advocate's months of case follow-up, and
  the cost of facilitating the survivor to attend court and testify — excluding
  juveniles, who are costed on their own line above.
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — OUTREACH & PREVENTION
# ════════════════════════════════════════════════════════════════════════════
section("🌍 Outreach & Prevention Costs", "teal")

col1, col2 = st.columns(2)
with col1:
    # Comparison of outreach types
    ot_types = [
        ("Community session",   ot_comm["avg"],   C["teal"]),
        ("School visit",        ot_school["avg"],  C["gold"]),
        ("Radio talk show",     ot_radio["avg"],   C["purple"]),
        ("Workshop (15 pax)",   workshop_cost_for_n(15), C["orange"]),
        ("Workshop (30 pax)",   workshop_cost_for_n(30), C["red"]),
    ]
    ot_df = pd.DataFrame(ot_types, columns=["Type","Cost (UGX)","Color"])

    fig_ot = px.bar(ot_df, x="Cost (UGX)", y="Type",
                    orientation="h", color="Type",
                    color_discrete_sequence=[t[2] for t in ot_types],
                    height=280, template="plotly_white",
                    title="Cost per outreach activity type",
                    text=[format_ugx(v,True) for v in ot_df["Cost (UGX)"]])
    fig_ot.update_traces(textposition="outside")
    fig_ot.update_layout(margin=dict(l=180,r=80,t=48,b=36), showlegend=False)
    st.plotly_chart(fig_ot, use_container_width=True)

with col2:
    # Workshop calculator
    st.markdown(f"""
    <div style='background:{C["teal_lt"]};border-radius:8px;padding:14px 16px;'>
      <div style='font-size:12px;font-weight:600;color:{C["teal"]};margin-bottom:8px;'>
        Workshop cost calculator
      </div>""", unsafe_allow_html=True)

    n_pax = st.slider("Number of workshop participants", 5, 60, 20, 5)
    w_cost = workshop_cost_for_n(n_pax)
    w_fixed = 300_000  # fuel + maintenance
    w_variable = WORKSHOP_PER_PARTICIPANT * n_pax

    st.markdown(f"""
      <table style='width:100%;font-size:11px;margin-top:8px;border-collapse:collapse;'>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Fixed cost (fuel + maintenance)</td>
            <td style='text-align:right;'>UGX 300,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Variable ({n_pax} × UGX 100,000)</td>
            <td style='text-align:right;border-top:0.5px solid #EEE;'>
              {format_ugx(w_variable)}</td></tr>
        <tr><td style='padding:5px 0;font-weight:600;color:{C["teal"]};border-top:1px solid #DDD;'>
              Total workshop cost</td>
            <td style='text-align:right;font-weight:600;color:{C["teal"]};border-top:1px solid #DDD;'>
              {format_ugx(w_cost)}</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Cost per participant</td>
            <td style='text-align:right;font-weight:500;'>
              {format_ugx(round(w_cost/n_pax))}</td></tr>
      </table>
    </div>""", unsafe_allow_html=True)

    # Reach efficiency
    st.markdown(f"""
    <div style='background:{C["gold_lt"]};border-left:3px solid {C["gold"]};
                border-radius:4px;padding:8px 12px;font-size:11px;
                color:#5D4037;margin-top:10px;line-height:1.8;'>
      <strong>Prevention reach efficiency:</strong><br>
      {actual_outreach:,} outreach sessions reached <strong>{actual_reach:,} people</strong>
      at a cost of {format_ugx(ot_comm["avg"],True)} per session.<br>
      Effective cost per person reached:
      <strong>{format_ugx(round(ot_comm["avg"] * actual_outreach / max(actual_reach,1)))}</strong>
    </div>""", unsafe_allow_html=True)

# School breakdown
st.markdown("<br/>", unsafe_allow_html=True)
col3, col4 = st.columns(2)
with col3:
    school_cost_per_session = ot_school["avg"]
    school_cost_per_student = ot_school.get("per_student", 1000)
    st.markdown(f"""
    <div style='background:{C["gold_lt"]};border-radius:8px;padding:14px 16px;'>
      <div style='font-size:12px;font-weight:600;color:#827717;margin-bottom:8px;'>
        🏫 School outreach economics
      </div>
      <table style='width:100%;font-size:11px;border-collapse:collapse;'>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Transport per visit</td>
            <td style='text-align:right;'>UGX 50,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Food per day</td>
            <td style='text-align:right;border-top:0.5px solid #EEE;'>UGX 10,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Airtime (monthly allocation)</td>
            <td style='text-align:right;border-top:0.5px solid #EEE;'>UGX 50,000</td></tr>
        <tr><td style='padding:5px 0;font-weight:600;color:#827717;border-top:1px solid #DDD;'>
              Cost per school session</td>
            <td style='text-align:right;font-weight:600;color:#827717;border-top:1px solid #DDD;'>
              {format_ugx(round(school_cost_per_session))}</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>
              {actual_school:,} sessions × {format_ugx(int(school_cost_per_session),True)}</td>
            <td style='text-align:right;font-weight:500;color:{C["purple"]};'>
              {format_ugx(round(school_cost_per_session*actual_school), True)} / year</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Cost per student reached</td>
            <td style='text-align:right;font-weight:500;'>
              ~{format_ugx(round(school_cost_per_session*actual_school/max(actual_students,1)))}</td></tr>
      </table>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div style='background:{C["purple_lt"]};border-radius:8px;padding:14px 16px;'>
      <div style='font-size:12px;font-weight:600;color:{C["purple"]};margin-bottom:8px;'>
        📻 Radio talk show economics
      </div>
      <table style='width:100%;font-size:11px;border-collapse:collapse;'>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Airtime (per show)</td>
            <td style='text-align:right;'>UGX 800K–1.0M</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Accommodation (staff)</td>
            <td style='text-align:right;border-top:0.5px solid #EEE;'>UGX 60,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Meals (per staff day)</td>
            <td style='text-align:right;border-top:0.5px solid #EEE;'>UGX 30,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};border-top:0.5px solid #EEE;'>
              Staff transport (2–3 staff)</td>
            <td style='text-align:right;border-top:0.5px solid #EEE;'>UGX 100K–150K</td></tr>
        <tr><td style='padding:5px 0;font-weight:600;color:{C["purple"]};border-top:1px solid #DDD;'>
              Total per show</td>
            <td style='text-align:right;font-weight:600;color:{C["purple"]};border-top:1px solid #DDD;'>
              {format_ugx(ot_radio["min"])} – {format_ugx(ot_radio["max"])}</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Estimated listeners</td>
            <td style='text-align:right;font-weight:500;'>~10,000–50,000</td></tr>
        <tr><td style='padding:5px 0;color:{C["grey"]};'>Cost per listener reached</td>
            <td style='text-align:right;font-weight:500;color:{C["green"]};'>
              ~UGX 20–100</td></tr>
      </table>
      <div style='margin-top:8px;font-size:10px;color:{C["grey"]};'>
        Radio has highest reach per UGX of all outreach modalities.
      </div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — HEALING CENTRE MODEL
# ════════════════════════════════════════════════════════════════════════════
section("🏥 Healing Centre Operating Cost Model", "orange")

# Interactive monthly survivors slider
col_sl, col_hc = st.columns([1, 2])
with col_sl:
    monthly_sv_input = st.slider(
        "Survivors served per centre per month",
        min_value=5, max_value=80, value=34,   # 2031 / 5 centres / 12 months ≈ 34
        step=1
    )
    hc_dynamic = healing_center_cost(monthly_sv_input)

    st.markdown(f"""
    <div style='background:{C["orange_lt"]};border-radius:8px;padding:12px 14px;
                margin-top:8px;'>
      <div style='font-size:12px;font-weight:600;color:{C["orange"]};
                  margin-bottom:6px;'>Monthly per-centre summary</div>
      <div style='font-size:11px;line-height:2.2;'>
        <strong>Monthly cost:</strong>
        {format_ugx(hc_dynamic["monthly_total"])}<br>
        <strong>Annual cost:</strong>
        {format_ugx(hc_dynamic["annualised"], True)}<br>
        <strong>Cost per survivor served:</strong>
        <span style='color:{C["orange"]};font-weight:600;'>
          {format_ugx(hc_dynamic["cost_per_survivor"])}
        </span>
      </div>
    </div>""", unsafe_allow_html=True)

with col_hc:
    hc_comps = hc_model["components"]
    hc_df = pd.DataFrame([
        {"Component": k, "Monthly UGX": v}
        for k, v in hc_comps.items()
    ]).sort_values("Monthly UGX", ascending=True)

    fig_hc = px.bar(hc_df, x="Monthly UGX", y="Component",
                     orientation="h", color_discrete_sequence=[C["orange"]],
                     title="Monthly healing centre cost — by component",
                     height=300, template="plotly_white",
                     text=[format_ugx(v, True) for v in hc_df["Monthly UGX"]])
    fig_hc.update_traces(textposition="outside")
    fig_hc.update_layout(margin=dict(l=240, r=80, t=48, b=36))
    st.plotly_chart(fig_hc, use_container_width=True)

section("Cost per survivor served — centre comparison", "teal")
st.caption("Based on actual survivor throughput data per healing centre "
           "(2022–2026). All centres carry the same fixed costs.")

try:
    sv_data = load_survivors()
    sv_enroll = sv_data[sv_data.get("report_category","").str.contains("enrollment",na=False)]
    hc_col = next((c for c in sv_enroll.columns if "healing_center_label" in c), None)
    if hc_col:
        hc_counts = sv_enroll.groupby(hc_col)["client_id"].count().reset_index()
        hc_counts.columns = ["Centre","Total survivors"]
        hc_counts["Monthly avg"] = (hc_counts["Total survivors"] / (4 * 12)).round(0)  # 4 yr approx
        hc_monthly = healing_center_cost()["monthly_total"]
        hc_counts["Cost per survivor"] = (hc_monthly / hc_counts["Monthly avg"]).round(0)
        hc_counts["Cost per survivor"] = hc_counts["Cost per survivor"].astype(int)

        fig_eff = go.Figure()
        fig_eff.add_trace(go.Bar(
            x=hc_counts["Centre"], y=hc_counts["Cost per survivor"],
            marker_color=C["orange"], name="Cost per survivor",
            text=[format_ugx(v,True) for v in hc_counts["Cost per survivor"]],
            textposition="outside"
        ))
        fig_eff.add_hline(y=hc_counts["Cost per survivor"].mean(),
                           line_dash="dash", line_color=C["purple"],
                           annotation_text=f"Average: {format_ugx(int(hc_counts['Cost per survivor'].mean()),True)}")
        fig_eff.update_layout(
            template="plotly_white", height=300,
            title="Cost per survivor by healing centre "
                  "(lower = more efficient use of fixed costs, driven by survivor volume)",
            margin=dict(l=36, r=16, t=70, b=80), showlegend=False,
            xaxis_tickangle=-20, yaxis_title="UGX"
        )
        st.plotly_chart(fig_eff, use_container_width=True)
        st.dataframe(hc_counts, use_container_width=True, hide_index=True)
        st.caption("⚠ Higher cost per survivor at Nyamirama reflects lower survivor volume "
                   "— the fixed costs (salary, motorcycle) are the same regardless of caseload. "
                   "This is a coverage argument, not an inefficiency argument.")
except Exception:
    st.info("Healing centre comparison will display once survivor data with healing centre "
            "labels is available.")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 6 — RUBANDA EXPANSION MODEL
# ════════════════════════════════════════════════════════════════════════════
section("🏗️ Expansion Model: Rubanda District Simulation", "red")

st.markdown(f"""
<div style='background:{C["red_lt"]};border-left:4px solid {C["red"]};
            border-radius:8px;padding:11px 16px;font-size:11px;
            color:#5D2020;margin-bottom:12px;'>
  <strong>Investment case:</strong> Rubanda has NO Nyaka presence,
  NO High Court (cases go to Kabale), and a CPS that is on average
  54.8km from where perpetrators are enrolled. Adding one healing centre
  to Rubanda creates a full justice pathway where currently none exists.
</div>""", unsafe_allow_html=True)

col_e1, col_e2 = st.columns([2, 1])

with col_e1:
    # Rubanda ramp-up cost model
    ramp_months = list(range(1, 25))
    cumulative_costs = []
    cumulative_survivors = []
    monthly_ops = exp_model["monthly_operating"]
    one_time    = exp_model["one_time_setup"]

    for m in ramp_months:
        cum_cost = one_time + (monthly_ops * m)
        # Ramp: 20% in month 1 growing linearly to 100% by month 6
        avg_monthly_sv = min(1.0, m / 6) * exp_model["expected_monthly_survivors"]
        cum_sv = sum(min(1.0, i/6) * exp_model["expected_monthly_survivors"]
                      for i in range(1, m+1))
        cumulative_costs.append(cum_cost)
        cumulative_survivors.append(round(cum_sv))

    ramp_df = pd.DataFrame({
        "Month": ramp_months,
        "Cumulative cost (UGX M)": [c / 1_000_000 for c in cumulative_costs],
        "Cumulative survivors": cumulative_survivors,
    })

    fig_ramp = go.Figure()
    fig_ramp.add_trace(go.Scatter(
        x=ramp_df["Month"], y=ramp_df["Cumulative cost (UGX M)"],
        mode="lines+markers", name="Cumulative cost (UGX M)",
        line=dict(color=C["red"], width=2.5), marker=dict(size=5),
        yaxis="y1"
    ))
    fig_ramp.add_trace(go.Bar(
        x=ramp_df["Month"], y=ramp_df["Cumulative survivors"],
        name="Cumulative survivors served",
        marker_color=C["purple"], opacity=0.5, yaxis="y2"
    ))
    fig_ramp.add_vline(x=6, line_dash="dash", line_color=C["green"],
                        annotation_text="Full capacity (Month 6)",
                        annotation_font_size=9)
    fig_ramp.update_layout(
        template="plotly_white", height=340,
        title="Rubanda expansion: 24-month cumulative cost vs survivors served",
        margin=dict(l=60, r=60, t=48, b=36),
        yaxis=dict(title="UGX (millions)", gridcolor="#EEE"),
        yaxis2=dict(title="Survivors", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.08)
    )
    st.plotly_chart(fig_ramp, use_container_width=True)

with col_e2:
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,{C["purple_dk"]} 0%,{C["purple"]} 100%);
                border-radius:8px;padding:16px 18px;color:white;'>
      <div style='font-size:13px;font-weight:600;margin-bottom:12px;'>
        💡 Rubanda investment case
      </div>

      <div style='font-size:11px;margin-bottom:6px;opacity:0.8;'>
        One-time setup cost
      </div>
      <div style='font-size:20px;font-weight:700;margin-bottom:12px;'>
        {format_ugx(exp_model["one_time_setup"], True)}
      </div>

      <div style='font-size:11px;margin-bottom:4px;opacity:0.8;'>
        Monthly operating cost
      </div>
      <div style='font-size:18px;font-weight:600;margin-bottom:12px;'>
        {format_ugx(exp_model["monthly_operating"], True)}
      </div>

      <div style='font-size:11px;margin-bottom:4px;opacity:0.8;'>
        Expected monthly survivors
      </div>
      <div style='font-size:18px;font-weight:600;margin-bottom:12px;'>
        {exp_model["expected_monthly_survivors"]} → {exp_model["expected_monthly_survivors"]*12}/yr
      </div>

      <div style='border-top:1px solid rgba(255,255,255,0.2);padding-top:10px;margin-top:4px;'>
        <div style='font-size:11px;opacity:0.8;'>Cost per survivor (year 1)</div>
        <div style='font-size:16px;font-weight:600;'>
          {format_ugx(exp_model["cost_per_survivor_year1"])}
        </div>
        <div style='font-size:11px;opacity:0.8;margin-top:6px;'>
          Cost per survivor (steady state)
        </div>
        <div style='font-size:16px;font-weight:600;'>
          {format_ugx(exp_model["cost_per_survivor_steady"])}
        </div>
      </div>
    </div>

    <div style='background:{C["green_lt"]};border-radius:6px;padding:10px 14px;
                margin-top:10px;font-size:11px;color:{C["green"]};line-height:1.7;'>
      At steady state ({exp_model["ramp_months"]}+ months), the Rubanda
      centre delivers the same full SGBV service package as existing centres
      at {format_ugx(exp_model["cost_per_survivor_steady"])} per survivor —
      comparable to existing operations.
    </div>""", unsafe_allow_html=True)

# Expansion components
col_ec1, col_ec2 = st.columns(2)
with col_ec1:
    exp_one_time = exp_model["one_time_components"]
    ot_df = pd.DataFrame([
        {"Item": k, "Cost (UGX)": v} for k, v in exp_one_time.items()
    ])
    fig_ot2 = px.pie(ot_df, values="Cost (UGX)", names="Item",
                      hole=0.5, height=260,
                      title="One-time setup cost breakdown",
                      color_discrete_sequence=[C["purple"],C["orange"],C["gold"]])
    fig_ot2.update_layout(margin=dict(l=16,r=16,t=48,b=16))
    st.plotly_chart(fig_ot2, use_container_width=True)

with col_ec2:
    hc_comps_rubanda = healing_center_cost(
        exp_model["expected_monthly_survivors"])["components"]
    rub_df = pd.DataFrame([
        {"Component": k, "Monthly UGX": v} for k, v in hc_comps_rubanda.items()
    ]).sort_values("Monthly UGX", ascending=True)
    fig_rub = px.bar(rub_df, x="Monthly UGX", y="Component",
                      orientation="h", color_discrete_sequence=[C["purple"]],
                      title="Rubanda monthly operating cost — by component",
                      height=260, template="plotly_white",
                      text=[format_ugx(v,True) for v in rub_df["Monthly UGX"]])
    fig_rub.update_traces(textposition="outside")
    fig_rub.update_layout(margin=dict(l=240,r=80,t=48,b=16))
    st.plotly_chart(fig_rub, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 7 — COST DRIVERS
# ════════════════════════════════════════════════════════════════════════════
section("📊 Cost Drivers Analysis", "purple")

col_d1, col_d2 = st.columns([1, 2])

with col_d1:
    driver_df = pd.DataFrame([
        {"Category": k, "Annual UGX": v}
        for k, v in drivers.items() if k != "total"
    ]).sort_values("Annual UGX", ascending=False)
    driver_df["Pct"] = (driver_df["Annual UGX"] / drivers["total"] * 100).round(1)

    fig_donut = go.Figure(go.Pie(
        labels=driver_df["Category"],
        values=driver_df["Annual UGX"],
        hole=0.55,
        marker=dict(
            colors=[C["purple"],C["orange"],C["red"],C["teal"],C["blue"],C["grey"]],
            line=dict(color="white", width=2)
        ),
        textinfo="label+percent",
        textfont=dict(size=10)
    ))
    fig_donut.update_layout(
        height=340, margin=dict(l=16,r=16,t=48,b=16),
        title="Programme cost by driver (%)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_d2:
    fig_drv = px.bar(
        driver_df.sort_values("Annual UGX"),
        x="Annual UGX", y="Category",
        orientation="h",
        color="Category",
        color_discrete_sequence=[C["purple"],C["orange"],C["red"],C["teal"],C["blue"],C["grey"]],
        text=[f"{format_ugx(v,True)} ({p}%)"
               for v, p in zip(driver_df.sort_values("Annual UGX")["Annual UGX"],
                                driver_df.sort_values("Annual UGX")["Pct"])],
        height=340, template="plotly_white",
        title="Annual cost by driver category (UGX)"
    )
    fig_drv.update_traces(textposition="outside")
    fig_drv.update_layout(margin=dict(l=180,r=120,t=48,b=16),
                            showlegend=False, xaxis_title="UGX")
    st.plotly_chart(fig_drv, use_container_width=True)

# Key insight
largest_driver = driver_df.iloc[0]
st.markdown(f"""
<div style='background:{C["purple_lt"]};border-left:4px solid {C["purple"]};
            border-radius:6px;padding:10px 16px;font-size:11px;color:{C["purple_dk"]};
            line-height:1.8;'>
  <strong>Key finding:</strong> {largest_driver["Category"]} is the largest
  cost driver at {largest_driver["Pct"]:.1f}% of total programme cost.
  This is expected and appropriate — Nyaka's model is staff-intensive by design,
  because the legal advocacy relationship between the advocate and the survivor
  is the core of the justice delivery mechanism.
  Transport & logistics ({driver_df[driver_df["Category"]=="Transport & logistics"]["Pct"].iloc[0]}%)
  is the second driver and is directly reduced by proximity to healing centres
  (see Distance Intelligence page).
</div>""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='text-align:center;color:{C["grey"]};font-size:10px;
            border-top:1px solid #EEE;padding-top:12px;margin-top:24px;'>
  Nyaka Cost of Impact Module · Unit costs from Nyaka programme financial records ·
  UGX amounts · USD equivalents at BOU rate ~3,750 UGX/USD ·
  Range-based costing — not fixed-line accounting
</div>""", unsafe_allow_html=True)