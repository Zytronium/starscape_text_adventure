# Starscape: Text Adventure Edition

## Lore
Starscape is a dying game. Starscape Text Adventure Edition takes place 
after everyone has stopped playing the game and it is dead for good. You,
the last player, find this hidden gem and play it alone like a singleplayer
game.

Players are a long forgotten type of person who has a special property:
They are sentient. Unlike the other NPCs in this galaxy, players have
free will and live on a whole 'nother plane of existence - literally.
They live in the real world, controlling their character in this universe.
All players of the past have lost interest in this universe and have
slowly disappeared over time. However, you, the last Starscape player,
 believe it is worth a play anyway, even if it is now basically a 
singleplayer game. 

Traditionally, CoreSec would clone new players into existence. How this was
done is not known, but this practice was used less and less often as time
went on until Core Sec has decided to shut down the program entirely after you
first clone in. There will be no more players after you. 

While the cloning bay is still open for cloning you in after you die, it is
best not to die, as it is rather unpleasant, and you will lose your ship and
inventory. CoreSec cannot recover this for you. They discontinued insurance 
due to so few people using it, as real players were the only people who were
eligible for insurance.

---

## Game Mechanics

### Star Systems
Star systems function as different zones you can travel to. You travel between
systems by warping in your spaceship. Most star systems in Core, Secure,
Contested, and Unsecure space have space stations. Wild systems have no space
stations.

There are several types of space stations, each with their own different types
of station modules you can visit, i.e., manufacturing, general marketplace, 
refinery, etc. While docked at a space station, you can visit each of these
facilities and interact with them. If the station has a repair bay, you can
also repair your ship's hull while docked. 

Each star system is likely to have anomalies. You can scan for anomalies using
system probes, which can be bought or manufactured for cheap. At each anomaly,
you can find rare ores to mine, encounter hostile forces, loot wreckage fields
from a previous battle, or purchase spice from special spice platforms. 

