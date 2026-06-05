"""pages/5_MEL_Analytics.py — Integrated MEL: logframe, targets, disaggregation"""
import streamlit as st, pandas as pd, plotly.graph_objects as go
import plotly.express as px, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from config import C, TARGETS
from utils.auth import check, sidebar_panel, can_access
from utils.data_loader import load_all, compute_kpis
from utils.viz import section,page_header,safe_notice,gauge,progress,bar_h

if not check(): st.warning("Please log in."); st.stop()
if not can_access("mel"): st.error("🔒 Access denied."); st.stop()
DATA=load_all(); sv=DATA["survivors"]; pp=DATA["perpetrators"]; ot=DATA["outreach"]; sc=DATA["school"]
sidebar_panel()
kpis=compute_kpis(sv,pp,ot,sc)
sv_e=sv[sv.get("report_category", pd.Series("", index=sv.index)).str.contains("enrollment",na=False)]
pp_e=pp[pp.get("is_enrolled",pd.Series(dtype=bool))] if "is_enrolled" in pp.columns else pp[pp.get("report_category", pd.Series("", index=pp.index))=="enrollment"]
pp_f=pp[pp.get("is_followup",pd.Series(dtype=bool))] if "is_followup" in pp.columns else pp[pp.get("report_category", pd.Series("", index=pp.index)).str.contains("followup",na=False)]

page_header("M&E Analytics","Logframe indicators · targets · disaggregation engine · quarterly performance","📈")
safe_notice()

section("Logframe Indicator Scorecard","purple")
indicators=[
    ("1.1","Survivors enrolled",kpis["total_survivors"],TARGETS["survivors_enrolled"],"survivors"),
    ("1.2","Children enrolled",kpis["children"],int(TARGETS["survivors_enrolled"]*0.6),"children"),
    ("2.1","Perpetrators registered",kpis["perpetrators"],"-","cases"),
    ("2.2","Arrest / legal pursuit rate",kpis["arrest_rate"],TARGETS["arrest_rate"],"%"),
    ("2.3","Conviction rate",kpis["conviction_rate"],TARGETS["conviction_rate"],"%"),
    ("3.1","Outreach sessions",kpis["outreach_sessions"],TARGETS["outreach_sessions"],"sessions"),
    ("3.2","People reached (outreach+school)",kpis["total_reach"],TARGETS["outreach_reach"],"people"),
    ("3.3","School sessions",kpis["school_sessions"],TARGETS["school_sessions"],"sessions"),
]
for code,name,actual,target,unit in indicators:
    pct=round(100*actual/target,1) if isinstance(target,(int,float)) and target not in [0,"-"] else None
    status=("🟢 On Track" if pct and pct>=75 else ("🟡 At Risk" if pct and pct>=50 else ("🔴 Off Track" if pct else "—")))
    c=st.columns([1,5,2,2,2])
    c[0].markdown(f"**{code}**"); c[1].write(name)
    c[2].markdown(f"**{actual:,}** {unit}"); c[3].write(f"{target} {unit}" if target!="-" else "—"); c[4].markdown(status)
    st.divider()

section("Key Performance Gauges","gold")
g=st.columns(4)
with g[0]: st.plotly_chart(gauge(kpis["arrest_rate"],"Arrest Rate",100,TARGETS["arrest_rate"],230),use_container_width=True)
with g[1]: st.plotly_chart(gauge(kpis["conviction_rate"],"Conviction Rate",100,TARGETS["conviction_rate"],230),use_container_width=True)
with g[2]:
    ot_pct=round(100*kpis["outreach_sessions"]/TARGETS["outreach_sessions"],1)
    st.plotly_chart(gauge(ot_pct,"Outreach vs Target",100,100,230),use_container_width=True)
with g[3]:
    sc_pct=round(100*kpis["school_sessions"]/TARGETS["school_sessions"],1)
    st.plotly_chart(gauge(sc_pct,"School vs Target",100,100,230),use_container_width=True)

