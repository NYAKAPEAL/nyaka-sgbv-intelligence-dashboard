"""utils/viz.py — Reusable Plotly + HTML components for Nyaka SGBV Platform."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np
from config import C, VIOLENCE_COLORS, LEGAL_COLORS, RELATION_COLORS

_MARG  = dict(l=36, r=16, t=48, b=36)
_FONT  = dict(family="Arial, sans-serif", size=11, color=C["dark"])

def _base(title="", h=340, **kw):
    base = dict(template="plotly_white", height=h, margin=dict(_MARG), font=dict(_FONT),
                title=dict(text=title, font=dict(size=13, color=C["dark"])),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    base.update(kw)   # caller-supplied keys (e.g. margin=...) override the defaults
    return base

# ── KPI COMPONENTS ────────────────────────────────────────────────────────────
def kpi(label, value, suffix="", color="purple", icon="", note="", delta=None, large=False):
    clr = C.get(color, C["purple"])
    sz  = "30px" if large else "24px"
    dh  = ""
    if delta is not None:
        dc, arrow = (C["green"], "▲") if delta >= 0 else (C["red"], "▼")
        dh = f"<div style='color:{dc};font-size:11px;margin-top:3px;'>{arrow} {abs(delta):.1f}%</div>"
    nh = f"<div style='color:{C['grey']};font-size:10px;margin-top:2px;'>{note}</div>" if note else ""
    return f"""
    <div style='background:{C["white"]};border-left:4px solid {clr};border-radius:8px;
                padding:14px 16px 12px;box-shadow:0 1px 6px rgba(0,0,0,0.07);'>
      <div style='color:{C["grey"]};font-size:9px;text-transform:uppercase;
                  letter-spacing:0.07em;margin-bottom:4px;'>{icon} {label}</div>
      <div style='color:{clr};font-size:{sz};font-weight:700;line-height:1.1;'>
        {value}{suffix}</div>{dh}{nh}</div>"""

def alert_kpi(label, value, color="red", icon="🚨"):
    clr = C.get(color, C["red"]); lt = C.get(color+"_lt", C["red_lt"])
    return f"""<div style='background:{lt};border:1px solid {clr};border-radius:8px;
        padding:10px 14px;text-align:center;'>
      <div style='font-size:22px;margin-bottom:2px;'>{icon}</div>
      <div style='color:{clr};font-size:22px;font-weight:700;'>{value}</div>
      <div style='color:{clr};font-size:10px;'>{label}</div></div>"""

def page_header(title, subtitle="", icon=""):
    # Small white Nyaka logo on the far right for per-page branding.
    import os as _os, base64 as _b64
    _logo_html = ""
    _lp = _os.path.join(_os.path.dirname(__file__), "..", "assets", "logo",
                        "nyaka_horizontal_white.png")
    if _os.path.exists(_lp):
        try:
            with open(_lp, "rb") as _f:
                _b64logo = _b64.b64encode(_f.read()).decode()
            _logo_html = (f"<img src='data:image/png;base64,{_b64logo}' "
                          f"style='height:30px;width:auto;opacity:0.92;"
                          f"flex-shrink:0;margin-left:16px;'/>")
        except Exception:
            _logo_html = ""
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,{C["purple_dk"]} 0%,
                {C["purple"]} 60%,{C["orange"]} 100%);
                border-radius:10px;padding:20px 26px;margin-bottom:20px;
                display:flex;align-items:center;justify-content:space-between;gap:16px;'>
      <div style='min-width:0;'>
        <div style='color:white;font-size:20px;font-weight:700;'>{icon} {title}</div>
        <div style='color:rgba(255,255,255,0.8);font-size:12px;margin-top:4px;'>{subtitle}</div>
      </div>
      {_logo_html}
    </div>""", unsafe_allow_html=True)

