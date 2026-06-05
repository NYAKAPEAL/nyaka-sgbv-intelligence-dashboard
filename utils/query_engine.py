"""
utils/query_engine.py
Offline natural-language query assistant for the Nyaka SGBV dashboard.

DESIGN (safe by construction):
- No LLM, no code generation, no code execution, no internet.
- A typed question is parsed for KEYWORDS, DATES, DISTRICTS, and CASE IDs.
- The parser routes to ONE of a fixed set of pre-built pandas functions.
- Every number returned is computed from the real data — nothing is invented.
- If no pattern matches, it says so and lists what it can answer.

This module is intentionally conservative: it would rather say "I can't answer
that precisely" than guess.
"""
import re
import pandas as pd
import numpy as np
from datetime import datetime

# ── month name lookup ─────────────────────────────────────────────────────────
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
DISTRICTS = ["kanungu", "rukungiri", "rubanda"]


# ─────────────────────────────────────────────────────────────────────────────
# PARSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _extract_dates(q):
    """Return (start_date, end_date, human_label) parsed from the question, or
    (None, None, None). Handles: 'March 2024', 'March to April 2024',
    'between March and April 2024', 'in 2025', 'Q1 2026', 'last month'."""
    ql = q.lower()
    year_matches = re.findall(r"\b(20\d{2})\b", ql)
    month_matches = [(m.start(), MONTHS[w]) for w in MONTHS
                     for m in re.finditer(rf"\b{w}\b", ql)]
    month_matches.sort()

    # Quarter: Q1 2026
    qmatch = re.search(r"\bq([1-4])\b", ql)
    if qmatch and year_matches:
        qn = int(qmatch.group(1)); yr = int(year_matches[0])
        start_m = (qn - 1) * 3 + 1
        start = pd.Timestamp(yr, start_m, 1)
        end = (start + pd.offsets.MonthEnd(3))
        return start, end, f"Q{qn} {yr}"

    # Two months → range (e.g. "March to April 2024")
    if len(month_matches) >= 2 and year_matches:
        yr = int(year_matches[-1])
        m1 = month_matches[0][1]; m2 = month_matches[1][1]
        start = pd.Timestamp(yr, m1, 1)
        end = pd.Timestamp(yr, m2, 1) + pd.offsets.MonthEnd(1)
        lbl = f"{pd.Timestamp(yr,m1,1):%B}–{pd.Timestamp(yr,m2,1):%B} {yr}"
        return start, end, lbl

    # Single month + year
    if len(month_matches) == 1 and year_matches:
        yr = int(year_matches[0]); m = month_matches[0][1]
        start = pd.Timestamp(yr, m, 1)
        end = start + pd.offsets.MonthEnd(1)
        return start, end, f"{start:%B %Y}"

    # Year only
    if year_matches and not month_matches:
        yr = int(year_matches[0])
        return pd.Timestamp(yr, 1, 1), pd.Timestamp(yr, 12, 31), str(yr)

    return None, None, None


def _extract_district(q):
    ql = q.lower()
    for d in DISTRICTS:
        if d in ql:
            return d.capitalize()
    return None


def _extract_case_id(q):
    """Find a case token like SRV-3DD68F7D or a raw 8-char hex."""
    m = re.search(r"\b(SRV-[0-9A-Fa-f]{8})\b", q)
    if m:
        return m.group(1).upper()
    m2 = re.search(r"\b([0-9A-Fa-f]{8})\b", q)
    if m2 and not re.search(r"20\d{2}", m2.group(1)):
        return f"SRV-{m2.group(1).upper()}"
    return None


def _date_filter(df, col, start, end):
    d = pd.to_datetime(df.get(col), errors="coerce")
    return df[(d >= start) & (d <= end)]


