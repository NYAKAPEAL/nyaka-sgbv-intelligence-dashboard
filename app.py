"""
app.py — Nyaka SGBV Intelligence Platform
Production-grade MEAL dashboard with real data integration.
Focus: Kanungu · Rukungiri · Rubanda · SW Uganda
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from config import C, TARGETS, VIOLENCE_COLORS, LEGAL_COLORS, SAFE_LIVING_TIPS, RISK_TIMES
from utils.auth import check, show_login, sidebar_panel, can_access
from utils.data_loader import load_all, compute_kpis, apply_filters
from utils.viz import (kpi, alert_kpi, page_header, section, safe_notice,
                       progress, line_area, bar_h, bar_v, donut, gauge,
                       funnel, scatter_map_px, density_map, heatmap_chart)

st.set_page_config(
    page_title="Nyaka SGBV Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(f"""<style>
[data-testid="stSidebar"]{{
    background:linear-gradient(180deg,{C["purple_lt"]} 0%,{C["purple_xlt"]} 60%,white 100%);
    border-right:1.5px solid {C["purple_lt"]};
}}
.main .block-container{{padding-top:1rem;padding-bottom:2rem;}}
.stButton>button{{background:{C["purple"]};color:white;border:none;
    border-radius:6px;font-weight:600;}}
.stButton>button:hover{{background:{C["orange"]};color:white;}}
[data-testid="stMetric"]{{background:white;padding:14px;border-radius:8px;
    box-shadow:0 1px 6px rgba(0,0,0,0.06);}}
.stTabs [data-baseweb="tab"]{{font-weight:600;font-size:12px;}}
div[data-testid="stVerticalBlock"]>div:has(div.stMarkdown)>div{{gap:0.5rem;}}
</style>""", unsafe_allow_html=True)

# ── AUTH ──────────────────────────────────────────────────────────────────────
if not check():
    show_login(); st.stop()

# ── DATA ──────────────────────────────────────────────────────────────────────
DATA = load_all()
sv, pp, ot, sc = DATA["survivors"], DATA["perpetrators"], DATA["outreach"], DATA["school"]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
sidebar_panel()
st.sidebar.markdown("---")
st.sidebar.markdown(f"<div style='font-weight:700;color:{C['purple']};font-size:12px;margin-bottom:8px;'>🔍 GLOBAL FILTERS</div>",
                    unsafe_allow_html=True)

all_years = sorted(sv["year"].dropna().unique().astype(int).tolist()) if len(sv) else [2022,2023,2024,2025,2026]
sel_years = st.sidebar.multiselect("Year", all_years, default=all_years)
sel_dist  = st.sidebar.selectbox("District", ["All","Kanungu","Rukungiri","Rubanda"])
sel_viol  = st.sidebar.selectbox("Violence Type", ["All","Defilement","Rape","Physical assault","Child neglect/abuse","Sexual assault","Denied resources"])
sel_gen   = st.sidebar.selectbox("Gender", ["All","F","M"])

filt = {"years": sel_years, "district": sel_dist, "violence": sel_viol, "gender": sel_gen}
sv_f  = apply_filters(sv, filt)
pp_f  = apply_filters(pp, filt)
ot_f  = apply_filters(ot, filt)
sc_f  = apply_filters(sc, filt)

sv_e = sv_f[sv_f.get("report_category","").str.contains("enrollment", na=False)]
pp_e = pp_f[pp_f.get("is_enrolled", pd.Series(dtype=bool))]

kpis = compute_kpis(sv_f, pp_f, ot_f, sc_f)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='font-size:10px;color:{C["grey"]};text-align:center;'>
  👤 {len(sv_e):,} survivors · ⚖️ {len(pp_e):,} perps<br>
  🌍 {len(ot_f):,} outreach · 🏫 {len(sc_f):,} school
</div>""", unsafe_allow_html=True)

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
page_header(
    "Nyaka SGBV Intelligence Platform",
    "Executive MEAL Dashboard · Kanungu · Rukungiri · Rubanda · SW Uganda · 2022–2026",
    "🛡️")
safe_notice()

