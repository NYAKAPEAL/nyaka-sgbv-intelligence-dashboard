"""pages/1_Survivors.py — Full survivor case management and demographics"""
import streamlit as st, pandas as pd, plotly.express as px
import plotly.graph_objects as go, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from config import C, TARGETS, VIOLENCE_COLORS
from utils.auth import check, sidebar_panel, can_access
from utils.data_loader import load_all, apply_filters, load_perp_narrative
from utils.viz import (kpi,section,page_header,safe_notice,bar_h,bar_v,
                       donut,gauge,heatmap_chart,line_area,funnel,sankey,pyramid)
MH_COLORS = {"Normal":C["green"],"Mild Depression":C["gold"],"Moderate Depression":C["orange"],"Severe Depression":C["red"]}

if not check(): st.warning("Please log in."); st.stop()
if not can_access("survivors"): st.error("🔒 Access denied."); st.stop()

DATA = load_all()
sv=DATA["survivors"]
sidebar_panel()
st.sidebar.markdown("---")
yrs = sorted(sv["year"].dropna().unique().astype(int).tolist()) if len(sv) else [2022,2023,2024,2025,2026]
sel_yrs = st.sidebar.multiselect("Year",yrs,default=yrs,key="sv_yr")
sel_dist = st.sidebar.selectbox("District",["All","Kanungu","Rukungiri","Rubanda"],key="sv_d")
filt = {"years":sel_yrs,"district":sel_dist}
sv_f = apply_filters(sv,filt)
sv_e = sv_f[sv_f.get("report_category","").str.contains("enrollment",na=False)]

page_header("Survivor Case Management","Enrollment · demographics · case tracking · mental health · safe living","👤")
safe_notice()

total=len(sv_e)
children=int(sv_e.get("is_child",pd.Series(dtype=bool)).sum())
female=int((sv_e.get("client_gender","")=="F").sum())
crisis=int(sv_e.get("has_crisis",pd.Series(dtype=bool)).sum())

c=st.columns(4)
for col,(lbl,val,clr,icon,note) in zip(c,[
    ("Total Enrolled",f"{total:,}","purple","👤",f"Target: {TARGETS['survivors_enrolled']:,}"),
    ("Children (<18)",f"{children:,}","orange","🧒",f"{round(100*children/max(total,1),0):.0f}%"),
    ("Female Survivors",f"{female:,}","teal","♀",f"{round(100*female/max(total,1),0):.0f}% of total"),
    ("Crisis-Flagged",f"{crisis:,}","red","🚨","Require urgent review"),
]):
    with col: st.markdown(kpi(lbl,val,color=clr,icon=icon,note=note),unsafe_allow_html=True)
st.markdown("<br/>",unsafe_allow_html=True)

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "📊 Case Status","👥 Demographics","⚡ Violence","💊 Mental Health","🔀 Case Flow"])

