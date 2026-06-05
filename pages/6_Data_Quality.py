"""pages/6_Data_Quality.py — Data quality monitoring, completeness, GPS audit"""
import streamlit as st, pandas as pd, plotly.express as px
import plotly.graph_objects as go, numpy as np, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from config import C
from utils.auth import check, sidebar_panel, can_access
from utils.data_loader import load_all
from utils.viz import section, page_header, safe_notice, kpi, bar_h

if not check(): st.warning("Please log in."); st.stop()
if not can_access("quality"): st.error("🔒 Access denied."); st.stop()
DATA=load_all(); sv=DATA["survivors"]; pp=DATA["perpetrators"]; ot=DATA["outreach"]; sc=DATA["school"]
sidebar_panel()
page_header("Data Quality Dashboard","Completeness · GPS coverage · duplicates · submission trends · enumerator performance","🔍")
safe_notice()

sv_e=sv[sv.get("report_category", pd.Series("", index=sv.index)).str.contains("enrollment",na=False)]

# Completeness
key_fields=["client_id","client_gender","client_age","date","assault_label","district",
            "healing_center_label","subcounty_label","parish","village"]
pf=[f for f in key_fields if f in sv_e.columns]
miss=pd.DataFrame({"Field":pf,"Missing %":[round(100*sv_e[f].isna().mean(),1) for f in pf],
                    "Non-Null":[int(sv_e[f].notna().sum()) for f in pf]})
miss["Status"]=miss["Missing %"].apply(lambda p:"🟢 Good" if p<5 else ("🟡 Review" if p<15 else "🔴 Poor"))
compl_score=round(100-miss["Missing %"].mean(),1)
gps_cov=round(100*sv_e.get("lat",pd.Series()).notna().mean(),1)
dups=int(sv_e["client_id"].duplicated().sum()) if "client_id" in sv_e.columns else 0

c=st.columns(4)
for col,(lbl,val,clr,icon) in zip(c,[
    ("Completeness Score",f"{compl_score}%","green","✅"),
    ("GPS Coverage",f"{gps_cov}%","teal","📍"),
    ("Duplicate Records",f"{dups:,}","orange" if dups==0 else "red","⚠"),
    ("Total Records",f"{len(sv_e):,}","purple","📊"),
]):
    with col: st.markdown(kpi(lbl,val,color=clr,icon=icon),unsafe_allow_html=True)
st.markdown("<br/>",unsafe_allow_html=True)

tab1,tab2,tab3=st.tabs(["📊 Completeness","📍 GPS Audit","📅 Submission Trends"])

with tab1:
    section("Field-Level Completeness","purple")
    col1,col2=st.columns([3,2])
    with col1:
        fig=px.bar(miss,x="Missing %",y="Field",orientation="h",color="Missing %",
                   color_continuous_scale="RdYlGn_r",height=340,template="plotly_white",
                   title="Missing Data % by Field")
        fig.add_vline(x=10,line_dash="dash",line_color=C["green"],annotation_text="10% threshold")
        fig.update_layout(margin=dict(l=160,r=16,t=48,b=36),showlegend=False)
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.dataframe(miss[["Field","Missing %","Status"]],use_container_width=True,hide_index=True)

    section("Logic Checks","red")
    checks={}
    age_n=pd.to_numeric(sv_e.get("client_age",pd.Series()),errors="coerce")
    checks["Age out of range (>90 or <5)"]=int(((age_n>90)|(age_n<5)).sum())
    checks["Gender not recorded"]=int(sv_e.get("client_gender",pd.Series()).isna().sum())
    checks["Enrollment date missing"]=int(sv_e.get("date",pd.Series()).isna().sum())
    checks["District = Other (outside operational area)"]=int((sv_e.get("district","")=="Other").sum())
    checks["High suicidal concern at intake (for follow-up)"]=int(
        (pd.to_numeric(sv_e.get("suicidal",pd.Series(dtype=float)),errors="coerce")>=4).sum()
    ) if "suicidal" in sv_e.columns else 0
    chk=pd.DataFrame({"Check":list(checks.keys()),"Count":list(checks.values())})
    chk["Severity"]=chk["Count"].apply(lambda v:"🔴 Critical" if v>20 else ("🟡 Warning" if v>0 else "🟢 Pass"))
    st.dataframe(chk,use_container_width=True,hide_index=True)
    if chk[chk["Count"]>0]["Count"].sum()>0:
        st.warning(f"⚠ {(chk['Count']>0).sum()} quality issues detected. Address in SurveyCTO source data.")
    else:
        st.success("✅ All logic checks passed.")

