# TODO: High Level Todo list

- add more items 
- add all ships
- add all turrets
- add ship upgrades
- add enemy structures
- add drone battleships
- make NPC ships drop salvage instead of credits
- make pirate hotspot systems more likely to have pirates
- add missions and faction standing
- add tutorial missions
  - *incomprehensible screaming*
- track player statistics
  - i.e., systems visited, number of deaths, enemy ships destroyed, etc.
- add spice hauling

When all of the above are done, the game can go from alpha to beta.
When all of Starscape's features (minus player market and PvP) are implemented
in some way (from Loyalty Points and PDT Turrets to Faction Warfare and player
stations), it can go from beta to release. After that, minor improvements, bug
fixes, QOL updates, and maybe the occasional new feature not in the original
Starscape may be added.

## Missions
When the player visits a mission agency, generate 3 random missions for the given tier.
Then save those missions to the player's save file for that specific mission agency.
Since mission agencies do not have IDs and can have duplicate names, save the index
of the mission agency in the station's facilities list, plus which station it is on.

Each mission will have:
- a description
- a credits reward based on the mission tier
- a standing reward based on the mission tier
- a target system (or multiple destinations sometimes)
  - The only exception is Destroy: {Faction}
- A origin system where you return to after the mission is complete
  - And which station & facility the mission originated from

The player can only do missions of the tier they are on in terms of faction standing.

### Tutorial Missions
These missions teach new players how to play the game. They include:
- Combat Mission
- Mining & Industry Mission
- Commerce Mission

### Faction Missions
- Office Supply Run
  - Use a hauler ship to grab supplies from an outpost in another system and bring them back to the station where the agent is.
  - Tier 0 missions need 2 cargo items to be transported, tier 2 needs 6, tier 4 needs 10.
  - "The field office is running out of supplies and won't be able to keep running in top condition much longer. Go to an outpost to pick up supplies and bring them back to the station. This mission requires a Hauler-class ship to complete."
- Resupply the Outpost
  - Use a hauler ship to grab supplies from the source station and deliver them to another outpost.
  - Tier 0 missions need 2 cargoes to be transported, tier 2 needs 6, tier 4 needs 10.
  - "A {Faction} listening post is in need of a resupply. Your task is to pick up the cargo and deliver it to the outpost. This mission requires a Hauler-class ship to complete."
- Law Enforcement
  - Warp to a system's asteroid field (often two systems away) to scare away pirates and reactivate proximity alarms (X number of them, scattered on asteroids) while fending off pirates occasionally. The pirates will always come back with a full fleet. 
  - Tier 0 missions need 3 alarms to be activated with only 2 fighters (Sabre, Aurora) and 2 interceptors (Zenith, Falcon) appearing. Tier 2 needs 4 alarms with a corvette (Radix) added to the fleet. Tier 4 needs 5 alarms with another corvette added to the fleet (Chevron)
  - "A nearby asteroid field which was designated an excavation site is being illegally mined by a group of pirates. Go to the asteroid field, drive off the pirates, and reactivate the proximity alert systems the pirates disabled."
- Defend the Transport
  - Warp to a system to defend a transport ship from 3 small waves of enemies, with the enemies depending on the faction's relations:
    - Kavani enemies: Lycentian, Foralkan
    - Foralkan enemies: Lycentian, Kavani
    - Lycentian enemies: Kavani, Foralkan
    - CoreSec enemies: Drones
    - Trade Union enemies: Pirates
    - Mining Guild enemies: Pirates
    - Syndicate enemies: Drones, Pirates
  - Difficulty is only raised by an additional corvette appearing on tier 2 missions. Tier 4 missions do not raise the difficulty from tier 2 (possibly unintended in original game).
  - The transport has approximately 250k hull. It cannot be destroyed unless the player makes a concentrated and deliberate attempt to do so.
  - Doing this mission will reduce the player's standing with the enemy faction if the enemy faction is not Drones or Pirates, since every ship destroyed will reduce standing with that faction.
  - "A transport took engine damage and is currently stranded in a potentially hostile region of space. Travel to its location and ensure it is able to complete its repairs safely."
- Intel Recovery
  - Warp to a system to collect information, there are 4 different scenarios that will randomize the mission:
    - The covert ship is ready to give information as you arrive. (Always the first scenario, and will be on every mission)
    - The covert ship is destroyed, the first part requires you to find the {Faction} black box. Then the 2nd part requires you to fight pirates or faction ships to get the intel. Difficulty of this scenario is parallel to the Law Enforcement mission.
    - The covert ship is under attack, it has the same difficulty as the 2nd scenario.
    - The covert ship's pilot thinks you've betrayed him, and goes insane. Difficulty does not raise. *incomprehensible screaming*
- Assault the Base
  - Destroy a base (type of base and ships that appear vary between which faction you are doing the mission for), often comprising of 2 factories and a outpost. The user have to counter 3 waves of ships comprising of fighters, corvettes and interceptors.
  - No more ships will spawn after the waves of ships are destroyed. It is not necessary to destroy the factories beside the bases -- no new ships will spawn after the 3 waves of ships are destroyed. It is however necessary to destroy all 3 waves before the base can take damage.
  - Tier 1 missions require you to fight corvettes and fighters (drone interceptors). Tier 3 missions will have frigates added to the fleet.
  - Doing this mission will reduce the player's standing with the enemy faction if the enemy faction is not Drones or Pirates, since every ship destroyed will reduce standing with that faction.
  - "{Faction} intelligence has learned the location of a secret {Enemy Faction} base nearby. Travel to the location of the base and destroy it and all its defenses."
