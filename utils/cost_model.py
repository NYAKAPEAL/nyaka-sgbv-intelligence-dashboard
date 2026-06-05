"""
utils/cost_model.py
Central cost engine for Nyaka SGBV programme.
All unit costs in UGX. Supports min/avg/max range outputs.

PURPOSE: Investment efficiency and scale decision intelligence — NOT accounting.
PRINCIPLE: Range-based, no double-counting, proportional shared-cost allocation.
"""

# ─────────────────────────────────────────────────────────────────────────────
# UNIT COSTS (UGX)  — all sourced from Nyaka programme financial records
# ─────────────────────────────────────────────────────────────────────────────

# Survivor pathway
MEDICAL_EXAM            = 50_000        # per exam (fixed)
MEDICATION_MIN          = 30_000        # drugs per treatment episode
MEDICATION_MAX          = 50_000
MEDICAL_CARE_EXTRA_MIN  = 20_000        # scans, lab tests, dressings (when needed)
MEDICAL_CARE_EXTRA_MAX  = 80_000
SANITARY_SUPPLIES       = 15_000        # pads, knickers, basic aid materials per survivor
AID_MATERIALS_OTHER     = 20_000        # other aid materials (blankets, soap, etc.) when issued
FOLLOWUP_TRANSPORT_MIN  = 20_000        # per case-manager follow-up visit (boda / taxi)
FOLLOWUP_TRANSPORT_MAX  = 30_000
# Survivors are followed up until their PTSD/PTSS score falls below 20%. The
# number of visits to reach that threshold varies — modelled as a range.
PSTD_FOLLOWUPS_MIN      = 4             # visits to reach <20% PTSD (faster recovery)
PSTD_FOLLOWUPS_MAX      = 10            # visits to reach <20% PTSD (complex trauma)
INTAKE_ADMIN            = 15_000        # staff time, stationery, printing

# Court / justice (survivor side)
COURT_TRANSPORT         = 100_000       # per court trip for survivor to testify (return)
COURT_TRIPS_MIN         = 2
COURT_TRIPS_MAX         = 3

# Legal / enforcement — ARREST (corrected per programme records)
POLICE_ARREST_FEE       = 30_000        # paid to police officer to effect the arrest
SUSPECT_TRANSPORT_CPS   = 30_000        # transport suspect from local post → CPS
ARREST_BASE_COST        = POLICE_ARREST_FEE + SUSPECT_TRANSPORT_CPS   # = 60,000 per arrest

# Juvenile-only cost (kept SEPARATE so it doesn't inflate the average arrest)
JUVENILE_REMAND_TRANSP  = 200_000       # transport juvenile suspect → Kabale remand home
JUVENILE_SHARE_ASSUMED  = 0.05          # assumed share of arrests that are juveniles (VERIFY)

# Legal case follow-up (justice outcome)
POLICE_SCENE_REPORT     = 30_000        # scene-of-crime / police report facilitation
MEDICAL_REPORT_PF3      = 30_000        # medical report (Police Form 3) facilitation
LEGAL_COORD_MONTHLY     = 120_000       # legal advocate case coordination per month per case
LEGAL_FOLLOWUP_MONTHS_MIN = 2           # months of advocate follow-up per case (min)
LEGAL_FOLLOWUP_MONTHS_MAX = 6           # months of advocate follow-up per case (max)

# Outreach / prevention
OUTREACH_TRANSPORT      = 40_000        # per session (fuel / hire)
OUTREACH_LUNCH          = 10_000        # per session (team)
WORKSHOP_FUEL           = 200_000       # fixed per workshop session
WORKSHOP_MAINTENANCE    = 100_000       # vehicle maintenance allocation
WORKSHOP_PER_PARTICIPANT= 100_000       # variable per participant (FIXED)
RADIO_AIRTIME_MIN       = 800_000       # per talk show
RADIO_AIRTIME_MAX       = 1_000_000
RADIO_ACCOMMODATION     = 60_000        # staff overnight
RADIO_MEALS             = 30_000        # per staff day
RADIO_STAFF_TRANSPORT   = 50_000        # per staff per trip (2–3 staff)
SCHOOL_VISIT_TRANSPORT  = 50_000        # per school visit
SCHOOL_VISIT_FOOD       = 10_000        # per day
SCHOOL_AIRTIME_MONTHLY  = 50_000        # mobile data/airtime allocation

