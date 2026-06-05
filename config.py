"""config.py — Nyaka SGBV Intelligence Platform — Global Configuration"""

# ── BRAND ─────────────────────────────────────────────────────────────────────
C = {
    "purple":     "#5B2D8E", "purple_dk":  "#3C1A6B", "purple_md":  "#7B52B5",
    "purple_lt":  "#EDE7F6", "purple_xlt": "#F5F2FC",
    "orange":     "#E07B29", "orange_lt":  "#FFF3E0",
    "gold":       "#C9A84C", "gold_lt":    "#FFFDE7",
    "green":      "#2E7D32", "green_lt":   "#E8F5E9",
    "teal":       "#00695C", "teal_lt":    "#E0F2F1",
    "red":        "#C62828", "red_lt":     "#FFEBEE",
    "amber":      "#E65100", "amber_lt":   "#FFF3E0",
    "blue":       "#1565C0", "blue_lt":    "#E3F2FD",
    "grey":       "#546E7A", "light":      "#F8F6FF",
    "white":      "#FFFFFF", "dark":       "#1A1A2E",
}

# Operational districts
DISTRICTS        = ["Kanungu", "Rukungiri", "Rubanda"]
DISTRICT_CENTRES = {
    "Kanungu":   {"lat": -0.878, "lon": 29.774, "zoom": 10},
    "Rukungiri": {"lat": -0.835, "lon": 29.948, "zoom": 10},
    "Rubanda":   {"lat": -1.188, "lon": 29.847, "zoom": 11},
}
DEFAULT_MAP_CENTRE = {"lat": -0.85, "lon": 29.85, "zoom": 9}

HEALING_CENTRES = [
    "Kambuga Healing Center", "Kihihi Healing Center",
    "Kanungu Healing Center", "Kebisoni Healing Center",
    "Nyamirama Healing Center",
]

VIOLENCE_TYPES = [
    "Defilement", "Rape", "Physical assault", "Child neglect/abuse",
    "Sexual assault", "Denied resources", "Early marriage",
    "Emotional/Psychological abuse", "Other",
]

PERPETRATOR_RELATIONS = [
    "Father/Mother", "Sibling", "Spouse", "Uncle/Aunt", "Grandparent",
    "Teacher", "Neighbor", "Stranger/Unknown", "Friend", "Boda rider",
    "Step-parent", "Cousin", "Other",
]

CASE_STATUSES = ["Police", "Court", "Household", "RSA", "Community", "Won", "Lost", "Transfers"]

LEGAL_STATUS = ["Arrested", "On the run", "Arrest underway", "Released on Arrest",
                "Convicted (sentenced)", "Household member"]

# ── COLORS FOR CHARTS ─────────────────────────────────────────────────────────
VIOLENCE_COLORS = {
    "Defilement":                C["purple"],
    "Rape":                      C["red"],
    "Physical assault":          C["amber"],
    "Child neglect/abuse":       C["orange"],
    "Sexual assault":            "#880E4F",
    "Denied resources":          C["gold"],
    "Early marriage":            "#BF360C",
    "Emotional/Psychological":   C["teal"],
    "Other":                     C["grey"],
}

RELATION_COLORS = {
    "Neighbor":          C["red"],
    "Stranger/Unknown":  "#7B1FA2",
    "Father/Mother":     C["amber"],
    "Sibling":           C["orange"],
    "Teacher":           C["blue"],
    "Spouse":            "#880E4F",
    "Other":             C["grey"],
}

LEGAL_COLORS = {
    "Police":     C["blue"],   "Court":      C["purple"],
    "Household":  C["orange"], "RSA":        C["teal"],
    "Won":        C["green"],  "Lost":       C["red"],
    "Community":  C["gold"],   "Transfers":  C["grey"],
}

# ── INDICATOR TARGETS ─────────────────────────────────────────────────────────
TARGETS = {
    "survivors_enrolled":     500,
    "followup_rate":           70,
    "referral_rate":           80,
    "gps_capture":             80,
    "medical_report":          60,
    "case_closure_rate":       65,
    "outreach_sessions":      300,
    "outreach_reach":       50000,
    "school_sessions":        200,
    "arrest_rate":             75,
    "conviction_rate":         30,
    "response_time_days":       7,
}

