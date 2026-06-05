"""
pages/8_Distance_Intelligence.py
Distance intelligence: survivor-to-court, survivor-to-healing-centre,
perpetrator-to-CPS, counterfactual access, facility maps.

Verified coordinates from:
- Rukungiri town: Wikipedia (-0.7900, 29.9250)
- Kanungu town: Wikipedia (-0.8970, 29.7756)
- Rubanda town: Wikipedia (-1.1864, 29.8433)
- Rukungiri High Court: judiciary.go.ug — opened Feb 2023, at Chief Magistrates Court
- Kabale High Court: sklwanga.org — serves Rubanda, Kabale, Rukiga districts
- Kambuga General Hospital: Wikipedia (-0.8139, 29.8008)
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
from utils.viz import section, page_header, safe_notice, kpi
from utils.cost_model import FACILITY_COORDS, DISTANCE_FACTS

if not check():
    st.warning("Please log in.")
    st.stop()
if not can_access("gis"):
    st.error("🔒 Access denied.")
    st.stop()

sidebar_panel()
page_header(
    "Distance & Service Access Intelligence",
    "Survivor travel to court · access to healing centres · perpetrator transport to CPS "
    "· counterfactual analysis · facility mapping",
    "📐"
)
safe_notice()

# ── COURT STRUCTURE NOTICE ────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:{C["blue_lt"]};border-left:4px solid {C["blue"]};
            padding:10px 16px;border-radius:6px;font-size:11px;
            color:#1A237E;margin-bottom:12px;'>
  <strong>⚖️ Court jurisdiction confirmed (judiciary.go.ug + Daily Monitor 2023):</strong>
  <ul style='margin:6px 0 0 16px;'>
    <li><strong>Rukungiri High Court</strong> — opened February 2023. Serves
        <strong>Rukungiri & Kanungu districts</strong>. Eliminated need to
        travel 125km to Kabale.</li>
    <li><strong>Kanungu</strong> — has a Grade I Magistrate Court only.
        High Court cases go to <strong>Rukungiri High Court</strong> (43km away).</li>
    <li><strong>Rubanda</strong> — has <strong>NO High Court</strong>.
        Served by <strong>Kabale High Court Circuit</strong> (covers Rubanda, Kabale & Rukiga districts).</li>
  </ul>
</div>""", unsafe_allow_html=True)

# ── TOP KPI STRIP ─────────────────────────────────────────────────────────────
D = DISTANCE_FACTS
section("Key distance metrics — computed from 1,169 real GPS records", "purple")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi("Survivor → Nearest HC",
                    f"{D['survivor_to_healing_mean_km']:.1f}",
                    suffix=" km avg",
                    color="purple", icon="🏥",
                    note=f"Median {D['survivor_to_healing_median_km']:.1f} km · "
                         f"{D['survivor_to_healing_pct_within_20']}% within 20km"),
                unsafe_allow_html=True)
with c2:
    st.markdown(kpi("Survivor → Court",
                    f"{D['survivor_to_court_mean_km']:.1f}",
                    suffix=" km avg",
                    color="orange", icon="⚖️",
                    note=f"Median {D['survivor_to_court_median_km']:.1f} km · "
                         "Rukungiri HC serves Kanungu cases"),
                unsafe_allow_html=True)
with c3:
    st.markdown(kpi("Perpetrator → Nearest CPS",
                    f"{D['perp_to_nearest_cps_mean_km']:.1f}",
                    suffix=" km avg",
                    color="red", icon="🔒",
                    note=f"Kanungu CPS: {D['perp_to_kanungu_cps_mean_km']:.1f} km avg"),
                unsafe_allow_html=True)