# Healing centre operations (monthly)
LEGAL_ADVOCATE_SALARY   = 1_500_000     # per month per centre
MOTORCYCLE_PURCHASE     = 8_000_000     # amortized over 5 years = 133,333/month
MOTORCYCLE_AMORT_MONTHLY = 8_000_000 // (5 * 12)   # = 133,333
MOTORCYCLE_MAINT_MONTHLY = 50_000
MOTORCYCLE_REPAIR_QTRLY  = 300_000      # = 100,000/month amortized
MOTORCYCLE_REPAIR_MONTHLY = 300_000 // 3

CASE_MANAGER_TRANSPORT   = 80_000       # per month allocation
OUTREACH_LINKAGE         = 150_000      # outreach support allocation per month
CENTRE_SETUP_ONE_TIME    = 5_000_000    # one-time setup (furniture, materials, signage)
CENTRE_ADMIN_MONTHLY     = 200_000      # stationery, printing, comms

# Expansion (Rubanda model)
RUBANDA_MOTORCYCLE       = 8_000_000
RUBANDA_SETUP            = 5_000_000
RUBANDA_STAFF_SETUP      = 500_000      # recruitment, training, onboarding
RUBANDA_EXPECTED_MONTHLY_SURVIVORS = 25  # conservative estimate
RUBANDA_RAMP_MONTHS      = 6            # months to full capacity

# Shared system costs (allocated proportionally across all outputs)
PROGRAMME_MANAGER_SALARY = 4_500_000    # per month
MEL_OFFICER_SALARY       = 2_500_000    # per month
VEHICLES_RUNNING_MONTHLY = 800_000      # programme vehicle(s)
COMMS_IT_MONTHLY         = 200_000      # internet, phone, software
TOTAL_SHARED_MONTHLY     = (PROGRAMME_MANAGER_SALARY + MEL_OFFICER_SALARY +
                             VEHICLES_RUNNING_MONTHLY + COMMS_IT_MONTHLY)

# Allocation weights for shared costs
SHARED_ALLOC = {
    "survivor_pathway":  0.40,   # 40% of shared to direct case work
    "legal":             0.25,   # 25% to legal/enforcement
    "outreach":          0.25,   # 25% to prevention/outreach
    "management":        0.10,   # 10% unallocated management
}

# Number of healing centres
N_CENTRES = 5

# Annual throughput (from real data)
ANNUAL_SURVIVORS      = 2031
ANNUAL_ARRESTS        = 571
ANNUAL_OUTREACH_SESS  = 1863
ANNUAL_SCHOOL_SESS    = 818
ANNUAL_STUDENTS_REACHED = 16464

# ─────────────────────────────────────────────────────────────────────────────
# COST FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def survivor_cost(include_shared: bool = True) -> dict:
    """
    Per-survivor support cost: all case-manager follow-ups until the survivor's
    PTSD/PTSS score falls below 20%, plus medical examination, medical care
    (drugs/scans), sanitary supplies (pads/knickers) and other aid materials.
    NOTE: this is the SUPPORT cost. Court/justice costs are NOT here — they live
    in justice_outcome_cost() to avoid double counting.
    Returns min / avg / max in UGX.
    """
    shared_per_survivor = (TOTAL_SHARED_MONTHLY * SHARED_ALLOC["survivor_pathway"]
                           * 12) / ANNUAL_SURVIVORS if ANNUAL_SURVIVORS else 0

    intake        = INTAKE_ADMIN + MEDICAL_EXAM
    # Case-manager follow-ups until PTSD < 20%
    followup_min  = FOLLOWUP_TRANSPORT_MIN * PSTD_FOLLOWUPS_MIN
    followup_max  = FOLLOWUP_TRANSPORT_MAX * PSTD_FOLLOWUPS_MAX
    # Medical care
    medication_min = MEDICATION_MIN
    medication_max = MEDICATION_MAX + MEDICAL_CARE_EXTRA_MAX   # drugs + scans/labs
    # Materials (most survivors receive these)
    materials     = SANITARY_SUPPLIES + AID_MATERIALS_OTHER

    total_min = intake + followup_min + medication_min + SANITARY_SUPPLIES
    total_max = intake + followup_max + medication_max + materials
    total_avg = (total_min + total_max) / 2

    if include_shared:
        total_min += shared_per_survivor
        total_max += shared_per_survivor
        total_avg += shared_per_survivor

    return {
        "min": round(total_min),
        "avg": round(total_avg),
        "max": round(total_max),
        "stages": {
            "Intake & medical exam":            intake,
            "Case-manager follow-ups (min, 4 visits)": followup_min,
            "Case-manager follow-ups (max, 10 visits)": followup_max,
            "Medication / drugs":               medication_min,
            "Medical care extra (scans, labs)": MEDICAL_CARE_EXTRA_MAX,
            "Sanitary supplies (pads, knickers)": SANITARY_SUPPLIES,
            "Other aid materials":              AID_MATERIALS_OTHER,
            "Shared system (allocated)":        round(shared_per_survivor) if include_shared else 0,
        },
        "note": ("Covers support until PTSD score falls below 20%. Follow-up count "
                 "varies (4–10 visits) by trauma severity. Court/justice costs are "
                 "tracked separately under Cost per Justice Outcome."),
    }


