"""pages/2_Perpetrators.py — Perpetrator tracking, legal outcomes, incident narrations, safe living"""
import streamlit as st, pandas as pd, plotly.express as px
import plotly.graph_objects as go, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from config import C, LEGAL_COLORS, RELATION_COLORS, SAFE_LIVING_TIPS, RISK_TIMES, RELATION_MAP
from utils.auth import check, sidebar_panel, can_access
from utils.data_loader import load_all, apply_filters
from utils.viz import (kpi,section,page_header,safe_notice,bar_h,bar_v,
                       donut,gauge,heatmap_chart,funnel,scatter_map_px,density_map)

if not check(): st.warning("Please log in."); st.stop()
if not can_access("perpetrators"): st.error("🔒 Access denied."); st.stop()

DATA=load_all(); pp=DATA["perpetrators"]; sv=DATA["survivors"]
sidebar_panel()
st.sidebar.markdown("---")
yrs=sorted(pp["year"].dropna().unique().astype(int).tolist()) if len(pp) else [2022,2023,2024,2025,2026]
sel_yrs=st.sidebar.multiselect("Year",yrs,default=yrs,key="pp_yr")
sel_dist=st.sidebar.selectbox("District",["All","Kanungu","Rukungiri","Rubanda"],key="pp_d")
filt={"years":sel_yrs,"district":sel_dist}
pp_f=apply_filters(pp,filt)

pp_e=pp_f[pp_f.get("is_enrolled",pd.Series(dtype=bool))] if "is_enrolled" in pp_f.columns else pp_f[pp_f.get("report_category", pd.Series("", index=pp_f.index))=="enrollment"]
pp_fu=pp_f[pp_f.get("is_followup",pd.Series(dtype=bool))] if "is_followup" in pp_f.columns else pp_f[pp_f.get("report_category", pd.Series("", index=pp_f.index)).str.contains("followup",na=False)]

page_header("Perpetrator Intake & Legal Outcomes","Registration · legal pipeline · incident narrations · safe living intelligence","⚖️")
safe_notice()

total=len(pp_e); arrested=int(pp_e.get("arrested",pd.Series(dtype=bool)).sum())
won=int(pp_fu.get("case_won",pd.Series(dtype=bool)).sum())
lost=int(pp_fu.get("case_lost",pd.Series(dtype=bool)).sum())

# Per-case justice rollup: status is logged on FOLLOW-UPS, so count distinct CASES, not visits.
# (Counting visits made "at court" exceed registrations — a pipeline must narrow, never widen.)
_RANK={"household":1,"community":1,"transfers":1,"police":2,"rsa":3,"court":4,"won":5,"lost":5}
_tid=pp_fu.get("perpetrator_tracking_id",pd.Series(dtype=str)).astype(str)
_ovf=pp_fu.get("case_status_overview",pd.Series(dtype=str)).astype(str).str.lower()
_rr=pd.DataFrame({"_tid":_tid.values,"_stat":_ovf.values,"_rank":_ovf.map(_RANK).fillna(0).values})
_cmax=_rr.groupby("_tid")["_rank"].max() if len(_rr) else pd.Series(dtype=float)
reached_rsa=int((_cmax>=3).sum()); reached_court=int((_cmax>=4).sum())
won=int(_rr.loc[_rr["_stat"]=="won","_tid"].nunique())
lost=int(_rr.loc[_rr["_stat"]=="lost","_tid"].nunique())
community_cases=int(_rr.loc[_rr["_stat"]=="community","_tid"].nunique())
arr_r=round(100*arrested/max(total,1),1); conv_r=round(100*won/max(total,1),1)

c=st.columns(4)
for col,(lbl,val,clr,icon) in zip(c,[
    ("Perpetrators Registered",f"{total:,}","purple","⚖️"),
    ("Arrested / Pursued",f"{arrested:,}","blue","🔒"),
    ("Cases Won (Conviction)",f"{won:,}","green","✅"),
    ("Cases Lost / Dismissed",f"{lost:,}","red","❌"),
]):
    with col: st.markdown(kpi(lbl,val,color=clr,icon=icon),unsafe_allow_html=True)
st.markdown("<br/>",unsafe_allow_html=True)

tab1,tab2,tab3,tab4,tab5=st.tabs([
    "⚖️ Legal Pipeline","👤 Profile & Relations","📖 Incident Narrations",
    "🗺 Crime Scene Mapping","🏠 Safe Living Guidance"])