Data on each star system, from the connected systems to the color of spice, are
taken from real in-game data scrapped by [Starscape Datamine](https://github.com/EnderBoy9217/Starscape-Datamine)
on GitHub.

### Marketplace
Unlike in Starscape, the general marketplace will be global across all star
systems. Simialr to Starscape, the player marketplace is disabled (as you're the
only player), so your buy and sell prices may not be as good as you would 
typically find during Starscape's prime. To account for this, prices will be
slightly better than what they actually are in-game.

You will be able to sell just about any item and buy a large variety of items
from the global NPC marketplace. There are several types of marketplaces:
- General Marketplace
  - This marketplace buys and sells almost any item except ships
- Ship Vendor
  - This marketplace buys and sells low-tier ships
- I can't think of anything else that makes sense for this version of the game
  - The original Starscape also had clothing shops and weapons dealers, but they
    are not applicable to a game with no ground combat.

### Combat
Upon entering a non-core system or certain anomalies, there's a random chance 
that you will encounter hostile enemies (usually drones or pirates). You will
get a choice to fight, run, or ignore the enemies. Your ship will take damage
based on what ship you're in, what upgrades is has, your skill level, and how
strong the enemies are. If you're in a destroyer and you encounter a small drone
fleet in secure space, you can easily ignore the drones while taking minimal 
shield damage. However, a smaller ship like a Stratos or a Falcon may have to 
fight or run. 

Choosing to fight increases your combat skill level, whether you win or loose. 
Winning increases your combat skill level even more. Choosing to run still risks
getting fired at or warp disrupted and forced to fight, but poses lower risk than
fighting and increases your piloting skill level (this helps you be more evasive
in the future). Choosing to ignore the fleet can be dangerous depending on the
situation, but is the fastest option if your ship is strong enough, however,
it has no effect on skill level.

Combat plays out in segments, allowing you to retreat if things aren't going your
way rather than taking a higher gamble at the start of the fight if you 
underestimate the enemy fleet.

#### Combat Events

##### Enemy Fleet Encounter
As mentioned previously, warping to a system or anomaly can sometimes trigger
en enemy fleet encounter. 

##### Warp Disruption
Pirates can sometimes disrupt your warp drive, preventing you from escaping.
To escape, you must either destroy the ship or deployed gadget disrupting you
or dodge enemy fire long enough to get out of range. This, however, rarely
happens in unsecure space unless you are in a pirate hotspot such as Gatinsir
or Emas. You must be ready for this to happen at any time in wild space.

### Anomalies

| **ID** | **Name**                  | **Location**                      | **Description**                                                                                                           |
|--------|---------------------------|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **AT** | Small Asteroid Field      | Secure, Contested, Unsecure, Wild | A small asteroid field with higher-quality ore than typical space                                                         |
| **AL** | Large Asteroid Field      | Secure, Contested, Unsecure, Wild | A larger version of an AT anomaly; More asteroids, more ores                                                              |
| **AA** | Axnit-Only Asteroid Field | Contested, Unsecure, Wild         | An asteroid field containing only Axnit                                                                                   |
| **AN** | Narcor Asteroid Field     | Wild                              | A small field containing only Narcor and Red Narcor ore                                                                   |
| **VX** | Vexnium Anomaly           | Wild                              | A rare asteroid field with up to 4 Vexnium asteroids; gaurded by crystaline entities that attack when you attempt to mine |
| **CM** | Comet Anomaly             | Secure, Contested, Unsecure, Wild | A large comet with Water Ice in its trail                                                                                 |
| **BF** | Battlefield Anomaly       | Secure, Contested, Unsecure, Wild | A wreckage field from a previous battle, with salvage to loot, often guarded by drones.                                   |
| **DH** | Drone Hideout             | Secure, Contested, Unsecure, Wild | A drone structure area with many drones; higher risk, higher reward                                                       |
| **SP** | Spice Platform            | Secure, Contested, Unsecure, Wild | A wrecked spice platform with spice crates; guarded by some drones.                                                       |
| **MT** | Monument Anomaly          | Secure, Contested, Unsecure, Wild | Contains a Tier-3 or higher Monument surrounded by pristine ore fields (Korrelite, Reknite, or Gellium)                   |
| **WH** | Wormhole                  | Secure, Contested, Unsecure, Wild | A wormhole linking to another system; may last for either 2 days (transient) or 2 weeks (enduring)                        |
| **FO** | Frontier Outpost          | Wild                              | A Syndicate Frontier Outpost in wild space with a small item shop and rare spice                                          |

Anomalies get more common, richer, and more dangerous the further out you go. 
Wild space is especially high-risk, high reward.

### (Fun) Mining
If you try to mine ores with a ship that's not a miner, it will be painfully
slow and boring. However, when you take a mining ship, things change significantly.

#### Mining Laser Intensity
With each mining laser blast, you must choose an intensity between 1 and 5.
Lower intensities make less progress but improve asteroid stability. Higher
values significantly reduce asteroid stability and may vaporize some of the ore,
reducing mining efficiency even though mining speed is higher.

#### Asteroid Stability
Most asteroids by default have their stability at 100%. Mining at the asteroid
at medium or high intensities makes the asteroid less stable. When stability
is low, the asteroid risks shattering or vaporizing, losing all remaining ore
forever. When stability hits 0%, the asteroid explodes, vaporizing all remaining
ore and severely damaging your ship. This explosion is capable of destroying 
ships if they are already damaged.

#### Random Events
Random events may occur while mining an asteroid, some may be more likely than
others depending on system security status, anomaly type, or ore type.

- Gas Pocket Exposed
  - A gas pocket is uncovered, causing a portion of the asteroid to disappear 
    with nor ore gained. In unstable asteroids, this may happen explosively,
    causing more of the asteroid's ore to be lost and potentially damaging 
    your ship. When gas pockets are exposed, they instantly vent the gas,
    reducing the asteroid's stability by a random amount.
  - This event is more likely with gellium ore and red narcor ore
- Dense Mineral Formation Uncovered
  - As the name suggests, a dense formation of the ore is uncovered, giving you
    a sudden burst of extra ore.
  - This event is more likely for vexnium ore, and axnit ore, and korrelite ore.
  - It is also even more likely for pristine ore variants. 
- Asteroid Collision
  - The asteroid being mined collides with another asteroid present, causing
    some ore from both asteroids to break off, some of which escapes you and
    cannot be recovered. If this happens, you may act fast to recover more of
    the ore thrown loose.
  - This event is more likely in AL and CM anomalies and cannot happen in VX and
    MT anomalies.
- Ancient Artifact Uncovered
  - An artifact from an ancient spacefaring civilization has been uncovered
    after being buried in the asteroid for ages. If using a high-intensity laser
    blast, the artifact may be vaporized. Otherwise, the artifact can be sold
    for a high price at a marketplace.
  - This event is more likely in wild space.
- Proximity-based Mine Encountered
  - This asteroid has been mined! No, no, the ore is intact, but someone has
    attached an explosive mine to this asteroid. Should you try to defuse it, 
    risking accidental detonation, or leave it be and skip this asteroid? If
    the mine goes off, your ship will be heavily damaged and the asteroid's
    ore will be unsalvageable.
  - This event is likely in unsecure and contested space and very likely
    in wild space. It cannot happen in secure space.


### Exploration & System Security Levels

There are five system security levels:
- **Core**: A core system with no anomalies or enemies. Perfectly safe. Usually 
located at a faction's homeworld.
- **Secure**: A safe, but not perfectly safe star system that may have weak
enemies and low-value anomalies. The only hostile forces here are drones.
- **Contested**: A system that falls between secure and unsecure in terms of
safety. The owner of this territory is disputable, and this may be a war zone.
- **Unsecure**: A system prone to piracy, especially if bordering secure space
or in the middle of a route commonly traveled. Higher value ores and anomalies
may appear here, but more dangerous enemies may also appear.
- **Wild**: A system far from any civilization, with no space stations except
the occasional Syndicate Frontier Outpost anomaly. While this is the best place
to find rich ore and high-value anomalies, it also contains the most dangerous
enemies in high volume. However, defeating these enemies may yield great rewards.
- **Uncharted**: ???

If you venture out far enough into the wild, you may stumble across some of the
galaxy's most hidden, ancient secrets.