def arrest_cost() -> dict:
    """
    Cost per ARREST only — the act of arresting and moving the suspect to CPS.
    Per Nyaka records: UGX 30,000 police facilitation + UGX 30,000 transport
    from local post to Central Police Station = UGX 60,000 base.
    Juvenile remand transport is NOT averaged in here (see juvenile_cost()).
    """
    base = ARREST_BASE_COST   # 60,000 — fixed, applies to every arrest
    return {
        "min": base,
        "avg": base,
        "max": base,
        "components": {
            "Police facilitation to arrest":     POLICE_ARREST_FEE,
            "Transport suspect → CPS":            SUSPECT_TRANSPORT_CPS,
        },
        "note": ("Flat UGX 60,000 per arrest (30k police facilitation + 30k "
                 "transport to CPS). Juvenile remand transport to Kabale is "
                 "excluded here and shown separately, as it applies to only a "
                 "small number of cases and would otherwise inflate the average."),
    }


def juvenile_cost() -> dict:
    """
    Separate cost line for juvenile suspects who must be transported to the
    Kabale remand home. Kept apart so it does not inflate the average arrest cost.
    """
    per_juvenile = ARREST_BASE_COST + JUVENILE_REMAND_TRANSP   # 60k + 200k = 260k
    est_juveniles = round(ANNUAL_ARRESTS * JUVENILE_SHARE_ASSUMED)
    return {
        "per_juvenile_case": per_juvenile,
        "remand_transport":  JUVENILE_REMAND_TRANSP,
        "assumed_share":     JUVENILE_SHARE_ASSUMED,
        "estimated_count":   est_juveniles,
        "note": (f"Juvenile suspects incur the standard UGX 60,000 arrest cost PLUS "
                 f"UGX 200,000 transport to the Kabale remand home (UGX 260,000 total). "
                 f"Assumed at {JUVENILE_SHARE_ASSUMED*100:.0f}% of arrests "
                 f"(~{est_juveniles} cases/yr) — VERIFY against actual juvenile records."),
    }


def justice_outcome_cost() -> dict:
    """
    Cost per JUSTICE OUTCOME (case pursued to court), EXCLUDING juveniles.
    Includes: arrest costs + legal advocate case follow-up + police reports
    (scene-of-crime + medical/PF3) + survivor facilitation to attend & testify.
    """
    shared = (TOTAL_SHARED_MONTHLY * SHARED_ALLOC["legal"] * 12) / max(ANNUAL_ARRESTS, 1)

    arrest      = ARREST_BASE_COST
    reports     = POLICE_SCENE_REPORT + MEDICAL_REPORT_PF3        # 60,000
    advocate_min = LEGAL_COORD_MONTHLY * LEGAL_FOLLOWUP_MONTHS_MIN  # 2 months
    advocate_max = LEGAL_COORD_MONTHLY * LEGAL_FOLLOWUP_MONTHS_MAX  # 6 months
    court_min   = COURT_TRANSPORT * COURT_TRIPS_MIN              # survivor testimony trips
    court_max   = COURT_TRANSPORT * COURT_TRIPS_MAX

    total_min = arrest + reports + advocate_min + court_min + shared
    total_max = arrest + reports + advocate_max + court_max + shared
    return {
        "min": round(total_min),
        "avg": round((total_min + total_max) / 2),
        "max": round(total_max),
        "components": {
            "Arrest (police + transport to CPS)": arrest,
            "Police reports (scene + medical/PF3)": reports,
            "Legal advocate follow-up (2–6 months)": f"{advocate_min:,}–{advocate_max:,}",
            "Survivor court facilitation (2–3 trips)": f"{court_min:,}–{court_max:,}",
            "Shared legal system (allocated)":    round(shared),
        },
        "note": ("Cost to pursue a case to court, EXCLUDING juveniles. Combines the "
                 "arrest cost, police scene-of-crime and medical reports, the legal "
                 "advocate's months of case follow-up, and facilitating the survivor "
                 "to attend court and testify."),
    }