with tab2:
    section("GPS Coverage by Dataset","teal")
    gps_summary=[]
    for name,df,lat_col in [
        ("Survivor Intake",sv_e,"lat"),("Perpetrator Tool",pp,"lat"),
        ("Outreach Tool",ot,"lat"),("School Social Work",sc,"lat")]:
        if lat_col in df.columns:
            valid=df[lat_col].notna().sum(); total=len(df)
            gps_summary.append({"Dataset":name,"Valid GPS":valid,"Total":total,
                                  "Coverage %":round(100*valid/max(total,1),1)})
    gps_df=pd.DataFrame(gps_summary)
    col1,col2=st.columns(2)
    with col1:
        fig=px.bar(gps_df,x="Coverage %",y="Dataset",orientation="h",
                   color="Coverage %",color_continuous_scale="RdYlGn",
                   height=280,template="plotly_white",title="GPS Coverage by Dataset",
                   text="Coverage %")
        fig.update_traces(texttemplate="%{text:.1f}%",textposition="outside")
        fig.update_layout(margin=dict(l=150,r=16,t=48,b=36),yaxis_range=[-0.5,len(gps_df)-0.5],
                          xaxis_range=[0,110],showlegend=False)
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.dataframe(gps_df,use_container_width=True,hide_index=True)

with tab3:
    section("Submission Volume Over Time","orange")
    if "date" in sv_e.columns:
        sub_d=sv_e.groupby(sv_e["date"].dt.date)["client_id"].count().reset_index()
        sub_d.columns=["Date","Submissions"]
        fig=px.bar(sub_d,x="Date",y="Submissions",color_discrete_sequence=[C["purple"]],
                   height=280,template="plotly_white",title="Daily Submission Volume — Survivor Tool")
        fig.update_layout(margin=dict(l=36,r=16,t=48,b=36))
        st.plotly_chart(fig,use_container_width=True)

    section("Submission Lag Analysis","teal")
    if "date" in sv_e.columns:
        sub_m=sv_e.groupby("month_label")["client_id"].count().reset_index()
        sub_m.columns=["Month","Submissions"]; sub_m=sub_m.sort_values("Month")
        fig2=go.Figure()
        fig2.add_trace(go.Bar(x=sub_m["Month"],y=sub_m["Submissions"],marker_color=C["teal"],name="Submissions"))
        fig2.add_hline(y=sub_m["Submissions"].mean(),line_dash="dash",line_color=C["orange"],
                       annotation_text=f"Avg: {sub_m['Submissions'].mean():.0f}/month")
        fig2.update_layout(template="plotly_white",height=260,title="Monthly Submission Volume",
                           margin=dict(l=36,r=16,t=48,b=36))
        st.plotly_chart(fig2,use_container_width=True)

    section("Enumerator Performance","purple")
    if "officer_name_tracking" in pp.columns or "officer_name" in pp.columns:
        enum_col=next((c for c in ["officer_name_tracking","officer_name","SGBV_staff_label"] if c in pp.columns),None)
        if enum_col:
            enum_perf=pp.groupby(enum_col).agg(submissions=("client_id","count")).reset_index()
            enum_perf=enum_perf.sort_values("submissions",ascending=False).head(15)
            enum_perf.columns=["Enumerator","Submissions"]
            fig3=px.bar(enum_perf,x="Submissions",y="Enumerator",orientation="h",
                        color_discrete_sequence=[C["purple"]],height=380,template="plotly_white",
                        title="Top 15 Enumerators by Submission Count — Perpetrator Tool")
            fig3.update_layout(margin=dict(l=180,r=16,t=48,b=36))
            st.plotly_chart(fig3,use_container_width=True)