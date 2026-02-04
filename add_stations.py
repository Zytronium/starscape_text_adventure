#!/usr/bin/env python3
"""
Script to add random stations to systems in system_data.json
"""
import json
import random
from collections import Counter


def generate_planet_count():
    """Generate planet count with exponential distribution, avg 5, cap 15"""
    # Weights for exponential-ish distribution centered around 5
    weights = {
        1: 1,
        2: 2,
        3: 4,
        4: 8,
        5: 16,
        6: 14,
        7: 10,
        8: 7,
        9: 5,
        10: 3,
        11: 2,
        12: 1.5,
        13: 1,
        14: 0.5,
        15: 0.3
    }

    planets = []
    planet_weights = []

    for num, weight in weights.items():
        planets.append(num)
        planet_weights.append(weight)

    return random.choices(planets, weights=planet_weights)[0]


def should_have_stations(security_level, num_stations=1):
    """Determine if a system should have stations based on security level"""
    probabilities = {
        "Core": {1: 1.0, 2: 0.0},
        "Secure": {1: 0.99, 2: 0.6667},
        "Contested": {1: 0.6667, 2: 0.0},
        "Unsecure": {1: 0.3333, 2: 0.0},
        "Wild": {1: 0.0, 2: 0.0}
    }

    prob = probabilities.get(security_level, {}).get(num_stations, 0.0)
    return random.random() < prob


def generate_mission_agency_tier():
    """Generate mission agency tier (0-5) with tier 1 being most common"""
    # Tier 1 is most common, others decrease
    weights = {
        0: 5,
        1: 20,  # Most common
        2: 10,
        3: 5,
        4: 2,
        5: 1
    }

    tiers = list(weights.keys())
    tier_weights = list(weights.values())

    return random.choices(tiers, weights=tier_weights)[0]


def generate_station_type(faction, region):
    """Generate station type (Industrial, Commercial, or Military)"""
    # Military stations are half as likely
    # Military only appears in non-Neutral factions or Core region
    can_have_military = (faction != "Neutral") or (region == "Core")

    if can_have_military:
        # Military is half as likely
        choices = ["Industrial", "Commercial", "Military"]
        weights = [2, 2, 1]
    else:
        choices = ["Industrial", "Commercial"]
        weights = [1, 1]

    return random.choices(choices, weights=weights)[0]


def generate_station_facilities(station_type, faction):
    """Generate 2-4 facilities for a station based on its type"""
    num_facilities = random.randint(2, 4)

    facility_pools = {
        "Industrial": [
            ("Refinery", 1.0),
            ("Manufacturing", 1.0),
            ("Repair Bay", 1.0),
            ("Observatory", 0.5)
        ],
        "Commercial": [
            ("Ship Vendor", 1.0),
            ("General Marketplace", 1.0),
            ("Observatory", 0.5)
        ],
        "Military": [
            (f"{faction} Mission Agency", 1.0),
            ("Ship Vendor", 1.0),
            ("Manufacturing", 1.0),
            ("Observatory", 0.5)
        ]
    }

    pool = facility_pools[station_type]
    facilities = []

    # Create weighted list
    facility_names = [f[0] for f in pool]
    facility_weights = [f[1] for f in pool]

    # Select unique facilities
    while len(facilities) < num_facilities and len(facilities) < len(
            facility_names):
        chosen = random.choices(facility_names, weights=facility_weights)[0]
        if chosen not in facilities:
            # Add tier to mission agencies
            if "Mission Agency" in chosen:
                tier = generate_mission_agency_tier()
                facilities.append(f"{chosen} (Tier {tier})")
            else:
                facilities.append(chosen)

    return facilities


def generate_citadel_station():
    """Generate the special all-purpose station for The Citadel"""
    # All factions for mission agencies
    factions = ["CoreSec", "Syndicate", "Trade Union", "Mining Guild",
                "Lycentia", "Forakus", "Kavani"]

    facilities = [
        "Global Storage",
        "Manufacturing",
        "Refinery",
        "General Marketplace",
        "Observatory",
        "Repair Bay"
    ]

    # Add mission agencies for all factions
    for faction in factions:
        tier = generate_mission_agency_tier()
        facilities.append(f"{faction} Mission Agency (Tier {tier})")

    return {
        "Name": "Citadel Central Station",
        "Type": "All-Purpose",
        "Facilities": facilities
    }