def outreach_cost(session_type: str = "community") -> dict:
    """
    Cost per outreach session by type.
    Types: community, workshop, radio, school
    """
    if session_type == "community":
        fixed = OUTREACH_TRANSPORT + OUTREACH_LUNCH
        return {"min": fixed, "avg": fixed, "max": fixed,
                "label": "Community outreach session",
                "components": {"Transport": OUTREACH_TRANSPORT, "Lunch": OUTREACH_LUNCH}}

    elif session_type == "workshop":
        fixed = WORKSHOP_FUEL + WORKSHOP_MAINTENANCE
        return {"min": fixed, "avg": fixed + WORKSHOP_PER_PARTICIPANT * 15,
                "max": fixed + WORKSHOP_PER_PARTICIPANT * 30,
                "per_participant": WORKSHOP_PER_PARTICIPANT,
                "label": "Training workshop",
                "components": {"Fuel": WORKSHOP_FUEL, "Maintenance": WORKSHOP_MAINTENANCE,
                                "Per participant (variable)": WORKSHOP_PER_PARTICIPANT}}

    elif session_type == "radio":
        min_cost = RADIO_AIRTIME_MIN + RADIO_ACCOMMODATION + RADIO_MEALS + (RADIO_STAFF_TRANSPORT * 2)
        max_cost = RADIO_AIRTIME_MAX + RADIO_ACCOMMODATION + RADIO_MEALS + (RADIO_STAFF_TRANSPORT * 3)
        return {"min": min_cost, "avg": round((min_cost+max_cost)/2), "max": max_cost,
                "label": "Radio talk show",
                "components": {
                    "Airtime": f"{RADIO_AIRTIME_MIN:,}–{RADIO_AIRTIME_MAX:,}",
                    "Accommodation": RADIO_ACCOMMODATION,
                    "Meals": RADIO_MEALS,
                    "Staff transport (2–3 staff)": f"{RADIO_STAFF_TRANSPORT*2:,}–{RADIO_STAFF_TRANSPORT*3:,}",
                }}

    elif session_type == "school":
        daily = SCHOOL_VISIT_TRANSPORT + SCHOOL_VISIT_FOOD
        monthly_fixed = SCHOOL_AIRTIME_MONTHLY
        per_student = round(daily / 60)   # assume avg 60 students per visit
        return {"min": daily, "avg": daily + monthly_fixed / 20, "max": daily * 2,
                "per_student": per_student,
                "label": "School outreach visit",
                "components": {"Transport": SCHOOL_VISIT_TRANSPORT,
                                "Food": SCHOOL_VISIT_FOOD,
                                "Airtime (monthly allocation)": SCHOOL_AIRTIME_MONTHLY}}
    return {}