# ── DATA STREAM BADGES ────────────────────────────────────────────────────────
st.markdown(f"""
<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;'>
  <span style='background:{C["purple_lt"]};color:{C["purple_dk"]};font-size:10px;
               padding:3px 11px;border-radius:12px;font-weight:600;'>
    👤 {len(sv_e):,} survivors enrolled</span>
  <span style='background:{C["red_lt"]};color:{C["red"]};font-size:10px;
               padding:3px 11px;border-radius:12px;font-weight:600;'>
    ⚖️ {len(pp_e):,} perpetrators tracked</span>
  <span style='background:{C["teal_lt"]};color:{C["teal"]};font-size:10px;
               padding:3px 11px;border-radius:12px;font-weight:600;'>
    🌍 {len(ot_f):,} outreach sessions · {kpis["outreach_reach"]:,} reached</span>
  <span style='background:{C["gold_lt"]};color:#827717;font-size:10px;
               padding:3px 11px;border-radius:12px;font-weight:600;'>
    🏫 {len(sc_f):,} school visits · {kpis["school_reach"]:,} students</span>
</div>""", unsafe_allow_html=True)

# ── CRISIS ALERT ──────────────────────────────────────────────────────────────
crisis = kpis.get("crisis_cases", 0)
if crisis > 0:
    st.markdown(f"""<div style='display:flex;align-items:center;gap:10px;
        padding:9px 16px;background:{C["red_lt"]};border:1px solid #EF9A9A;
        border-radius:7px;font-size:11px;color:{C["red"]};margin-bottom:12px;'>
      🚨 <strong>{crisis} crisis-flagged survivors</strong> require Clinical Lead review.
      Navigate to Survivors → Mental Health for pending reviews.
    </div>""", unsafe_allow_html=True)

# ── PRIMARY KPIS ──────────────────────────────────────────────────────────────
section("Core Programme Indicators", "purple")
c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(kpi("Survivors Enrolled",f"{kpis['total_survivors']:,}",color="purple",icon="👤",note=f"Target: {TARGETS['survivors_enrolled']:,}"),unsafe_allow_html=True)
with c2: st.markdown(kpi("Children (<18)",f"{kpis['children']:,}",color="orange",icon="🧒",note=f"{round(100*kpis['children']/max(kpis['total_survivors'],1),0):.0f}% of survivors"),unsafe_allow_html=True)
with c3: st.markdown(kpi("Perpetrators Arrested",f"{kpis['arrested']:,}",color="blue",icon="🔒",note=f"Arrest rate: {kpis['arrest_rate']}%"),unsafe_allow_html=True)
with c4: st.markdown(kpi("Cases Won (Conviction)",f"{kpis['convicted']:,}",color="green",icon="⚖️",note=f"Conviction rate: {kpis['conviction_rate']}%"),unsafe_allow_html=True)
st.markdown("<br/>",unsafe_allow_html=True)

c5,c6,c7,c8 = st.columns(4)
with c5: st.markdown(kpi("Outreach Sessions",f"{kpis['outreach_sessions']:,}",color="teal",icon="🌍",note=f"Target: {TARGETS['outreach_sessions']}"),unsafe_allow_html=True)
with c6: st.markdown(kpi("People Reached",f"{kpis['outreach_reach']:,}",color="gold",icon="👥"),unsafe_allow_html=True)
with c7: st.markdown(kpi("School Sessions",f"{kpis['school_sessions']:,}",color="purple",icon="🏫",note=f"Target: {TARGETS['school_sessions']}"),unsafe_allow_html=True)
with c8: st.markdown(kpi("Crisis-Flagged",f"{kpis['crisis_cases']:,}",color="red",icon="🚨",note="Require Clinical Lead review"),unsafe_allow_html=True)

st.markdown("<br/>",unsafe_allow_html=True)

# ── ROW 1: TREND + VIOLENCE ───────────────────────────────────────────────────
section("Case Trends & Violence Profile", "purple")
col1, col2 = st.columns([3,2])

with col1:
    monthly = sv_e.groupby("month_label")["client_id"].count().reset_index()
    monthly.columns = ["Month","Cases"]
    monthly = monthly.sort_values("Month").tail(36)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["Month"],y=monthly["Cases"],
        mode="lines+markers",line=dict(color=C["purple"],width=2.5),
        marker=dict(size=6),fill="tozeroy",fillcolor="rgba(91,45,142,0.08)",
        name="Cases"))
    fig.update_layout(template="plotly_white",height=310,margin=dict(l=36,r=16,t=48,b=36),
                      title="Monthly Survivor Enrollments",
                      xaxis=dict(showgrid=False,title=""),
                      yaxis=dict(gridcolor="#EEE"))
    st.plotly_chart(fig,use_container_width=True)