section("Disaggregation Engine","orange")
indicator=st.selectbox("Indicator",["Survivor Count","Children Count","Female Count","Defilement Cases","Rape Cases"])
breakby=st.selectbox("Break by",["district","subcounty_label","client_age_group","client_gender","assault_cat","healing_center_label"])

def dis_compute(df,ind,col):
    g=df.groupby(col)
    if ind=="Survivor Count": return g["client_id"].count().reset_index().rename(columns={"client_id":"Value"})
    elif ind=="Children Count":
        r=df.groupby(col).apply(lambda x: x.get("is_child",pd.Series(dtype=bool)).sum()).reset_index()
        r.columns=[col,"Value"]; return r
    elif ind=="Female Count":
        r=df.groupby(col).apply(lambda x:(x.get("client_gender","")=="F").sum()).reset_index()
        r.columns=[col,"Value"]; return r
    elif ind=="Defilement Cases":
        r=df.groupby(col).apply(lambda x:(x.get("assault_label","")=="Defilement").sum()).reset_index()
        r.columns=[col,"Value"]; return r
    else:
        r=df.groupby(col).apply(lambda x:(x.get("assault_label","")=="Rape").sum()).reset_index()
        r.columns=[col,"Value"]; return r

try:
    if breakby in sv_e.columns:
        dis=dis_compute(sv_e,indicator,breakby).sort_values("Value",ascending=False).head(20)
        dis.columns=[breakby,"Value"]
        fig=go.Figure(go.Bar(x=dis["Value"],y=dis[breakby],orientation="h",marker_color=C["purple"]))
        fig.update_layout(template="plotly_white",height=max(300,len(dis)*28),
                          title=f"{indicator} by {breakby}",margin=dict(l=160,r=16,t=48,b=20))
        st.plotly_chart(fig,use_container_width=True)
        with st.expander("Data table"): st.dataframe(dis,use_container_width=True,hide_index=True)
    else:
        st.warning(f"Column '{breakby}' not available in survivor data.")
except Exception as e:
    st.warning(f"Cannot compute: {e}")

section("Quarterly Performance","purple")
qc=sv_e.groupby("quarter")["client_id"].count().reset_index(); qc.columns=["Quarter","Cases"]; qc=qc.sort_values("Quarter")
fig2=go.Figure()
fig2.add_trace(go.Bar(x=qc["Quarter"],y=qc["Cases"],marker_color=C["purple"],name="Cases"))
fig2.add_hline(y=TARGETS["survivors_enrolled"]/4,line_dash="dash",line_color=C["green"],annotation_text="Quarterly target")
fig2.update_layout(template="plotly_white",height=300,margin=dict(l=36,r=16,t=48,b=36),
                   title="Quarterly Survivor Enrollments")
st.plotly_chart(fig2,use_container_width=True)

section("Year-on-Year Comparison","teal")
yoy=sv_e.groupby("year")["client_id"].count().reset_index(); yoy.columns=["Year","Survivors"]
yoy2=pp_e.groupby("year")["client_id"].count().reset_index(); yoy2.columns=["Year","Perpetrators"] if "client_id" in pp_e.columns else yoy2
yoy3=ot.groupby("year")["date"].count().reset_index(); yoy3.columns=["Year","Sessions"]
fig3=go.Figure()
fig3.add_trace(go.Bar(name="Survivors",x=yoy["Year"],y=yoy["Survivors"],marker_color=C["purple"]))
if len(yoy2): fig3.add_trace(go.Bar(name="Perpetrators",x=yoy2["Year"],y=yoy2["Perpetrators"],marker_color=C["red"]))
fig3.update_layout(template="plotly_white",height=300,barmode="group",
                   title="Year-on-Year: Survivors vs Perpetrators",
                   margin=dict(l=36,r=16,t=48,b=36),legend=dict(orientation="h",y=1.08))
st.plotly_chart(fig3,use_container_width=True)