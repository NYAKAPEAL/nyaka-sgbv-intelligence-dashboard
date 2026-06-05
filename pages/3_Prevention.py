"""pages/3_Prevention.py — Outreach, school sensitization, prevention analytics"""
import streamlit as st, pandas as pd, plotly.express as px
import plotly.graph_objects as go, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from config import C, TARGETS
from utils.auth import check, sidebar_panel, can_access
from utils.data_loader import load_all, apply_filters
from utils.viz import (kpi,section,page_header,safe_notice,bar_h,bar_v,
                       donut,scatter_map_px,density_map,heatmap_chart,progress)

if not check(): st.warning("Please log in."); st.stop()
if not can_access("prevention"): st.error("🔒 Access denied."); st.stop()

DATA=load_all(); ot=DATA["outreach"]; sc=DATA["school"]
sidebar_panel()
st.sidebar.markdown("---")
yrs=sorted(ot["year"].dropna().unique().astype(int).tolist()) if len(ot) else [2022,2023,2024,2025,2026]
sel_yrs=st.sidebar.multiselect("Year",yrs,default=yrs,key="ot_yr")
sel_dist=st.sidebar.selectbox("District",["All","Kanungu","Rukungiri","Rubanda"],key="ot_d")
filt={"years":sel_yrs,"district":sel_dist}
ot_f=apply_filters(ot,filt); sc_f=apply_filters(sc,filt)

page_header("Prevention & Outreach Analytics","Community outreach · school sensitization · reach analysis · coverage maps","🌍")
safe_notice()

ot_reach=int(ot_f.get("total",pd.Series(dtype=float)).sum())
sc_reach=int(sc_f.get("total",pd.Series(dtype=float)).sum())
ot_male=int(ot_f.get("males",pd.Series(dtype=float)).sum())
ot_female=int(ot_f.get("females",pd.Series(dtype=float)).sum())

c=st.columns(4)
for col,(lbl,val,clr,icon,note) in zip(c,[
    ("Outreach Sessions",f"{len(ot_f):,}","teal","🌍",f"Target: {TARGETS['outreach_sessions']}"),
    ("People Reached",f"{ot_reach:,}","purple","👥",f"Target: {TARGETS['outreach_reach']:,}"),
    ("School Sessions",f"{len(sc_f):,}","gold","🏫",f"Target: {TARGETS['school_sessions']}"),
    ("Students Reached",f"{sc_reach:,}","orange","🎒","School social work"),
]):
    with col: st.markdown(kpi(lbl,val,color=clr,icon=icon,note=note),unsafe_allow_html=True)
st.markdown("<br/>",unsafe_allow_html=True)

tab1,tab2,tab3=st.tabs(["📊 Outreach Analysis","🏫 Schools","🗺 Coverage Maps"])

with tab1:
    section("Activity & Reach Trend","teal")
    ot_m=ot_f.groupby("month_label").agg(Sessions=("date","count"),Reach=("total","sum"),
                                          Males=("males","sum"),Females=("females","sum")).reset_index()
    ot_m=ot_m.sort_values("month_label").tail(36)
    fig=go.Figure()
    fig.add_trace(go.Bar(x=ot_m["month_label"],y=ot_m["Reach"],name="Total Reached",
                         marker_color=C["teal"],opacity=0.65))
    fig.add_trace(go.Scatter(x=ot_m["month_label"],y=ot_m["Sessions"],name="Sessions",
                              mode="lines+markers",line=dict(color=C["orange"],width=2.5),yaxis="y2"))
    fig.update_layout(template="plotly_white",height=310,
                      title="Monthly Outreach Activity & Reach",
                      margin=dict(l=36,r=40,t=48,b=36),
                      yaxis=dict(title="People Reached",gridcolor="#EEE"),
                      yaxis2=dict(title="Sessions",overlaying="y",side="right"),
                      legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig,use_container_width=True)

    section("Event Types & Gender Breakdown","orange")
    col1,col2=st.columns(2)
    with col1:
        if "event_cat" in ot_f.columns:
            et=ot_f.groupby("event_cat").agg(Sessions=("date","count"),Reach=("total","sum")).reset_index()
            et=et.sort_values("Reach",ascending=False)
            fig2=px.bar(et,x="Reach",y="event_cat",orientation="h",
                        color_discrete_sequence=[C["teal"]],height=320,
                        template="plotly_white",title="Reach by Event Category")
            fig2.update_layout(margin=dict(l=140,r=16,t=48,b=36),yaxis_title="")
            st.plotly_chart(fig2,use_container_width=True)
    with col2:
        males_tot=int(ot_f.get("males",pd.Series()).sum()); females_tot=int(ot_f.get("females",pd.Series()).sum())
        fig3=go.Figure(go.Pie(labels=["Male","Female"],values=[males_tot,females_tot],hole=0.6,
            marker=dict(colors=[C["blue"],C["orange"]],line=dict(color="white",width=2)),
            textinfo="label+percent+value",textfont=dict(size=11)))
        fig3.update_layout(template="plotly_white",height=320,margin=dict(l=36,r=16,t=48,b=36),
                           title=f"Gender Breakdown\n(Total: {males_tot+females_tot:,})",
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3,use_container_width=True)

    section("District Coverage","purple")
    dist_ot=ot_f.groupby("district").agg(Sessions=("date","count"),Reach=("total","sum")).reset_index()
    fig4=go.Figure()
    fig4.add_trace(go.Bar(name="Sessions",x=dist_ot["district"],y=dist_ot["Sessions"],marker_color=C["purple"]))
    fig4.add_trace(go.Bar(name="Reach",x=dist_ot["district"],y=dist_ot["Reach"]/100,marker_color=C["teal"],
                          customdata=dist_ot["Reach"],hovertemplate="%{customdata:,.0f} people<extra></extra>"))
    fig4.update_layout(template="plotly_white",height=280,barmode="group",
                       title="Outreach by District (Sessions & Reach/100)",
                       margin=dict(l=36,r=16,t=48,b=36),legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig4,use_container_width=True)

    section("Sample Outreach Topics (from field data)","teal")
    topics=ot_f.get("outreach_topics",pd.Series(dtype=str)).dropna()
    if len(topics):
        for t in topics.sample(min(3,len(topics))).tolist():
            st.markdown(f"""<div style='background:{C["teal_lt"]};border-left:3px solid {C["teal"]};
                border-radius:6px;padding:9px 14px;font-size:11px;margin-bottom:6px;color:#00362E;'>
              📋 {t[:300]}...
            </div>""",unsafe_allow_html=True)