with col2:
    vt = sv_e["assault_label"].value_counts().reset_index()
    vt.columns = ["Type","Count"]
    clrs = [VIOLENCE_COLORS.get(t,C["grey"]) for t in vt["Type"]]
    fig2 = go.Figure(go.Pie(labels=vt["Type"],values=vt["Count"],hole=0.55,
        marker=dict(colors=clrs,line=dict(color="white",width=2)),
        textinfo="label+percent",textfont=dict(size=10)))
    fig2.update_layout(template="plotly_white",height=310,
                       margin=dict(l=36,r=16,t=48,b=36),
                       title="Violence Categories",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2,use_container_width=True)

# ── ROW 2: DISTRICT + LEGAL ───────────────────────────────────────────────────
section("District Coverage & Legal Outcomes", "orange")
col3, col4 = st.columns(2)

with col3:
    dist = sv_e.groupby("district")["client_id"].count().reset_index()
    dist.columns = ["District","Survivors"]
    clrs_d = {"Kanungu":C["purple"],"Rukungiri":C["orange"],"Rubanda":C["teal"],"Other":C["grey"]}
    fig3 = px.bar(dist.sort_values("Survivors"),x="Survivors",y="District",
                  orientation="h",color="District",
                  color_discrete_map=clrs_d,height=260,template="plotly_white",
                  title="Survivors by District")
    fig3.update_layout(margin=dict(l=100,r=16,t=48,b=36),showlegend=False)
    st.plotly_chart(fig3,use_container_width=True)

with col4:
    pp_enroll = pp_f[pp_f.get("is_enrolled",pd.Series(dtype=bool))]
    if len(pp_enroll):
        ls = pp_enroll["perpetrator_location_label"].value_counts().reset_index()
        ls.columns = ["Status","Count"]
        ls_clrs = {"Arrested":C["green"],"On the run":C["red"],"Arrest underway":C["amber"],
                   "Released on Arrest":C["orange"],"Convicted (sentenced)":C["purple"]}
        fig4 = px.bar(ls.sort_values("Count"),x="Count",y="Status",orientation="h",
                      color="Status",color_discrete_map=ls_clrs,height=260,
                      template="plotly_white",title="Perpetrator Legal Status")
        fig4.update_layout(margin=dict(l=140,r=16,t=48,b=36),showlegend=False)
        st.plotly_chart(fig4,use_container_width=True)

# ── ROW 3: OUTREACH + INDICATOR PROGRESS ─────────────────────────────────────
section("Prevention Coverage & Indicator Progress", "teal")
col5, col6 = st.columns([3,2])

with col5:
    ot_m = ot_f.groupby("month_label").agg(Sessions=("date","count"),Reach=("total","sum")).reset_index()
    ot_m = ot_m.sort_values("month_label").tail(24)
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(x=ot_m["month_label"],y=ot_m["Reach"],name="People Reached",
                          marker_color=C["teal"],opacity=0.7))
    fig5.add_trace(go.Scatter(x=ot_m["month_label"],y=ot_m["Sessions"],name="Sessions",
                               mode="lines+markers",line=dict(color=C["orange"],width=2.5),yaxis="y2"))
    fig5.update_layout(template="plotly_white",height=290,
                       title="Monthly Outreach: Sessions & People Reached",
                       margin=dict(l=36,r=40,t=48,b=36),
                       yaxis=dict(title="People Reached"),
                       yaxis2=dict(title="Sessions",overlaying="y",side="right"),
                       legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig5,use_container_width=True)

with col6:
    prog_html = "".join([
        progress("Survivors enrolled",kpis["total_survivors"],TARGETS["survivors_enrolled"]),
        progress("Arrest rate",kpis["arrest_rate"],TARGETS["arrest_rate"],"%"),
        progress("Outreach sessions",kpis["outreach_sessions"],TARGETS["outreach_sessions"]),
        progress("School sessions",kpis["school_sessions"],TARGETS["school_sessions"]),
        progress("People reached",kpis["outreach_reach"],TARGETS["outreach_reach"]),
    ])
    st.markdown(f"<div style='margin-top:24px;'>{prog_html}</div>",unsafe_allow_html=True)