def section(label, color="purple"):
    clr = C.get(color, C["purple"])
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:10px;margin:18px 0 8px;'>
      <div style='width:18px;height:3px;background:{clr};border-radius:2px;'></div>
      <span style='font-weight:600;color:{clr};font-size:12px;text-transform:uppercase;
                   letter-spacing:0.06em;'>{label}</span>
      <div style='flex:1;height:1px;background:#EBEBEB;'></div>
    </div>""", unsafe_allow_html=True)

def safe_notice():
    st.markdown(f"""<div style='background:{C["orange_lt"]};border-left:3px solid {C["orange"]};
        padding:7px 12px;border-radius:4px;font-size:11px;color:{C["amber"]};margin-bottom:10px;'>
      🔒 <strong>Survivor-safe:</strong> No real names or exact locations displayed.
      Survivor tokens replace identifiers. Access is role-restricted and audited.
    </div>""", unsafe_allow_html=True)

def progress(label, actual, target, unit=""):
    pct = min(100, round(actual / target * 100)) if target else 0
    clr = C["green"] if pct >= 75 else C["amber"] if pct >= 50 else C["red"]
    return f"""<div style='margin-bottom:12px;'>
      <div style='display:flex;justify-content:space-between;font-size:11px;color:{C["grey"]};'>
        <span>{label}</span>
        <span style='font-weight:600;'>{actual:,.0f}/{target:,.0f}{" "+unit if unit else ""} ({pct}%)</span>
      </div>
      <div style='background:#EEEEEE;border-radius:4px;height:7px;margin-top:4px;'>
        <div style='background:{clr};width:{pct}%;height:7px;border-radius:4px;'></div>
      </div></div>"""

def risk_badge(level):
    clrs = {"high": (C["red"], C["red_lt"]), "medium": (C["amber"], C["amber_lt"]), "low": (C["green"], C["green_lt"])}
    clr, lt = clrs.get(level, (C["grey"], "#EEE"))
    labels  = {"high": "HIGH RISK", "medium": "MODERATE", "low": "LOWER RISK"}
    return f"<span style='background:{lt};color:{clr};font-size:9px;font-weight:700;padding:2px 8px;border-radius:10px;'>{labels.get(level,'?')}</span>"

# ── CHARTS ────────────────────────────────────────────────────────────────────
def line_area(df, x, y, title="", color=None, h=300, label=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], name=label or y,
        mode="lines+markers", line=dict(color=color or C["purple"], width=2.5),
        marker=dict(size=6), fill="tozeroy", fillcolor="rgba(91,45,142,0.07)"))
    fig.update_layout(**_base(title, h))
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(gridcolor="#EEEEEE")
    return fig

def multi_line(df, x, y_cols, names, colors, title="", h=320):
    fig = go.Figure()
    for y, name, color in zip(y_cols, names, colors):
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=name,
            mode="lines+markers", line=dict(color=color, width=2),
            marker=dict(size=5)))
    fig.update_layout(**_base(title, h), legend=dict(orientation="h", y=1.08))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#EEEEEE")
    return fig

def bar_v(df, x, y, title="", color=None, h=300, text=None):
    fig = px.bar(df, x=x, y=y, color_discrete_sequence=[color or C["purple"]], text=text)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(**_base(title, h))
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(gridcolor="#EEEEEE", title="")
    return fig

def bar_h(df, x, y, title="", color=None, h=300, color_col=None, color_map=None):
    if color_col:
        fig = px.bar(df, x=x, y=y, orientation="h", color=color_col,
                     color_discrete_map=color_map or {})
    else:
        fig = px.bar(df, x=x, y=y, orientation="h",
                     color_discrete_sequence=[color or C["purple"]])
    fig.update_traces(marker_line_width=0)
    fig.update_layout(**_base(title, h))
    fig.update_xaxes(gridcolor="#EEEEEE", title="")
    fig.update_yaxes(title="")
    return fig

def grouped_bar(df, x, y_cols, names, colors, title="", h=320):
    fig = go.Figure()
    for y, name, clr in zip(y_cols, names, colors):
        fig.add_trace(go.Bar(name=name, x=df[x], y=df[y], marker_color=clr))
    fig.update_layout(**_base(title, h), barmode="group",
                      legend=dict(orientation="h", y=1.08))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#EEEEEE")
    return fig

def stacked_bar(df, x, y_cols, names, colors, title="", h=320):
    fig = go.Figure()
    for y, name, clr in zip(y_cols, names, colors):
        fig.add_trace(go.Bar(name=name, x=df[x], y=df[y], marker_color=clr))
    fig.update_layout(**_base(title, h), barmode="stack",
                      legend=dict(orientation="h", y=1.08))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#EEEEEE")
    return fig

def donut(labels, values, title="", h=300, colors=None, hole=0.55):
    from config import C
    clrs = colors or [C["purple"],C["orange"],C["gold"],C["teal"],C["green"],
                      C["red"],C["blue"],C["grey"]]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=hole,
        marker=dict(colors=clrs[:len(labels)], line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=10)))
    fig.update_layout(**_base(title, h))
    return fig

def funnel(stages, values, title="", h=360):
    clrs = [C["purple"],C["orange"],C["gold"],C["teal"],C["green"],C["red"],C["blue"]]
    fig = go.Figure(go.Funnel(y=stages, x=values, textinfo="value+percent initial",
        marker=dict(color=clrs[:len(stages)]),
        connector=dict(line=dict(color="white", width=2))))
    fig.update_layout(**_base(title, h))
    return fig

def gauge(value, title, max_val=100, target=None, h=240):
    pct = min(value / max_val * 100, 100)
    clr = C["green"] if pct >= 75 else C["amber"] if pct >= 50 else C["red"]
    steps = [dict(range=[0,max_val*0.5],color=C["red_lt"]),
             dict(range=[max_val*0.5,max_val*0.75],color=C["orange_lt"]),
             dict(range=[max_val*0.75,max_val],color=C["green_lt"])]
    thresh = dict(line=dict(color=C["dark"],width=3),thickness=0.75,value=target) if target else None
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number=dict(suffix="%" if max_val==100 else "", font=dict(size=26, color=clr)),
        gauge=dict(axis=dict(range=[0,max_val]),bar=dict(color=clr,thickness=0.55),
                   steps=steps,threshold=thresh),
        title=dict(text=title, font=dict(size=12, color=C["dark"]))))
    fig.update_layout(height=h, margin=dict(l=24,r=24,t=48,b=16),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig

def heatmap_chart(z, x, y, title="", h=380, scale="Purples"):
    fig = go.Figure(go.Heatmap(z=z, x=x, y=y, colorscale=scale,
        showscale=True, text=z, texttemplate="%{text}", textfont=dict(size=9)))
    fig.update_layout(**_base(title, h, margin=dict(l=150,r=16,t=48,b=80)))
    fig.update_xaxes(tickangle=-30)
    return fig

def sankey(labels, src, tgt, vals, title="", h=460):
    nc = [f"rgba(91,45,142,{0.35+0.08*i})" for i in range(len(labels))]
    fig = go.Figure(go.Sankey(arrangement="snap",
        node=dict(pad=15,thickness=18,line=dict(color="white",width=0.5),
                  label=labels,color=nc),
        link=dict(source=src,target=tgt,value=vals,color="rgba(91,45,142,0.10)")))
    fig.update_layout(**_base(title, h))
    return fig

def scatter_map_px(df, title="", h=500, color_col=None, color_map=None, hover_data=None):
    gdf = df[df["lat"].notna() & df["lon"].notna()].copy()
    if gdf.empty:
        fig = go.Figure(); fig.update_layout(**_base(title+" (no GPS data)", h)); return fig
    kw = {}
    if color_col and color_col in gdf.columns:
        kw["color"] = color_col
        if color_map: kw["color_discrete_map"] = color_map
    kw_hover = hover_data or {}
    fig = px.scatter_mapbox(gdf, lat="lat", lon="lon", zoom=9, height=h,
                            mapbox_style="open-street-map", title=title,
                            hover_data=kw_hover, **kw)
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
    return fig

def density_map(df, title="", h=500):
    gdf = df[df["lat"].notna() & df["lon"].notna()].copy()
    if gdf.empty:
        fig = go.Figure(); fig.update_layout(**_base(title, h)); return fig
    fig = px.density_mapbox(gdf, lat="lat", lon="lon", radius=20, zoom=9, height=h,
                            mapbox_style="open-street-map", title=title,
                            color_continuous_scale="Reds")
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
    return fig

def pyramid(age_groups, male_counts, female_counts, title="Age-Sex Pyramid", h=420):
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Male", y=age_groups, x=[-v for v in male_counts],
                         orientation="h", marker_color=C["blue"]))
    fig.add_trace(go.Bar(name="Female", y=age_groups, x=female_counts,
                         orientation="h", marker_color=C["orange"]))
    max_v = max(max(male_counts or [1]), max(female_counts or [1]))
    fig.update_layout(**_base(title, h), barmode="relative",
                      xaxis=dict(tickvals=list(range(-max_v,max_v+1,max(1,max_v//5))),
                                 ticktext=[str(abs(v)) for v in range(-max_v,max_v+1,max(1,max_v//5))]),
                      legend=dict(orientation="h", y=1.05))
    return fig