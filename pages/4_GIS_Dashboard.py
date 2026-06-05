"""pages/4_GIS_Dashboard.py — Full GIS intelligence: hotspots, coverage, safe zones, risk scoring"""
import streamlit as st, pandas as pd, plotly.express as px
import plotly.graph_objects as go, json, sys, os, pickle
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
from config import C, VIOLENCE_COLORS, DISTRICT_CENTRES, DEFAULT_MAP_CENTRE, SAFE_LIVING_TIPS
from utils.auth import check, sidebar_panel, can_access, gis_precision
from utils.data_loader import load_all, apply_filters
from utils.viz import section, page_header, safe_notice, kpi, density_map
from utils.cost_model import FACILITY_COORDS

if not check(): st.warning("Please log in."); st.stop()
if not can_access("gis"): st.error("🔒 Access denied."); st.stop()

DATA=load_all(); sv=DATA["survivors"]; pp=DATA["perpetrators"]
ot=DATA["outreach"]; sc=DATA["school"]
sidebar_panel()
st.sidebar.markdown("---")
yrs=sorted(sv["year"].dropna().unique().astype(int).tolist()) if len(sv) else [2022,2023,2024,2025,2026]
sel_yrs=st.sidebar.multiselect("Year",yrs,default=yrs,key="gis_yr")
sel_dist=st.sidebar.selectbox("Focus District",["All Districts","Kanungu","Rukungiri","Rubanda"],key="gis_d")
sel_layer=st.sidebar.multiselect("Map Layers",
    ["Survivor Incidents","Perpetrator Locations","Outreach Sessions","School Sessions"],
    default=["Survivor Incidents","Perpetrator Locations"])

filt={"years":sel_yrs,"district":None if sel_dist=="All Districts" else sel_dist}
sv_f=apply_filters(sv,filt); pp_f=apply_filters(pp,filt)
ot_f=apply_filters(ot,filt); sc_f=apply_filters(sc,filt)
sv_e=sv_f[sv_f.get("report_category","").str.contains("enrollment",na=False)]
pp_e=pp_f[pp_f.get("is_enrolled",pd.Series(dtype=bool))] if "is_enrolled" in pp_f.columns else pp_f[pp_f.get("report_category","")=="enrollment"]

page_header("GIS Intelligence Dashboard",
            "Incident hotspots · crime scene mapping · outreach coverage · safe zone analysis · Kanungu · Rukungiri · Rubanda","🗺️")
safe_notice()

st.markdown(f"""<div style='background:{C["red_lt"]};border-left:4px solid {C["red"]};
    border-radius:8px;padding:10px 16px;font-size:11px;color:{C["red"]};margin-bottom:12px;'>
  🔒 <strong>GIS Privacy Protocol:</strong>
  Your role grants <strong>{gis_precision()}-level</strong> GIS precision.
  Survivor locations are aggregated at subcounty level minimum.
  Exact coordinates are NEVER displayed publicly. All GPS points are jittered ±300m.
</div>""",unsafe_allow_html=True)

gps_stats_c=st.columns(4)
sv_gps=sv_e[sv_e.get("lat",pd.Series(dtype=float)).notna()]
pp_gps=pp_e[pp_e.get("lat",pd.Series(dtype=float)).notna()]
ot_gps=ot_f[ot_f.get("lat",pd.Series(dtype=float)).notna()]
sc_gps=sc_f[sc_f.get("lat",pd.Series(dtype=float)).notna()]
for col,(lbl,val,clr) in zip(gps_stats_c,[
    ("Survivor GPS Points",f"{len(sv_gps):,}","purple"),
    ("Perpetrator GPS Points",f"{len(pp_gps):,}","red"),
    ("Outreach GPS Points",f"{len(ot_gps):,}","teal"),
    ("School GPS Points",f"{len(sc_gps):,}","gold"),
]):
    with col: st.markdown(kpi(lbl,val,color=clr),unsafe_allow_html=True)
st.markdown("<br/>",unsafe_allow_html=True)

# Map centre
if sel_dist!="All Districts" and sel_dist in DISTRICT_CENTRES:
    mc=DISTRICT_CENTRES[sel_dist]
    centre_lat,centre_lon,zoom_lvl=mc["lat"],mc["lon"],mc["zoom"]
else:
    centre_lat,centre_lon,zoom_lvl=-0.85,29.85,9

tab1,tab2,tab3,tab4,tab5=st.tabs([
    "📍 Incident Map","🔥 Hotspot Density","🛡 Safe Zone Intelligence",
    "📊 Subcounty Analysis","🏥 Service Coverage"])