def healing_center_cost(survivors_served_monthly: int = None) -> dict:
    """
    Monthly operating cost per healing centre.
    """
    if survivors_served_monthly is None:
        survivors_served_monthly = round(ANNUAL_SURVIVORS / N_CENTRES / 12)

    monthly_fixed = (LEGAL_ADVOCATE_SALARY + MOTORCYCLE_AMORT_MONTHLY +
                     MOTORCYCLE_MAINT_MONTHLY + MOTORCYCLE_REPAIR_MONTHLY +
                     CASE_MANAGER_TRANSPORT + OUTREACH_LINKAGE + CENTRE_ADMIN_MONTHLY)

    cost_per_survivor = round(monthly_fixed / max(survivors_served_monthly, 1))

    return {
        "monthly_total": monthly_fixed,
        "cost_per_survivor": cost_per_survivor,
        "annualised": monthly_fixed * 12,
        "components": {
            "Legal advocate salary":       LEGAL_ADVOCATE_SALARY,
            "Motorcycle (amortised)":      MOTORCYCLE_AMORT_MONTHLY,
            "Motorcycle maintenance":      MOTORCYCLE_MAINT_MONTHLY,
            "Motorcycle repair (monthly)": MOTORCYCLE_REPAIR_MONTHLY,
            "Case manager transport":      CASE_MANAGER_TRANSPORT,
            "Outreach linkage":            OUTREACH_LINKAGE,
            "Admin / stationery":          CENTRE_ADMIN_MONTHLY,
        }
    }


def expansion_cost(target_district: str = "Rubanda",
                   expected_monthly_survivors: int = None) -> dict:
    """
    One-time and ongoing cost to open a new healing centre in a new district.
    """
    if expected_monthly_survivors is None:
        expected_monthly_survivors = RUBANDA_EXPECTED_MONTHLY_SURVIVORS

    one_time = RUBANDA_MOTORCYCLE + RUBANDA_SETUP + RUBANDA_STAFF_SETUP
    monthly_ops = healing_center_cost(expected_monthly_survivors)["monthly_total"]
    annual_ops  = monthly_ops * 12
    total_year1 = one_time + annual_ops

    break_even_cost_per_survivor = round(total_year1 / (expected_monthly_survivors * 12))
    steady_state_cps = round(monthly_ops / max(expected_monthly_survivors, 1))

    return {
        "district":                target_district,
        "one_time_setup":          one_time,
        "monthly_operating":       monthly_ops,
        "annual_operating":        annual_ops,
        "total_year_1":            total_year1,
        "expected_monthly_survivors": expected_monthly_survivors,
        "cost_per_survivor_year1": break_even_cost_per_survivor,
        "cost_per_survivor_steady": steady_state_cps,
        "ramp_months":             RUBANDA_RAMP_MONTHS,
        "one_time_components": {
            "Motorcycle":             RUBANDA_MOTORCYCLE,
            "Centre setup":           RUBANDA_SETUP,
            "Staff onboarding":       RUBANDA_STAFF_SETUP,
        }
    }


def cost_drivers_breakdown() -> dict:
    """
    Proportional breakdown of total programme cost by driver category.
    Used for donut/bar chart in dashboard.
    """
    # Annual estimates
    salaries     = (LEGAL_ADVOCATE_SALARY * N_CENTRES + PROGRAMME_MANAGER_SALARY +
                    MEL_OFFICER_SALARY) * 12
    transport    = ((MOTORCYCLE_AMORT_MONTHLY + MOTORCYCLE_MAINT_MONTHLY +
                     MOTORCYCLE_REPAIR_MONTHLY + CASE_MANAGER_TRANSPORT +
                     VEHICLES_RUNNING_MONTHLY) * 12 +
                    OUTREACH_TRANSPORT * ANNUAL_OUTREACH_SESS +
                    COURT_TRANSPORT * COURT_TRIPS_MIN * ANNUAL_SURVIVORS * 0.4)
    legal        = (SUSPECT_TRANSPORT_CPS * ANNUAL_ARRESTS +
                    JUVENILE_REMAND_TRANSP * ANNUAL_ARRESTS * 0.1 +
                    LEGAL_COORD_MONTHLY * ANNUAL_ARRESTS * 2)
    outreach_act = (OUTREACH_TRANSPORT + OUTREACH_LUNCH) * ANNUAL_OUTREACH_SESS
    medical      = (MEDICAL_EXAM + MEDICATION_MIN * 0.4) * ANNUAL_SURVIVORS
    admin_it     = (COMMS_IT_MONTHLY + CENTRE_ADMIN_MONTHLY * N_CENTRES) * 12

    total = salaries + transport + legal + outreach_act + medical + admin_it
    return {
        "Salaries":                round(salaries),
        "Transport & logistics":   round(transport),
        "Legal actions":           round(legal),
        "Outreach activities":     round(outreach_act),
        "Medical / clinical":      round(medical),
        "Administration & IT":     round(admin_it),
        "total":                   round(total),
    }