# ── ROLES ─────────────────────────────────────────────────────────────────────
ROLES = {
    "admin":        {"label": "System Administrator",  "icon": "🔐",
                     "gis_precision": "village",  "can_export": True,
                     "see_names": False, "see_raw": True,
                     "pages": ["home","survivors","perpetrators","prevention",
                               "gis","mel","reports","quality","narratives","distance","cost","staff"]},
    "programme":    {"label": "Programme Manager",     "icon": "📊",
                     "gis_precision": "village",  "can_export": True,
                     "see_names": False, "see_raw": True,
                     "pages": ["home","survivors","perpetrators","prevention",
                               "gis","mel","reports","narratives","distance","cost","staff"]},
    "legal":        {"label": "Legal Advocate",        "icon": "⚖️",
                     "gis_precision": "subcounty", "can_export": False,
                     "see_names": False, "see_raw": False,
                     "pages": ["home","perpetrators","survivors","narratives","distance"]},
    "social_worker":{"label": "Social Worker/SSW",     "icon": "🤝",
                     "gis_precision": "parish",   "can_export": False,
                     "see_names": False, "see_raw": False,
                     "pages": ["home","survivors","prevention","narratives","distance"]},
    "outreach":     {"label": "Outreach Officer",      "icon": "🌍",
                     "gis_precision": "subcounty", "can_export": False,
                     "see_names": False, "see_raw": False,
                     "pages": ["home","prevention","gis"]},
    "mel":          {"label": "MEL Officer",           "icon": "📈",
                     "gis_precision": "village",  "can_export": True,
                     "see_names": False, "see_raw": True,
                     "pages": ["home","survivors","perpetrators","prevention",
                               "gis","mel","reports","quality","narratives","distance","cost","staff"]},
    "donor":        {"label": "Donor / Partner",       "icon": "🌐",
                     "gis_precision": "district",  "can_export": False,
                     "see_names": False, "see_raw": False,
                     "pages": ["home","mel","prevention","cost"]},
}

DEMO_USERS = {
    "dag.ainamani":   {"password": "nyaka2026!", "role": "admin",        "name": "Dag Ainamani"},
    "programme.mgr":  {"password": "prog2026!",  "role": "programme",    "name": "Programme Manager"},
    "legal.advocate": {"password": "legal2026!", "role": "legal",        "name": "Legal Advocate"},
    "social.worker":  {"password": "sw2026!",    "role": "social_worker","name": "SSW Officer"},
    "outreach.off":   {"password": "out2026!",   "role": "outreach",     "name": "Outreach Officer"},
    "mel.officer":    {"password": "mel2026!",   "role": "mel",          "name": "MEL Officer"},
    "donor.view":     {"password": "donor2026!", "role": "donor",        "name": "Donor Partner"},
}

SESSION_TIMEOUT = 30  # minutes

# ── SAFE LIVING GUIDANCE ──────────────────────────────────────────────────────
# Time slots mapped to risk level based on incident data
RISK_TIMES = {
    "06:00-09:00": {"risk": "medium", "label": "Morning — moderate risk on rural paths"},
    "09:00-12:00": {"risk": "low",    "label": "Mid-morning — generally safer"},
    "12:00-15:00": {"risk": "low",    "label": "Afternoon — lower risk"},
    "15:00-18:00": {"risk": "medium", "label": "Evening — increasing risk as darkness approaches"},
    "18:00-21:00": {"risk": "high",   "label": "Early night — HIGH RISK — avoid isolated paths"},
    "21:00-06:00": {"risk": "high",   "label": "Night — VERY HIGH RISK — stay indoors"},
}

SAFE_LIVING_TIPS = [
    "Walk in groups, especially children returning from school or women fetching water.",
    "Avoid shortcuts through isolated bush, especially after 17:00.",
    "Know the location of your nearest Nyaka Healing Centre (see map below).",
    "Teach children to report uncomfortable situations to a trusted adult immediately.",
    "Boda boda riders account for incidents — note the number plate and share with family.",
    "Neighbors are the most frequent perpetrators — trust your instincts, report early.",
    "HIV status screening is available free at healing centres for all survivors.",
    "Early reporting (within 72 hours) enables medical evidence collection.",
    "Perpetrators are more likely to be known to the victim — talk to children about body safety.",
    "Crime scenes around water collection points and forest paths — travel in pairs.",
]

# ── STAFF ROSTER ──────────────────────────────────────────────────────────────
# Canonical staff list with role + employment status. Name variants in the raw
# data are mapped to these canonical names via STAFF_NAME_MAP below.
STAFF_ROSTER = {
    "Moreen Namara":          {"role": "Case Manager",            "status": "active"},
    "Improve Ahereza":        {"role": "Case Manager",            "status": "active"},
    "Jenninah Tumukwasibwe":  {"role": "Case Manager",            "status": "active"},
    "Christine Twakiire":     {"role": "Case Manager",            "status": "active"},
    "Amon Mateeka":           {"role": "Legal Advocate",          "status": "active"},
    "Sylivia Katushabe":      {"role": "Legal Advocate",          "status": "active"},
    "Penninah Nahabwe":       {"role": "Schools Social Worker",   "status": "active"},
    "Bylon (current PC)":     {"role": "Programme Coordinator",   "status": "active"},
    # Departed staff — retained for historical analysis
    "Jennifer Nahwera":       {"role": "Programme Coordinator",   "status": "left"},
    "Tom Nahurira":           {"role": "Legal Advocate",          "status": "left"},
    "Moses Tumukunde":        {"role": "Legal Advocate",          "status": "left"},
    "Kenneth Kukundakwe":     {"role": "Legal Advocate",          "status": "left"},
    "Clare Kiconco":          {"role": "Case Manager (Nyamirama)","status": "left"},
    "Bwishimo Evelyn":        {"role": "Case Manager",            "status": "left"},
    "Bosco Kahiigi":          {"role": "Outreach Coordinator",    "status": "left"},
    "Paul Nzerebende":        {"role": "Staff (unspecified)",     "status": "unknown"},
}