- Salvage Operation
  - Salvage the cargo remains from a destroyed fleet. Use a hauler class ship, preferably a small and agile one, to navigate through a mine field, and collect cargo crates from destroyed ships. Cargo amount increases with mission difficulty
  - Tier 1: 2 cargo, Tier 3: 5 cargo, Tier 5: 8 cargo
  - "A transport ship on a risky mission got trapped and destroyed in a minefield. Go to the wreckage site and salvage the cargo crates it was transporting. This mission requires a Hauler-Class ship to complete."
- Rescue Operation
  - Protect a transport from enemy fighters, interceptors and corvettes while it is rescuing a prisoner.
  - Difficulty raises by more corvettes, fighters and turrets added into the fleet (Tier 1, 3 and 5).
  - The transport has approximately 250k hull. It cannot be destroyed unless the player makes a concentrated and deliberate attempt to do so.
  - "A technician was servicing a {Faction} outpost when hostile ships assaulted it, overrunning its defenses and stranding the technician. {Faction} is sending a transport to retrieve the technician, but it needs you to protect it from the hostiles in the area."
- Destroy: {Enemy Faction}
  - Destroy a given set of ships (the type of ships varies between factions), often 10 Fighters and either 10 interceptors or 5 corvettes.
  - The rewards are higher at 500 Credits and +60 Faction Standing for Tier 1. At Tier 3, you'll have to destroy 10 fighters, interceptors and corvettes each or 10 corvettes and 3 frigates, giving a higher reward at 1000 Credits and +80 Faction Standing. At Tier 5, You'll need to destroy 10 fighters, interceptors, corvettes and 3 frigates for 1600 credits and +100 faction standing. (For non-CoreSec missions, corvettes are after tier 3, and frigates are the only ship on tier 5.)
  - Quotes:
    - CoreSec & Syndicate: 
      - "Drones have been encroaching further and further into civilized space. Destroy them wherever you find them across the galaxy to prevent the problem from getting any worse."
    - Lycentian: 
      - "It is difficult to find an entity in the galaxy the Foralkans have not agitated, and the Federation is no exception. Help turn the tide in the conflict by destroying Foralkan ships wherever you can find them across the galaxy."
      - "The conflict with the Kavani has gone on for generations. As the two original great nations, the Federation and the Mandate were destined to be at odds. Help turn the tide in the conflict by destroying Kavani ships wherever you can find them across the galaxy."
    - Kavani: 
      - "The conflict with the Lycentians has gone on for generations. As the two original great nations, Lycentia and Kavani were destined to be at odds. Help turn the tide in the conflict by destroying Lycentian ships wherever you can find them across the galaxy."
      - "It is difficult to find an entity in the galaxy the Foralkans have not agitated, and the Mandate is no exception. Help turn the tide in the conflict by destroying Foralkan ships wherever you can find them across the galaxy."
    - Foralkan: 
      - "The Kavani believe they have a mandate, but the empire disagrees. Help turn the tide in the conflict by destroying Kavani ships wherever you can find them across the galaxy."
      - "The Lycentians and Foralkans have been bitter enemies since the rise of the Empire. Help turn the tide in the conflict by destroying Lycentian ships wherever you can find them across the galaxy."

Refer to https://starscape-roblox.fandom.com/wiki/Missions for more information.

Missions that can be implemented with current features:
- Law Enforcement
- Defend the Transport
- Intel Recovery
- Rescue Operation

### Standing
When visiting a mission agency, the player can view their standing tier.
In future versions of the game, standing will also grant perks, such as
discount on warp relay usage or a way to purchase blueprints for faction
ships.

### Mission Agencies
I need to change "Visit Mission Agent" to "Visit {agency name}". To do this, I
need to figure out how to get the name of the mission agency from system_data.json.
Here's an example system from the json:
```json
    "Eltikum": {
        "Faction": "Neutral",
        "Region": "Core",
        "Sector": "InnerCore",
        "SecurityLevel": "Secure",
        "SpectralClass": "B",
        "Spice": "Orange",
        "Connections": [
            "Hiredzo",
            "Viax Terjit",
            "Iolc-go"
        ],
        "Name": "Eltikum",
        "Planets": 12,
        "Stations": [
            {
                "Name": "Eltikum Military Station",
                "Type": "Military",
                "Facilities": [
                    "CoreSec Mission Agency (Tier 1)",
                    "CoreSec Mission Agency (Tier 0)",
                    "CoreSec Mission Agency (Tier 1)"
                ]
            },
            {
                "Name": "Eltikum Industrial Station 2",
                "Type": "Industrial",
                "Facilities": [
                    "Refinery",
                    "Manufacturing",
                    "Observatory",
                    "Repair Bay"
                ]
            }
        ]
    },
```
(Ordinarily, a station shouldn't have this many mission agencies and nothing else,
but this is an outlier, and I picked this outlier for a reason.)
This system has 2 stations, and the first station has 3 mission agencies.
The mission agencies are stored in the Facilities array, which is in the station
object in the Stations array. When saving mission information, we need to save
the name of the station (those are unique) and the index of the mission agency
in the station's facilities list. We can't just rely on the name of the agency,
since mission agencies can have duplicate names.

We also need to manually edit some systems so that they have specific stations 
with specific facilities, including mission agencies, so that it matches the
original game. For example, Lycentia has at least 3 stations and at least one
mission agency in the original game. At the time of writing this, Lycentia only 
has a single military space station in this game.