with tab2:
    section("School Sensitization Analytics","gold")
    col1,col2=st.columns(2)
    with col1:
        if "school_label" in sc_f.columns:
            by_sch=sc_f.groupby("school_label")["total"].sum().nlargest(10).reset_index()
            by_sch.columns=["School","Students"]
            fig=px.bar(by_sch.sort_values("Students"),x="Students",y="School",orientation="h",
                       color_discrete_sequence=[C["gold"]],height=360,
                       template="plotly_white",title="Top 10 Schools — Students Reached")
            fig.update_layout(margin=dict(l=200,r=16,t=48,b=36))
            st.plotly_chart(fig,use_container_width=True)
    with col2:
        if "event_type_label" in sc_f.columns:
            et_sc=sc_f["event_type_label"].value_counts().head(8).reset_index()
            et_sc.columns=["Activity","Count"]
            fig2=px.bar(et_sc.sort_values("Count"),x="Count",y="Activity",orientation="h",
                        color_discrete_sequence=[C["purple"]],height=360,
                        template="plotly_white",title="School Session Types")
            fig2.update_layout(margin=dict(l=200,r=16,t=48,b=36))
            st.plotly_chart(fig2,use_container_width=True)

    section("School Reach Trend","orange")
    sc_m=sc_f.groupby("month_label").agg(Sessions=("date","count"),Students=("total","sum")).reset_index()
    sc_m=sc_m.sort_values("month_label").tail(30)
    fig3=go.Figure()
    fig3.add_trace(go.Bar(x=sc_m["month_label"],y=sc_m["Students"],name="Students Reached",
                          marker_color=C["gold"],opacity=0.7))
    fig3.add_trace(go.Scatter(x=sc_m["month_label"],y=sc_m["Sessions"],name="Sessions",
                               mode="lines+markers",line=dict(color=C["purple"],width=2),yaxis="y2"))
    fig3.update_layout(template="plotly_white",height=290,title="Monthly School Social Work Activity",
                       margin=dict(l=36,r=40,t=48,b=36),
                       yaxis=dict(title="Students"),yaxis2=dict(title="Sessions",overlaying="y",side="right"),
                       legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig3,use_container_width=True)

    sc_m2=sc_f.groupby("month_label").agg(Males=("males","sum"),Females=("females","sum")).reset_index().sort_values("month_label").tail(30)
    fig4=go.Figure()
    fig4.add_trace(go.Bar(x=sc_m2["month_label"],y=sc_m2["Females"],name="Female",marker_color=C["orange"]))
    fig4.add_trace(go.Bar(x=sc_m2["month_label"],y=sc_m2["Males"],name="Male",marker_color=C["blue"]))
    fig4.update_layout(template="plotly_white",height=260,barmode="stack",
                       title="School Reach by Gender",margin=dict(l=36,r=16,t=48,b=36),
                       legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig4,use_container_width=True)

with tab3:
    section("Outreach Session GPS Map","teal")
    ot_gps=ot_f[ot_f.get("lat",pd.Series(dtype=float)).notna() & ot_f.get("lon",pd.Series(dtype=float)).notna()].copy()
    if len(ot_gps):
        fig=px.scatter_mapbox(ot_gps,lat="lat",lon="lon",zoom=9,height=480,
                              mapbox_style="open-street-map",
                              color="event_cat" if "event_cat" in ot_gps.columns else "district",
                              size="total",size_max=20,
                              hover_data={"district":True,"event_cat":True,"total":True,"lat":False,"lon":False},
                              title=f"Outreach Coverage — {len(ot_gps):,} GPS Sessions")
        fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig,use_container_width=True)

    section("School Location Map","gold")
    sc_gps=sc_f[sc_f.get("lat",pd.Series(dtype=float)).notna()].copy()
    if len(sc_gps):
        fig2=px.scatter_mapbox(sc_gps,lat="lat",lon="lon",zoom=10,height=420,
                               mapbox_style="open-street-map",
                               color="school_label" if "school_label" in sc_gps.columns else "district",
                               size="total",size_max=15,
                               hover_data={"school_label":True,"total":True,"district":True,
                                           "lat":False,"lon":False},
                               title="School Social Work Session Locations")
        fig2.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2,use_container_width=True)