def add_stations_to_systems(data):
    """Add stations to all systems based on rules"""

    for system_name, system_info in data.items():
        # Add system name to data
        system_info["Name"] = system_name

        security_level = system_info.get("SecurityLevel", "Wild")
        faction = system_info.get("Faction", "Neutral")
        region = system_info.get("Region", "Unknown")

        # Special handling for The Citadel
        if system_name == "The Citadel":
            system_info["Planets"] = 2
            system_info["Stations"] = [generate_citadel_station()]
            continue

        # Generate planet count
        planets = generate_planet_count()
        system_info["Planets"] = planets

        # Determine number of stations
        stations = []

        if should_have_stations(security_level, 1):
            stations.append(1)

            if should_have_stations(security_level, 2):
                stations.append(2)

        # Generate stations (up to planet count)
        station_list = []
        num_stations = min(len(stations), planets)

        for i in range(num_stations):
            station_type = generate_station_type(faction, region)

            # Determine faction for military stations
            station_faction = faction if faction != "Neutral" else "CoreSec"

            # Generate facilities
            facilities = generate_station_facilities(station_type,
                                                     station_faction)

            # Generate station name
            station_name = f"{system_name} {station_type} Station"
            if len(station_list) > 0:
                station_name = f"{system_name} {station_type} Station {i + 1}"

            station = {
                "Name": station_name,
                "Type": station_type,
                "Facilities": facilities
            }

            station_list.append(station)

        if station_list:
            system_info["Stations"] = station_list


def main():
    """Main function"""
    # Load system data
    print("Loading system_data.json...")
    try:
        with open('system_data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("ERROR: system_data.json not found!")
        print("Please make sure the file exists in the current directory.")
        return

    print(f"Loaded {len(data)} systems")

    # Check if The Citadel exists
    if "The Citadel" not in data:
        print("\nWARNING: 'The Citadel' system not found in data!")
        print("Creating a placeholder entry for The Citadel...")
        data["The Citadel"] = {
            "Faction": "CoreSec",
            "Region": "Core",
            "Sector": "Origin",
            "SecurityLevel": "Core",
            "SpectralClass": "G",
            "Spice": "None",
            "Connections": []
        }

    # Add stations
    print("Generating planets and stations...")
    add_stations_to_systems(data)

    # Statistics
    total_systems = len(data)
    systems_with_stations = sum(
        1 for s in data.values() if "Stations" in s and s["Stations"])
    total_stations = sum(len(s.get("Stations", [])) for s in data.values())
    total_planets = sum(s.get("Planets", 0) for s in data.values())

    station_types = []
    for system in data.values():
        for station in system.get("Stations", []):
            station_types.append(station["Type"])

    type_counts = Counter(station_types)

    print(f"\nStatistics:")
    print(f"  Total systems: {total_systems}")
    print(
        f"  Systems with stations: {systems_with_stations} ({systems_with_stations / total_systems * 100:.1f}%)")
    print(
        f"  Total planets: {total_planets} (avg {total_planets / total_systems:.1f} per system)")
    print(f"  Total stations: {total_stations}")
    print(f"\nStation types:")
    for station_type, count in type_counts.most_common():
        print(f"  {station_type}: {count}")

    # Save updated data
    output_file = 'system_data.json'
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)

    print("Done!")

    # Show a few examples
    print("\nExample systems:")
    examples = random.sample(list(data.keys()), min(5, len(data)))
    for system_name in examples:
        system = data[system_name]
        print(f"\n{system_name} ({system['SecurityLevel']}):")
        print(f"  Planets: {system.get('Planets', 0)}")
        if "Stations" in system and system["Stations"]:
            for station in system["Stations"]:
                print(f"  - {station['Name']} ({station['Type']})")
                for facility in station["Facilities"]:
                    print(f"    • {facility}")
        else:
            print(f"  No stations")


if __name__ == "__main__":
    main()
