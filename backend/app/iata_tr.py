"""Turkey IATA support for target-airport normalization."""

# Source references used while curating this set:
# - OpenFlights airport data: https://openflights.org/data.php
# - Wikipedia airport pages / airport lists for Turkey
#
# This list is intentionally focused on IATA codes used in Turkey operations.

TURKEY_IATA_CODES = {
    "ADA",
    "ADB",
    "ADF",
    "AJI",
    "ANK",
    "AOE",
    "ASR",
    "AYT",
    "BAL",
    "BGG",
    "BJV",
    "BZI",
    "CKZ",
    "DIY",
    "DLM",
    "DNZ",
    "EDO",
    "ERC",
    "ERZ",
    "ESB",
    "EZS",
    "GKD",
    "GNY",
    "GZT",
    "GZP",
    "HTY",
    "IGD",
    "ISE",
    "IST",
    "KCM",
    "KFS",
    "KSY",
    "KYA",
    "KZR",
    "MLX",
    "MQM",
    "MSR",
    "MZH",
    "NAV",
    "NKT",
    "NOP",
    "OGU",
    "ONQ",
    "RZV",
    "SAW",
    "SFQ",
    "SQD",
    "SXZ",
    "SZF",
    "TEQ",
    "TJK",
    "TZX",
    "USQ",
    "VAN",
    "VAS",
    "YEI",
    "YKO",
}

# City/metro groups for operational matching.
IATA_EQUIVALENT_GROUPS = {
    "IST": {"IST", "SAW"},
    "SAW": {"IST", "SAW"},
}