def workshop_cost_for_n(n_participants: int) -> int:
    """Total cost for a workshop with n participants."""
    fixed = WORKSHOP_FUEL + WORKSHOP_MAINTENANCE
    return fixed + (WORKSHOP_PER_PARTICIPANT * n_participants)


def format_ugx(amount: int, short: bool = False) -> str:
    """Format UGX amount for display."""
    if short:
        if amount >= 1_000_000_000:
            return f"UGX {amount/1_000_000_000:.1f}B"
        if amount >= 1_000_000:
            return f"UGX {amount/1_000_000:.1f}M"
        if amount >= 1_000:
            return f"UGX {amount/1_000:.0f}K"
    return f"UGX {amount:,.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# DISTANCE INTELLIGENCE — confirmed from GPS data + verified facility coords
# ─────────────────────────────────────────────────────────────────────────────
DISTANCE_FACTS = {
    # From real computation on 1,169 survivor GPS records
    "survivor_to_healing_mean_km":      12.0,
    "survivor_to_healing_median_km":    11.5,
    "survivor_to_healing_pct_within_10": 36,
    "survivor_to_healing_pct_within_20": 96,
    # Counterfactual — nearest public hospital without Nyaka specialised HCs
    # NOTE: Public hospitals are more numerous but provide no SGBV-specific
    # care (no legal advocacy, case management, or justice pathway support)
    "survivor_to_public_hosp_mean_km":  9.5,
    "survivor_to_public_hosp_median_km": 3.9,
    # Counterfactual distance to SGBV-equivalent care (nearest Kampala/Mbarara)
    "survivor_to_specialist_no_nyaka_km": 125,   # Kabale or Mbarara (nearest equiv.)
    # Court distances
    "survivor_to_court_mean_km":        16.8,
    "survivor_to_court_median_km":      14.7,
    # Perpetrator to CPS
    "perp_to_nearest_cps_mean_km":      11.1,
    "perp_to_rukungiri_cps_mean_km":    17.7,
    "perp_to_kanungu_cps_mean_km":      18.0,
    "perp_to_rubanda_cps_mean_km":      54.8,
}

# Verified facility coordinates (confirmed via Wikipedia, judiciary.go.ug, monitor.co.ug)
FACILITY_COORDS = {
    "Rukungiri CPS":                   {"lat":-0.7900,"lon":29.9250,"type":"police","district":"Rukungiri"},
    "Kanungu CPS":                     {"lat":-0.8970,"lon":29.7756,"type":"police","district":"Kanungu"},
    "Rubanda CPS":                     {"lat":-1.1864,"lon":29.8433,"type":"police","district":"Rubanda"},
    "Rukungiri High Court":            {"lat":-0.7900,"lon":29.9250,"type":"court", "district":"Rukungiri",
                                        "note":"Serves Rukungiri & Kanungu. Opened Feb 2023."},
    "Kanungu Grade I Court":           {"lat":-0.8970,"lon":29.7756,"type":"court", "district":"Kanungu",
                                        "note":"No High Court. HC cases → Rukungiri (43km)."},
    "Kabale High Court":               {"lat":-1.2508,"lon":29.9843,"type":"court", "district":"Kabale",
                                        "note":"Serves Rubanda, Kabale & Rukiga. Rubanda has no HC."},
    "Kambuga Healing Centre":          {"lat":-0.813902,"lon":29.800839,"type":"healing","district":"Kanungu"},
    "Kihihi Healing Centre":           {"lat":-0.748620,"lon":29.696700,"type":"healing","district":"Kanungu"},
    "Kanungu Healing Centre":          {"lat":-0.896950,"lon":29.775560,"type":"healing","district":"Kanungu"},
    "Kebisoni Healing Centre":         {"lat":-0.857400,"lon":30.015430,"type":"healing","district":"Rukungiri"},
    "Nyamirama Healing Centre":        {"lat":-0.701070,"lon":29.768360,"type":"healing","district":"Rukungiri"},
    "Kambuga General Hospital":        {"lat":-0.8139,"lon":29.8008,"type":"hospital","district":"Kanungu",
                                        "note":"Wikipedia confirmed: 0°48'50\"S 29°48'03\"E"},
}