# ─────────────────────────────────────────────────────────────────────────────
# ANSWER FUNCTIONS  (each returns a dict: {answer, detail, table?})
# ─────────────────────────────────────────────────────────────────────────────
def _count_survivors(data, q):
    sv = data["survivors"]
    sv = sv[sv.get("report_category", "").str.contains("enrollment", na=False)] \
        if "report_category" in sv.columns else sv
    district = _extract_district(q)
    start, end, lbl = _extract_dates(q)
    if district and "district" in sv.columns:
        sv = sv[sv["district"].str.contains(district, na=False, case=False)]
    if start is not None:
        sv = _date_filter(sv, "date_enrolled", start, end)
    where = []
    if district: where.append(f"in {district}")
    if lbl: where.append(f"during {lbl}")
    where_str = " ".join(where) if where else "in total (all time)"
    return {"answer": f"{len(sv):,} survivors were supported {where_str}.",
            "detail": "Counted from survivor enrollment records."}


def _count_arrests(data, q):
    pp = data["perpetrators"]
    district = _extract_district(q)
    start, end, lbl = _extract_dates(q)
    if district and "district" in pp.columns:
        pp = pp[pp["district"].str.contains(district, na=False, case=False)]
    if start is not None and "date_enrolled" in pp.columns:
        pp = _date_filter(pp, "date_enrolled", start, end)
    arr = pp[pp.get("perpetrator_location_label", "").astype(str)
             .str.contains("Arrest", na=False)] if "perpetrator_location_label" in pp.columns else pp
    where = []
    if district: where.append(f"in {district}")
    if lbl: where.append(f"({lbl})")
    return {"answer": f"{len(arr):,} perpetrators were arrested "
                      f"{' '.join(where) if where else 'in total'}.",
            "detail": f"Out of {len(pp):,} perpetrator cases in that scope."}


def _count_perpetrators(data, q):
    pp = data["perpetrators"]
    district = _extract_district(q)
    start, end, lbl = _extract_dates(q)
    if district and "district" in pp.columns:
        pp = pp[pp["district"].str.contains(district, na=False, case=False)]
    if start is not None and "date_enrolled" in pp.columns:
        pp = _date_filter(pp, "date_enrolled", start, end)
    where = []
    if district: where.append(f"in {district}")
    if lbl: where.append(f"during {lbl}")
    return {"answer": f"{len(pp):,} perpetrator cases were registered "
                      f"{' '.join(where) if where else 'in total'}.",
            "detail": "Counted from perpetrator enrollment records."}


def _last_won(data, q):
    ppf = data["perp_followup"]
    if "case_status_overview" not in ppf.columns:
        return {"answer": "Case status data isn't available to answer that.",
                "detail": ""}
    won = ppf[ppf["case_status_overview"] == "Won"].copy()
    if not len(won):
        return {"answer": "No cases are marked as Won in the current data.", "detail": ""}
    won["d"] = pd.to_datetime(won["follow_up_date"], errors="coerce")
    won = won.sort_values("d", na_position="first")
    last = won.iloc[-1]
    when = last["d"]
    when_str = f"{when:%d %B %Y}" if pd.notna(when) else "an unrecorded date"
    dist = last.get("district", "")
    return {"answer": f"The most recent case won in court was on {when_str}"
                      + (f" in {dist}." if dist and str(dist) != 'nan' else "."),
            "detail": f"{len(won):,} cases have been won in total."}


def _count_won(data, q):
    ppf = data["perp_followup"]
    start, end, lbl = _extract_dates(q)
    won = ppf[ppf.get("case_status_overview", "") == "Won"].copy()
    if start is not None:
        won = _date_filter(won, "follow_up_date", start, end)
    return {"answer": f"{len(won):,} cases were won "
                      f"{('during ' + lbl) if lbl else 'in total'}.",
            "detail": "A 'won' case is one with a court conviction outcome recorded."}


def _outreach_stats(data, q):
    ot = data["outreach"]
    district = _extract_district(q)
    start, end, lbl = _extract_dates(q)
    if district and "district" in ot.columns:
        ot = ot[ot["district"].str.contains(district, na=False, case=False)]
    if start is not None:
        ot = _date_filter(ot, "date", start, end)
    reached = int(ot["total"].sum()) if "total" in ot.columns else 0
    where = []
    if district: where.append(f"in {district}")
    if lbl: where.append(f"during {lbl}")
    ws = " ".join(where) if where else "in total"
    return {"answer": f"{len(ot):,} outreach sessions were held {ws}, "
                      f"reaching approximately {reached:,} people.",
            "detail": "Counted from community outreach records."}