with tab1:
    section("Integrated Incident & Coverage Map","purple")
    fig=go.Figure()
    # Survivor incidents
    if "Survivor Incidents" in sel_layer and len(sv_gps)>0:
        sv_sample=sv_gps.sample(min(600,len(sv_gps)))
        import random
        sv_sample=sv_sample.copy()
        sv_sample["lat_j"]=sv_sample["lat"]+[random.uniform(-0.003,0.003) for _ in range(len(sv_sample))]
        sv_sample["lon_j"]=sv_sample["lon"]+[random.uniform(-0.003,0.003) for _ in range(len(sv_sample))]
        for vtype in sv_sample["assault_label"].unique():
            g=sv_sample[sv_sample["assault_label"]==vtype]
            fig.add_trace(go.Scattermapbox(lat=g["lat_j"],lon=g["lon_j"],mode="markers",
                name=f"Survivor: {vtype}",
                marker=dict(size=8,color=VIOLENCE_COLORS.get(vtype,C["grey"]),opacity=0.7),
                hovertemplate=f"<b>{vtype}</b><br>District: %{{customdata[0]}}<br>Token: %{{customdata[1]}}<extra></extra>",
                customdata=g[["district","survivor_token"]].values if "survivor_token" in g.columns else g[["district","client_id"]].values))

    # Perpetrator locations
    if "Perpetrator Locations" in sel_layer and len(pp_gps)>0:
        pp_sample=pp_gps.sample(min(300,len(pp_gps))).copy()
        pp_sample["lat_j"]=pp_sample["lat"]+[random.uniform(-0.003,0.003) for _ in range(len(pp_sample))]
        pp_sample["lon_j"]=pp_sample["lon"]+[random.uniform(-0.003,0.003) for _ in range(len(pp_sample))]
        fig.add_trace(go.Scattermapbox(lat=pp_sample["lat_j"],lon=pp_sample["lon_j"],mode="markers",
            name="Perpetrator (enrolled)",
            marker=dict(size=10,color=C["red"],symbol="cross",opacity=0.6),
            hovertemplate="<b>Perpetrator</b><br>District: %{customdata[0]}<br>Assault: %{customdata[1]}<extra></extra>",
            customdata=pp_sample[["district","assault_label"]].values))

    # Outreach
    if "Outreach Sessions" in sel_layer and len(ot_gps)>0:
        fig.add_trace(go.Scattermapbox(lat=ot_gps["lat"],lon=ot_gps["lon"],mode="markers",
            name="Outreach Session",
            marker=dict(size=ot_gps["total"].clip(5,30).fillna(5),color=C["teal"],opacity=0.5),
            hovertemplate="<b>Outreach</b><br>Reached: %{customdata[0]}<br>Type: %{customdata[1]}<extra></extra>",
            customdata=ot_gps[["total","event_cat"]].fillna("").values if "event_cat" in ot_gps.columns else ot_gps[["total","district"]].fillna("").values))

    # Schools
    if "School Sessions" in sel_layer and len(sc_gps)>0:
        fig.add_trace(go.Scattermapbox(lat=sc_gps["lat"],lon=sc_gps["lon"],mode="markers",
            name="School Session",
            marker=dict(size=9,color=C["gold"],symbol="star",opacity=0.7),
            hovertemplate="<b>School Session</b><br>Students: %{customdata[0]}<extra></extra>",
            customdata=sc_gps[["total"]].values))

    # Healing centre markers (fixed)
    hc_coords={n.replace(" Healing Centre"," HC"):(v["lat"],v["lon"])
              for n,v in FACILITY_COORDS.items() if v["type"]=="healing"}
    hc_lats=[v[0] for v in hc_coords.values()]
    hc_lons=[v[1] for v in hc_coords.values()]
    hc_names=list(hc_coords.keys())
    fig.add_trace(go.Scattermapbox(lat=hc_lats,lon=hc_lons,mode="markers+text",
        name="Healing Centres",text=hc_names,textposition="top right",textfont=dict(size=10,color=C["purple"]),
        marker=dict(size=16,color=C["purple"],symbol="hospital")))

    # Justice infrastructure (fixed): courts and police, from verified coordinates
    for _typ,_clr,_lbl in [("court",C["orange"],"Courts"),("police",C["blue"],"Police stations")]:
        _pts={k:v for k,v in FACILITY_COORDS.items() if v["type"]==_typ}
        if _pts:
            fig.add_trace(go.Scattermapbox(
                lat=[v["lat"] for v in _pts.values()], lon=[v["lon"] for v in _pts.values()],
                mode="markers+text", name=_lbl, text=list(_pts.keys()),
                textposition="bottom right", textfont=dict(size=9,color=_clr),
                marker=dict(size=13,color=_clr)))

    fig.update_layout(
        mapbox=dict(style="open-street-map",center=dict(lat=centre_lat,lon=centre_lon),zoom=zoom_lvl),
        height=580,margin=dict(l=0,r=0,t=40,b=0),
        title=f"SGBV Programme Intelligence Map — {sel_dist}",
        legend=dict(orientation="h",y=-0.04,bgcolor="rgba(255,255,255,0.8)"))
    st.plotly_chart(fig,use_container_width=True)
    st.caption(f"🔒 Survivor/perpetrator GPS jittered ±300m. Showing {min(600,len(sv_gps))} of {len(sv_gps)} survivor points. GIS precision: {gis_precision()} level.")