# Maps every name variant found in the raw tools → canonical roster name
STAFF_NAME_MAP = {
    "Namara Moreen": "Moreen Namara", "Moreen Namara": "Moreen Namara",
    "NAMARA MOREEN": "Moreen Namara",
    "Ahereza Improve": "Improve Ahereza",
    "Jenninah Tumukwasibwe": "Jenninah Tumukwasibwe",
    "Tukwasibwe Jeninah": "Jenninah Tumukwasibwe",
    "Jenninah": "Jenninah Tumukwasibwe",
    "Twakiire Christine": "Christine Twakiire", "Twakiira Christine": "Christine Twakiire",
    "Christine": "Christine Twakiire",
    "TWAKIIRE CHRISTINE": "Christine Twakiire",
    "Mateeka Amon": "Amon Mateeka",
    "Sylivia Katushabe": "Sylivia Katushabe",
    "Peninnah Nahabwe Annet": "Penninah Nahabwe",
    "Nahwera Jenipher": "Jennifer Nahwera",
    "Nahurira Tom": "Tom Nahurira",
    "Tumukunde Moses": "Moses Tumukunde", "Tumukunde  Moses": "Moses Tumukunde",
    "TUMUKUNDE  MOSES": "Moses Tumukunde",
    "Kukundakwe Kenneth": "Kenneth Kukundakwe", "Kukundakwe kenneth": "Kenneth Kukundakwe",
    "Kiconco Claire": "Clare Kiconco",
    "Byishimo Evelyn": "Bwishimo Evelyn",
    "Mubangizi Bosco Kahiigi": "Bosco Kahiigi",
    "Paul Nzerebende": "Paul Nzerebende",
}

STAFF_STATUS_COLORS = {
    "active":  "#2E7D32",
    "left":    "#9E9E9E",
    "unknown": "#E65100",
}

# ── STAFF DUTY STATIONS ───────────────────────────────────────────────────────
# Where each staff member is physically based, and from where they travel to the
# field. Coordinates verified via web search (Wikipedia, OpenStreetMap, Mapcarta).
# Travel distance in the staff scorecard is measured from these bases, not from
# the nearest healing centre.
STAFF_DUTY_STATIONS = {
    "Amon Mateeka":          {"base": "Nyaka Field Office (Blue Lupin Library), Kambuga",
                              "lat": -0.8140, "lon": 29.7960, "jurisdiction": "Kanungu"},
    "Christine Twakiire":    {"base": "Kambuga Hospital, Kambuga",
                              "lat": -0.8139, "lon": 29.8008, "jurisdiction": "Kanungu"},
    "Moreen Namara":         {"base": "Kanungu Health Centre IV (Katate), Kanungu",
                              "lat": -0.8970, "lon": 29.7756, "jurisdiction": "Kanungu"},
    "Jenninah Tumukwasibwe": {"base": "Kihihi Health Centre IV, Kihihi",
                              "lat": -0.7480, "lon": 29.6970, "jurisdiction": "Kanungu"},
    "Improve Ahereza":       {"base": "Kebisoni Health Centre III, Kebisoni",
                              "lat": -0.8120, "lon": 29.9210, "jurisdiction": "Rukungiri"},
    "Sylivia Katushabe":     {"base": "Kebisoni Health Centre III, Kebisoni",
                              "lat": -0.8120, "lon": 29.9210, "jurisdiction": "Rukungiri"},
    "Penninah Nahabwe":      {"base": "Schools (cross-district)",
                              "lat": -0.8139, "lon": 29.8008, "jurisdiction": "All districts"},
}


# Perpetrator-to-survivor relationship codes (from survivor/perp tool 'relations' list)
RELATION_MAP = {
    "1":"Father/Mother","2":"Boyfriend/Girlfriend","3":"Uncle/Aunt","4":"Daughter/Son",
    "5":"Brother/Sister","6":"Husband/Wife (spouse)","7":"Neighbour","8":"Stranger",
    "9":"Step Parents","10":"Grand Parent","11":"Other Relative","12":"Don't Know",
    "13":"Other, specify","14":"Well wisher","15":"Survivor",
}