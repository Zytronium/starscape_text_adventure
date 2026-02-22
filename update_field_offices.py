import json, re
import random

with open("system_data.json", "r") as f:
    data = json.load(f)

# (display name used in office name,  canonical faction key for save data)
FACTION_MAP = {
    "CoreSec":      ("CoreSec",       "CoreSec"),
    "Syndicate":    ("Syndicate",     "Syndicate"),
    "TradeUnion":   ("Trade Union",   "Trade Union"),
    "Trade Union":  ("Trade Union",   "Trade Union"),
    "MiningGuild":  ("Mining Guild",  "Mining Guild"),
    "Mining Guild": ("Mining Guild",  "Mining Guild"),
    "Lycentia":     ("Lycentian",     "Lycentia"),
    "Lycentian":    ("Lycentian",     "Lycentia"),
    "Forakus":      ("Foralkan",      "Forakus"),
    "Foralkan":     ("Foralkan",      "Forakus"),
    "Kavani":       ("Kavani",        "Kavani"),
}

pattern = re.compile(r"^(.+?) Mission Agency \(Tier (\d+)\)$")

for system in data.values():
    for station in system.get("Stations", []):
        facilities = station.get("Facilities", [])

        faction_tiers: dict[str, list[int]] = {}
        non_agency: list = []

        for facility in facilities:
            if not isinstance(facility, str):
                non_agency.append(facility)
                continue
            match = pattern.match(facility)
            if match:
                raw_faction, tier = match.group(1), int(match.group(2))
                faction_tiers.setdefault(raw_faction, []).append(tier)
            else:
                non_agency.append(facility)

        field_offices = []
        for raw_faction, tiers in faction_tiers.items():
            display_name, faction_key = FACTION_MAP.get(raw_faction, (raw_faction, raw_faction))
            agents = [tiers[0], random.randint(0, 5)] if len(tiers) == 1 else tiers[:2]
            field_offices.append({
                "Name": f"{display_name} Field Office",
                "Faction": faction_key,
                "Agents": agents
            })

        station["Facilities"] = non_agency + field_offices

with open("system_data.json", "w") as f:
    json.dump(data, f, indent=4)

print("Done.")