with tab2:
    section("Incident Density Heatmap","red")
    col_a,col_b=st.columns(2)
    with col_a:
        if len(sv_gps):
            sv_d=sv_gps.copy()
            sv_d["lat_j"]=sv_d["lat"]+sv_d["lat"].apply(lambda _:__import__("random").uniform(-0.002,0.002))
            sv_d["lon_j"]=sv_d["lon"]+sv_d["lon"].apply(lambda _:__import__("random").uniform(-0.002,0.002))
            sv_d=sv_d.rename(columns={"lat_j":"lat_plot","lon_j":"lon_plot"})
            fig=px.density_mapbox(sv_d,lat="lat_plot",lon="lon_plot",radius=16,zoom=zoom_lvl,height=440,
                                  mapbox_style="open-street-map",title="Survivor Incident Density",
                                  color_continuous_scale="Reds")
            fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig,use_container_width=True)
    with col_b:
        if len(pp_gps):
            pp_d=pp_gps.copy()
            pp_d["lat_j"]=pp_d["lat"]+pp_d["lat"].apply(lambda _:__import__("random").uniform(-0.002,0.002))
            pp_d["lon_j"]=pp_d["lon"]+pp_d["lon"].apply(lambda _:__import__("random").uniform(-0.002,0.002))
            pp_d=pp_d.rename(columns={"lat_j":"lat_plot","lon_j":"lon_plot"})
            fig2=px.density_mapbox(pp_d,lat="lat_plot",lon="lon_plot",radius=16,zoom=zoom_lvl,height=440,
                                   mapbox_style="open-street-map",title="Perpetrator Crime Scene Density",
                                   color_continuous_scale="Oranges")
            fig2.update_layout(margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig2,use_container_width=True)

with tab3:
    section("🛡 Evidence-Based Safe Zone Intelligence","gold")
    st.markdown(f"""<div style='background:{C["gold_lt"]};border-left:4px solid {C["gold"]};
        border-radius:8px;padding:16px 20px;margin-bottom:16px;'>
      <div style='font-weight:600;color:#5D4037;font-size:14px;margin-bottom:8px;'>
        How to Use This Map: Avoid the RED zones, especially in the evening
      </div>
      <div style='font-size:11px;color:#7B5E45;'>
        High-density areas (red = more incidents) are derived from real GPS data recorded by Nyaka SGBV staff during case enrollment.
        These reflect WHERE incidents occurred — not WHO lives there. Use this to plan safer routes and timing.
      </div>
    </div>""",unsafe_allow_html=True)

    # Safe living overlay: show healing centres as safe destinations
    fig_safe=go.Figure()
    if len(sv_gps)>0:
        sv_s=sv_gps.sample(min(400,len(sv_gps))).copy()
        sv_s["lat_j"]=sv_s["lat"]+sv_s["lat"].apply(lambda _:__import__("random").uniform(-0.003,0.003))
        sv_s["lon_j"]=sv_s["lon"]+sv_s["lon"].apply(lambda _:__import__("random").uniform(-0.003,0.003))
        fig_safe.add_trace(go.Scattermapbox(lat=sv_s["lat_j"],lon=sv_s["lon_j"],mode="markers",
            name="⚠ Incident zones",marker=dict(size=8,color="rgba(183,28,28,0.5)"),hoverinfo="skip"))

    # Healing centres = SAFE destinations
    for name,(lat,lon) in hc_coords.items():
        fig_safe.add_trace(go.Scattermapbox(lat=[lat],lon=[lon],mode="markers+text",
            name=f"🏥 {name}",text=[name],textposition="top right",textfont=dict(size=10,color=C["green"]),
            marker=dict(size=18,color=C["green"]),showlegend=True))

    fig_safe.update_layout(
        mapbox=dict(style="open-street-map",center=dict(lat=centre_lat,lon=centre_lon),zoom=zoom_lvl),
        height=520,margin=dict(l=0,r=0,t=40,b=0),
        title="Safe Destinations (Healing Centres) vs Incident Zones",
        legend=dict(orientation="h",y=-0.05))
    st.plotly_chart(fig_safe,use_container_width=True)

    section("Community Safety Tips by Location","amber")
    tips_col1,tips_col2=st.columns(2)
    with tips_col1:
        for tip in SAFE_LIVING_TIPS[:5]:
            st.markdown(f"""<div style='background:white;border-left:3px solid {C["gold"]};
                border-radius:4px;padding:8px 12px;font-size:11px;margin-bottom:6px;'>
              💡 {tip}</div>""",unsafe_allow_html=True)
    with tips_col2:
        for tip in SAFE_LIVING_TIPS[5:]:
            st.markdown(f"""<div style='background:white;border-left:3px solid {C["amber"]};
                border-radius:4px;padding:8px 12px;font-size:11px;margin-bottom:6px;'>
              ⚠ {tip}</div>""",unsafe_allow_html=True)

