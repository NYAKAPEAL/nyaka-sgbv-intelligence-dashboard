"""
utils/duty_stations.py

Verified coordinates for the GPS travel audit (the "did the worker actually travel?"
check). These were confirmed on 2026-06 against independent sources:

  - Kambuga: identical to Kambuga General Hospital (Wikipedia), -0.813902, 29.800839
  - Kanungu HC IV: matches Kanungu town (Wikipedia), -0.896950, 29.775560
  - Kebisoni: confirmed by Open Location Code 6GFG42V8+25 -> -0.857400, 30.015430
  - Kihihi HC: -0.748620, 29.696700 (matches prior dashboard value)
  - Blue Lupin library, Kambuga: -0.809917, 29.809000

IMPORTANT: the FACILITY_COORDS table in cost_model.py currently holds WRONG values for
Kambuga Healing Centre (off ~22 km) and Kebisoni Healing Centre (off ~12 km). The audit
must use the verified coordinates below, not those. Correct cost_model.py before relying
on its Kambuga/Kebisoni entries elsewhere.

A worker is treated as "did not travel" when an in-person (onsite) contact's GPS falls
within NO_TRAVEL_RADIUS_KM of their own duty base.
"""

# Verified duty bases (where each worker physically sits)
DUTY_BASES = {
    "Kambuga Healing Centre":      {"lat": -0.813902, "lon": 29.800839},
    "Kebisoni Healing Centre":     {"lat": -0.857400, "lon": 30.015430},
    "Kanungu Health Centre IV":    {"lat": -0.896950, "lon": 29.775560},
    "Kihihi Health Centre IV":     {"lat": -0.748620, "lon": 29.696700},
    "Nyaka Blue Lupin Library":    {"lat": -0.809917, "lon": 29.809000},
}

# Staff -> duty base.
STAFF_DUTY_BASE = {
    "Christine Twakiire":  "Kambuga Healing Centre",
    "Improve Ahereza":     "Kebisoni Healing Centre",
    "Sylivia Katushabe":   "Kebisoni Healing Centre",   # sits with Ahereza
    "Moreen Namara":       "Kanungu Health Centre IV",
    "Jenninah Tumukwasibwe": "Kihihi Health Centre IV",
    "Amon Mateeka":        "Nyaka Blue Lupin Library",
    "Penninah Nahabwe":    "Nyaka Blue Lupin Library",
    "Bylon":               "Nyaka Blue Lupin Library",
}

# A contact whose GPS is within this distance of the worker's base counts as "no travel".
NO_TRAVEL_RADIUS_KM = 0.5