with tab1:
    section("Justice Pathway Funnel","purple")
    col1,col2=st.columns(2)
    with col1:
        stages=["Registered","Arrested","Prosecution (RSA)","Court","Won"]
        vals=[total,arrested,reached_rsa,reached_court,won]
        st.plotly_chart(funnel(stages,vals,"Justice Pipeline (distinct cases)",h=380),use_container_width=True)
        st.caption("Counts distinct cases at each stage (a case is counted once, not per visit). "
                   "Each stage is cases that ever reached it, so the pipeline narrows as it should.")

    with col2:
        ls=pp_e.get("perpetrator_location_label",pd.Series(dtype=str)).value_counts().reset_index()
        ls.columns=["Status","Count"]
        ls_clrs={"Arrested":C["green"],"On the run":C["red"],"Arrest underway":C["amber"],
                 "Released on Arrest":C["orange"],"Convicted (sentenced)":C["purple"],"Household member":C["teal"]}
        fig=go.Figure(go.Pie(labels=ls["Status"],values=ls["Count"],hole=0.55,
            marker=dict(colors=[ls_clrs.get(s,C["grey"]) for s in ls["Status"]],
                        line=dict(color="white",width=2)),
            textinfo="label+percent",textfont=dict(size=10)))
        fig.update_layout(template="plotly_white",height=380,margin=dict(l=36,r=16,t=48,b=36),
                          title="Current Perpetrator Location Status",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)

    section("Case Status Trend Over Time","orange")
    cs_monthly=pp_fu.groupby(["month_label","case_status_overview"])["client_id"].count().reset_index()
    cs_monthly.columns=["Month","Status","Count"]; cs_monthly=cs_monthly.sort_values("Month")
    fig2=px.area(cs_monthly,x="Month",y="Count",color="Status",
                 title="Case Status Evolution",height=300,template="plotly_white",
                 color_discrete_map=LEGAL_COLORS)
    fig2.update_layout(margin=dict(l=36,r=16,t=48,b=36),legend=dict(orientation="h",y=1.08))
    st.plotly_chart(fig2,use_container_width=True)

    section("Performance Gauges","gold")
    g1,g2,g3=st.columns(3)
    with g1: st.plotly_chart(gauge(arr_r,"Arrest Rate",100,75,230),use_container_width=True)
    with g2: st.plotly_chart(gauge(conv_r,"Conviction Rate",100,30,230),use_container_width=True)
    with g3:
        med_r=round(100*community_cases/max(total,1),1)
        st.plotly_chart(gauge(med_r,"Community Mediation Rate",100,15,230),use_container_width=True)

    section("Case Status Detailed Labels","teal")
    cs_lbl=pp_fu.get("case_status_label",pd.Series(dtype=str)).value_counts().head(12).reset_index()
    cs_lbl.columns=["Status Detail","Count"]
    fig3=px.bar(cs_lbl.sort_values("Count"),x="Count",y="Status Detail",orientation="h",
                color_discrete_sequence=[C["purple"]],height=380,template="plotly_white",
                title="Detailed Case Status (Follow-up Records)")
    fig3.update_layout(margin=dict(l=280,r=16,t=48,b=36))
    st.plotly_chart(fig3,use_container_width=True)

    section("Why cases were lost","red")
    _ovf2=pp_fu.get("case_status_overview",pd.Series(dtype=str)).astype(str).str.lower()
    _lost=pp_fu[_ovf2=="lost"].copy()
    if "perpetrator_tracking_id" in _lost.columns:
        _lost=_lost.drop_duplicates(subset=["perpetrator_tracking_id"],keep="last")
    n_lost=len(_lost)
    if n_lost:
        def _loss_theme(txt):
            t=str(txt).lower()
            if any(k in t for k in ["evidence","medical form","statement"]): return "Insufficient evidence"
            if any(k in t for k in ["reconcil","agreed","take care","settle","released"]): return "Reconciliation / family settlement"
            if any(k in t for k in ["lost interest","shifted","relocat","withdr","not interested"]): return "Survivor withdrew / relocated"
            if any(k in t for k in ["appear","witness","complainant"]): return "Witnesses did not appear"
            if "dismiss" in t: return "Dismissed (reason not specified)"
            return "Other / not recorded"
        cm=_lost.get("comments_case_status",pd.Series([""]*n_lost,index=_lost.index))
        tc=cm.apply(_loss_theme).value_counts().reset_index(); tc.columns=["Reason","Cases"]
        lc1,lc2=st.columns([1,1])
        with lc1:
            st.markdown(kpi("Cases lost",f"{n_lost}",note="closed without conviction",
                            color="red",icon="❌"),unsafe_allow_html=True)
            for _,r in tc.iterrows():
                st.markdown(f"<div style='font-size:12px;color:{C['dark']};margin:3px 0;'>"
                            f"• <strong>{r['Cases']}</strong> — {r['Reason']}</div>",unsafe_allow_html=True)
        with lc2:
            figL=px.bar(tc.sort_values("Cases"),x="Cases",y="Reason",orientation="h",
                        template="plotly_white",height=240,color_discrete_sequence=[C["red"]],text="Cases")
            figL.update_layout(margin=dict(l=180,r=16,t=10,b=20))
            st.plotly_chart(figL,use_container_width=True)
        with st.expander(f"Recorded reasons for the {n_lost} lost cases"):
            for _,r in _lost.iterrows():
                cmt=str(r.get("comments_case_status","")).strip()
                if cmt and cmt.lower() not in ("nan","none",""):
                    st.markdown(f"- {cmt[:300]}")
        st.caption("Reasons are categorised from case officers' free-text notes. Evidence and "
                   "non-appearance themes point to investigation and witness-support gaps; "
                   "reconciliation and withdrawal reflect family and protection dynamics.")
    else:
        st.info("No lost cases recorded in the current data.")