def _case_lookup(data, q):
    token = _extract_case_id(q)
    pp = data["perpetrators"]
    if not token or "survivor_token" not in pp.columns:
        return {"answer": "I couldn't find a case ID in your question. "
                          "Case IDs look like SRV-3DD68F7D.", "detail": ""}
    match = pp[pp["survivor_token"] == token]
    if not len(match):
        return {"answer": f"No case found with ID {token}.",
                "detail": "Check the token — it should look like SRV-3DD68F7D."}
    r = match.iloc[0]
    rows = []
    def add(label, val):
        if pd.notna(val) and str(val) not in ("", "nan"):
            rows.append((label, str(val)))
    add("Case ID", token)
    add("Violence type", r.get("assault_label"))
    add("District", r.get("district"))
    add("Subcounty", r.get("subcounty_label"))
    add("Date enrolled", str(r.get("date_enrolled", ""))[:10])
    add("Perpetrator status", r.get("perpetrator_location_label"))
    add("Perpetrator relation", r.get("perpetrator_relation_label"))
    add("Last case status", r.get("last_status"))
    if "days_since_update" in r and pd.notna(r.get("days_since_update")):
        add("Days since last update", int(r["days_since_update"]))
    add("Follow-ups recorded", int(r.get("n_followups", 0)) if pd.notna(r.get("n_followups")) else 0)
    return {"answer": f"Case {token} — {r.get('assault_label','case')} in "
                      f"{r.get('district','')}.",
            "detail": "", "table": rows}


def _breakdown(data, q):
    """Breakdowns by district/violence type for survivors."""
    sv = data["survivors"]
    sv = sv[sv.get("report_category", "").str.contains("enrollment", na=False)] \
        if "report_category" in sv.columns else sv
    ql = q.lower()
    if "violence" in ql or "type" in ql or "defilement" in ql or "rape" in ql:
        col = next((c for c in ["assault_label", "violence_type"] if c in sv.columns), None)
        title = "survivors by violence type"
    else:
        col = "district" if "district" in sv.columns else None
        title = "survivors by district"
    if not col:
        return {"answer": "I can't break that down with the available fields.", "detail": ""}
    vc = sv[col].value_counts().head(8)
    rows = [(str(k), f"{v:,}") for k, v in vc.items()]
    return {"answer": f"Breakdown of {title}:", "detail": "", "table": rows}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
def answer_query(question, data):
    """Main entry. Returns a result dict. Pure keyword routing — no LLM."""
    if not question or not question.strip():
        return {"answer": "Type a question above to begin.", "detail": ""}
    q = question.strip()
    ql = q.lower()

    # 1. Case ID lookup takes priority if an ID is present
    if _extract_case_id(q) and any(w in ql for w in
                                    ["case", "lookup", "look up", "find", "show", "srv", "id"]):
        return _case_lookup(data, q)
    if re.search(r"\bSRV-[0-9A-Fa-f]{8}\b", q):
        return _case_lookup(data, q)

    # 2. "last ... won" / "when was ... won"
    if "won" in ql and any(w in ql for w in ["last", "when", "recent", "latest"]):
        return _last_won(data, q)
    if ("won" in ql or "conviction" in ql or "convicted" in ql) and \
       any(w in ql for w in ["how many", "number", "count", "total"]):
        return _count_won(data, q)
    if "won" in ql:
        return _count_won(data, q)

    # 3. arrests
    if "arrest" in ql:
        return _count_arrests(data, q)

    # 4. outreach / reached / sessions
    if any(w in ql for w in ["outreach", "reached", "sensitiz", "sensitis",
                              "community session", "awareness"]):
        return _outreach_stats(data, q)

    # 5. perpetrators (cases/registered) — before survivors since 'case' is generic
    if any(w in ql for w in ["perpetrator", "suspect", "offender", "accused"]):
        return _count_perpetrators(data, q)

    # 6. breakdown requests
    if any(w in ql for w in ["breakdown", "by district", "by type", "by violence",
                              "distribution", "how many in each"]):
        return _breakdown(data, q)

    # 7. survivors (default count subject)
    if any(w in ql for w in ["survivor", "supported", "enrolled", "helped",
                              "client", "victim"]):
        return _count_survivors(data, q)

    # 8. bare "how many" with a date/district → assume survivors
    if any(w in ql for w in ["how many", "count", "number", "total"]):
        return _count_survivors(data, q)

    # No match
    return {"answer": "I couldn't match that to a question I can answer precisely, "
                      "so I won't guess.",
            "detail": "", "no_match": True}