with tab1:
    section("Case Status Distribution","purple")
    col1,col2=st.columns(2)
    with col1:
        cs=sv_e.get("case_status_clean",pd.Series(["Active"]*total)).value_counts().reset_index()
        cs.columns=["Status","Count"]
        fig=go.Figure(go.Pie(labels=cs["Status"],values=cs["Count"],hole=0.55,
            marker=dict(colors=[C["purple"],C["green"],C["orange"],C["grey"],C["red"]],
                        line=dict(color="white",width=2)),
            textinfo="label+percent",textfont=dict(size=10)))
        fig.update_layout(template="plotly_white",height=300,margin=dict(l=36,r=16,t=48,b=36),
                          title="Case Status",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        monthly=sv_e.groupby("month_label")["client_id"].count().reset_index()
        monthly.columns=["Month","Cases"]; monthly=monthly.sort_values("Month").tail(30)
        st.plotly_chart(line_area(monthly,"Month","Cases","Monthly Enrollment Trend",h=300),use_container_width=True)

    section("Healing Centre Comparison","orange")
    hc_col=next((c for c in sv_e.columns if "healing_center_label" in c),None)
    if hc_col:
        hc=sv_e.groupby(hc_col)["client_id"].count().reset_index(); hc.columns=["Centre","Count"]
        by_yr=sv_e.groupby(["year",hc_col])["client_id"].count().reset_index(); by_yr.columns=["Year","Centre","Count"]
        fig2=px.bar(by_yr.sort_values("Year"),x="Year",y="Count",color="Centre",barmode="group",
                    height=300,template="plotly_white",title="Enrollments by Centre & Year",
                    color_discrete_sequence=[C["purple"],C["orange"],C["gold"],C["teal"],C["blue"]])
        fig2.update_layout(margin=dict(l=36,r=16,t=48,b=36),legend=dict(orientation="h",y=1.08))
        st.plotly_chart(fig2,use_container_width=True)

    section("Programme Indicators","gold")
    st.caption("Computed from survivor records. Some indicators depend on fields "
               "that are still being captured consistently in the field tools — "
               "these are labelled so the figure isn't misread.")
    g1,g2,g3=st.columns(3)

    # GPS capture rate — fully supported by the data (a real data-quality metric)
    gps_rate = round(100*(sv_e["lat"].notna()&sv_e["lon"].notna()).sum()/max(total,1),1) \
               if "lat" in sv_e.columns else 0.0

    # Medical report completion — share of records with a medical report filed
    medreport = 0
    if "report_category" in sv.columns:
        med_ids = sv[sv["report_category"].str.contains("medreport",na=False)]
        medreport = len(med_ids)
    med_rate = round(100*medreport/max(total,1),1)

    # Referral rate — only where referral was actually recorded
    ref_filled = sv_e["referral_label"].notna().sum() if "referral_label" in sv_e.columns else 0
    ref_yes = (sv_e.get("referral_label","")=="Yes").sum() if "referral_label" in sv_e.columns else 0
    ref_rate = round(100*ref_yes/max(ref_filled,1),1) if ref_filled else 0.0

    with g1:
        st.plotly_chart(gauge(gps_rate,"GPS Capture Rate",100,
                              TARGETS.get("gps_capture",80),230),use_container_width=True)
        st.caption(f"{(sv_e['lat'].notna()&sv_e['lon'].notna()).sum():,} of {total:,} "
                   "enrollments have GPS — supports mapping & distance analysis.")
    with g2:
        st.plotly_chart(gauge(med_rate,"Medical Report Rate",100,
                              TARGETS.get("medical_report",60),230),use_container_width=True)
        st.caption(f"{medreport:,} medical reports filed. Low values may reflect "
                   "under-recording in the tool rather than missed exams.")
    with g3:
        st.plotly_chart(gauge(ref_rate,"Referral Rate",100,
                              TARGETS.get("referral_rate",70),230),use_container_width=True)
        st.caption(f"Of {ref_filled:,} cases where referral was recorded, "
                   f"{ref_yes:,} were referred. Referral field is filled for "
                   f"{round(100*ref_filled/max(total,1))}% of cases.")

    st.markdown(f"""
    <div style='background:{C["amber_lt"]};border-left:3px solid {C["amber"]};
                border-radius:4px;padding:8px 12px;font-size:11px;color:#5A3000;
                margin-top:8px;'>
      ⏳ <strong>Note on follow-up & case-closure rates:</strong> these were
      removed from this view because the survivor enrollment and follow-up records
      cannot currently be linked (the follow-up tool's client ID field is not being
      populated). Once that link is captured in the field tool, follow-up and
      closure rates can be shown here reliably. Case ageing for perpetrator cases
      is available on the Narratives page.
    </div>""", unsafe_allow_html=True)

with tab2:
    section("Gender & Age Distribution","purple")
    col1,col2=st.columns(2)
    with col1:
        gd=sv_e.get("client_gender",pd.Series(dtype=str)).value_counts().reset_index()
        gd.columns=["Gender","Count"]
        gd["Gender"]=gd["Gender"].map({"F":"Female","M":"Male"}).fillna("Unknown")
        fig=go.Figure(go.Pie(labels=gd["Gender"],values=gd["Count"],hole=0.6,
            marker=dict(colors=[C["orange"],C["blue"],C["grey"]],line=dict(color="white",width=2)),
            textinfo="label+percent",textfont=dict(size=11)))
        fig.update_layout(template="plotly_white",height=280,margin=dict(l=36,r=16,t=48,b=36),
                          title="Gender Distribution",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        ag=sv_e.get("client_age_group",pd.Series(dtype=str)).value_counts().sort_index().reset_index()
        ag.columns=["Age Group","Count"]
        st.plotly_chart(bar_v(ag,"Age Group","Count","Age Group Distribution",C["purple"],h=280),use_container_width=True)

    section("Age-Sex Pyramid","orange")
    age_grps=["0-5","6-10","11-15","16-17","18-25","26-29","30-35","36+"]
    male_c=[]; female_c=[]
    age_num=pd.to_numeric(sv_e.get("client_age",pd.Series()),errors="coerce")
    bins=[(0,5),(6,10),(11,15),(16,17),(18,25),(26,29),(30,35),(36,120)]
    for lo,hi in bins:
        g=sv_e[(age_num>=lo) & (age_num<=hi)]
        male_c.append(int((g.get("client_gender","")=="M").sum()))
        female_c.append(int((g.get("client_gender","")=="F").sum()))
    st.plotly_chart(pyramid(age_grps,male_c,female_c,"Age-Sex Distribution of Survivors",h=380),use_container_width=True)

    section("District × Age Group Heatmap","teal")
    ct=pd.crosstab(sv_e.get("district","Unknown"),sv_e.get("client_age_group","Unknown"))
    if len(ct):
        st.plotly_chart(heatmap_chart(ct.values.tolist(),ct.columns.tolist(),ct.index.tolist(),
                                       "District × Age Group",h=280),use_container_width=True)

with tab3:
    section("Violence Type Analysis","red")
    col1,col2=st.columns(2)
    with col1:
        vt=sv_e.get("assault_label",pd.Series(dtype=str)).value_counts().reset_index()
        vt.columns=["Type","Count"]
        clrs=[VIOLENCE_COLORS.get(t,C["grey"]) for t in vt["Type"]]
        fig=go.Figure(go.Pie(labels=vt["Type"],values=vt["Count"],hole=0.55,
            marker=dict(colors=clrs,line=dict(color="white",width=2)),
            textinfo="label+percent",textfont=dict(size=10)))
        fig.update_layout(template="plotly_white",height=300,margin=dict(l=36,r=16,t=48,b=36),
                          title="Violence Types",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        vt2=sv_e.get("assault_label",pd.Series(dtype=str)).value_counts().head(8).reset_index()
        vt2.columns=["Type","Count"]
        clrs2=[VIOLENCE_COLORS.get(t,C["grey"]) for t in vt2["Type"]]
        fig2=px.bar(vt2.sort_values("Count"),x="Count",y="Type",orientation="h",
                    color="Type",color_discrete_map=VIOLENCE_COLORS,height=300,
                    template="plotly_white",title="Frequency by Type")
        fig2.update_layout(margin=dict(l=180,r=16,t=48,b=36),showlegend=False)
        st.plotly_chart(fig2,use_container_width=True)

    section("Violence Trends Over Time","orange")
    top5=sv_e.get("assault_label","").value_counts().head(5).index.tolist()
    vt_m=sv_e[sv_e.get("assault_label","").isin(top5)].groupby(["month_label","assault_label"])["client_id"].count().reset_index()
    vt_m.columns=["Month","Type","Count"]; vt_m=vt_m.sort_values("Month")
    fig3=px.line(vt_m,x="Month",y="Count",color="Type",markers=True,
                 height=300,template="plotly_white",title="Top 5 Violence Types — Monthly",
                 color_discrete_map=VIOLENCE_COLORS)
    fig3.update_layout(margin=dict(l=36,r=16,t=48,b=36),legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig3,use_container_width=True)

    section("Violence × District Heatmap","purple")
    ct2=pd.crosstab(sv_e.get("assault_label",""),sv_e.get("district",""))
    if len(ct2):
        st.plotly_chart(heatmap_chart(ct2.values.tolist(),ct2.columns.tolist(),ct2.index.tolist(),
                                       "Violence Type × District",h=300),use_container_width=True)

with tab4:
    section("Mental Health — Depression & PTSD","purple")
    st.caption("Depression is recorded for every survivor through the programme's symptom "
               "scale. PTSD (CRIES-8 for children, HTQ for adults) is captured by the updated "
               "tool and builds up as new assessments are recorded. Lower scores are better.")

    def _pct(v):
        try: return float(str(v).strip())
        except Exception: return None
    def _dep_band(p):
        if p is None: return None
        if p < 25: return "Normal"
        if p < 50: return "Mild"
        if p < 75: return "Moderate"
        return "Severe"
    BAND_CLR={"Normal":C["green"],"Mild":C["gold"],"Moderate":C["orange"],"Severe":C["red"]}
    BAND_ORDER=["Normal","Mild","Moderate","Severe"]

    dep = sv_e["depression_percent"].apply(_pct) if "depression_percent" in sv_e.columns else pd.Series(dtype=float)
    dep_band = dep.apply(_dep_band).dropna()

    col1,col2=st.columns(2)
    with col1:
        if len(dep_band):
            vc=dep_band.value_counts().reindex(BAND_ORDER).dropna()
            fig=go.Figure(go.Pie(labels=list(vc.index),values=[int(v) for v in vc.values],hole=0.55,
                marker=dict(colors=[BAND_CLR[b] for b in vc.index],line=dict(color="white",width=2)),
                textinfo="label+percent",textfont=dict(size=10)))
            fig.update_layout(template="plotly_white",height=280,margin=dict(l=36,r=16,t=48,b=36),
                              title="Depression profile at enrollment",paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("No depression scores available yet.")
    with col2:
        date_src=next((c for c in ["date_enrolled","survey_date"] if c in sv_e.columns),None)
        if len(dep_band) and date_src:
            tmp=pd.DataFrame({"Category":dep_band.values,
                              "Month":pd.to_datetime(sv_e.loc[dep_band.index,date_src],
                                                     errors="coerce").dt.to_period("M").astype(str)})
            tmp=tmp[tmp["Month"]!="NaT"]
            mh_t=tmp.groupby(["Month","Category"]).size().reset_index(name="Count").sort_values("Month")
            if len(mh_t):
                fig2=px.area(mh_t,x="Month",y="Count",color="Category",
                             title="Depression band trend (enrollment)",height=280,
                             template="plotly_white",color_discrete_map=BAND_CLR,
                             category_orders={"Category":BAND_ORDER})
                fig2.update_layout(margin=dict(l=36,r=16,t=48,b=36),legend=dict(orientation="h",y=1.08))
                st.plotly_chart(fig2,use_container_width=True)
        else:
            st.caption("Trend appears once dated depression scores are available.")

    if "pre_ptsd_percent" in sv_e.columns:
        ptsd=sv_e["pre_ptsd_percent"].apply(_pct).dropna()
        if len(ptsd):
            pos=int((ptsd>=42).sum())
            st.markdown(f"<div style='background:{C['purple_xlt']};border-radius:6px;padding:9px 14px;"
                        f"font-size:12px;color:{C['dark']};margin-top:8px;'>"
                        f"<strong>PTSD screened (updated tool):</strong> {len(ptsd):,} survivors &middot; "
                        f"{pos:,} at or above the screening threshold. CRIES-8 is used for children, "
                        f"HTQ for adults.</div>",unsafe_allow_html=True)
        else:
            st.caption("PTSD screening data is accumulating from the updated tool.")
    else:
        st.caption("PTSD screening (CRIES-8 / HTQ) accrues from the updated tool; "
                   "no scores recorded in the current data yet.")

    section("Crisis flags — safeguarding","red")
    st.info("Survivors who report frequent suicidal feelings at intake are surfaced here for "
            "safeguarding follow-up. A flag is a referral trigger for the case team, not a diagnosis.")
    if "suicidal" in sv_e.columns:
        sui=pd.to_numeric(sv_e["suicidal"],errors="coerce")
        high=int((sui>=4).sum()); some=int((sui==3).sum()); screened=int(sui.notna().sum())
        c1,c2,c3=st.columns(3)
        c1.metric("High concern (frequent)",f"{high:,}")
        c2.metric("Some concern",f"{some:,}")
        c3.metric("Screened",f"{screened:,}")
        st.caption("High concern = top two response levels on the intake suicidal-feelings item.")
    else:
        st.caption("Suicidal-ideation item not present in the current data.")


with tab5:
    section("Survivor Journey Flow","purple")
    st.caption("Case flow from violence type through healing centre to case outcome.")
    hc_col2=next((c for c in sv_e.columns if "healing_center_label" in c),None)
    if hc_col2:
        intake=sv_e[["assault_cat","client_gender",hc_col2]].dropna()
        intake["gender_lbl"]=intake["client_gender"].map({"F":"Female","M":"Male"}).fillna("Unknown")
        vt_n=intake["assault_cat"].unique().tolist()
        hc_n=intake[hc_col2].unique().tolist()
        all_n=vt_n+hc_n; idx={l:i for i,l in enumerate(all_n)}
        srcs,tgts,vals=[],[],[]
        for (a,b),cnt in intake.groupby(["assault_cat",hc_col2]).size().items():
            if a in idx and b in idx:
                srcs.append(idx[a]); tgts.append(idx[b]); vals.append(int(cnt))
        if srcs:
            st.plotly_chart(sankey(all_n,srcs,tgts,vals,"Violence Category → Healing Centre",h=440),use_container_width=True)

    section("Case Progression Funnel","orange")
    # Per-case progression from the live rollup (not fabricated ratios).
    _cn = load_perp_narrative()
    # scope the rollup to the same cases currently in view, if filterable by client_id
    if "client_id" in sv_e.columns and "client_id" in _cn.columns:
        _cn = _cn[_cn["client_id"].astype(str).isin(set(sv_e["client_id"].astype(str)))]
    tot = len(_cn) if len(_cn) else len(sv_e)
    fu  = int((_cn.get("n_followups", pd.Series(dtype=float)) > 0).sum())
    closed = int(_cn.get("is_closed", pd.Series(dtype=bool)).fillna(False).sum())
    st.plotly_chart(funnel(
        ["Survivors Enrolled","Received Follow-up","Case Formally Closed"],
        [tot,fu,closed],"Survivor Service Pathway",h=320),use_container_width=True)
    st.caption("Distinct survivor cases (not follow-up visits). 'Received follow-up' is cases with "
               "at least one logged follow-up; 'closed' is cases with a closing status.")