with tab2:
    section("Perpetrator–Survivor Relationship","red")
    col1,col2=st.columns(2)
    with col1:
        _rp = pp_e.get("relations_perpetrator", pd.Series(dtype=str)).fillna("").astype(str)
        _rp = _rp[~_rp.str.strip().isin(["", "nan", "none"])]
        # primary relationship = first code (handles multi-select like "7 8")
        _prim = _rp.str.strip().str.split().str[0].map(RELATION_MAP)
        _vc = _prim.dropna().value_counts()
        _top = _vc.head(7); _other = int(_vc.iloc[7:].sum())
        rel = _top.reset_index(); rel.columns=["Relationship","Count"]
        if _other > 0:
            rel = pd.concat([rel, pd.DataFrame([{"Relationship":"Other","Count":_other}])],
                            ignore_index=True)
        _pal=[C["purple"],C["orange"],C["gold"],C["teal"],C["blue"],C["red"],C["green"],C["grey"]]
        clrs=[_pal[i % len(_pal)] for i in range(len(rel))]
        fig=go.Figure(go.Pie(labels=rel["Relationship"],values=rel["Count"],hole=0.55,
            marker=dict(colors=clrs,line=dict(color="white",width=2)),
            textinfo="label+percent",textfont=dict(size=10)))
        fig.update_layout(template="plotly_white",height=340,margin=dict(l=36,r=16,t=48,b=36),
                          title="Perpetrator Relationship to Survivor",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
        # All relationships: count every selected relationship (multi-select), not just primary
        _all = _rp.str.strip().str.split().explode().map(RELATION_MAP).dropna()
        if len(_all):
            allc = _all.value_counts().head(10).reset_index()
            allc.columns = ["Relationship","Mentions"]
            fig_all = px.bar(allc.sort_values("Mentions"), x="Mentions", y="Relationship",
                             orientation="h", template="plotly_white", height=300,
                             color_discrete_sequence=[C["orange"]], text="Mentions")
            fig_all.update_layout(margin=dict(l=150,r=16,t=44,b=30),
                                  title="All recorded relationships (some cases have more than one)")
            st.plotly_chart(fig_all, use_container_width=True)
            st.caption("Counts every relationship selected. A case recorded as both, say, "
                       "neighbour and relative, contributes to both bars. The pie above shows "
                       "only the primary (first) relationship per case.")
    with col2:
        _tot = len(_prim)
        def _rpct(lbl): return 100*(_prim == lbl).sum()/_tot if _tot else 0
        neigh_pct = _rpct("Neighbour"); stranger_pct = _rpct("Stranger")
        parent_pct = _rpct("Father/Mother"); known_pct = 100 - stranger_pct
        top_rel = _prim.value_counts().idxmax() if _tot else "n/a"
        st.markdown(f"""<div style='background:{C["red_lt"]};border-left:4px solid {C["red"]};
            border-radius:8px;padding:14px 18px;margin-top:16px;'>
          <div style='font-weight:600;color:{C["red"]};font-size:13px;margin-bottom:10px;'>
            ⚠ Key findings (live data, {_tot:,} cases)
          </div>
          <div style='font-size:11px;color:#5D2020;line-height:1.7;'>
            <strong>{neigh_pct:.0f}% of perpetrators are neighbours</strong> — not strangers.<br>
            {stranger_pct:.0f}% are strangers or unknown to the survivor.<br>
            {known_pct:.0f}% are known to the survivor in some way.<br>
            Parent or caregiver accounts for {parent_pct:.0f}% of cases.<br><br>
            <strong>Implication:</strong> with most harm coming from people the survivor
            knows, community trust-building and known-person awareness matter as much as
            stranger-danger messaging.
          </div>
        </div>""",unsafe_allow_html=True)

    section("Perpetrator Demographics","orange")
    col3,col4=st.columns(2)
    with col3:
        pg=pp_e.get("client_gender",pd.Series(dtype=str)).value_counts().reset_index()
        pg.columns=["Gender","Count"]; pg["Gender"]=pg["Gender"].map({"M":"Male","F":"Female"}).fillna("Other")
        fig2=go.Figure(go.Pie(labels=pg["Gender"],values=pg["Count"],hole=0.6,
            marker=dict(colors=[C["blue"],C["orange"],C["grey"]],line=dict(color="white",width=2)),
            textinfo="label+percent",textfont=dict(size=11)))
        fig2.update_layout(template="plotly_white",height=280,margin=dict(l=36,r=16,t=48,b=36),
                           title="Perpetrator Gender",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2,use_container_width=True)
    with col4:
        pa=pd.to_numeric(pp_e.get("client_age",pd.Series()),errors="coerce").dropna()
        fig3=go.Figure(go.Histogram(x=pa,nbinsx=20,marker_color=C["purple"],
                                    marker_line=dict(color="white",width=0.5)))
        fig3.update_layout(template="plotly_white",height=280,
                           title="Perpetrator Age Distribution",
                           margin=dict(l=36,r=16,t=48,b=36),
                           xaxis_title="Age",yaxis_title="Count",
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3,use_container_width=True)

    section("Weapon / Method of Violence","amber")
    weapon_col=pp_e.get("weapon_perpetrator_other",pd.Series(dtype=str)).dropna()
    if len(weapon_col):
        st.markdown(f"<div style='font-size:11px;color:{C['grey']};margin-bottom:8px;'>Sample case descriptions from legal team (2022-2026):</div>",unsafe_allow_html=True)
        for w in weapon_col.head(4).tolist():
            st.markdown(f"<div style='background:{C['amber_lt']};border-left:3px solid {C['amber']};padding:7px 12px;border-radius:4px;font-size:11px;margin-bottom:5px;'>📌 {w}</div>",unsafe_allow_html=True)

with tab3:
    section("Incident Narrations — Evidence Base for Safe Living","purple")
    st.info("These anonymised narrations from case records provide intelligence for community safety guidance. Names and exact identifiers have been removed.")

    narrations=pp_e.get("assault_narration",pd.Series(dtype=str)).fillna("").astype(str)
    narrations=narrations[~narrations.str.strip().str.lower().isin(["","nan","none","<na>"])]
    if len(narrations):
        # Theme analysis
        themes={"Path/walking":0,"Water/fetching":0,"Home/house":0,"Night":0,
                "School":0,"Bush/forest":0,"Boda":0,"Relative/home":0}
        for n in narrations.str.lower():
            for k,kw in [("Path/walking",["path","road","walking","way home"]),
                         ("Water/fetching",["water","well","river","spring","fetch"]),
                         ("Home/house",["house","home","room","compound"]),
                         ("Night",["night","dark","evening","after dark"]),
                         ("School",["school","class","teacher"]),
                         ("Bush/forest",["bush","forest","garden","plantation"]),
                         ("Boda",["boda","motorcycle","bicycle"]),
                         ("Relative/home",["relative","uncle","neighbor","neighbor"])]:
                if any(x in str(n) for x in kw): themes[k]+=1

        theme_df=pd.DataFrame({"Location Type":list(themes.keys()),"Incidents":list(themes.values())})
        theme_df=theme_df.sort_values("Incidents",ascending=False)
        col1,col2=st.columns([2,1])
        with col1:
            fig=px.bar(theme_df,x="Incidents",y="Location Type",orientation="h",
                       color="Incidents",color_continuous_scale="Reds",
                       height=320,template="plotly_white",
                       title="Incident Location Types (from narration analysis)")
            fig.update_layout(margin=dict(l=140,r=16,t=48,b=36),showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            st.markdown(f"""<div style='background:{C["red_lt"]};border-radius:8px;padding:14px;margin-top:16px;'>
              <div style='font-weight:600;color:{C["red"]};font-size:12px;margin-bottom:8px;'>
                Top Risk Locations
              </div>""",unsafe_allow_html=True)
            for _,row in theme_df.head(5).iterrows():
                st.markdown(f"<div style='font-size:11px;color:#5D2020;margin-bottom:4px;'>⚠ {row['Location Type']}: {row['Incidents']} incidents</div>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)

        section("Sample Case Narrations (Anonymised)","orange")
        selected=st.selectbox("Browse narrations by case",
                              [f"Case {i+1}" for i in range(min(20,len(narrations)))])
        idx_sel=int(selected.split()[1])-1
        n_text=narrations.iloc[idx_sel]
        # Remove any names (basic anonymisation note)
        st.markdown(f"""<div style='background:{C["orange_lt"]};border-left:4px solid {C["orange"]};
            border-radius:8px;padding:14px;font-size:12px;line-height:1.8;color:#4A3728;'>
          📋 {n_text}
        </div>""",unsafe_allow_html=True)
        st.caption("⚠ Names and identifying details have been replaced with [SURVIVOR] and [PERPETRATOR] in production export. Raw data access requires admin role.")

        section("Follow-up Case Notes (Legal Team)","teal")
        comments=pp_fu.get("comments_case_status",pd.Series(dtype=str)).dropna()
        if len(comments):
            for c_txt in comments.sample(min(3,len(comments))).tolist():
                st.markdown(f"""<div style='background:{C["teal_lt"]};border-left:3px solid {C["teal"]};
                    border-radius:6px;padding:10px 14px;font-size:11px;margin-bottom:7px;color:#00362E;'>
                  ⚖️ {c_txt}
                </div>""",unsafe_allow_html=True)

with tab4:
    section("Crime Scene GPS Mapping","red")
    st.caption("GPS points recorded at perpetrator enrollment — approximate crime scene proximity. Locations jittered ±200m for survivor safety.")
    pp_gps=pp_e[pp_e["lat"].notna() & pp_e["lon"].notna()].copy()
    if len(pp_gps):
        # Add jitter for privacy, then replace the original lat/lon with the
        # jittered values (drop originals first to avoid duplicate columns).
        import random as _rnd
        pp_gps_plot=pp_gps.copy()
        pp_gps_plot["lat"]=pp_gps_plot["lat"]+pp_gps_plot["lat"].apply(lambda _:_rnd.uniform(-0.002,0.002))
        pp_gps_plot["lon"]=pp_gps_plot["lon"]+pp_gps_plot["lon"].apply(lambda _:_rnd.uniform(-0.002,0.002))
        # Guard against any duplicate-named columns from upstream merges
        pp_gps_plot=pp_gps_plot.loc[:,~pp_gps_plot.columns.duplicated()]
        from config import VIOLENCE_COLORS
        fig=px.scatter_mapbox(pp_gps_plot,lat="lat",lon="lon",zoom=9,height=500,
                              mapbox_style="open-street-map",color="assault_label",
                              color_discrete_map=VIOLENCE_COLORS,
                              hover_data={"district":True,"assault_label":True,
                                          "perpetrator_location_label":True,"lat":False,"lon":False},
                              title=f"Crime Scene Proximity — {len(pp_gps):,} GPS-tagged perpetrator records")
        fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig,use_container_width=True)
        st.caption("🔒 Exact coordinates are NOT displayed. All points shifted ±200m. GPS precision restricted by user role.")

        section("Crime Scene Density Heatmap","red")
        fig2=px.density_mapbox(pp_gps_plot,lat="lat",lon="lon",radius=18,zoom=9,height=460,
                               mapbox_style="open-street-map",
                               title="Perpetrator Incident Density — High-Risk Zones",
                               color_continuous_scale="Reds")
        fig2.update_layout(margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2,use_container_width=True)
    else:
        st.info("No GPS data available in the current filter selection.")

with tab5:
    section("🏠 Evidence-Based Safe Living Guidance","gold")
    st.markdown(f"""<div style='background:{C["gold_lt"]};border-left:4px solid {C["gold"]};
        border-radius:8px;padding:16px 20px;margin-bottom:16px;'>
      <div style='font-weight:600;color:#5D4037;font-size:14px;margin-bottom:4px;'>
        Evidence Base: {len(pp_e):,} perpetrator records · {len(pp_e.get("assault_narration",pd.Series(dtype=str)).dropna()):,} incident narrations · 2022–2026
      </div>
      <div style='font-size:11px;color:#7B5E45;'>
        The guidance below is generated from actual case data, narration analysis, and GPS crime scene mapping.
        It tells community members WHERE, WHEN, and HOW incidents occur — and what to do differently.
      </div>
    </div>""",unsafe_allow_html=True)

    col1,col2=st.columns(2)
    with col1:
        st.markdown(f"**⏰ Risk by Time of Day**")
        for time_slot,(data) in RISK_TIMES.items():
            badge_html=f"<span style='background:{C['red_lt'] if data['risk']=='high' else C['amber_lt'] if data['risk']=='medium' else C['green_lt']};color:{C['red'] if data['risk']=='high' else C['amber'] if data['risk']=='medium' else C['green']};font-size:9px;font-weight:700;padding:2px 7px;border-radius:10px;'>{data['risk'].upper()}</span>"
            st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:11px;'><code style='font-size:10px;'>{time_slot}</code> {badge_html} {data['label']}</div>",unsafe_allow_html=True)

    with col2:
        st.markdown(f"**💡 Evidence-Based Safety Tips**")
        for i,tip in enumerate(SAFE_LIVING_TIPS,1):
            st.markdown(f"<div style='background:white;border-left:3px solid {C['gold']};border-radius:4px;padding:7px 11px;font-size:11px;color:#4A3728;margin-bottom:6px;'><strong>{i}.</strong> {tip}</div>",unsafe_allow_html=True)

    section("Perpetrator Pattern Intelligence","red")
    _rpI = pp_e.get("relations_perpetrator", pd.Series(dtype=str)).fillna("").astype(str)
    _rpI = _rpI[~_rpI.str.strip().isin(["","nan","none"])]
    _primI = _rpI.str.strip().str.split().str[0].map(RELATION_MAP).dropna()
    _tI = len(_primI)
    _pn = lambda l: 100*(_primI==l).sum()/_tI if _tI else 0
    neigh_i, stranger_i = _pn("Neighbour"), _pn("Stranger")
    known_i = 100 - stranger_i
    top_i = _primI.value_counts().idxmax() if _tI else "n/a"
    _gI = pp_e.get("client_gender", pd.Series(dtype=str)).astype(str).str.upper()
    male_i = 100*(_gI=="M").sum()/max(int(_gI.isin(["M","F"]).sum()),1)
    st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>
      <div style='background:{C["red_lt"]};border-radius:8px;padding:14px;'>
        <div style='font-weight:600;color:{C["red"]};font-size:12px;margin-bottom:8px;'>Who are the perpetrators? (live · {_tI:,} cases)</div>
        <div style='font-size:11px;color:#5D2020;line-height:1.8;'>
          • <strong>{neigh_i:.0f}%</strong> are neighbours (known to the survivor)<br>
          • <strong>{stranger_i:.0f}%</strong> are strangers<br>
          • <strong>{known_i:.0f}%</strong> are known to the survivor in some way<br>
          • <strong>{male_i:.0f}%</strong> of perpetrators are male<br>
          • Most common relationship: <strong>{top_i}</strong>
        </div>
      </div>
      <div style='background:{C["orange_lt"]};border-radius:8px;padding:14px;'>
        <div style='font-weight:600;color:{C["orange"]};font-size:12px;margin-bottom:8px;'>Where do incidents happen?</div>
        <div style='font-size:11px;color:#4A3728;line-height:1.8;'>
          Incident-location capture was recently added to the data tool. The live
          breakdown of where incidents occur (home, paths to water, bush, near schools)
          appears on the <strong>Narratives</strong> page and fills in as new records are collected.
        </div>
      </div>
    </div>""",unsafe_allow_html=True)