# ── ROW 4: GIS PREVIEW + HEALING CENTRES ─────────────────────────────────────
section("Geographic Intelligence Preview", "purple")
tab_inc, tab_out = st.tabs(["📍 Incident Hotspots (GPS)", "🌍 Outreach Coverage"])

with tab_inc:
    sv_gps = sv_e[sv_e["lat"].notna() & sv_e["lon"].notna()].copy()
    if len(sv_gps) > 0:
        from config import VIOLENCE_COLORS
        fig_m = px.scatter_mapbox(sv_gps.sample(min(800,len(sv_gps))),
                                   lat="lat",lon="lon",zoom=9,height=440,
                                   mapbox_style="open-street-map",
                                   color="assault_label",
                                   color_discrete_map=VIOLENCE_COLORS,
                                   hover_data={"survivor_token":True,"district":True,
                                               "assault_label":True,"lat":False,"lon":False},
                                   title=f"Incident Locations — {len(sv_gps):,} GPS-tagged survivors")
        fig_m.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_m,use_container_width=True)
        st.caption(f"Showing {min(800,len(sv_gps)):,} of {len(sv_gps):,} GPS-tagged records (sampled for performance). Full map in GIS Dashboard page.")
    else:
        st.info("No GPS data in current filter.")

with tab_out:
    ot_gps = ot_f[ot_f["lat"].notna() & ot_f["lon"].notna()].copy()
    if len(ot_gps) > 0:
        fig_ot = px.scatter_mapbox(ot_gps,lat="lat",lon="lon",zoom=9,height=440,
                                    mapbox_style="open-street-map",
                                    color="event_cat" if "event_cat" in ot_gps.columns else "district",
                                    size="total",size_max=18,
                                    hover_data={"district":True,"event_cat":True,"total":True,
                                                "lat":False,"lon":False},
                                    title="Outreach Session Locations & Reach")
        fig_ot.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_ot,use_container_width=True)

# ── HEALING CENTRE SUMMARY ────────────────────────────────────────────────────
section("Healing Centre Performance", "orange")
hc_col = ("healing_center_label" if "healing_center_label" in sv_e.columns
          else ("healing_center" if "healing_center" in sv_e.columns else None))
if hc_col and hc_col in sv_e.columns:
    hc_data = sv_e.groupby(hc_col)["client_id"].count().reset_index()
    hc_data.columns = ["Centre","Survivors"]
    hc_data = hc_data.sort_values("Survivors",ascending=False)
    fig_hc = px.bar(hc_data,x="Survivors",y="Centre",orientation="h",
                    color_discrete_sequence=[C["purple"]],height=260,
                    template="plotly_white",title="Survivors by Healing Centre")
    fig_hc.update_layout(margin=dict(l=200,r=16,t=48,b=36))
    st.plotly_chart(fig_hc,use_container_width=True)

# ── SAFE LIVING GUIDANCE TEASER ───────────────────────────────────────────────
section("🏠 Safe Living Guidance", "gold")
st.markdown(f"""
<div style='background:{C["gold_lt"]};border-left:4px solid {C["gold"]};
            border-radius:8px;padding:14px 18px;'>
  <div style='font-weight:600;color:#5D4037;margin-bottom:8px;font-size:13px;'>
    Evidence-Based Community Safety Intelligence
  </div>
  <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
""",unsafe_allow_html=True)

for tip in SAFE_LIVING_TIPS[:4]:
    st.markdown(f"""
    <div style='background:white;border-radius:6px;padding:8px 12px;font-size:11px;color:#4A3728;'>
      💡 {tip}
    </div>""",unsafe_allow_html=True)

st.markdown("</div><div style='margin-top:10px;font-size:11px;color:#7B5E45;'>→ See full Safe Living Dashboard (GIS page) for location-specific risk maps.</div></div>",
            unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='text-align:center;color:{C["grey"]};font-size:10px;
            border-top:1px solid #EEE;padding-top:12px;margin-top:24px;'>
  Nyaka SGBV Intelligence Platform v3.0 · Nyaka AIDS Orphans Project ·
  Kanungu · Rukungiri · Rubanda · SW Uganda ·
  Data: {len(sv_e):,} survivors | {len(pp_e):,} perpetrators | {kpis["total_reach"]:,} prevention reach ·
  All data anonymised · Access audited
</div>""",unsafe_allow_html=True)