with c4:
    nyaka_saving = D['survivor_to_specialist_no_nyaka_km'] - D['survivor_to_healing_mean_km']
    st.markdown(kpi("Distance saved vs nearest specialist",
                    f"{nyaka_saving:.0f}",
                    suffix=" km",
                    color="green", icon="💚",
                    note=f"Without Nyaka: ~{D['survivor_to_specialist_no_nyaka_km']} km "
                         "to Kabale/Mbarara SGBV services"),
                unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Facility Map",
    "📐 Survivor Distance Analysis",
    "🚔 Perpetrator Transport",
    "📊 Counterfactual Analysis",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — FACILITY MAP
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    section("All facilities — police stations, courts, healing centres", "purple")

    # Layer toggles
    col_t, col_s = st.columns([3, 1])
    with col_t:
        show_police   = st.checkbox("Police stations (CPS)", value=True)
        show_courts   = st.checkbox("Courts", value=True)
        show_healing  = st.checkbox("Nyaka Healing Centres", value=True)
        show_hospital = st.checkbox("Public hospital (reference)", value=True)
    with col_s:
        st.markdown(f"""
        <div style='background:{C["purple_lt"]};border-radius:6px;
                    padding:8px 10px;font-size:10px;line-height:1.8;'>
          <strong>Map symbols:</strong><br>
          🔵 Healing centres<br>
          🔴 Police stations<br>
          🟣 Courts<br>
          🟠 Public hospital
        </div>""", unsafe_allow_html=True)

    # Build map
    try:
        sv_dist = pd.read_csv("data/survivors_with_distances.csv", low_memory=False)
        sv_gps  = sv_dist[sv_dist["lat"].notna()].sample(min(600, len(sv_dist)))
    except Exception:
        sv_gps = pd.DataFrame()

    fig_map = go.Figure()

    # Survivor incident points (background layer)
    if len(sv_gps):
        fig_map.add_trace(go.Scattermapbox(
            lat=sv_gps["lat"], lon=sv_gps["lon"],
            mode="markers", name="Survivor incidents",
            marker=dict(size=5, color="rgba(198,40,40,0.4)"),
            hoverinfo="skip"
        ))

    TYPE_CFG = {
        "police":  (show_police,  C["red"],    "square", 14, "CPS"),
        "court":   (show_courts,  C["purple"], "star",   16, "Court"),
        "healing": (show_healing, C["blue"],   "circle", 18, "Healing Centre"),
        "hospital":(show_hospital,C["orange"], "diamond",14, "Hospital"),
    }

    for name, f in FACILITY_COORDS.items():
        visible, color, sym, sz, lbl = TYPE_CFG[f["type"]]
        if not visible:
            continue
        dist_note = ""
        if f["type"] == "court":
            dist_note = f"<br><i>{f.get('note','')}</i>"
        hover = (f"<b>{name}</b><br>District: {f.get('district','')}"
                 f"{dist_note}<extra></extra>")
        fig_map.add_trace(go.Scattermapbox(
            lat=[f["lat"]], lon=[f["lon"]], mode="markers+text",
            name=f"{lbl}: {name}",
            marker=dict(size=sz, color=color),
            text=[name.split()[0]], textposition="top right",
            textfont=dict(size=9, color=color),
            hovertemplate=hover
        ))

    fig_map.update_layout(
        mapbox=dict(style="open-street-map",
                    center=dict(lat=-0.95, lon=29.85), zoom=9),
        height=560, margin=dict(l=0, r=0, t=40, b=0),
        title="Nyaka operational area — police stations, courts, healing centres",
        legend=dict(orientation="h", y=-0.06, font=dict(size=9))
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Facility directory
    section("Facility directory — verified coordinates", "orange")
    fac_rows = []
    for name, f in FACILITY_COORDS.items():
        fac_rows.append({
            "Facility":   name,
            "Type":       f["type"].capitalize(),
            "District":   f.get("district",""),
            "Latitude":   f["lat"],
            "Longitude":  f["lon"],
            "Note":       f.get("note",""),
        })
    fac_df = pd.DataFrame(fac_rows)
    st.dataframe(fac_df, use_container_width=True, hide_index=True)
    st.caption("Sources: Wikipedia (town coordinates), judiciary.go.ug (Rukungiri High Court), "
               "Kabale High Court Circuit website (Rubanda jurisdiction confirmed), "
               "Daily Monitor Oct 2022 (Rukungiri HC operationalisation).")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — SURVIVOR DISTANCE ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    section("Survivor travel distances — 1,169 GPS-tagged cases", "purple")

    try:
        sv_dist = pd.read_csv("data/survivors_with_distances.csv", low_memory=False)
        has_real = True
    except Exception:
        has_real = False
        sv_dist  = pd.DataFrame()

    if has_real and len(sv_dist):
        col1, col2 = st.columns(2)

        with col1:
            # Distribution to healing centres
            fig_hc = px.histogram(
                sv_dist["dist_to_healing_km"].dropna(),
                nbins=30, color_discrete_sequence=[C["purple"]],
                title="Distribution: survivor → nearest Nyaka healing centre",
                height=300, template="plotly_white",
                labels={"value": "Distance (km)", "count": "Survivors"}
            )
            fig_hc.add_vline(x=sv_dist["dist_to_healing_km"].mean(),
                              line_dash="dash", line_color=C["orange"],
                              annotation_text=f"Mean {sv_dist['dist_to_healing_km'].mean():.1f}km")
            fig_hc.add_vline(x=sv_dist["dist_to_healing_km"].median(),
                              line_dash="dot", line_color=C["green"],
                              annotation_text=f"Median {sv_dist['dist_to_healing_km'].median():.1f}km")
            fig_hc.update_layout(margin=dict(l=36, r=16, t=48, b=36), showlegend=False)
            st.plotly_chart(fig_hc, use_container_width=True)

        with col2:
            fig_ct = px.histogram(
                sv_dist["dist_to_court_km"].dropna(),
                nbins=30, color_discrete_sequence=[C["orange"]],
                title="Distribution: survivor → nearest court",
                height=300, template="plotly_white",
                labels={"value": "Distance (km)", "count": "Survivors"}
            )
            fig_ct.add_vline(x=sv_dist["dist_to_court_km"].mean(),
                              line_dash="dash", line_color=C["red"],
                              annotation_text=f"Mean {sv_dist['dist_to_court_km'].mean():.1f}km")
            fig_ct.update_layout(margin=dict(l=36, r=16, t=48, b=36), showlegend=False)
            st.plotly_chart(fig_ct, use_container_width=True)

        # Access zone breakdown
        section("Proximity zones — healing centre access", "teal")
        zones = pd.cut(sv_dist["dist_to_healing_km"].dropna(),
                        bins=[0,5,10,20,30,999],
                        labels=["0–5km","5–10km","10–20km","20–30km","30km+"])
        zone_cnt = zones.value_counts().sort_index().reset_index()
        zone_cnt.columns = ["Zone","Survivors"]
        zone_cnt["Pct"] = (zone_cnt["Survivors"] / zone_cnt["Survivors"].sum() * 100).round(1)
        zone_cnt["Color"] = [C["green"], C["teal"], C["gold"], C["amber"], C["red"]]

        fig_z = px.bar(zone_cnt, x="Zone", y="Survivors",
                        color="Zone",
                        color_discrete_sequence=[C["green"],C["teal"],C["gold"],C["amber"],C["red"]],
                        text="Pct",
                        title="Survivors by distance band to nearest healing centre",
                        height=280, template="plotly_white")
        fig_z.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_z.update_layout(margin=dict(l=36,r=16,t=48,b=36), showlegend=False)
        st.plotly_chart(fig_z, use_container_width=True)

        # Distance by healing centre
        section("Average survivor travel per healing centre", "orange")
        if "nearest_healing" in sv_dist.columns:
            hc_dist = sv_dist.groupby("nearest_healing").agg(
                Survivors=("dist_to_healing_km","count"),
                AvgDist=("dist_to_healing_km","mean"),
                MedianDist=("dist_to_healing_km","median")
            ).reset_index().rename(columns={"nearest_healing":"Centre"})
            hc_dist["AvgDist"] = hc_dist["AvgDist"].round(1)
            hc_dist["MedianDist"] = hc_dist["MedianDist"].round(1)

            fig_hc2 = px.bar(hc_dist.sort_values("AvgDist", ascending=False),
                              x="AvgDist", y="Centre", orientation="h",
                              color_discrete_sequence=[C["purple"]],
                              height=280, template="plotly_white",
                              title="Average survivor travel distance by healing centre (km)",
                              text="AvgDist")
            fig_hc2.update_traces(texttemplate="%{text:.1f}km", textposition="outside")
            fig_hc2.update_layout(margin=dict(l=200,r=60,t=48,b=36))
            st.plotly_chart(fig_hc2, use_container_width=True)
            st.dataframe(hc_dist, use_container_width=True, hide_index=True)

    else:
        # Show summary statistics from pre-computed DISTANCE_FACTS
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div style='background:{C["purple_lt"]};border-radius:8px;padding:14px 16px;'>
              <div style='font-weight:600;color:{C["purple"]};margin-bottom:8px;'>
                Survivor → Nyaka Healing Centre
              </div>
              <div style='font-size:11px;line-height:2;'>
                <strong>Mean distance:</strong> {D["survivor_to_healing_mean_km"]} km<br>
                <strong>Median distance:</strong> {D["survivor_to_healing_median_km"]} km<br>
                <strong>Within 10km:</strong> {D["survivor_to_healing_pct_within_10"]}% of survivors<br>
                <strong>Within 20km:</strong> {D["survivor_to_healing_pct_within_20"]}% of survivors<br>
              </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style='background:{C["orange_lt"]};border-radius:8px;padding:14px 16px;'>
              <div style='font-weight:600;color:{C["orange"]};margin-bottom:8px;'>
                Survivor → Nearest Court
              </div>
              <div style='font-size:11px;line-height:2;'>
                <strong>Mean distance:</strong> {D["survivor_to_court_mean_km"]} km<br>
                <strong>Median distance:</strong> {D["survivor_to_court_median_km"]} km<br>
                <strong>Kanungu survivors → Rukungiri HC:</strong> ~43km avg road distance<br>
                <strong>Rubanda survivors → Kabale HC:</strong> ~35km avg road distance<br>
              </div>
            </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — PERPETRATOR TRANSPORT
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    section("Perpetrator transport to Central Police Stations", "red")

    col1, col2, col3 = st.columns(3)
    for col, (cps, mean_km, clr) in zip([col1,col2,col3], [
        ("Rukungiri CPS", D["perp_to_rukungiri_cps_mean_km"], "blue"),
        ("Kanungu CPS",   D["perp_to_kanungu_cps_mean_km"],   "purple"),
        ("Rubanda CPS",   D["perp_to_rubanda_cps_mean_km"],   "red"),
    ]):
        with col:
            st.markdown(kpi(f"Avg to {cps}", f"{mean_km:.1f}",
                            suffix=" km", color=clr, icon="🚔",
                            note="One-way road distance estimate"),
                        unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    section("Perpetrator GPS — distance to each CPS", "orange")
    try:
        pp_dist = pd.read_csv("data/perpetrators_with_distances.csv", low_memory=False)
        has_pp = True
    except Exception:
        has_pp = False

    if has_pp and len(pp_dist):
        cps_cols = [c for c in pp_dist.columns if c.startswith("dist_to_") and c.endswith("_km") and "nearest" not in c]
        cps_labels = {c: c.replace("dist_to_","").replace("_CPS_km","").replace("_"," ") for c in cps_cols}

        box_data = []
        for col_name, label in cps_labels.items():
            vals = pp_dist[col_name].dropna()
            for v in vals:
                box_data.append({"CPS": label, "Distance (km)": v})
        if box_data:
            box_df = pd.DataFrame(box_data)
            fig_box = px.box(box_df, x="CPS", y="Distance (km)",
                              color="CPS",
                              color_discrete_sequence=[C["blue"],C["purple"],C["red"]],
                              title="Perpetrator distance distribution to each CPS (km)",
                              height=340, template="plotly_white",
                              points="outliers")
            fig_box.update_layout(margin=dict(l=36,r=16,t=48,b=36), showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)

        # Map: perpetrators + CPS locations
        section("Perpetrator GPS locations vs CPS locations", "red")
        pp_gps_map = pp_dist[pp_dist["lat"].notna()].sample(min(300, len(pp_dist)))
        fig_pp = go.Figure()
        fig_pp.add_trace(go.Scattermapbox(
            lat=pp_gps_map["lat"], lon=pp_gps_map["lon"],
            mode="markers", name="Perpetrator location (jittered)",
            marker=dict(size=6, color="rgba(198,40,40,0.55)"),
            hoverinfo="skip"
        ))
        for cps_name, cps in FACILITY_COORDS.items():
            if cps["type"] == "police":
                fig_pp.add_trace(go.Scattermapbox(
                    lat=[cps["lat"]], lon=[cps["lon"]],
                    mode="markers+text", name=cps_name,
                    marker=dict(size=16, color=C["blue"]),
                    text=[cps_name.split()[0]], textposition="top right",
                    textfont=dict(size=10, color=C["blue"])
                ))
        fig_pp.update_layout(
            mapbox=dict(style="open-street-map", center=dict(lat=-0.95,lon=29.85), zoom=9),
            height=480, margin=dict(l=0,r=0,t=40,b=0),
            title="Perpetrator locations (jittered ±300m) vs Central Police Stations",
            legend=dict(orientation="h", y=-0.06)
        )
        st.plotly_chart(fig_pp, use_container_width=True)

    else:
        st.info("Perpetrator GPS data file not found. Showing pre-computed statistics.")
        stats_df = pd.DataFrame({
            "Police Station":  ["Rukungiri CPS","Kanungu CPS","Rubanda CPS"],
            "Mean distance km":[D["perp_to_rukungiri_cps_mean_km"],
                                 D["perp_to_kanungu_cps_mean_km"],
                                 D["perp_to_rubanda_cps_mean_km"]],
            "Primary district":["Rukungiri","Kanungu","Rubanda"],
        })
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    st.markdown(f"""
    <div style='background:{C["amber_lt"]};border-left:3px solid {C["amber"]};
                padding:8px 12px;border-radius:4px;font-size:11px;
                color:#4A2800;margin-top:10px;'>
      ⚠ <strong>Rubanda note:</strong>
      Rubanda perpetrators face the longest transport distance to CPS (avg 54.8km).
      This is a significant operational challenge for legal pursuit in Rubanda —
      one more reason the Rubanda expansion case is compelling.
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — COUNTERFACTUAL ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    section("Without Nyaka: what changes for survivors?", "teal")

    st.markdown(f"""
    <div style='background:{C["teal_lt"]};border-left:4px solid {C["teal"]};
                border-radius:8px;padding:12px 16px;font-size:11px;
                color:#003024;margin-bottom:12px;line-height:1.8;'>
      <strong>Important distinction:</strong> The counterfactual is NOT
      simply about physical distance to the nearest building. It is about
      access to <em>specialised, trauma-informed SGBV care</em> that includes
      legal advocacy, case management, psychosocial support, and justice
      pathway navigation. Public hospitals provide medical care only.
      Without Nyaka, the nearest equivalent SGBV service would be in
      Kabale or Mbarara — 80–125km away.
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        cf_data = {
            "Metric":    ["Nearest healing service (Nyaka)",
                           "Nearest public hospital",
                           "Nearest SGBV specialist (without Nyaka)",
                           "Nearest court"],
            "Mean km":   [D["survivor_to_healing_mean_km"],
                           D["survivor_to_public_hosp_mean_km"],
                           D["survivor_to_specialist_no_nyaka_km"],
                           D["survivor_to_court_mean_km"]],
            "Service type":["Full SGBV care + legal + MH",
                              "Medical only (no legal, no PSS)",
                              "SGBV specialist equivalent",
                              "Justice system"],
        }
        cf_df = pd.DataFrame(cf_data)
        colors = [C["purple"], C["grey"], C["red"], C["orange"]]
        fig_cf = px.bar(cf_df, x="Mean km", y="Metric", orientation="h",
                        color="Metric", color_discrete_sequence=colors,
                        text="Mean km", height=280, template="plotly_white",
                        title="Service access distance comparison (km)")
        fig_cf.update_traces(texttemplate="%{text:.1f} km", textposition="outside")
        fig_cf.update_layout(margin=dict(l=260,r=60,t=48,b=36), showlegend=False)
        st.plotly_chart(fig_cf, use_container_width=True)

    with col2:
        saving = D["survivor_to_specialist_no_nyaka_km"] - D["survivor_to_healing_mean_km"]
        saving_pct = round(100 * saving / D["survivor_to_specialist_no_nyaka_km"])

        st.markdown(f"""
        <div style='background:{C["green_lt"]};border-radius:8px;
                    padding:14px 16px;height:100%;'>
          <div style='font-size:13px;font-weight:600;color:{C["green"]};
                      margin-bottom:10px;'>
            🌿 Nyaka access advantage
          </div>
          <div style='font-size:12px;line-height:2.2;'>
            <strong>Distance saved per survivor:</strong>
            <span style='color:{C["green"]};font-weight:500;'>
              ~{saving:.0f} km
            </span><br>
            <strong>Reduction in travel:</strong>
            <span style='color:{C["green"]};font-weight:500;'>
              {saving_pct}%
            </span><br>
            <strong>Survivors within 20km:</strong>
            <span style='color:{C["green"]};font-weight:500;'>
              {D["survivor_to_healing_pct_within_20"]}%
            </span><br>
            <strong>Total survivors served:</strong>
            <span style='color:{C["green"]};font-weight:500;'>2,031</span>
          </div>
          <div style='margin-top:12px;font-size:11px;color:{C["teal"]};
                      background:{C["teal_lt"]};padding:7px 10px;border-radius:4px;'>
            Without Nyaka healing centres, survivors in Kanungu and Rukungiri
            would need to travel to Kabale (~80km) or Mbarara (~125km) to access
            any equivalent specialised SGBV support. The journey alone is a
            significant barrier to reporting and justice.
          </div>
        </div>""", unsafe_allow_html=True)

    section("Rubanda: the access gap that expansion closes", "red")

    rubanda_note = f"""
    <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;'>
      <div style='background:{C["red_lt"]};border-radius:8px;padding:12px 14px;'>
        <div style='font-size:11px;font-weight:600;color:{C["red"]};margin-bottom:6px;'>
          Current: No Nyaka presence
        </div>
        <div style='font-size:11px;color:#5D2020;line-height:1.8;'>
          Nearest Nyaka HC: &gt;50km<br>
          Nearest High Court: Kabale (~35km)<br>
          Nearest CPS: Rubanda Town<br>
          SGBV specialist care: Kabale (35km+)
        </div>
      </div>
      <div style='background:{C["amber_lt"]};border-radius:8px;padding:12px 14px;'>
        <div style='font-size:11px;font-weight:600;color:{C["amber"]};margin-bottom:6px;'>
          Service gap
        </div>
        <div style='font-size:11px;color:#4A2800;line-height:1.8;'>
          No legal advocacy<br>
          No case management<br>
          No psychosocial support<br>
          Court cases go to Kabale HC (not Rukungiri)
        </div>
      </div>
      <div style='background:{C["green_lt"]};border-radius:8px;padding:12px 14px;'>
        <div style='font-size:11px;font-weight:600;color:{C["green"]};margin-bottom:6px;'>
          With Rubanda Healing Centre
        </div>
        <div style='font-size:11px;color:#1B3A1B;line-height:1.8;'>
          Access: &lt;15km avg<br>
          Full case management<br>
          Legal advocacy on-site<br>
          Expected reach: ~300 survivors/yr
        </div>
      </div>
    </div>
    """
    st.markdown(rubanda_note, unsafe_allow_html=True)

    section("Distance-cost linkage", "gold")
    st.markdown(f"""
    <div style='font-size:11px;color:{C["grey"]};background:{C["gold_lt"]};
                border-left:3px solid {C["gold"]};border-radius:4px;
                padding:9px 14px;line-height:1.8;'>
      Every additional 10km a survivor travels to court costs approximately
      <strong>UGX 100,000</strong> in transport (2–3 return trips).
      Every 10km a perpetrator must be transported to CPS costs
      <strong>UGX 30,000+</strong>. The distance data directly feeds the
      Cost of Impact analysis — see the <strong>Cost of Impact page</strong>.
    </div>""", unsafe_allow_html=True)