# Suggested example questions (shown in the UI)
EXAMPLE_QUESTIONS = [
    "How many survivors were supported between March and April 2024?",
    "When was the last case won in court?",
    "How many perpetrators were arrested in Kanungu?",
    "How many outreach sessions in Q1 2026?",
    "Survivors by violence type",
    "How many cases were won in 2025?",
]


def _load_query_data():
    """Load the data the query engine needs. Cached by the caller."""
    def _try(p):
        try:
            return pd.read_csv(p, low_memory=False)
        except Exception:
            return pd.DataFrame()
    return {
        "survivors":     _try("data/survivors.csv"),
        "perpetrators":  _try("data/perpetrators_narrative.csv"),
        "perp_followup": _try("data/perpetrators_followup.csv"),
        "outreach":      _try("data/outreach.csv"),
        "school":        _try("data/school_social_work.csv"),
    }


def render_sidebar_assistant(st, C):
    """Render the offline query assistant in the Streamlit sidebar.
    Pass the streamlit module and the colour dict C from config."""
    import streamlit as _st  # noqa

    @_st.cache_data(ttl=300, show_spinner=False)
    def _cached_data():
        return _load_query_data()

    with st.sidebar.expander("💬 Ask the data (offline)", expanded=False):
        st.caption("Type a question about survivors, cases, arrests, or outreach. "
                   "Answers are computed from the data — nothing is invented.")

        q = st.text_input("Your question", key="ai_query_box",
                          placeholder="e.g. survivors supported in March 2025")

        # Quick-tap example chips
        st.caption("Or tap an example:")
        for i, ex in enumerate(EXAMPLE_QUESTIONS[:4]):
            if st.button(ex, key=f"ai_ex_{i}", use_container_width=True):
                q = ex
                st.session_state["ai_query_box"] = ex

        if q and q.strip():
            try:
                data = _cached_data()
                res = answer_query(q, data)
                # Answer card
                bg = C["red_lt"] if res.get("no_match") else C["purple_lt"]
                brd = C["red"] if res.get("no_match") else C["purple"]
                st.markdown(f"""
                <div style='background:{bg};border-left:3px solid {brd};
                            border-radius:0 6px 6px 0;padding:9px 12px;
                            font-size:12px;color:{C["dark"]};margin-top:6px;line-height:1.5;'>
                  {res["answer"]}
                </div>""", unsafe_allow_html=True)
                if res.get("detail"):
                    st.caption(res["detail"])
                if res.get("table"):
                    for k, v in res["table"]:
                        st.markdown(f"<div style='font-size:11px;display:flex;"
                                    f"justify-content:space-between;padding:2px 0;'>"
                                    f"<span style='color:{C['grey']};'>{k}</span>"
                                    f"<span style='font-weight:600;'>{v}</span></div>",
                                    unsafe_allow_html=True)
                if res.get("no_match"):
                    st.caption("Try one of the example questions above, or rephrase "
                               "using words like survivors, arrested, won, outreach, "
                               "a month/year, or a district.")
            except Exception as e:
                st.caption(f"Could not process that question. ({e})")