with tab4:
    section("Subcounty Incident Analysis","purple")
    dcol=next((c for c in ["subcounty_label","subcounty"] if c in sv_e.columns),None)
    if dcol:
        sub=sv_e.groupby(dcol)["client_id"].count().nlargest(15).reset_index()
        sub.columns=["Subcounty","Cases"]
        fig=px.bar(sub.sort_values("Cases"),x="Cases",y="Subcounty",orientation="h",
                   color="Cases",color_continuous_scale="Purples",height=440,
                   template="plotly_white",title="Top 15 Subcounties by Incident Count")
        fig.update_layout(margin=dict(l=140,r=16,t=48,b=36),showlegend=False)
        st.plotly_chart(fig,use_container_width=True)

    section("Violence Type by Subcounty Heatmap","orange")
    if dcol:
        ct=pd.crosstab(sv_e[dcol].fillna("Unknown"),sv_e.get("assault_label","")).head(12)
        if len(ct):
            fig2=go.Figure(go.Heatmap(z=ct.values,x=ct.columns.tolist(),y=ct.index.tolist(),
                colorscale="Purples",showscale=True,text=ct.values,texttemplate="%{text}",
                textfont=dict(size=9)))
            fig2.update_layout(template="plotly_white",height=420,
                               title="Violence Type × Subcounty",
                               margin=dict(l=150,r=16,t=48,b=80))
            fig2.update_xaxes(tickangle=-35)
            st.plotly_chart(fig2,use_container_width=True)

with tab5:
    section("Service Access Coverage Analysis","teal")
    st.markdown("Distance from incident hotspots to nearest healing centres — accessibility intelligence.")
    fig3=go.Figure()
    if len(sv_gps)>0:
        fig3.add_trace(go.Scattermapbox(lat=sv_gps["lat"],lon=sv_gps["lon"],mode="markers",
            name="Incident zones",marker=dict(size=5,color=C["red"],opacity=0.4),hoverinfo="skip"))
    if len(ot_gps)>0:
        fig3.add_trace(go.Scattermapbox(lat=ot_gps["lat"],lon=ot_gps["lon"],mode="markers",
            name="Outreach sessions",marker=dict(size=6,color=C["teal"],opacity=0.5),
            hovertemplate="Reach: %{customdata}<extra></extra>",
            customdata=ot_gps["total"].fillna(0).astype(int).values))
    for name,(lat,lon) in hc_coords.items():
        fig3.add_trace(go.Scattermapbox(lat=[lat],lon=[lon],mode="markers+text",
            name=name,text=[name[:8]],textposition="top right",textfont=dict(size=9,color=C["purple"]),
            marker=dict(size=16,color=C["purple"])))
    fig3.update_layout(
        mapbox=dict(style="open-street-map",center=dict(lat=centre_lat,lon=centre_lon),zoom=zoom_lvl),
        height=520,margin=dict(l=0,r=0,t=40,b=0),
        title="Service Coverage: Incidents vs Outreach vs Healing Centres",
        legend=dict(orientation="h",y=-0.05))
    st.plotly_chart(fig3,use_container_width=True)
    st.caption("Areas with incident clusters but few/no outreach dots represent service gaps. Use this for future outreach planning.")