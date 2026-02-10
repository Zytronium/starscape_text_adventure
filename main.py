"""
Starscape: Text Adventure Edition
A text-based recreation of the Roblox game Starscape by Zolar Keth
"""
import math
import random
import sys
import json
import os
from pathlib import Path
from io import StringIO
from time import sleep, time
from uuid import uuid4
from colors import set_color, set_background_color, reset_color

# Discord Rich Presence support
try:
    from pypresence import Presence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("Warning: pypresence not installed. Discord Rich Presence disabled.")
    print("Install with: pip install pypresence")
    sleep(3)

VERSION_CODE = 2
CORE_COLOR = "\033[1;32m"     # lime
SECURE_COLOR = "\033[36m"     # cyan
CONTESTED_COLOR = "\033[33m"  # orange/brown
UNSECURE_COLOR = "\033[31m"   # red
WILD_COLOR = "\033[35m"       # purple
RESET_COLOR = "\033[0m"       # reset

# Discord Application Client ID
DISCORD_CLIENT_ID = "1469089302578200799"

# Global Discord RPC instance
discord_rpc = None


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def init_discord_rpc():
    """Initialize Discord Rich Presence"""
    global discord_rpc

    if not DISCORD_AVAILABLE:
        return False

    try:
        discord_rpc = Presence(DISCORD_CLIENT_ID)
        discord_rpc.connect()

        # Set initial presence
        discord_rpc.update(
            state="In Main Menu",
            details="Playing Starscape Text Adventure",
            large_text="Starscape: Text Adventure",
            start=int(time())
        )
        return True
    except Exception as e:
        print(f"Warning: Could not connect to Discord: {e}")
        discord_rpc = None
        return False


def get_adaptive_presence(data, context="default"):
    """Determine adaptive Discord presence based on game state

    Args:
        data: Game save data dictionary
        context: Current game context - "docked", "combat", "dead", "traveling", "menu", etc.

    Returns:
        tuple: (details, state) for Discord Rich Presence
    """
    # Load system data to get security level
    try:
        with open(resource_path('system_data.json'), 'r') as f:
            all_systems_data = json.load(f)
    except:
        all_systems_data = {}

    current_system = data.get("current_system", "Unknown")
    security_level = "Unknown"

    if current_system in all_systems_data:
        security_level = all_systems_data[current_system].get("SecurityLevel", "Unknown")

    # Format security level for display
    security_text = f"somewhere in {security_level.lower()} space"

    # Get current ship info
    active_ship_idx = data.get("active_ship", 0)
    ships = data.get("ships", [])
    ship_name = "Unknown Ship"

    if ships and 0 <= active_ship_idx < len(ships):
        ship_name = ships[active_ship_idx].get("name", "Unknown Ship")

    # Determine presence based on context
    if context == "dead":
        return ("Getting obliterated by hostile forces",
                "transferring consciousness to cloning bay...")

    elif context == "docked":
        docked_at = data.get("docked_at", "a space station")
        return (f"Docked at {docked_at}", security_text)

    elif context == "combat":
        return ("Engaged in combat", security_text)

    elif context == "traveling":
        return (f"Piloting a {ship_name}", security_text)

    elif context == "mining":
        return ("Mining asteroids", security_text)

    elif context == "menu":
        return ("Navigating menus", "In Main Menu")

    elif context == "galaxy_map":
        return ("Viewing galaxy map", f"planning route in {current_system}")

    elif context == "station_menu":
        docked_at = data.get("docked_at", "a space station")
        return (f"Managing affairs at {docked_at}", security_text)

    elif context == "trading":
        return ("Trading goods", security_text)

    elif context == "outfitting":
        return ("Outfitting ship", f"at {data.get('docked_at', 'station')}")

    # Default: flying around
    else:
        return (f"Piloting a {ship_name}", security_text)


def update_discord_presence(state=None, details=None, data=None, context=None):
    """Update Discord Rich Presence status

    Args:
        state: Small text shown below details (e.g., current location)
        details: Main text (e.g., current activity)
        data: Game save data (optional, for adaptive presence)
        context: Game context for adaptive presence (optional)
    """
    global discord_rpc

    if discord_rpc is None:
        return

    try:
        update_args = {
            "large_text": "Starscape: Text Adventure"
        }

        # Use adaptive presence if data and context provided
        if data and context:
            details, state = get_adaptive_presence(data, context)

        if state:
            update_args["state"] = state
        if details:
            update_args["details"] = details

        discord_rpc.update(**update_args)
    except Exception as e:
        # Silently fail - don't interrupt gameplay
        pass


def close_discord_rpc():
    """Close Discord Rich Presence connection"""
    global discord_rpc

    if discord_rpc:
        try:
            discord_rpc.clear()
            discord_rpc.close()
        except:
            pass
        discord_rpc = None


def read_data(save_name):
    """Load game data from save file"""
    save_path = Path.home() / ".starscape_text_adventure" / "saves" / save_name / "save.json"

    if not save_path.exists():
        return None

    with open(save_path, 'r') as f:
        return json.load(f)


def save_data(save_name, data):
    """Save game data to file"""
    save_path = Path.home() / ".starscape_text_adventure" / "saves" / save_name / "save.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, 'w') as f:
        json.dump(data, f, indent=4)


def get_key():
    """Get a single keypress (cross-platform)"""
    if os.name == 'nt':  # Windows
        import msvcrt
        key = msvcrt.getch()
        if key in [b'\xe0', b'\x00']:  # Arrow key prefix
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                return 'up'
            elif key == b'P':  # Down arrow
                return 'down'
        elif key == b'\r':  # Enter
            return 'enter'
        elif key == b'\x1b':  # Escape
            return 'esc'
        else:
            # Return the actual character
            try:
                return key.decode('utf-8').lower()
            except:
                return None
    else:  # Unix/Linux/Mac
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':  # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':  # Up arrow
                        return 'up'
                    elif ch3 == 'B':  # Down arrow
                        return 'down'
                return 'esc'
            elif ch == '\n' or ch == '\r':  # Enter
                return 'enter'
            else:
                # Return the actual character (lowercased)
                return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def capture_screen_content(func, *args, **kwargs):
    """Capture the output of a function without displaying it"""
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        func(*args, **kwargs)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    return output


def display_menu(title_, options, selected_index, previous_content=""):
    """Display menu with highlighted selection, preserving previous content"""
    clear_screen()

    # Re-print previous content if it exists
    if previous_content:
        print(previous_content, end='')
        print()  # Add spacing between content and menu

    title(title_)
    print()

    for i, option in enumerate(options):
        if i == selected_index:
            print(f"  > {option}")
        else:
            print(f"    {option}")

    print()
    print("  Use ↑/↓ arrows to navigate, Enter to select")


def arrow_menu(title, options, previous_content=""):
    """Display menu with arrow key navigation, return selected index"""
    selected = 0

    while True:
        display_menu(title, options, selected, previous_content)
        key = get_key()

        if key == 'up':
            selected = (selected - 1) % len(options)
        elif key == 'down':
            selected = (selected + 1) % len(options)
        elif key == 'enter':
            return selected


def default_data():
    """Return default game data structure"""
    return {
        "v": VERSION_CODE,  # save version code.
        "player_name": "Player",
        "credits": 5000,
        "current_system": "The Citadel",
        "docked_at": "The Citadel",
        "ships": [
            {
                "id": str(uuid4()),
                "name": "stratos",
                "nickname": "Stratos",
                "hull_hp": 200,
                "shield_hp": 200,
                "modules_installed": [],
            }
        ],
        "active_ship": 0,  # Index of currently active ship
        "inventory": {},
        "storage": {},
        "skills": {
            "combat": 0,      # Increases damage dealt and reduces damage taken
            "combat_xp": 0,   # XP towards next combat level
            "piloting": 0,    # Increases evasion chance and escape success rate
            "piloting_xp": 0, # XP towards next piloting level
            "mining": 0,      # Increases mining efficiency and stability management
            "mining_xp": 0,   # XP towards next mining level
        },
        "standing": {
            "Core Sec": 0,
            "Syndicate": 0,
            "Trade Union": 0,
            "Mining Guild": 0,
            "Lycentia": 0,
            "Forakus": 0,
            "Kavani": 0,
        },
        "tutorial_progress": {
            "completed": True  # there is no tutorial, so we skip it if the save is loaded in a future version with tutorial
        },
        "destination": "",  # Current navigation destination
        "anomalies": {},  # Discovered anomalies per system: {system_name: [anomaly1, anomaly2, ...]}
    }


def get_active_ship(data):
    """Get the player's currently active ship"""
    active_idx = data.get("active_ship", 0)
    if active_idx < len(data["ships"]):
        return data["ships"][active_idx]
    return data["ships"][0]


def load_ships_data():
    """Load ship data from ships.json"""
    with open(resource_path('ships.json'), 'r') as f:
        ships_data = json.load(f)
    return {ship['name'].lower(): ship for ship in ships_data['ships']}


def load_items_data():
    """Load item data from items.json"""
    with open(resource_path('items.json'), 'r') as f:
        items_data = json.load(f)
    return {item['name']: item for item in items_data['items']}


def get_ship_stats(ship_name):
    """Get ship stats from ships.json by ship name"""
    ships = load_ships_data()
    return ships.get(ship_name.lower(), {}).get('stats', {})


def get_max_hull(ship):
    """Get max hull HP for a ship from ships.json"""
    stats = get_ship_stats(ship['name'])
    return stats.get('Hull', 200)


def get_max_shield(ship):
    """Get max shield HP for a ship from ships.json"""
    stats = get_ship_stats(ship['name'])
    return stats.get('Shield', 200)


def xp_required_for_level(level):
    """Calculate XP required to reach the next level"""
    # Progressive scaling: each level requires more XP
    # Level 1: 100 XP, Level 2: 150 XP, Level 3: 200 XP, etc.
    return 100 + (level * 50)


def add_skill_xp(data, skill_name, xp_amount):
    """Add XP to a skill and handle level ups

    Args:
        data: Game data dictionary
        skill_name: 'combat', 'piloting', or 'mining'
        xp_amount: Amount of XP to add

    Returns:
        Number of levels gained (0 if no level up)
    """
    xp_key = f"{skill_name}_xp"

    # Initialize skill & XP if it doesn't exist (for old saves)
    if skill_name not in data["skills"]:
        data["skills"][skill_name] = 0
    if xp_key not in data["skills"]:
        data["skills"][xp_key] = 0

    data["skills"][xp_key] += xp_amount

    levels_gained = 0
    current_level = data["skills"][skill_name]

    # Check for level ups
    while data["skills"][xp_key] >= xp_required_for_level(current_level):
        data["skills"][xp_key] -= xp_required_for_level(current_level)
        data["skills"][skill_name] += 1
        current_level += 1
        levels_gained += 1

    return levels_gained


def display_xp_gain(skill_name, xp_gained, levels_gained, current_level, current_xp):
    """Display XP gain and level up information"""
    if levels_gained > 0:
        set_color("green")
        print(f"  {skill_name.title()} Skill Level Up! +{levels_gained} (now Level {current_level})")
        reset_color()

    xp_needed = xp_required_for_level(current_level)
    print(f"  +{xp_gained} {skill_name.title()} XP ({current_xp}/{xp_needed})")



def generate_enemy_fleet(security_level, data):
    """Generate an enemy fleet based on system security level and player progress"""
    # Get player's combat skill to scale enemy difficulty
    combat_skill = data.get("skills", {}).get("combat", 0)

    # Base enemy stats
    fleet = {
        "type": "",
        "size": 0,
        "ships": [],
        "total_firepower": 0,
        "warp_disruptor": False
    }

    # Determine fleet type and strength based on security
    match security_level:
        case "Secure":
            # Small drone fleets, weak
            fleet_types = [("Light Drones", 1, 3, 25, 10), ("Drone Fireteam", 3, 5, 30, 10)]
            chosen = random.choice(fleet_types)
            fleet["type"] = chosen[0]
            fleet["size"] = random.randint(chosen[1], chosen[2])
            base_hp = chosen[3]
            base_damage = chosen[4]
            disruptor_chance = 0.0

        case "Contested":
            # Medium drone fleets or small pirate groups
            if random.random() < 0.3:
                fleet["type"] = "Pirate Scouts"
                fleet["size"] = random.randint(1, 2)
                base_hp = 100
                base_damage = 20
            else:
                fleet["type"] = "Drone Squadron"
                fleet["size"] = random.randint(2, 4)
                base_hp = 55
                base_damage = 15
            disruptor_chance = 0.0

        case "Unsecure":
            # Larger pirate fleets or drone swarms
            fleet_types = [
                ("Pirate Raiders", 2, 3, 90, 30),
                ("Drone Swarm", 3, 5, 70, 22),
                ("Pirate Squadron", 2, 4, 115, 40)
            ]
            chosen = random.choice(fleet_types)
            fleet["type"] = chosen[0]
            fleet["size"] = random.randint(chosen[1], chosen[2])
            base_hp = chosen[3]
            base_damage = chosen[4]
            disruptor_chance = 0.2 if chosen != "Drone Swarm" else 0.0

        case "Wild":
            # Powerful pirate fleets, highly dangerous
            fleet_types = [
                ("Large Pirate Den", 4, 6, 180, 40),
                ("Large Drone Fleet", 4, 7, 75, 28),
                ("Drone Armada", 8, 14, 80, 35)
            ]
            chosen = random.choice(fleet_types)
            fleet["type"] = chosen[0]
            fleet["size"] = random.randint(chosen[1], chosen[2])
            base_hp = chosen[3]
            base_damage = chosen[4]
            disruptor_chance = 0.30

        case _:
            # Default case (shouldn't happen in Core space)
            return None

    # Scale enemies slightly with player combat skill
    skill_scaling = 1.0 + (combat_skill * 0.025)

    # Generate individual ships in fleet
    # Determine ship type name based on fleet type
    if "Pirate" in fleet["type"]:
        ship_type = "Pirate Fighter"
    else:
        ship_type = "Drone Fighter"

    for i in range(fleet["size"]):
        max_hull = int(base_hp * skill_scaling)
        max_shield = int(base_hp * 0.5 * skill_scaling)

        ship = {
            "name": f"{ship_type} #{i + 1}",
            "hull_hp": max_hull,
            "max_hull_hp": max_hull,
            "shield_hp": max_shield,
            "max_shield_hp": max_shield,
            "damage": int(
                base_damage * skill_scaling * random.uniform(0.9, 1.1)),
        }
        fleet["ships"].append(ship)
        fleet["total_firepower"] += ship["damage"]

    # Chance for warp disruptor (pirates only)
    if "Pirate" in fleet["type"] and random.random() < disruptor_chance:
        fleet["warp_disruptor"] = True

    return fleet


def enemy_encounter(enemy_fleet, system, save_name, data, previous_content=""):
    """Handle initial enemy encounter - choice to fight, run, or ignore"""
    clear_screen()

    if previous_content:
        print(previous_content, end='')
        print()

    print("=" * 60)
    print("  ", end="")
    set_color("red")
    set_color("blinking")
    set_color("reverse")
    print(" ⚠ HOSTILE CONTACT ⚠ ")
    reset_color()
    print("=" * 60)
    print()
    print(f"  Fleet Type: {enemy_fleet['type']}")
    print(f"  Fleet Size: {enemy_fleet['size']} ships")
    print(f"  Threat Level: ", end="")

    # Calculate threat level based on total firepower vs player ship
    player_ship = get_active_ship(data)
    max_hull = get_max_hull(player_ship)
    max_shield = get_max_shield(player_ship)
    threat_ratio = enemy_fleet["total_firepower"] / (max_hull + max_shield)

    if threat_ratio < 0.3:
        set_color("green")
        print("LOW")
    elif threat_ratio < 0.7:
        set_color("yellow")
        print("MODERATE")
    elif threat_ratio < 1.2:
        set_color("red")
        print("HIGH")
    else:
        set_color("red")
        set_color("blinking")
        print("EXTREME")
    reset_color()

    if enemy_fleet["warp_disruptor"]:
        print()
        set_color("red")
        print("  ⚠ WARP DISRUPTED ⚠")
        reset_color()

    print()

    content_buffer = StringIO()
    old_stdout = sys.stdout
    sys.stdout = content_buffer

    # Get screen content
    import io
    temp_buffer = io.StringIO()
    sys.stdout = temp_buffer

    # Print the encounter info again to capture it
    print("=" * 60)
    print("  ", end="")
    set_color("red")
    set_color("blinking")
    set_color("reverse")
    print(" ⚠ HOSTILE CONTACT ⚠ ")
    reset_color()
    print("=" * 60)
    print()
    print(f"  Fleet Type: {enemy_fleet['type']}")
    print(f"  Fleet Size: {enemy_fleet['size']} ships")
    print(f"  Threat Level: ", end="")
    if threat_ratio < 0.3:
        print("LOW")
    elif threat_ratio < 0.7:
        print("MODERATE")
    elif threat_ratio < 1.2:
        print("HIGH")
    else:
        print("EXTREME")
    if enemy_fleet["warp_disruptor"]:
        print()
        print("  ⚠ WARP DISRUPTOR DETECTED ⚠")
    print()

    encounter_content = temp_buffer.getvalue()
    sys.stdout = old_stdout

    options = ["Fight!", "Attempt to Escape", "Ignore and Tank Damage"]
    choice = arrow_menu("What will you do?", options, previous_content + encounter_content)

    if choice == 0:
        # Fight
        result = combat_loop(enemy_fleet, system, save_name, data)
        return result

    elif choice == 1:
        # Attempt escape
        return attempt_escape(enemy_fleet, system, save_name, data)

    elif choice == 2:
        # Ignore & tank damage
        return ignore_enemies(enemy_fleet, system, save_name, data)


def attempt_escape(enemy_fleet, system, save_name, data):
    """Attempt to escape from combat"""
    clear_screen()
    title("ATTEMPTING ESCAPE")
    print()

    player_ship = get_active_ship(data)
    piloting_skill = data.get("skills", {}).get("piloting", 0)

    # Warp disruptor prevents escape entirely
    if enemy_fleet["warp_disruptor"]:
        print("  ⚠ WARP DISRUPTOR DETECTED ⚠")
        print()
        print("  The enemy's warp disruption field prevents any escape!")
        print("  Your jump drive is completely disabled.")
        print()
        print("  You are forced into combat!")
        sleep(2)
        input("Press Enter to engage...")

        return combat_loop(enemy_fleet, system, save_name, data, forced_combat=True)

    # Base escape chance: 75%
    escape_chance = 0.75

    # Piloting skill increases escape chance
    escape_chance += min(piloting_skill * 0.05, 0.50)

    if random.random() < escape_chance:
        # Successful escape
        print("  Successfully escaped!")
        print()

        save_data(save_name, data)
        input("Press Enter to continue...")

        return "continue"
    else:
        # Failed escape - forced into combat
        print("  You reacted too slow!")
        print("  Enemy fleet has intercepted you!")
        print()
        input("Press Enter to engage in combat...")

        return combat_loop(enemy_fleet, system, save_name, data, forced_combat=True)


def ignore_enemies(enemy_fleet, system, save_name, data):
    """Ignore enemies and tank the damage"""
    clear_screen()
    title("IGNORING HOSTILE FLEET")
    print()

    player_ship = get_active_ship(data)

    print("  You continue on your course, ignoring the hostile fleet.")
    print("  They open fire on your ship!")
    print()
    sleep(1)

    # Calculate damage - 70% of total firepower
    total_damage = int(enemy_fleet["total_firepower"] * 0.7 * random.uniform(0.8, 1.2))

    print(f"  Incoming damage: {total_damage}")
    print()
    sleep(0.5)

    # Apply damage
    remaining_damage = total_damage

    if player_ship["shield_hp"] > 0:
        shield_damage = min(remaining_damage, player_ship["shield_hp"])
        player_ship["shield_hp"] -= shield_damage
        remaining_damage -= shield_damage
        max_shield = get_max_shield(player_ship)
        print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield} (-{shield_damage})")
        sleep(0.3)

    if remaining_damage > 0:
        player_ship["hull_hp"] -= remaining_damage
        max_hull = get_max_hull(player_ship)
        print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull} (-{remaining_damage})")
        sleep(0.3)

    print()

    if player_ship["hull_hp"] <= 0:
        print("  Your ship has been destroyed!")
        sleep(1.5)
        return "death"
    elif player_ship["hull_hp"] < get_max_hull(player_ship) * 0.2:
        set_color("red")
        print("  ⚠ WARNING: CRITICAL HULL DAMAGE ⚠")
        reset_color()
        print()

    print("  You've successfully passed through the hostile zone.")
    print()

    # No skill increase for ignoring
    save_data(save_name, data)
    input("Press Enter to continue...")
    return "continue"


def combat_loop(enemy_fleet, system, save_name, data, forced_combat=False):
    """Main turn-based combat loop"""
    # Update Discord presence for combat
    update_discord_presence(data=data, context="combat")

    player_ship = get_active_ship(data)
    combat_skill = data.get("skills", {}).get("combat", 0)
    piloting_skill = data.get("skills", {}).get("piloting", 0)

    turn = 1
    combat_ongoing = True

    while combat_ongoing:
        # Regenerate shields slightly each turn (10% of max shields)
        max_shield = get_max_shield(player_ship)
        shield_regen = int(max_shield * 0.10)
        if player_ship["shield_hp"] < max_shield:
            player_ship["shield_hp"] = min(player_ship["shield_hp"] + shield_regen, max_shield)

        # Also regenerate enemy shields slightly (5%)
        for ship in enemy_fleet["ships"]:
            if ship["hull_hp"] > 0 and ship["shield_hp"] < ship["max_shield_hp"]:
                enemy_shield_regen = int(ship["max_shield_hp"] * 0.05)
                ship["shield_hp"] = min(ship["shield_hp"] + enemy_shield_regen, ship["max_shield_hp"])

        clear_screen()
        title(f"COMBAT - TURN {turn}")
        print()

        # Display player status
        print("YOUR SHIP:")
        max_shield = get_max_shield(player_ship)
        max_hull = get_max_hull(player_ship)
        print(f"  Shield: {player_ship['shield_hp']}/{max_shield}")
        shield_bar = create_health_bar(player_ship['shield_hp'], max_shield, 30, "cyan")
        print(f"  {shield_bar}")
        print(f"  Hull:   {player_ship['hull_hp']}/{max_hull}")
        hull_bar = create_health_bar(player_ship['hull_hp'], max_hull, 30, "red")
        print(f"  {hull_bar}")
        print()

        # Display enemy fleet status
        print(f"ENEMY FLEET ({enemy_fleet['type']}):")
        alive_enemies = [ship for ship in enemy_fleet["ships"] if ship["hull_hp"] > 0]

        for i, ship in enumerate(alive_enemies):
            print(f"  [{i+1}] {ship['name']}")
            print(f"      Shield: {ship['shield_hp']}/{ship['max_shield_hp']} | Hull: {ship['hull_hp']}/{ship['max_hull_hp']}")

        print()
        print("=" * 60)
        print()

        # Combat options
        options = [
            "Fire Weapons (All Targets)",
            "Focus Fire (Single Target)",
            "Attempt Retreat",
            "View Detailed Stats"
        ]

        # Capture current screen
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        # Re-print combat status
        print(f"COMBAT - TURN {turn}")
        print()
        print("YOUR SHIP:")
        max_shield = get_max_shield(player_ship)
        max_hull = get_max_hull(player_ship)
        print(f"  Shield: {player_ship['shield_hp']}/{max_shield}")
        print(f"  Hull:   {player_ship['hull_hp']}/{max_hull}")
        print()
        print(f"ENEMY FLEET ({enemy_fleet['type']}):")
        for i, ship in enumerate(alive_enemies):
            print(f"  [{i+1}] {ship['name']}")
            print(f"      Shield: {ship['shield_hp']}/{ship['max_shield_hp']} | Hull: {ship['hull_hp']}/{ship['max_hull_hp']}")
        print()

        combat_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Select action:", options, combat_content)

        if choice == 0:
            # Fire at all targets
            player_damage_distributed(alive_enemies, combat_skill, data)

        elif choice == 1:
            # Focus fire on single target
            clear_screen()
            print(combat_content)
            target_options = [f"{ship['name']} (Hull: {ship['hull_hp']}/{ship['max_hull_hp']})" for ship in alive_enemies]
            target_options.append("Cancel")

            target_choice = arrow_menu("Select target:", target_options, combat_content)

            if target_choice == len(alive_enemies):
                continue  # Cancel, go back to combat menu

            player_damage_focused(alive_enemies[target_choice], combat_skill, data)

        elif choice == 2:
            # Attempt retreat
            retreat_result = attempt_retreat_from_combat(enemy_fleet, turn, forced_combat, data)

            if retreat_result == "success":
                # Small combat XP for participating
                add_skill_xp(data, "combat", 5)
                save_data(save_name, data)
                # Update presence - back to traveling after escape
                update_discord_presence(data=data, context="traveling")
                return "continue"
            elif retreat_result == "death":
                # Died while retreating - still get small combat XP
                add_skill_xp(data, "combat", 5)
                save_data(save_name, data)
                return "death"
            elif retreat_result == "failed":
                # Take extra damage and continue combat
                print()
                print("  Retreat failed! Taking extra damage...")
                sleep(1)
            # If "impossible", just continue combat
            continue

        elif choice == 3:
            # View detailed stats
            show_detailed_combat_stats(player_ship, enemy_fleet, data)
            continue

        # Check if all enemies destroyed
        alive_enemies = [ship for ship in enemy_fleet["ships"] if ship["hull_hp"] > 0]
        if not alive_enemies:
            clear_screen()
            title("VICTORY!")
            print()
            print("  All enemy ships have been destroyed!")
            print()

            # Calculate rewards
            credits_earned = enemy_fleet["size"] * 150 * random.randint(8, 12) // 10
            data["credits"] += credits_earned

            # Combat XP gain - scales with fleet size
            combat_xp = 20 + (enemy_fleet["size"] * 10)
            levels_gained = add_skill_xp(data, "combat", combat_xp)

            print(f"  Credits earned: ¢{credits_earned}")
            display_xp_gain("combat", combat_xp, levels_gained,
                          data["skills"]["combat"], data["skills"]["combat_xp"])
            print()

            save_data(save_name, data)
            # Update presence - back to traveling after victory
            update_discord_presence(data=data, context="traveling")
            input("Press Enter to continue...")
            return "continue"

        # Enemy turn - they attack
        enemy_attacks(alive_enemies, player_ship, piloting_skill)

        # Check if player died
        if player_ship["hull_hp"] <= 0:
            clear_screen()
            title("DEFEAT")
            print()
            print("  Your ship has been destroyed!")
            print()
            sleep(1.5)

            # Small combat XP even on loss
            combat_xp = 5
            add_skill_xp(data, "combat", combat_xp)
            save_data(save_name, data)

            return "death"

        print()
        input("Press Enter to continue to next turn...")
        turn += 1


def create_health_bar(current, maximum, width, color="green"):
    """Create a colored health bar"""
    if maximum == 0:
        filled = 0
    else:
        filled = int((current / maximum) * width)

    empty = width - filled

    # Color codes
    colors = {
        "green": "\033[32m",
        "cyan": "\033[36m",
        "yellow": "\033[33m",
        "red": "\033[31m",
    }

    color_code = colors.get(color, "\033[32m")

    bar = f"{color_code}{'█' * filled}{RESET_COLOR}{'░' * empty}"
    return bar


def player_damage_distributed(enemies, combat_skill, data):
    """Player attacks all enemies with distributed damage"""
    clear_screen()
    title("FIRING WEAPONS")
    print()

    # Base damage - scales with combat skill
    base_damage = 40 + (combat_skill * 2)
    damage_per_enemy = base_damage // len(enemies)

    print(f"  Distributing {base_damage} damage across {len(enemies)} targets...")
    print()
    sleep(0.5)

    for enemy in enemies:
        # Random variance
        damage = int(damage_per_enemy * random.uniform(0.85, 1.15))
        apply_damage_to_enemy(enemy, damage)
        sleep(0.3)

    print()
    input("Press Enter to continue...")


def player_damage_focused(enemy, combat_skill, data):
    """Player attacks single enemy with focused damage"""
    clear_screen()
    title("FOCUSED FIRE")
    print()

    # Higher damage when focused - scales with combat skill
    damage = int((60 + (combat_skill * 3)) * random.uniform(0.9, 1.1))

    print(f"  Targeting {enemy['name']}...")
    print()
    sleep(0.5)

    apply_damage_to_enemy(enemy, damage)

    print()
    input("Press Enter to continue...")


def apply_damage_to_enemy(enemy, damage):
    """Apply damage to an enemy ship"""
    remaining_damage = damage

    # Damage shields first
    if enemy["shield_hp"] > 0:
        shield_damage = min(remaining_damage, enemy["shield_hp"])
        enemy["shield_hp"] -= shield_damage
        remaining_damage -= shield_damage
        print(f"  Hit {enemy['name']}'s shields for {shield_damage} damage!")

    # Then damage hull
    if remaining_damage > 0:
        enemy["hull_hp"] -= remaining_damage
        print(f"  Hit {enemy['name']}'s hull for {remaining_damage} damage!")

        if enemy["hull_hp"] <= 0:
            enemy["hull_hp"] = 0
            set_color("green")
            print(f"  {enemy['name']} DESTROYED!")
            reset_color()


def apply_damage_to_player(player_ship, damage):
    """Apply damage to player ship, shields first then hull

    Returns:
        bool: True if ship was destroyed, False otherwise
    """
    remaining_damage = damage

    # Damage shields first
    if player_ship["shield_hp"] > 0:
        shield_damage = min(remaining_damage, player_ship["shield_hp"])
        player_ship["shield_hp"] -= shield_damage
        remaining_damage -= shield_damage
        set_color("cyan")
        print(f"     Shield damaged: -{shield_damage} HP")
        reset_color()

    # Then damage hull
    if remaining_damage > 0:
        player_ship["hull_hp"] -= remaining_damage
        set_color("red")
        print(f"     Hull damaged: -{remaining_damage} HP")
        reset_color()

        # Check if ship is destroyed
        if player_ship["hull_hp"] <= 0:
            player_ship["hull_hp"] = 0
            return True

    return False


def enemy_attacks(enemies, player_ship, piloting_skill):
    """All enemies attack the player"""
    clear_screen()
    title("ENEMY TURN")
    print()

    print("  Enemy fleet is attacking!")
    print()
    sleep(0.8)

    total_damage = 0

    for enemy in enemies:
        # Base damage with variance
        damage = int(enemy["damage"] * random.uniform(0.8, 1.2))

        # Piloting skill gives evasion chance
        evasion_chance = min(piloting_skill * 0.02, 0.25)  # Max 25% evasion

        if random.random() < evasion_chance:
            print(f"  {enemy['name']}'s attack missed! (Evaded)")
            sleep(0.3)
        else:
            total_damage += damage
            print(f"  {enemy['name']} deals {damage} damage!")
            sleep(0.3)

    print()
    print(f"  Total incoming damage: {total_damage}")
    print()
    sleep(0.5)

    # Apply damage to player
    remaining_damage = total_damage

    if player_ship["shield_hp"] > 0:
        shield_damage = min(remaining_damage, player_ship["shield_hp"])
        player_ship["shield_hp"] -= shield_damage
        remaining_damage -= shield_damage
        print(f"  Your shields absorbed {shield_damage} damage")
        max_shield = get_max_shield(player_ship)
        print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield}")
        sleep(0.3)

    if remaining_damage > 0:
        player_ship["hull_hp"] -= remaining_damage
        set_color("red")
        print(f"  Your hull took {remaining_damage} damage!")
        reset_color()
        max_hull = get_max_hull(player_ship)
        print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull}")
        sleep(0.3)

        if player_ship["hull_hp"] < max_hull * 0.2:
            print()
            set_color("red")
            set_color("blinking")
            print("  ⚠ CRITICAL HULL DAMAGE ⚠")
            reset_color()


def attempt_retreat_from_combat(enemy_fleet, turn, forced_combat, data):
    """Attempt to retreat during combat"""
    clear_screen()
    title("ATTEMPTING RETREAT")
    print()

    if forced_combat and turn < 2:
        print("  You cannot retreat yet!")
        print("  The enemy has you locked down.")
        print(f"  You must fight for at least 1 turn. (Turn {turn}/1)")
        print()
        input("Press Enter to continue...")
        return "impossible"

    # Warp disruptor prevents retreat for first 5 turns
    if enemy_fleet["warp_disruptor"] and turn < 6:
        print("  ⚠ WARP DISRUPTOR ACTIVE ⚠")
        print()
        print("  The enemy's warp disruption field prevents retreat!")
        print(f"  You must fight for at least 5 turns. (Turn {turn}/5)")
        print()
        input("Press Enter to continue...")
        return "impossible"

    piloting_skill = data.get("skills", {}).get("piloting", 0)

    # Retreat chance decreases as combat goes on
    base_retreat_chance = max(0.50 - (turn * 0.05), 0.20)
    retreat_chance = base_retreat_chance + (piloting_skill * 0.03)

    # Warp disruptor makes retreat harder (if it's past turn 5)
    if enemy_fleet["warp_disruptor"]:
        retreat_chance *= 0.4
        print("  Warp disruptor is weakening, but still interfering!")
        print()

    print("  Charging jump drive...")
    sleep(1)
    print("  Calculating escape vector...")
    sleep(1)
    print("  Attempting to disengage...")
    sleep(1)

    if random.random() < retreat_chance:
        print()
        print("  Successfully retreated from combat!")
        print()

        # Piloting XP for successful retreat
        piloting_xp = 30
        levels_gained = add_skill_xp(data, "piloting", piloting_xp)
        display_xp_gain("piloting", piloting_xp, levels_gained,
                       data["skills"]["piloting"], data["skills"]["piloting_xp"])
        print()

        # Take damage while retreating
        player_ship = get_active_ship(data)
        damage_taken = int(enemy_fleet["total_firepower"] * 0.3 * random.uniform(0.5, 1.0))

        if player_ship["shield_hp"] > 0:
            shield_damage = min(damage_taken, player_ship["shield_hp"])
            player_ship["shield_hp"] -= shield_damage
            damage_taken -= shield_damage
            max_shield = get_max_shield(player_ship)
            print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield} (-{shield_damage})")

        if damage_taken > 0:
            player_ship["hull_hp"] -= damage_taken
            max_hull = get_max_hull(player_ship)
            print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull} (-{damage_taken})")

        print()
        input("Press Enter to continue...")

        if player_ship["hull_hp"] <= 0:
            return "death"
        return "success"
    else:
        print()
        print("  Retreat failed!")
        print("  You remain engaged in combat.")
        print()
        input("Press Enter to continue...")
        return "failed"


def show_detailed_combat_stats(player_ship, enemy_fleet, data):
    """Show detailed stats during combat"""
    clear_screen()
    title("DETAILED COMBAT STATISTICS")
    print()

    max_shield = get_max_shield(player_ship)
    max_hull = get_max_hull(player_ship)

    print("YOUR SHIP:")
    print(f"  Name: {player_ship.get('nickname', 'Unknown')}")
    print(f"  Type: {player_ship.get('name', 'Unknown').title()}")
    print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield}")
    print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull}")
    print()

    print("YOUR SKILLS:")
    combat_level = data['skills']['combat']
    combat_xp = data['skills'].get('combat_xp', 0)
    combat_xp_needed = xp_required_for_level(combat_level)
    print(f"  Combat: Level {combat_level} ({combat_xp}/{combat_xp_needed} XP)")
    print(f"    - Damage Bonus: +{combat_level * 2}")

    piloting_level = data['skills']['piloting']
    piloting_xp = data['skills'].get('piloting_xp', 0)
    piloting_xp_needed = xp_required_for_level(piloting_level)
    print(f"  Piloting: Level {piloting_level} ({piloting_xp}/{piloting_xp_needed} XP)")
    print(f"    - Evasion Chance: {min(piloting_level * 2, 25)}%")
    print()

    print("ENEMY FLEET:")
    print(f"  Type: {enemy_fleet['type']}")
    print(f"  Total Ships: {enemy_fleet['size']}")
    alive_count = sum(1 for ship in enemy_fleet['ships'] if ship['hull_hp'] > 0)
    print(f"  Remaining: {alive_count}")
    print(f"  Warp Disruptor: {'ACTIVE' if enemy_fleet['warp_disruptor'] else 'None'}")
    print()

    print("ENEMY SHIPS:")
    for ship in enemy_fleet['ships']:
        if ship['hull_hp'] > 0:
            print(f"  • {ship['name']}")
            print(f"    Shield: {ship['shield_hp']}/{ship['max_shield_hp']}")
            print(f"    Hull: {ship['hull_hp']}/{ship['max_hull_hp']}")
            print(f"    Damage: {ship['damage']}")

    print()
    input("Press Enter to return to combat...")


def generate_anomalies(system_name, system_security):
    """Generate random anomalies for a star system based on security level"""
    anomalies = []
    current_time = time()

    # Anomaly spawn rates by security level
    anomaly_counts = {
        "Core": 0,
        "Secure": random.randint(1, 2),
        "Contested": random.randint(2, 3),
        "Unsecure": random.randint(2, 4),
        "Wild": random.randint(3, 6),
    }

    num_anomalies = anomaly_counts.get(system_security, 0)

    # Weighted anomaly types by security level
    anomaly_pools = {
        "Secure": ["AT", "AL", "CM", "BF", "SP"],
        "Contested": ["AT", "AL", "AA", "CM", "BF", "DH", "SP", "MT"],
        "Unsecure": ["AT", "AL", "AA", "CM", "BF", "DH", "SP", "MT", "WH"],
        "Wild": ["AL", "AA", "AN", "VX", "CM", "BF", "DH", "SP", "MT", "WH", "FO"],
    }

    pool = anomaly_pools.get(system_security, [])

    for _ in range(num_anomalies):
        if pool:
            anomaly_type = random.choice(pool)

            # Determine duration for wormholes
            if anomaly_type == "WH":
                # 5% chance for 2-week wormhole, 95% chance for 48-hour wormhole
                if random.random() < 0.05:
                    duration = 14 * 24 * 3600  # 2 weeks in seconds
                else:
                    duration = 48 * 3600  # 48 hours in seconds
            else:
                duration = 48 * 3600  # Standard 48 hours

            anomaly = {
                "type": anomaly_type,
                "visited": False,
                "timestamp": current_time,
                "duration": duration,
            }
            anomalies.append(anomaly)

    return anomalies


def manage_system_anomalies(save_name, data, system_name):
    """Manage anomalies for a system: clean up expired ones and generate new ones if needed"""
    current_time = time()
    system = system_data(system_name)
    system_security = system.get("SecurityLevel", "Secure")

    # Initialize anomalies dict if needed
    if "anomalies" not in data:
        data["anomalies"] = {}

    # Initialize system visit tracking
    if "last_system_visit" not in data:
        data["last_system_visit"] = {}

    # Get existing anomalies for this system
    existing_anomalies = data["anomalies"].get(system_name, [])

    # Clean up expired anomalies (older than their duration)
    cleaned_anomalies = []
    for anomaly in existing_anomalies:
        anomaly_age = current_time - anomaly.get("timestamp", current_time)
        duration = anomaly.get("duration", 48 * 3600)

        if anomaly_age < duration:
            cleaned_anomalies.append(anomaly)

    # Get last visit time
    last_visit = data["last_system_visit"].get(system_name, 0)
    time_since_visit = current_time - last_visit

    # Generate new anomalies if enough time has passed (every 12 hours, capped at 48 hours)
    if last_visit == 0:
        # First visit - generate anomalies
        new_anomalies = generate_anomalies(system_name, system_security)
        cleaned_anomalies.extend(new_anomalies)
    elif time_since_visit >= 12 * 3600:
        # Generate anomalies for each 12-hour period, capped at 48 hours
        periods_elapsed = min(int(time_since_visit / (12 * 3600)), 4)  # Cap at 4 periods (48 hours)

        for _ in range(periods_elapsed):
            new_anomalies = generate_anomalies(system_name, system_security)
            cleaned_anomalies.extend(new_anomalies)

    # Update system data
    data["anomalies"][system_name] = cleaned_anomalies
    data["last_system_visit"][system_name] = current_time
    save_data(save_name, data)

    return cleaned_anomalies


def get_anomaly_name(anomaly_type):
    """Get the full name of an anomaly type"""
    names = {
        "AT": "Small Asteroid Field",
        "AL": "Large Asteroid Field",
        "AA": "All-Axnit Asteroid Field",
        "AN": "All-Narcor Asteroid Field",
        "VX": "Vexnium Asteroid Field",
        "CM": "Comet",
        "BF": "Battlefield",
        "DH": "Drone Hideout",
        "SP": "Spice Platform",
        "MT": "Monument",
        "WH": "Wormhole",
        "FO": "Frontier Outpost",
    }
    return names.get(anomaly_type, "Unknown Anomaly")


def scan_for_anomalies(save_name, data):
    """Scan the current system for anomalies using a system probe"""
    clear_screen()
    title("SCAN FOR ANOMALIES")
    print()

    # Check if player has a system probe
    if data.get("inventory", {}).get("System Probe", 0) < 1:
        print("  You need a System Probe to scan for anomalies!")
        print()
        print("  System Probes can be purchased from the General Marketplace")
        print("  at most space stations.")
        print()
        input("Press Enter to continue...")
        return

    # Consume the probe
    data["inventory"]["System Probe"] -= 1
    if data["inventory"]["System Probe"] <= 0:
        del data["inventory"]["System Probe"]

    current_system = data["current_system"]

    # Scan animation
    print("  Deploying System Probe...")
    sleep(0.5)
    print("  Scanning...")
    for i in range(3):
        print("  .", end="", flush=True)
        sleep(0.3)
    print()
    print()
    sleep(0.3)

    # Manage anomalies (cleanup expired + generate new if needed)
    manage_system_anomalies(save_name, data, current_system)

    anomalies = data.get("anomalies", {}).get(current_system, [])

    # Display results
    clear_screen()
    title("SCAN RESULTS")
    print()
    print(f"  System: {current_system}")
    system = system_data(current_system)
    system_security = system.get("SecurityLevel", "Secure")
    print(f"  Security: {system_security}")
    print()

    if not anomalies:
        print("  No anomalies detected in this system.")
    else:
        print(f"  {len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} detected:")
        print()
        for i, anomaly in enumerate(anomalies):
            visited_str = " (Visited)" if anomaly.get("visited") else ""
            anomaly_name = get_anomaly_name(anomaly['type'])

            # Show duration for wormholes
            if anomaly['type'] == "WH":
                duration_hours = anomaly.get('duration', 48 * 3600) / 3600
                if duration_hours >= 24:
                    duration_days = duration_hours / 24
                    if duration_days >= 7:
                        duration_str = f" ({int(duration_days/7)} week duration)"
                    else:
                        duration_str = f" ({int(duration_days)} day duration)"
                else:
                    duration_str = f" ({int(duration_hours)}h duration)"
                print(f"    [{i+1}] {anomaly_name}{duration_str}{visited_str}")
            else:
                print(f"    [{i+1}] {anomaly_name}{visited_str}")

    print()
    save_data(save_name, data)
    input("Press Enter to continue...")


def visit_anomalies_menu(save_name, data):
    """Menu to visit discovered anomalies in current system"""
    current_system = data["current_system"]

    if current_system not in data.get("anomalies", {}):
        clear_screen()
        title("ANOMALIES")
        print()
        print("  No anomalies have been scanned in this system yet.")
        print("  Use a System Probe to scan for anomalies.")
        print()
        input("Press Enter to continue...")
        return

    anomalies = data["anomalies"][current_system]

    if not anomalies:
        clear_screen()
        title("ANOMALIES")
        print()
        print("  No anomalies detected in this system.")
        print()
        input("Press Enter to continue...")
        return

    while True:
        clear_screen()
        title(f"ANOMALIES - {current_system}")
        print()
        print(f"  {len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} detected:")
        print()

        options = []
        for i, anomaly in enumerate(anomalies):
            visited_str = " (Visited)" if anomaly.get("visited") else ""
            options.append(f"{get_anomaly_name(anomaly['type'])}{visited_str}")
        options.append("Back")

        choice = arrow_menu("Select anomaly to visit:", options)

        if choice == len(anomalies):
            return

        # Visit the selected anomaly
        visit_anomaly(save_name, data, anomalies[choice])


def visit_anomaly(save_name, data, anomaly):
    """Visit a specific anomaly"""
    anomaly_type = anomaly["type"]
    anomaly_name = get_anomaly_name(anomaly_type)

    # Mark as visited
    anomaly["visited"] = True
    save_data(save_name, data)

    # Ore-bearing anomalies
    if anomaly_type in ["AT", "AL", "AA", "AN", "VX", "CM", "MT"]:
        mine_anomaly(save_name, data, anomaly)
    else:
        clear_screen()
        title(anomaly_name.upper())
        print()
        print(f"  {anomaly_name} visit not yet implemented.")
        print()
        input("Press Enter to continue...")


def mine_anomaly(save_name, data, anomaly):
    """Mine ores from an ore-bearing anomaly"""
    anomaly_type = anomaly["type"]
    anomaly_name = get_anomaly_name(anomaly_type)

    update_discord_presence(data=data, context="mining")

    # Define ore types and quantities for each anomaly type
    ore_configs = {
        "AT": {
            "ores": ["Korrelite Ore", "Korrelite Ore (Superior)", "Reknite Ore", "Gellium Ore"],
            "count": random.randint(3, 8),
        },
        "AL": {
            "ores": ["Korrelite Ore", "Korrelite Ore (Superior)", "Reknite Ore", "Reknite Ore (Superior)", "Gellium Ore", "Gellium Ore (Superior)"],
            "count": random.randint(7, 16),
        },
        "AA": {
            "ores": ["Axnit Ore", "Axnit Ore (Pristine)"],
            "count": random.randint(4, 10),
        },
        "AN": {
            "ores": ["Narcor Ore", "Red Narcor Ore"],
            "count": random.randint(4, 9),
        },
        "VX": {
            "ores": ["Vexnium Ore"],
            "count": random.randint(1, 4),
        },
        "CM": {
            "ores": ["Water Ice"],
            "count": random.randint(3, 8),
        },
        "MT": {
            "ores": ["Korrelite Ore (Pristine)", "Reknite Ore (Pristine)", "Gellium Ore (Pristine)"],
            "count": 8,
        },
    }

    config = ore_configs.get(anomaly_type, {"ores": ["Korrelite Ore"], "count": 3})

    # Load or generate asteroids for this anomaly
    if "asteroids" not in anomaly:
        # Generate asteroids for first visit
        asteroids = []
        for _ in range(config["count"]):
            ore_type = random.choice(config["ores"])
            # Adjust quantity based on anomaly type
            if anomaly_type == "VX":
                quantity = random.randint(4, 8)
            elif anomaly_type == "CM":
                quantity = random.randint(8, 24)
            else:
                quantity = random.randint(32, 96)
            asteroids.append({"ore": ore_type, "quantity": quantity, "mined": 0, "anomaly_type": anomaly_type})
        anomaly["asteroids"] = asteroids
    else:
        asteroids = anomaly["asteroids"]
        # Add anomaly_type to existing asteroids if not present
        for asteroid in asteroids:
            if "anomaly_type" not in asteroid:
                asteroid["anomaly_type"] = anomaly_type

    # Check for crystalline entities at VX anomalies
    vexnium_guarded = anomaly_type == "VX" and random.random() < 0.8
    if vexnium_guarded:
        clear_screen()
        title("VEXNIUM ANOMALY")
        print()
        print("  ⚠ WARNING: Crystalline entities detected!")
        print()
        print("  This anomaly is guarded by hostile crystalline life forms.")
        print("  They will attack if you attempt to mine here.")
        print()
        print("  Proceed with caution.")
        print()
        input("Press Enter to continue...")

    # Mining loop
    while asteroids:
        clear_screen()
        title(f"{anomaly_name.upper()} - MINING")
        print()
        print(f"  {len(asteroids)} asteroid{'s' if len(asteroids) != 1 else ''} remaining")
        print()

        options = []
        for i, asteroid in enumerate(asteroids):
            ore_name = asteroid["ore"]
            quantity = asteroid["quantity"]
            mined = asteroid["mined"]
            progress_str = f" [{mined}/{quantity} mined]" if mined > 0 else ""
            options.append(f"{ore_name} ({quantity} units){progress_str}")
        options.append("Leave anomaly")

        choice = arrow_menu("Select asteroid to mine:", options)

        if choice == len(asteroids):
            # Save asteroid states before leaving
            save_data(save_name, data)
            update_discord_presence(data=data, context="traveling")
            return

        # Mine the selected asteroid
        result = mine_asteroid(save_name, data, asteroids[choice], vexnium_guarded)

        if result == "death":
            animated_death_screen(save_name, data)
            return
        elif result == "escaped":
            save_data(save_name, data)
            return
        elif result == "completed":
            # Remove the depleted asteroid
            asteroids.pop(choice)
            # Save updated asteroid list
            save_data(save_name, data)

    # If all asteroids depleted, mark for deletion
    if not asteroids:
        # Find and remove this anomaly from the system's anomaly list
        current_system = data["current_system"]
        if current_system in data.get("anomalies", {}):
            system_anomalies = data["anomalies"][current_system]
            # Find this specific anomaly object and remove it
            if anomaly in system_anomalies:
                system_anomalies.remove(anomaly)
                save_data(save_name, data)

        clear_screen()
        title("ANOMALY DEPLETED")
        print()
        print(f"  {anomaly_name} has been fully mined.")
        print("  The anomaly has dissipated.")
        print()
        input("Press Enter to continue...")


def mine_asteroid(save_name, data, asteroid, guarded=False):
    """Mine a single asteroid with interactive laser intensity, stability, and random events"""
    ore_name = asteroid["ore"]
    total_quantity = asteroid["quantity"]
    current_mined = asteroid["mined"]

    # Get player ship stats
    player_ship = get_active_ship(data)
    ship_data = load_ships_data().get(player_ship["name"].lower(), {})
    ship_class = ship_data.get("class", "Fighter")
    ship_stats = ship_data.get("stats", {})
    dps = ship_stats.get("DPS", 100)

    # Check if ship is a miner
    if ship_class != "Miner":
        clear_screen()
        title("INEFFICIENT MINING SHIP")
        print()
        set_color("yellow")
        print("  ⚠ WARNING: This ship is not designed for mining!")
        reset_color()
        print()
        print(f"  Your {player_ship.get('nickname', player_ship['name'].title())} ({ship_class})")
        print("  is poorly equipped for mining operations.")
        print()
        print("  Mining will be extremely slow and inefficient.")
        print("  Consider using a Miner-class ship for better results.")
        print()
        input("Press Enter to continue anyway...")

    # Get current system and security level for random events
    current_system = data.get("current_system", "Unknown")
    try:
        with open(resource_path('system_data.json'), 'r') as f:
            all_systems_data = json.load(f)
        security_level = all_systems_data.get(current_system, {}).get("SecurityLevel", "Secure")
    except:
        security_level = "Secure"

    # Get mining skill level
    mining_skill = data.get("skills", {}).get("mining", 0)

    # Asteroid state
    stability = 100.0
    remaining_ore = total_quantity - current_mined
    units_collected = current_mined

    # Base mining efficiency based on ship class
    if ship_class == "Miner":
        base_efficiency = 1.0 + (dps / 500) + (mining_skill * 0.05)
    else:
        base_efficiency = 0.15 * (0.5 + (dps / 1000)) + (mining_skill * 0.02)

    # Trigger crystalline guardian attack if guarded
    if guarded and random.random() < 0.8:
        clear_screen()
        update_discord_presence(data=data, context="combat")
        print("=" * 60)
        set_color("magenta")
        set_color("blinking")
        set_color("reverse")
        print("⚠ CRYSTALLINE GUARDIAN ATTACK ⚠")
        reset_color()
        print("=" * 60)
        print()
        print("  The crystalline guardians are attacking!")
        print()
        sleep(1)

        # Generate crystalline enemy fleet
        enemy_fleet = {
            "type": "Crystalline Guardians",
            "size": random.randint(2, 4),
            "warp_disruptor": False,
            "total_firepower": 500,
            "ships": []
        }

        for i in range(enemy_fleet["size"]):
            entity = {
                "name": f"Crystalline Guardian {i+1}",
                "shield_hp": 100,
                "max_shield_hp": 100,
                "hull_hp": 500,
                "max_hull_hp": 500,
                "damage": 125,
            }
            enemy_fleet["ships"].append(entity)

        system = system_data(data["current_system"])
        result = combat_loop(enemy_fleet, system, save_name, data, forced_combat=True)

        if result == "death":
            return "death"
        elif result == "continue":
            # Successfully defeated, continue mining
            pass
        else:
            # Escaped
            return "escaped"

    # Mining loop
    total_xp_gained = 0

    while remaining_ore > 0 and stability > 0:
        clear_screen()
        update_discord_presence(data=data, context="mining")
        title("MINING ASTEROID")
        print()
        print(f"  Ore: {ore_name}")
        print(f"  Ship: {player_ship.get('nickname', player_ship['name'].title())} ({ship_class})")
        print(f"  Mining Skill: Level {mining_skill}")
        print()

        # Display ore and stability status
        ore_percent = (remaining_ore / total_quantity) * 100
        stability_color = get_stability_color(stability)

        print(f"  Ore Remaining: {int(remaining_ore)}/{total_quantity} ({ore_percent:.1f}%)")
        print(f"  Asteroid Stability: {stability_color}{stability:.1f}%{RESET_COLOR}")
        print()

        # Stability bar
        stability_bar_width = 40
        stability_filled = int((stability / 100) * stability_bar_width)
        stability_empty = stability_bar_width - stability_filled
        stability_bar = f"[{stability_color}{'█' * stability_filled}{'░' * stability_empty}{RESET_COLOR}]"
        print(f"  {stability_bar}")
        print()

        print("=" * 60)
        print()
        print("  Select Mining Laser Intensity:")
        print()
        print("  [1] Minimum    - Safest, slowest      (+5% stability)")
        print("  [2] Low        - Safe, slow           (neutral)")
        print("  [3] Medium     - Balanced             (-5% stability)")
        print("  [4] High       - Fast, risky          (-10% stability)")
        print("  [5] Maximum    - Fastest, dangerous   (-20% stability)")
        print()
        print("  [ESC] Stop mining and leave")
        print()
        print("=" * 60)

        # Get player choice
        choice = None
        while choice not in ['1', '2', '3', '4', '5', 'esc']:
            key = get_key()
            if key in ['1', '2', '3', '4', '5']:
                choice = key
            elif key == 'esc':
                choice = 'esc'

        if choice == 'esc':
            break

        intensity = int(choice)

        # Calculate mining results based on intensity
        # Intensity affects: mining speed, stability loss, ore vaporization risk
        intensity_data = {
            1: {"speed": 0.5, "stability_loss": 0, "stability_gain": 5, "vaporize_chance": 0},
            2: {"speed": 1.0, "stability_loss": 0, "stability_gain": 0, "vaporize_chance": 0},
            3: {"speed": 1.8, "stability_loss": 5, "stability_gain": 0, "vaporize_chance": 0.02},
            4: {"speed": 2.8, "stability_loss": 10, "stability_gain": 0, "vaporize_chance": 0.05},
            5: {"speed": 4.0, "stability_loss": 20, "stability_gain": 0, "vaporize_chance": 0.10},
        }

        int_data = intensity_data[intensity]

        # Base ore extraction
        base_extraction = 2 + (intensity * 1.5)
        ore_extracted = base_extraction * int_data["speed"] * 0.1 * base_efficiency

        # Vaporization check
        vaporized = 0
        if random.random() < int_data["vaporize_chance"]:
            vaporize_percent = random.uniform(0.05, 0.15)
            vaporized = int(ore_extracted * vaporize_percent)
            ore_extracted -= vaporized

        ore_extracted = min(ore_extracted, remaining_ore)

        # Update stability
        stability_change = int_data["stability_gain"] - int_data["stability_loss"]

        # Mining skill reduces stability loss
        if stability_change < 0:
            stability_change *= (1.0 - mining_skill * 0.02)

        stability += stability_change
        stability = max(0, min(100, stability))

        # Display mining action
        clear_screen()
        title("MINING IN PROGRESS")
        print()
        set_color("cyan")
        print(f"  Firing mining laser at intensity {intensity}...")
        reset_color()
        print()
        sleep(0.5)

        # Random events check
        event_occurred = check_mining_event(data, ore_name, stability, security_level, intensity, anomaly_type=asteroid.get("anomaly_type", "AT"))

        if event_occurred:
            event_type, event_data = event_occurred

            if event_type == "gas_pocket":
                ore_lost = event_data["ore_lost"]
                stability_lost = event_data["stability_lost"]
                ship_damage = event_data["ship_damage"]

                remaining_ore -= ore_lost
                stability -= stability_lost

                set_color("yellow")
                print(f"  Gas Pocket Exposed!")
                reset_color()
                print(f"     Lost {ore_lost:.1f} units of ore")
                print(f"     Stability decreased by {stability_lost:.1f}%")

                if ship_damage > 0:
                    ship_destroyed = apply_damage_to_player(player_ship, ship_damage)
                    if ship_destroyed:
                        print()
                        set_color("red")
                        set_color("blinking")
                        print("     ⚠ CRITICAL: SHIP DESTROYED ⚠")
                        reset_color()
                        print()
                        input("Press Enter to continue...")
                        return "death"
                print()
                input("Press Enter to continue...")


            elif event_type == "dense_formation":
                bonus_ore = event_data["bonus_ore"]
                ore_extracted += bonus_ore

                set_color("green")
                print(f"  Dense Mineral Formation Uncovered!")
                reset_color()
                print(f"     Bonus: +{bonus_ore:.1f} units of {ore_name}")
                print()
                input("Press Enter to continue...")


            elif event_type == "collision":
                ore_lost = event_data["ore_lost"]
                recoverable = event_data["recoverable"]

                remaining_ore -= ore_lost

                set_color("yellow")
                print(f"  Asteroid Collision!")
                reset_color()
                print(f"     {ore_lost:.1f} units of ore broke off")
                print(f"     {recoverable:.1f} units are recoverable if you act fast!")
                print()
                print("  [A] Act fast to recover ore")
                print("  [Any other key] Continue mining")
                print()

                key = get_key()
                if key == 'a':
                    # Quick time event - player has to spam a key
                    print()
                    set_color("cyan")
                    print("  Quickly press SPACE to recover ore!")
                    reset_color()
                    print()

                    recovered = 0
                    start_time = time()
                    presses = 0

                    while time() - start_time < 3:
                        key = get_key()
                        if key == ' ':
                            presses += 1
                            print(f"  Press #{presses}")

                    recovery_rate = min(1.0, presses / 10)
                    recovered = recoverable * recovery_rate
                    ore_extracted += recovered

                    print()
                    print(f"  Recovered {recovered:.1f} units! ({recovery_rate * 100:.0f}%)")
                    print()
                    sleep(1.5)

            elif event_type == "artifact":
                artifact_destroyed = event_data["destroyed"]

                if artifact_destroyed:
                    set_color("red")
                    print(f"  Ancient Artifact Vaporized!")
                    reset_color()
                    print(f"     The high-intensity laser destroyed a valuable artifact!")
                    print()
                    input("Press Enter to continue...")
                else:
                    set_color("green")
                    print(f"  Ancient Artifact Uncovered!")
                    reset_color()
                    print(f"     Added to inventory: Ancient Artifact")
                    print(f"     This can be sold for a high price!")
                    print()

                    if "Ancient Artifact" not in data.get("inventory", {}):
                        data["inventory"]["Ancient Artifact"] = 0
                    data["inventory"]["Ancient Artifact"] += 1
                    input("Press Enter to continue...")


            elif event_type == "proximity_mine":
                mine_defused = event_data["defused"]
                mine_detonated = event_data["detonated"]

                if mine_detonated:
                    ship_damage = event_data["damage"]
                    ship_destroyed = apply_damage_to_player(player_ship, ship_damage)
                    remaining_ore = 0
                    stability = 0

                    set_color("red")
                    print(f"  MINE DETONATED!")
                    reset_color()
                    print(f"     Asteroid destroyed - all remaining ore lost")
                    print()

                    if ship_destroyed:
                        set_color("red")
                        set_color("blinking")
                        print("     ⚠ CRITICAL: SHIP DESTROYED ⚠")
                        reset_color()
                        print()
                        input("Press Enter to continue...")
                        return "death"

                    input("Press Enter to continue...")
                elif mine_defused:
                    set_color("green")
                    print(f"  Mine successfully defused!")
                    reset_color()
                    print()
                    input("Press Enter to continue...")
                else:
                    set_color("yellow")
                    print(f"  You decided to skip this asteroid to avoid the mine")
                    reset_color()
                    print()
                    sleep(1.5)
                    return "skipped"


        # Update ore amounts
        if vaporized > 0:
            set_color("yellow")
            print(f"  ⚠ {vaporized:.1f} units vaporized by high-intensity laser")
            reset_color()
            print()
            sleep(1)

        print(f"  Extracted: {ore_extracted:.1f} units of {ore_name}")
        print()

        remaining_ore -= ore_extracted
        remaining_ore = max(0, remaining_ore)
        units_collected += ore_extracted

        # XP calculation based on ore type
        ore_xp_values = {
            "Korrelite Ore (Inferior)": 1,
            "Korrelite Ore": 2,
            "Korrelite Ore (Superior)": 3,
            "Korrelite Ore (Pristine)": 5,
            "Reknite Ore (Inferior)": 2,
            "Reknite Ore": 3,
            "Reknite Ore (Superior)": 4,
            "Reknite Ore (Pristine)": 6,
            "Gellium Ore": 5,
            "Gellium Ore (Superior)": 7,
            "Gellium Ore (Pristine)": 10,
            "Axnit Ore": 8,
            "Axnit Ore (Pristine)": 15,
            "Narcor Ore": 12,
            "Red Narcor Ore": 20,
            "Vexnium Ore": 30,
            "Water Ice": 3,
        }

        xp_per_unit = ore_xp_values.get(ore_name, 2)
        xp_gain = int(ore_extracted * xp_per_unit)
        total_xp_gained += xp_gain

        sleep(1.5)

        # Check for catastrophic stability failure
        if stability <= 0:
            clear_screen()
            set_color("red")
            set_color("blinking")
            print()
            print("  " + "=" * 56)
            print("  ⚠ ⚠ ⚠  CRITICAL STABILITY FAILURE  ⚠ ⚠ ⚠")
            print("  " + "=" * 56)
            reset_color()
            print()
            sleep(1)

            set_color("red")
            print("  The asteroid is exploding!")
            reset_color()
            print()
            sleep(1)

            # Massive ship damage
            explosion_damage = int(player_ship["hull_hp"] * 0.6)
            ship_destroyed = apply_damage_to_player(player_ship, explosion_damage)

            print(f"  ⚠ All remaining ore vaporized")
            print()

            if ship_destroyed:
                set_color("red")
                set_color("blinking")
                print("  ⚠ CRITICAL: SHIP DESTROYED ⚠")
                reset_color()
                print()
                input("Press Enter to continue...")
                return "death"

            input("Press Enter to continue...")

            remaining_ore = 0
            break

    # Add collected ore to inventory
    ore_collected = int(units_collected - current_mined)
    if ore_collected > 0:
        if ore_name not in data.get("inventory", {}):
            data["inventory"][ore_name] = 0
        data["inventory"][ore_name] += ore_collected

    # Award mining XP
    if total_xp_gained > 0:
        old_level = mining_skill
        old_xp = data.get("skills", {}).get("mining_xp", 0)
        levels_gained = add_skill_xp(data, "mining", total_xp_gained)
        new_level = data["skills"]["mining"]
        new_xp = data["skills"]["mining_xp"]

        clear_screen()
        title("MINING COMPLETE")
        print()
        print(f"  Collected {ore_collected}x {ore_name}!")
        print()

        display_xp_gain("mining", total_xp_gained, levels_gained, new_level, new_xp)

        print()
        save_data(save_name, data)
        sleep(1)
        input("Press Enter to continue...")

    # Update asteroid state
    asteroid["mined"] = int(units_collected)

    if remaining_ore <= 0 or stability <= 0:
        return "completed"
    else:
        return "partial"


def get_stability_color(stability):
    """Get color code based on asteroid stability"""
    if stability >= 80:
        return "\033[32m"  # Green
    elif stability >= 60:
        return "\033[33m"  # Yellow
    elif stability >= 40:
        return "\033[38;5;208m"  # Orange
    elif stability >= 20:
        return "\033[31m"  # Red
    else:
        return "\033[1;31m"  # Bright red


def check_mining_event(data, ore_name, stability, security_level, intensity, anomaly_type="AT"):
    """Check for random mining events

    Returns:
        tuple: (event_type, event_data) or None if no event
    """
    # Base event chances (modified by various factors)
    event_chances = {
        "gas_pocket": 0.08,
        "dense_formation": 0.10,
        "collision": 0.06,
        "artifact": 0.03,
        "proximity_mine": 0.06,
    }

    # Modify chances based on ore type
    if ore_name in ["Gellium Ore", "Gellium Ore (Superior)", "Gellium Ore (Pristine)", "Red Narcor Ore"]:
        event_chances["gas_pocket"] *= 1.8

    if ore_name in ["Vexnium Ore", "Axnit Ore", "Axnit Ore (Pristine)",
                    "Korrelite Ore (Pristine)", "Reknite Ore (Pristine)"]:
        event_chances["dense_formation"] *= 1.6

    # Modify based on anomaly type
    if anomaly_type in ["AL", "CM"]:
        event_chances["collision"] *= 2.0
    elif anomaly_type in ["VX", "MT"]:
        event_chances["collision"] = 0

    # Modify based on security level
    if security_level == "Wild":
        event_chances["artifact"] *= 3.0
        event_chances["proximity_mine"] *= 2.5
    elif security_level == "Unsecure":
        event_chances["proximity_mine"] *= 1.5
    elif security_level in ["Contested"]:
        event_chances["proximity_mine"] *= 1.2
    elif security_level == "Secure":
        event_chances["proximity_mine"] = 0
        event_chances["artifact"] *= 0.25

    # Roll for each event
    for event_type, chance in event_chances.items():
        if random.random() < chance:
            return trigger_mining_event(event_type, data, ore_name, stability, intensity)

    return None


def trigger_mining_event(event_type, data, ore_name, stability, intensity):
    """Trigger a specific mining event

    Returns:
        tuple: (event_type, event_data)
    """
    if event_type == "gas_pocket":
        # Gas pocket - loses ore and stability
        # Worse if asteroid is already unstable
        base_ore_loss = random.uniform(2, 5)
        stability_factor = 1.0 + ((100 - stability) / 100)
        ore_lost = base_ore_loss * stability_factor

        base_stability_loss = random.uniform(5, 15)
        stability_lost = base_stability_loss * stability_factor

        # Ship damage if very unstable
        ship_damage = 0
        if stability < 40:
            ship_damage = random.randint(20, 50)

        return ("gas_pocket", {
            "ore_lost": ore_lost,
            "stability_lost": stability_lost,
            "ship_damage": ship_damage
        })

    elif event_type == "dense_formation":
        # Dense formation - extra ore
        base_bonus = random.uniform(3, 8)

        # Pristine ore gives more bonus
        if "Pristine" in ore_name:
            base_bonus *= 1.5

        return ("dense_formation", {
            "bonus_ore": base_bonus
        })

    elif event_type == "collision":
        # Asteroid collision
        ore_lost = random.uniform(4, 10)
        recoverable = ore_lost * random.uniform(0.5, 0.9)

        return ("collision", {
            "ore_lost": ore_lost,
            "recoverable": recoverable
        })

    elif event_type == "artifact":
        # Ancient artifact
        # High intensity can destroy it
        destroyed = intensity >= 4 and random.random() < 0.6

        return ("artifact", {
            "destroyed": destroyed
        })

    elif event_type == "proximity_mine":
        # Proximity mine
        clear_screen()
        set_color("red")
        set_color("blinking")
        print()
        print("  " + "=" * 56)
        print("  ⚠ ⚠ ⚠  PROXIMITY MINE DETECTED  ⚠ ⚠ ⚠")
        print("  " + "=" * 56)
        reset_color()
        print()
        sleep(1)

        print("  This asteroid has an explosive mine attached!")
        print()
        print("  What do you want to do?")
        print()
        print("  [D] Attempt to defuse the mine (risky)")
        print("  [S] Skip this asteroid entirely")
        print()

        choice = None
        while choice not in ['d', 's']:
            choice = get_key()

        if choice == 'd':
            # Defuse attempt
            mining_skill = data.get("skills", {}).get("mining", 0)
            success_chance = 0.5 + (mining_skill * 0.03)  # 50% base, +3% per level

            print()
            set_color("cyan")
            print("  Attempting to defuse...")
            reset_color()
            sleep(2)

            if random.random() < success_chance:
                return ("proximity_mine", {
                    "defused": True,
                    "detonated": False,
                    "damage": 0
                })
            else:
                # Detonation
                damage = random.randint(150, 300)
                return ("proximity_mine", {
                    "defused": False,
                    "detonated": True,
                    "damage": damage
                })
        else:
            # Skip asteroid
            return ("proximity_mine", {
                "defused": False,
                "detonated": False,
                "damage": 0
            })

    return None


def visit_refinery(save_name, data):
    """Visit the refinery to process ores and metal scraps into materials"""
    # Define refining rules
    refining_rules = {
        "Korrelite Ore (Inferior)": ("Korrelite", 1),
        "Korrelite Ore": ("Korrelite", 2),
        "Korrelite Ore (Superior)": ("Korrelite", 3),
        "Korrelite Ore (Pristine)": ("Korrelite", 4),
        "Reknite Ore (Inferior)": ("Reknite", 1),
        "Reknite Ore": ("Reknite", 2),
        "Reknite Ore (Superior)": ("Reknite", 3),
        "Reknite Ore (Pristine)": ("Reknite", 4),
        "Gellium Ore": ("Gellium", 2),
        "Gellium Ore (Superior)": ("Gellium", 3),
        "Gellium Ore (Pristine)": ("Gellium", 4),
        "Axnit Ore": ("Axnit", 1),
        "Axnit Ore (Pristine)": ("Axnit", 2),
        "Narcor Ore": ("Narcor", 1),
        "Red Narcor Ore": ("Red Narcor", 1),
        "Vexnium Ore": ("Vexnium", 1),
        "Water Ice": ("Water", 1),
    }

    while True:
        clear_screen()
        title("REFINERY")
        print()
        print("  Process ores and salvage into refined materials")
        print()
        print("=" * 60)
        print()

        # Get refinable items from inventory
        refinable_items = []
        inventory = data.get("inventory", {})

        for item_name, quantity in inventory.items():
            if quantity > 0:
                if item_name in refining_rules:
                    material, yield_amount = refining_rules[item_name]
                    refinable_items.append((item_name, quantity, material, yield_amount))
                elif item_name == "Metal Scraps":
                    refinable_items.append((item_name, quantity, "Random", "?"))

        if not refinable_items:
            print("  You don't have any items that can be refined.")
            print()
            input("Press Enter to continue...")
            return

        # Display refinable items
        options = []
        for item_name, quantity, material, yield_amount in refinable_items:
            if item_name == "Metal Scraps":
                options.append(f"{item_name} (x{quantity}) → Random material (20% chance)")
            else:
                options.append(f"{item_name} (x{quantity}) → {material} (x{yield_amount} per ore)")
        options.append("Back")

        choice = arrow_menu("Select item to refine:", options)

        if choice == len(refinable_items):
            return

        # Process refinement
        item_name, quantity, material, yield_amount = refinable_items[choice]

        clear_screen()
        title("REFINING")
        print()
        print(f"Item: {item_name}")
        print(f"Available: {quantity}")
        print()

        if item_name == "Metal Scraps":
            print("Metal Scraps have a 20% chance to refine into a random material.")
            print("Higher tier materials are rarer.")
            print()
            print("How many would you like to process? (0 to cancel): ", end="")
        else:
            print(f"Refines into: {material} (x{yield_amount} per ore)")
            print()
            print("How many would you like to refine? (0 to cancel): ", end="")

        try:
            amount = int(input())
            if amount <= 0:
                continue
            if amount > quantity:
                print()
                print("You don't have that many!")
                print()
                input("Press Enter to continue...")
                continue

            # Process the refinement
            data["inventory"][item_name] -= amount
            if data["inventory"][item_name] <= 0:
                del data["inventory"][item_name]

            if item_name == "Metal Scraps":
                # Metal scraps special processing
                successful_refines = 0
                materials_gained = {}

                # Material pool with weighted chances
                material_pool = [
                    ("Korrelite", 40),      # 40% of successes
                    ("Reknite", 30),        # 30% of successes
                    ("Gellium", 15),        # 15% of successes
                    ("Axnit", 10),          # 10% of successes
                    ("Narcor", 4),          # 4% of successes
                    ("Red Narcor", 1),      # 1% of successes
                ]

                for _ in range(amount):
                    if random.random() < 0.20:  # 20% success rate
                        successful_refines += 1
                        # Choose material based on weights
                        total_weight = sum(weight for _, weight in material_pool)
                        rand = random.randint(1, total_weight)
                        cumulative = 0
                        for mat, weight in material_pool:
                            cumulative += weight
                            if rand <= cumulative:
                                materials_gained[mat] = materials_gained.get(mat, 0) + 1
                                break

                print()
                print(f"Processed {amount} Metal Scraps")
                print(f"Successful refines: {successful_refines} ({int(successful_refines/amount*100)}%)")

                if materials_gained:
                    print()
                    print("Materials gained:")
                    for mat, qty in materials_gained.items():
                        if mat not in data["inventory"]:
                            data["inventory"][mat] = 0
                        data["inventory"][mat] += qty
                        print(f"  +{qty}x {mat}")
                else:
                    print("No materials recovered.")

            else:
                # Standard ore refinement
                total_yield = amount * yield_amount

                if material not in data["inventory"]:
                    data["inventory"][material] = 0
                data["inventory"][material] += total_yield

                print()
                print(f"Refined {amount}x {item_name}")
                print(f"Produced: {total_yield}x {material}")

            print()
            save_data(save_name, data)
            input("Press Enter to continue...")

        except ValueError:
            print()
            print("Invalid input!")
            print()
            input("Press Enter to continue...")


def game_loop(save_name, data):
    clear_screen()
    if data["v"] < VERSION_CODE:
        title("CONTINUE GAME")
        print()
        print("ERROR: Save file is of an older data format.")
        print("       No migration method has been programmed.")
        print("       This save file can therefore not be loaded.")
        print()
        input("Press Enter to return to main menu")
        return

    # Set initial presence based on whether player is docked
    if data.get("docked_at"):
        update_discord_presence(data=data, context="docked")
    else:
        update_discord_presence(data=data, context="traveling")

    while True:
        main_screen(save_name, data)


def main_screen(save_name, data):
    system_name = data["current_system"]
    system = system_data(system_name)
    system["Name"] = system_name
    system_security = system["SecurityLevel"]

    gate_mapping = {
        "Hualt": "G-01",
        "Vesma": "G-02",
        "Arpirom": "G-03",
        "Toracas": "G-04",
        "Lisaer": "G-05",
        "Arosiah": "G-06",
        "Io Zadkia": "G-07",
        "Droku": "G-08",
        "Delta Anca": "G-09"
    }

    if system_name in gate_mapping:
        gate_name = gate_mapping[system_name]
        # Show discovery message
        clear_screen()
        print()
        set_color("cyan")
        print(f"  ⚬ ANOMALOUS SIGNATURE DETECTED ⚬")
        print(f"  New system discovered: {gate_name}")
        reset_color()
        print()
        sleep(2)

    if data["docked_at"] != "":
        # get index of station docked at
        stations = system["Stations"]
        station_index = None
        i = 0
        for station in stations:
            if station["Name"] == data["docked_at"]:
                station_index = i
                break
            i += 1

        if station_index is not None:
            station_screen(system, station_index, save_name, data)
            return
        # else:
            # data is corrupted. Pretend the player was never docked and put
            # them outside the station

    # Update presence - player is in space/traveling
    update_discord_presence(data=data, context="traveling")

    # Capture the screen content before showing the menu
    content_buffer = StringIO()
    old_stdout = sys.stdout
    sys.stdout = content_buffer

    # Check if current system is a gate (starts with "G-")
    is_gate_system = system_name.startswith("G-")

    # Chance for enemy encounter (0 for gate systems)
    enemy_encounter_chance = 0.0
    if not is_gate_system:  # Only generate encounters in non-gate systems
        match system_security:
            case "Core":
                enemy_encounter_chance = 0.0
            case "Secure":
                enemy_encounter_chance = 1/8
            case "Contested":
                enemy_encounter_chance = 1/4
            case "Unsecure":
                enemy_encounter_chance = 1/2
            case "Wild":
                enemy_encounter_chance = 5/6

    rng = random.random()
    if rng <= enemy_encounter_chance:
        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Generate enemy fleet based on system security
        enemy_fleet = generate_enemy_fleet(system_security, data)

        # Enemy encounter
        result = enemy_encounter(enemy_fleet, system, save_name, data, previous_content)

        if result == "death":
            animated_death_screen(save_name, data)
            return
        elif result == "continue":
            # Combat was resolved, continue to main menu
            pass

    title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
    print(f"  {system["Region"]} > {system["Sector"]}")

    # Show destination info if set
    destination = data.get("destination", "")
    if destination:
        # Load all systems data for pathfinding
        with open(resource_path('system_data.json'), 'r') as f:
            all_systems_data = json.load(f)

        route = find_route_to_destination(system_name, destination, all_systems_data)

        if route and len(route) > 1:
            jumps = len(route) - 1
            dest_security = all_systems_data[destination].get("SecurityLevel", "Unknown")
            dest_color = get_security_color(dest_security)

            # Show destination and jump count
            print(f"  Destination: {dest_color}{destination}{RESET_COLOR} ({jumps} jump{'s' if jumps != 1 else ''})")

            # Show security dots for next 5 systems (excluding current)
            print(f"  Route: ", end="")
            next_systems = route[1:6]  # Get next 5 systems (excluding current)
            for next_sys in next_systems:
                next_security = all_systems_data[next_sys].get("SecurityLevel", "Unknown")
                next_color = get_security_color(next_security)
                print(f"{next_color}●{RESET_COLOR}", end="")
            print()  # newline
        elif route and len(route) == 1:
            # Already at destination
            print(f"  Destination: {get_security_color(all_systems_data[destination].get('SecurityLevel', 'Unknown'))}{destination}{RESET_COLOR} (Arrived!)")
        else:
            # No route found
            print(f"  Destination: {destination} (No route found)")

    title(f"CREDITS: ¢{data["credits"]}")

    if system_name == "Gatinsir":
        sys.stdout = old_stdout
        clear_screen()

        title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
        print(f"  {system["Region"]} > {system["Sector"]}")
        title(f"CREDITS: ¢{data["credits"]}")
        print()
        print("A fleet of pirates approaches! What will you do?")
        title("ACTIONS MENU")
        print()
        print("  > Fight")
        print("    Warp to another system")
        print("    Ignore the fleet")
        print()
        print("  Use ↑/↓ arrows to navigate, Enter to select")
        sleep(0.75)

        clear_screen()

        title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
        print(f"  {system["Region"]} > {system["Sector"]}")
        title(f"CREDITS: ¢{data["credits"]}")
        print()
        print("The fleet of pirates obliterated your ship! You died.")
        sleep(2)

        # Call the animated death screen
        animated_death_screen(save_name, data)
        return

    previous_content = content_buffer.getvalue()
    sys.stdout = old_stdout

    options = ["View status", "Warp to another system", "View inventory",
               "Dock at station", "Scan for anomalies", "Visit anomalies", "Map", "Save and quit"]
    choice = arrow_menu("Select action:", options, previous_content)

    match choice:
        case 0:
            view_status_screen(data)
        case 1:
            warp_menu(system, save_name, data)
        case 2:
            view_inventory(data)
        case 3:
            select_station_menu(system, save_name, data)
        case 4:
            scan_for_anomalies(save_name, data)
        case 5:
            visit_anomalies_menu(save_name, data)
        case 6:
            galaxy_map(save_name, data)
        case 7:
            clear_screen()
            title("SAVE & QUIT")
            print("Saving...")
            close_discord_rpc()
            save_data(save_name, data)
            print("Game saved.")
            input("Press Enter to exit...")
            sys.exit(0)


def view_status_screen(data):
    """Display player status including ship and skills"""
    clear_screen()
    title("STATUS")
    print()

    player_ship = get_active_ship(data)
    max_shield = get_max_shield(player_ship)
    max_hull = get_max_hull(player_ship)

    # Regenerate shields slightly when checking status (2% of max shields)
    shield_regen = int(max_shield * 0.02)
    if player_ship["shield_hp"] < max_shield:
        player_ship["shield_hp"] = min(player_ship["shield_hp"] + shield_regen, max_shield)

    print("PILOT INFORMATION:")
    print(f"  Name: {data['player_name']}")
    print(f"  Credits: ¢{data['credits']}")
    print()

    print("ACTIVE SHIP:")
    print(f"  Name: {player_ship.get('nickname', 'Unknown')}")
    print(f"  Type: {player_ship.get('name', 'Unknown').title()}")
    print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield}")
    shield_percent = int((player_ship['shield_hp'] / max_shield) * 100)
    print(f"  Shield: [{create_health_bar(player_ship['shield_hp'], max_shield, 30, 'cyan')}] {shield_percent}%")
    print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull}")
    hull_percent = int((player_ship['hull_hp'] / max_hull) * 100)
    print(f"  Hull:   [{create_health_bar(player_ship['hull_hp'], max_hull, 30, 'red')}] {hull_percent}%")
    print()

    print("SKILLS:")
    combat_level = data['skills']['combat']
    combat_xp = data['skills'].get('combat_xp', 0)
    combat_xp_needed = xp_required_for_level(combat_level)
    print(f"  Combat: Level {combat_level} ({combat_xp}/{combat_xp_needed} XP)")
    print(f"    - Increases damage dealt")
    print(f"    - Reduces damage taken")
    print(f"    - Current damage bonus: +{combat_level * 2}")
    print()

    piloting_level = data['skills']['piloting']
    piloting_xp = data['skills'].get('piloting_xp', 0)
    piloting_xp_needed = xp_required_for_level(piloting_level)
    print(f"  Piloting: Level {piloting_level} ({piloting_xp}/{piloting_xp_needed} XP)")
    print(f"    - Increases evasion chance in combat")
    print(f"    - Improves escape success rate")
    print(f"    - Current evasion chance: {min(piloting_level * 2, 25)}%")
    print()

    # Ship status warnings
    if player_ship['hull_hp'] < max_hull * 0.3:
        set_color("red")
        print("⚠ WARNING: Hull damage detected! Visit a repair bay soon.")
        reset_color()
        print()

    if player_ship['shield_hp'] < max_shield * 0.5:
        set_color("yellow")
        print("⚠ NOTICE: Shields need recharging.")
        reset_color()
        print()

    input("Press Enter to continue...")


def type_lines(lines):
    for line in lines:
        if line == "":
            print()
        else:
            for char in line:
                print(char, end='', flush=True)
                match char:
                    case ' ':
                        delay = 0.05
                    case '.':
                        delay = 0.15
                    case '?':
                        delay = 0.15
                    case '!':
                        delay = 0.15
                    case ',':
                        delay = 0.1
                    case ';':
                        delay = 0.125
                    case _:
                        delay = 0.025

                sleep(delay)
            print()
        sleep(0.15)

def warp_to_gate_system(gate_name, save_name, data):
    """Special warp sequence for entering gate systems with lore and ASCII art"""
    clear_screen()

    # Store the previous system before entering the gate
    previous_system = data["current_system"]
    data["previous_system"] = previous_system

    # Different lore for G-09 vs other gates
    if gate_name == "G-09":
        # G-09 specific lore - the destroyed gate
        lore_lines = [
            "Jumping to system...",
            "",
            "...",
            "",
            "You have arrived here. But where is here? Everything is pitch black.",
            "Your scanner struggles against unexplained interference.",
            "Static electricity fills the void, occasionally releasing as lightning,",
            "powerful enough for you to hear the thunder through empty space.",
            "",
            "In the distance, a faint neutron star pulses rhythmically.",
            "",
            "Then, you see it...",
            "What is that?",
            "It looks like some sort of dying planet. Totally cracked and coming apart.",
            "",
            "Then you look around and something else catches your eye.",
            "",
            "A battlefield, practically frozen in time.",
            "Fighter wrecks scattered in the debris.",
            "Three massive capital ships, their hulls bearing names:",
            "",
            "  - 'Blade of Perseus'",
            "  - 'Singularity'  ",
            "  - 'Blue Space'",
            "",
            "And at the center... a stargate, but this one is not like the others.",
            "It's completely destroyed. Torn into pieces.",
            "Its pieces floating around like a shattered monument to those who died here.",
            "",
            "...",
            "",
            "What happened here?",
            "",
            "It looks like there was some sort of space battle over the stargate.",
            "You've never seen ships of this design. Who were these people? ",
            "Who were they fighting? And why?",
            "",
            "You move your ship closer to the wreckage and get a peak inside",
            "one of the capital ships torn in half. You see alien bodies in",
            "some sort of armor, just floating lifeless in the exposed vacuum",
            "inside the ship, and the captain still sitting in his seat, helmet"
            "cracked.",
            "",
            "You take a good look at the gate...",
            "",
            "...",
            "",
        ]
    else:
        # Standard gate lore
        lore_lines = [
            "Jumping to system...",
            "",
            "...",
            "",
            "You have arrived here. But where is here? Everything is pitch black.",
            "Your scanner struggles against unexplained interference.",
            "The only thing here is a black nebula, slightly illuminated by a",
            "faint neutron star in the distance, pulsing rhythmically, casting",
            "a flickering light across the star system.",
            "",
            "You wander around for a while looking for something, anything.",
            "",
            "...",
            "",
            "What's that in the distance?",
            "As you approach, it reveals itself:",
            "",
            "An ancient stargate.",
            "Inactive, (as far as you know) just sitting there.",
            "",
            "What's its purpose? Who built it? You may never know.",
            "",
            "...",
        ]

    # Display lore with typing effect
    type_lines(lore_lines)
    print()
    sleep(3)
    input("Press Enter to continue...")

    # Update player location
    data["current_system"] = gate_name

    # Manage anomalies for the gate system
    manage_system_anomalies(save_name, data, gate_name)

    # Regenerate shields slightly when warping
    player_ship = get_active_ship(data)
    max_shield = get_max_shield(player_ship)
    shield_regen = int(max_shield * 0.03)
    if player_ship["shield_hp"] < max_shield:
        player_ship["shield_hp"] = min(player_ship["shield_hp"] + shield_regen, max_shield)

    save_data(save_name, data)

    # Loop ASCII art animation until Enter is pressed
    if gate_name == "G-09":
        # Animated ASCII art for G-09
        ascii_files = [f"g_09-{i}.txt" for i in range(1, 10)]

        # Use threading for non-blocking input check
        import threading
        stop_animation = threading.Event()

        def wait_for_enter():
            input()  # Wait for any key press
            stop_animation.set()

        # Start input thread
        input_thread = threading.Thread(target=wait_for_enter, daemon=True)
        input_thread.start()

        # Animation loop
        while not stop_animation.is_set():
            clear_screen()
            random_file = random.choice(ascii_files)
            try:
                with open(resource_path(f'ascii_art/{random_file}'), 'r', encoding='utf-8') as f:
                    art = f.read()
                print(art)
            except FileNotFoundError:
                print(f"[ASCII art file {random_file} not found]")

            print()
            print(f"Press Enter to return to {previous_system}")
            print()

            # Wait for frame duration or until stop signal
            stop_animation.wait(timeout=0.125)

        # Warp back to previous system
        data["current_system"] = previous_system

        # Manage anomalies for the previous system
        manage_system_anomalies(save_name, data, previous_system)

        save_data(save_name, data)
        return

    else:
        # Static ASCII art for other gates - loop until Enter
        clear_screen()
        try:
            with open(resource_path('ascii_art/gate.txt'), 'r', encoding='utf-8') as f:
                art = f.read()
            print(art)
        except FileNotFoundError:
            print("[Gate ASCII art not found]")
            print()
            print("     ═══════════════════════════")
            print("    ║                           ║")
            print("    ║     ANCIENT STARGATE      ║")
            print("    ║                           ║")
            print("     ═══════════════════════════")

        print()
        print(f"Press Enter to return to {previous_system}")

        # Wait for Enter key
        input()

        # Warp back to previous system
        data["current_system"] = previous_system

        # Manage anomalies for the previous system
        manage_system_anomalies(save_name, data, previous_system)

        save_data(save_name, data)
        return


def warp_menu(system, save_name, data):
    connected_systems = system["Connections"]

    # Gates have one-way connections pointing to regular systems
    # We need to search all systems to find which gates connect here
    with open(resource_path('system_data.json'), 'r') as f:
        all_systems_data = json.load(f)

    current_system_name = data["current_system"]

    # Find any hidden systems (gates) that connect to our current system
    for sys_name, sys_info in all_systems_data.items():
        if sys_info.get("hidden", False):  # This is a hidden gate
            # Check if this gate connects to our current system
            if current_system_name in sys_info.get("Connections", []):
                # Add this gate to our connection list if not already there
                if sys_name not in connected_systems:
                    connected_systems.append(sys_name)
    # === END FIX ===

    options = connected_systems + [f"{UNSECURE_COLOR}x{RESET_COLOR} Cancel"]

    # Load all systems data for route checking
    with open(resource_path('system_data.json'), 'r') as f:
        all_systems_data = json.load(f)

    # Check if we've reached destination and unset it
    current_system = data["current_system"]
    destination = data.get("destination", "")
    if destination and current_system == destination:
        data["destination"] = ""
        destination = ""
        save_data(save_name, data)

    # Find next system in route if destination is set
    next_in_route = None
    if destination:
        current_system = data["current_system"]
        route = find_route_to_destination(current_system, destination, all_systems_data)
        if route and len(route) > 1:
            next_in_route = route[1]  # Next system in route

    i = 0
    for sys_name in connected_systems:
        security_level = system_data(sys_name)["SecurityLevel"]

        # Determine security color
        match security_level:
            case "Core":
                color = CORE_COLOR
            case "Secure":
                color = SECURE_COLOR
            case "Contested":
                color = CONTESTED_COLOR
            case "Unsecure":
                color = UNSECURE_COLOR
            case "Wild":
                color = WILD_COLOR
            case _:
                color = RESET_COLOR

        # If this is the next system in route, use yellow, bold, italicized text; otherwise use color of security status
        if sys_name == next_in_route:
            options[i] = f"{color}⬤ \033[33m\033[1m\033[3m{sys_name}{RESET_COLOR}"
        else:
            options[i] = f"{color}⬤ {sys_name}{RESET_COLOR}"
        i += 1

    clear_screen()
    title("WARP MENU")
    choice = arrow_menu("Select system to warp to", options)

    # If Cancel was selected
    if choice == len(connected_systems):
        return

    # Check if warping to a gate system - use special sequence
    target_system = connected_systems[choice]
    if target_system.startswith("G-"):
        warp_to_gate_system(target_system, save_name, data)
        return

    total_padding1 = 80 - len(connected_systems[choice]) - 14
    spacingL1 = " " * math.ceil(total_padding1 / 2)
    spacingR1 = " " * math.floor(total_padding1 / 2)

    clear_screen()
    set_color("white")
    set_background_color("blue")
    print(
r"                                                                 X              " + "\n" +
r" $   &&&   &; ;   :  $  &  $   ;   x& +        : ::  X&  $   &&&& ;     +& xX   " + "\n" +
r"  :$    ;&x  :$          $X         X .       &  .  $$ +:  ;x&X       &&Xx    &x" + "\n" +
r" &&&:x ;   x$$  +;         &   x   .         &     &. x    $X     +&&+    &&&&& " + "\n" +
r"     .&&X::    +&  +:       x;  &    :      .     & ;    &     +&     &&&&+     " + "\n" +
r"          $&::;               &  .     .    +   :;     ;    +$    &&&&    +   +." + "\n" +
r"   &+          && +   :        X       ;       X         $    .;&+      .&x& ;& " + "\n" +
r"X&                ;;&;  +&       ;     +       .      .    &&.    +&&&&&& ;     " + "\n" +
r" :&&&&&&$&&            &.+ &&x                     $:  x.    &&&&+$;            " + "\n" +
r"          &:;&&+&$            .&&              X$+  ; ;:;& $        :.+&&&&&&&& " + "\n" +
r"                                  &;       ;:&               :&&&               " + "\n" +
r"                                                 +&&&&:          :$&&&&&&&&&&&& " + "\n" +
        f"{spacingL1}Warping to {connected_systems[choice]}...{spacingR1}"          + "\n" +
r"  +&&&x;.X&&&&+&$:.      &.       ;.        :;     ;&                           " + "\n" +
r"+X  ;+:        x&  &           :&              X$    ;+  $X &&        ;:        " + "\n" +
r"  X;  XX:&&&      .:+X     :&&:                   ;:: .  & x     &&.$X       ;& " + "\n" +
r"&& ; x$     ::&& . ;    :&&X  &                         ;.    &&      &X+&&& .  " + "\n" +
r"      &+&&:  $&  X + +&&X  &&  +             &;   + X ;     &;  ;& +&.    & X&& " + "\n" +
r" $&&&   :&:+.; x  ;X&&   &:  &&       ..      +;    + $  &      $.  : &  &&     " + "\n" +
r"   ;&&& $  $;  &:&&;   &   &&   ;.  $ ::    :  $&    ;; x; ;&       &:x  X :+X&$" + "\n" +
r" $X +  :X$ $&+ &&   +&:   &X   + : $  .: ;  .   +&  ;  X  + .XXX       +&$+     " + "\n" +
r" :  && :&&   &&   &&    &&    & &  X  $  $   $   X&  X   $  X  $x$  .      &&&: " + "\n" +
r" & ; &&   &&    &&    &&&    X &    X $  ::  x.  & &  +  $ X  &  &&$$  &Xx&   ::" + "\n" +
 "   :    &     x      &                            : X               +        &  \033[0m")

    ships_data = load_ships_data()
    current_ship = get_active_ship(data)
    ship_stats = ships_data[current_ship["name"].lower()]
    warp_speed = ship_stats["stats"]["Warp Speed"]
    sleep_time = 5 / warp_speed
    sleep(sleep_time)

    data["current_system"] = connected_systems[choice]

    # Manage anomalies for the new system
    manage_system_anomalies(save_name, data, data["current_system"])

    # Regenerate shields slightly when warping (3% of max shields)
    player_ship = get_active_ship(data)
    max_shield = get_max_shield(player_ship)
    shield_regen = int(max_shield * 0.03)
    if player_ship["shield_hp"] < max_shield:
        player_ship["shield_hp"] = min(player_ship["shield_hp"] + shield_regen, max_shield)

    save_data(save_name, data)
    new_system = system_data(data["current_system"])
    system_color = ""
    match new_system["SecurityLevel"]:
        case "Core":
            system_color = CORE_COLOR
        case "Secure":
            system_color = SECURE_COLOR
        case "Contested":
            system_color = CONTESTED_COLOR
        case "Unsecure":
            system_color = UNSECURE_COLOR
        case "Wild":
            system_color = WILD_COLOR

    clear_screen()

    total_padding2 = 58 - len(connected_systems[choice])
    spacingL2 = " " * math.ceil(total_padding2 / 2)
    spacingR2 = " " * math.floor(total_padding2 / 2)

    print("—" * 60)
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print(f"|{spacingL2}{system_color}{connected_systems[choice]}{RESET_COLOR}{spacingR2}|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("—" * 60)
    sleep(2)


def select_station_menu(system, save_name, data):
    options = []
    stations = system.get("Stations", [])

    for station in stations:
        options.append(station.get("Name"))

    options.append("Cancel")

    clear_screen()
    title("SELECT STATION")
    choice = arrow_menu("Select station to dock with", options)

    # If Cancel was selected
    if choice == len(stations):
        return

    data["docked_at"] = stations[choice]["Name"]

    # Automatically recharge shields to full when docking
    player_ship = get_active_ship(data)
    player_ship["shield_hp"] = get_max_shield(player_ship)

    save_data(save_name, data)
    # Update presence to docked
    update_discord_presence(data=data, context="docked")
    station_screen(system, choice, save_name, data)


def station_screen(system, station_num, save_name, data):
    # Update Discord presence for station menu
    update_discord_presence(data=data, context="docked")

    # Check if system has any stations
    if "Stations" not in system or not system["Stations"]:
        clear_screen()
        title("NO STATION")
        print()
        print("This system does not have any orbital stations.")
        print("You cannot dock here.")
        input("Press Enter to continue...")
        return

    # Regenerate shields slightly when accessing station facilities (2% of max shields)
    player_ship = get_active_ship(data)
    max_shield = get_max_shield(player_ship)
    shield_regen = int(max_shield * 0.02)
    if player_ship["shield_hp"] < max_shield:
        player_ship["shield_hp"] = min(player_ship["shield_hp"] + shield_regen, max_shield)

    while True:
        clear_screen()

        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        # Get station data
        station = system["Stations"][station_num]
        station_name = station.get("Name", f"{system.get('Name', 'Unknown Station')}")
        facilities = station.get("Facilities", [])

        title(f"DOCKED AT: {station_name}")

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Build options list based on available facilities
        options = []
        option_actions = []  # Track what each option does

        # Always show global storage option
        options.append("Access Global Storage")
        option_actions.append("global_storage")

        # Facility-based options
        facility_mapping = {
            "Manufacturing": ("Visit Manufacturing", "manufacturing"),
            "Refinery": ("Visit Refinery", "refinery"),
            "Ship Vendor": ("Visit Ship Vendor", "ship_vendor"),
            "General Marketplace": ("Visit General Marketplace", "marketplace"),
            "Observatory": ("Visit Observatory", "observatory"),
            "Repair Bay": ("Repair Ship", "repair"),
        }

        # Check each facility type
        for facility in facilities:
            # Handle mission agencies (they have tier info)
            if "Mission Agency" in facility:
                if "Visit Mission Agent" not in options:
                    options.append("Visit Mission Agent")
                    option_actions.append("mission_agent")
            else:
                # Check standard facilities
                for facility_key, (option_text, action) in facility_mapping.items():
                    if facility_key in facility and option_text not in options:
                        options.append(option_text)
                        option_actions.append(action)

        # Always show switch ships option
        options.append("Switch Ships")
        option_actions.append("switch_ships")

        # Always add undock option
        options.append("Return to Ship & Undock")
        option_actions.append("undock")

        # Always add save & quit option
        options.append("Save & Quit")
        option_actions.append("quit")

        choice = arrow_menu("Select facility:", options, previous_content)

        # Handle the selected option
        action = option_actions[choice]

        if action == "observatory":
            visit_observatory()
            continue

        if action == "repair":
            visit_repair_bay(save_name, data)
            continue

        if action == "marketplace":
            visit_marketplace(save_name, data)
            continue

        if action == "global_storage":
            access_global_storage(save_name, data)
            continue

        if action == "ship_vendor":
            visit_ship_vendor(save_name, data)
            continue

        if action == "refinery":
            visit_refinery(save_name, data)
            continue

        if action == "switch_ships":
            switch_ships_menu(save_name, data)
            continue

        if action == "undock":
            data["docked_at"] = ""
            save_data(save_name, data)
            # Update presence to traveling after undocking
            update_discord_presence(data=data, context="traveling")
            return

        if action == "quit":
            clear_screen()
            title("SAVE & QUIT")
            print("Saving...")
            save_data(save_name, data)
            close_discord_rpc()
            print("Game saved.")
            input("Press Enter to exit...")
            sys.exit(0)

        # All other options - not implemented yet
        clear_screen()
        title(options[choice].upper().replace("VISIT ", ""))
        print()
        print("Not implemented yet")
        input("Press Enter to continue...")


def visit_repair_bay(save_name, data):
    """Repair ship hull and shields"""
    clear_screen()
    title("REPAIR BAY")
    print()

    player_ship = get_active_ship(data)
    max_hull = get_max_hull(player_ship)

    hull_damage = max_hull - player_ship["hull_hp"]

    print(f"Ship: {player_ship.get('nickname', 'Unknown')}")
    print()
    print(f"Hull HP:   {player_ship['hull_hp']}/{max_hull}")
    print()

    if hull_damage == 0:
        print("Your ship is already in perfect condition!")
        print()
        input("Press Enter to continue...")
        return

    # Perform free repair
    player_ship["hull_hp"] = max_hull

    print("Hull fully repaired!")
    print()

    save_data(save_name, data)
    input("Press Enter to continue...")


def visit_marketplace(save_name, data):
    """Visit the General Marketplace to buy and sell items"""
    items_data = load_items_data()

    while True:
        clear_screen()
        title("GENERAL MARKETPLACE")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)

        # Show tabs
        options = ["Buy Items", "Sell Items", "Cancel"]
        choice = arrow_menu("Select:", options)

        if choice == 0:
            # Buy tab
            marketplace_buy(save_name, data, items_data)
        elif choice == 1:
            # Sell tab
            marketplace_sell(save_name, data, items_data)
        elif choice == 2:
            # Back
            return


def marketplace_buy(save_name, data, items_data):
    """Buy items from marketplace"""
    while True:
        clear_screen()
        title("MARKETPLACE - BUY")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)
        print()

        # Get all buyable items (items with buy_price specified)
        buyable_items = []
        for item_name, item_info in items_data.items():
            if item_info.get('buy_price') and item_info['buy_price'] != "":
                buyable_items.append((item_name, item_info))

        # Sort by price
        buyable_items.sort(key=lambda x: int(x[1]['buy_price']))

        if not buyable_items:
            print("No items available for purchase.")
            print()
            input("Press Enter to continue...")
            return

        # Display items
        options = []
        for item_name, item_info in buyable_items:
            price = item_info['buy_price']
            item_type = item_info.get('type', 'Unknown')
            # Get current inventory count
            inv_count = data.get('inventory', {}).get(item_name, 0)
            options.append(f"{item_name} - {price} CR ({item_type}) [Own: {inv_count}]")

        options.append("Back")

        # Capture current screen for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print(f"MARKETPLACE - BUY")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Select item to buy:", options, previous_content)

        if choice == len(options) - 1:
            # Back
            return

        # Show item details and purchase confirmation
        item_name, item_info = buyable_items[choice]
        price = int(item_info['buy_price'])

        clear_screen()
        title("PURCHASE ITEM")
        print()
        print(f"Item: {item_name}")
        print(f"Type: {item_info.get('type', 'Unknown')}")
        print(f"Description: {item_info.get('description', 'No description available.')}")
        print()
        print(f"Price: {price} CR")
        print(f"Your Credits: {data['credits']} CR")
        print()

        if data['credits'] < price:
            print("You don't have enough credits!")
            print()
            input("Press Enter to continue...")
            continue

        # Ask how many to buy
        print("Enter quantity to purchase (0 to cancel): ", end="")
        try:
            quantity = int(input())
            if quantity <= 0:
                continue

            total_cost = price * quantity
            if data['credits'] < total_cost:
                print()
                print("You don't have enough credits for that quantity!")
                print()
                input("Press Enter to continue...")
                continue

            # Process purchase
            data['credits'] -= total_cost
            if item_name not in data['inventory']:
                data['inventory'][item_name] = 0
            data['inventory'][item_name] += quantity

            save_data(save_name, data)

            print()
            print(f"Purchased {quantity}x {item_name} for {total_cost} CR")
            print()
            input("Press Enter to continue...")

        except ValueError:
            print()
            print("Invalid input!")
            print()
            input("Press Enter to continue...")


def marketplace_sell(save_name, data, items_data):
    """Sell items to marketplace"""
    while True:
        clear_screen()
        title("MARKETPLACE - SELL")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)
        print()

        # Ask whether to sell from inventory or storage
        options = [
            "Sell from Inventory",
            "Sell from Storage",
            "Back"
        ]

        # Capture current screen for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print(f"MARKETPLACE - SELL")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Sell from:", options, previous_content)

        if choice == 2:
            # Back
            return

        # Determine source (inventory or storage)
        source_name = "inventory" if choice == 0 else "storage"
        source = data.get(source_name, {})

        if not source:
            clear_screen()
            title("MARKETPLACE - SELL")
            print()
            print(f"Your {source_name} is empty.")
            print()
            input("Press Enter to continue...")
            continue

        # Get all sellable items from the chosen source
        sellable_items = []
        for item_name, quantity in source.items():
            if quantity > 0:
                item_info = items_data.get(item_name, {})
                if item_info.get('sell_price') and item_info['sell_price'] != "":
                    sellable_items.append((item_name, item_info, quantity))

        if not sellable_items:
            clear_screen()
            title("MARKETPLACE - SELL")
            print()
            print(f"No sellable items in your {source_name}.")
            print()
            input("Press Enter to continue...")
            continue

        # Sort by sell price (descending)
        sellable_items.sort(key=lambda x: int(x[1]['sell_price']), reverse=True)

        # Display items
        while True:
            clear_screen()
            title(f"MARKETPLACE - SELL FROM {source_name.upper()}")
            print()
            print(f"Credits: {data['credits']}")
            print()
            print("=" * 60)
            print()

            options = []
            for item_name, item_info, quantity in sellable_items:
                price = item_info['sell_price']
                item_type = item_info.get('type', 'Unknown')
                options.append(f"{item_name} - {price} CR ({item_type}) [Have: {quantity}]")

            options.append("Back")

            # Capture current screen for display
            content_buffer = StringIO()
            old_stdout = sys.stdout
            sys.stdout = content_buffer

            print(f"MARKETPLACE - SELL FROM {source_name.upper()}")
            print()
            print(f"Credits: {data['credits']}")
            print()
            print("=" * 60)

            previous_content = content_buffer.getvalue()
            sys.stdout = old_stdout

            item_choice = arrow_menu("Select item to sell:", options, previous_content)

            if item_choice == len(options) - 1:
                # Back
                break

            # Show item details and sale confirmation
            item_name, item_info, available_quantity = sellable_items[item_choice]
            price = int(item_info['sell_price'])

            clear_screen()
            title("SELL ITEM")
            print()
            print(f"Item: {item_name}")
            print(f"Type: {item_info.get('type', 'Unknown')}")
            print(f"Description: {item_info.get('description', 'No description available.')}")
            print()
            print(f"Sell Price: {price} CR (each)")
            print(f"Available: {available_quantity}")
            print(f"Your Credits: {data['credits']} CR")
            print()

            # Ask how many to sell
            print(f"Enter quantity to sell (0 to cancel, max {available_quantity}): ", end="")
            try:
                quantity = int(input())
                if quantity <= 0:
                    continue

                if quantity > available_quantity:
                    print()
                    print("You don't have that many!")
                    print()
                    input("Press Enter to continue...")
                    continue

                # Process sale
                total_value = price * quantity
                data['credits'] += total_value
                data[source_name][item_name] -= quantity

                # Remove item from source if quantity reaches 0
                if data[source_name][item_name] <= 0:
                    del data[source_name][item_name]
                    # Update sellable_items list to reflect the removal
                    sellable_items = [(name, info, qty) for name, info, qty in sellable_items if name != item_name]
                else:
                    # Update the quantity in sellable_items
                    for i, (name, info, qty) in enumerate(sellable_items):
                        if name == item_name:
                            sellable_items[i] = (name, info, qty - quantity)
                            break

                save_data(save_name, data)

                print()
                print(f"Sold {quantity}x {item_name} for {total_value} CR")
                print()
                input("Press Enter to continue...")

                # If no more sellable items, break out
                if not sellable_items:
                    clear_screen()
                    title("MARKETPLACE - SELL")
                    print()
                    print(f"No more sellable items in your {source_name}.")
                    print()
                    input("Press Enter to continue...")
                    break

            except ValueError:
                print()
                print("Invalid input!")
                print()
                input("Press Enter to continue...")


def view_inventory(data):
    """View current inventory"""
    clear_screen()
    title("INVENTORY")
    print()

    inventory = data.get('inventory', {})

    if not inventory:
        print("Your inventory is empty.")
    else:
        print("Current Inventory:")
        print("=" * 60)

        # Load items data to show descriptions
        items_data = load_items_data()

        # Sort items by name
        sorted_items = sorted(inventory.items())

        for item_name, quantity in sorted_items:
            item_info = items_data.get(item_name, {})
            item_type = item_info.get('type', 'Unknown')
            print(f"  {item_name} x{quantity} ({item_type})")
            if item_info.get('description'):
                print(f"    {item_info['description']}")

    print()
    input("Press Enter to continue...")


def access_global_storage(save_name, data):
    """Access global storage to view and transfer items"""
    while True:
        clear_screen()
        title("GLOBAL STORAGE")
        print()

        inventory = data.get('inventory', {})
        storage = data.get('storage', {})

        print("=" * 60)
        print("INVENTORY:")
        if not inventory:
            print("  Empty")
        else:
            for item_name, quantity in sorted(inventory.items()):
                print(f"  {item_name} x{quantity}")

        print()
        print("STORAGE:")
        if not storage:
            print("  Empty")
        else:
            for item_name, quantity in sorted(storage.items()):
                print(f"  {item_name} x{quantity}")

        print("=" * 60)

        options = [
            "Move Items: Inventory → Storage",
            "Move Items: Storage → Inventory",
            "View Item Details",
            "Back"
        ]

        # Capture current screen
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print("GLOBAL STORAGE")
        print()
        print("=" * 60)
        print("INVENTORY:")
        if not inventory:
            print("  Empty")
        else:
            for item_name, quantity in sorted(inventory.items()):
                print(f"  {item_name} x{quantity}")

        print()
        print("STORAGE:")
        if not storage:
            print("  Empty")
        else:
            for item_name, quantity in sorted(storage.items()):
                print(f"  {item_name} x{quantity}")

        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Select action:", options, previous_content)

        if choice == 0:
            # Move from inventory to storage
            transfer_items(save_name, data, "inventory", "storage")
        elif choice == 1:
            # Move from storage to inventory
            transfer_items(save_name, data, "storage", "inventory")
        elif choice == 2:
            # View item details
            view_item_details(data)
        elif choice == 3:
            # Back
            return


def transfer_items(save_name, data, source_key, dest_key):
    """Transfer items between inventory and storage"""
    source = data.get(source_key, {})

    if not source:
        clear_screen()
        title("TRANSFER ITEMS")
        print()
        print(f"Your {source_key} is empty!")
        print()
        input("Press Enter to continue...")
        return

    while True:
        clear_screen()
        title(f"TRANSFER: {source_key.upper()} → {dest_key.upper()}")
        print()

        # Display source items
        print(f"{source_key.upper()}:")
        print("=" * 60)

        sorted_items = sorted(source.items())

        for i, (item_name, quantity) in enumerate(sorted_items):
            print(f"  [{i+1}] {item_name} x{quantity}")

        print()
        print("=" * 60)

        options = [f"{item_name} (x{quantity})" for item_name, quantity in sorted_items]
        options.append("Back")

        # Capture current screen
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print(f"TRANSFER: {source_key.upper()} → {dest_key.upper()}")
        print()
        print(f"{source_key.upper()}:")
        print("=" * 60)
        for i, (item_name, quantity) in enumerate(sorted_items):
            print(f"  [{i+1}] {item_name} x{quantity}")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Select item to transfer:", options, previous_content)

        if choice == len(options) - 1:
            # Back
            return

        # Get selected item
        item_name, available_quantity = sorted_items[choice]

        # Ask for quantity
        clear_screen()
        title("TRANSFER QUANTITY")
        print()
        print(f"Item: {item_name}")
        print(f"Available: {available_quantity}")
        print()
        print("Enter quantity to transfer (0 to cancel): ", end="")

        try:
            quantity = int(input())

            if quantity <= 0:
                continue

            if quantity > available_quantity:
                print()
                print("You don't have that many!")
                print()
                input("Press Enter to continue...")
                continue

            # Perform transfer
            source[item_name] -= quantity
            if source[item_name] <= 0:
                del source[item_name]

            dest = data.get(dest_key, {})
            if item_name not in dest:
                dest[item_name] = 0
            dest[item_name] += quantity
            data[dest_key] = dest

            save_data(save_name, data)

            print()
            print(f"Transferred {quantity}x {item_name} to {dest_key}")
            print()
            input("Press Enter to continue...")

        except ValueError:
            print()
            print("Invalid input!")
            print()
            input("Press Enter to continue...")


def view_item_details(data):
    """View detailed information about items in inventory or storage"""
    # Combine inventory and storage for viewing
    all_items = {}

    for item_name, quantity in data.get('inventory', {}).items():
        all_items[item_name] = all_items.get(item_name, 0) + quantity

    for item_name, quantity in data.get('storage', {}).items():
        all_items[item_name] = all_items.get(item_name, 0) + quantity

    if not all_items:
        clear_screen()
        title("ITEM DETAILS")
        print()
        print("No items to display.")
        print()
        input("Press Enter to continue...")
        return

    while True:
        clear_screen()
        title("ITEM DETAILS")
        print()

        sorted_items = sorted(all_items.items())

        options = [f"{item_name} (Total: {quantity})" for item_name, quantity in sorted_items]
        options.append("Back")

        choice = arrow_menu("Select item to view details:", options)

        if choice == len(options) - 1:
            # Back
            return

        # Show item details
        item_name = sorted_items[choice][0]
        items_data = load_items_data()
        item_info = items_data.get(item_name, {})

        clear_screen()
        title("ITEM INFORMATION")
        print()
        print(f"Name: {item_name}")
        print(f"Type: {item_info.get('type', 'Unknown')}")
        print(f"Description: {item_info.get('description', 'No description available.')}")
        print()

        inv_qty = data.get('inventory', {}).get(item_name, 0)
        stor_qty = data.get('storage', {}).get(item_name, 0)

        print(f"In Inventory: {inv_qty}")
        print(f"In Storage: {stor_qty}")
        print(f"Total: {inv_qty + stor_qty}")
        print()

        if item_info.get('sell_price') and item_info['sell_price'] != "":
            print(f"Sell Price: {item_info['sell_price']} CR")
        if item_info.get('buy_price') and item_info['buy_price'] != "":
            print(f"Buy Price: {item_info['buy_price']} CR")

        print()
        input("Press Enter to continue...")


def visit_ship_vendor(save_name, data):
    """Visit ship vendor to buy ships"""
    ships_data = load_ships_data()

    while True:
        clear_screen()
        title("SHIP VENDOR")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)

        # Get all purchasable ships (ships with buy_price specified)
        purchasable_ships = []
        for ship_name_lower, ship_info in ships_data.items():
            if ship_info.get('buy_price') and ship_info['buy_price'] != "":
                purchasable_ships.append((ship_name_lower, ship_info))

        # Sort by price
        purchasable_ships.sort(key=lambda x: int(x[1]['buy_price']))

        if not purchasable_ships:
            print("No ships available for purchase.")
            print()
            input("Press Enter to continue...")
            return

        # Display ships
        print("Available Ships:")
        print()

        for ship_name_lower, ship_info in purchasable_ships:
            price = ship_info['buy_price']
            ship_class = ship_info.get('class', 'Unknown')
            ship_name = ship_info['name']

            print(f"  {ship_name} ({ship_class}) - {price} CR")
            print(f"    {ship_info.get('description', '')}")

            stats = ship_info.get('stats', {})
            print(f"    Stats: DPS {stats.get('DPS', '?')} | Shield {stats.get('Shield', '?')} | Hull {stats.get('Hull', '?')}")
            print(f"           Speed {stats.get('Speed', '?')} | Warp {stats.get('Warp Speed', '?')}")
            print()

        print("=" * 60)

        options = [f"{ship_info['name']} - {ship_info['buy_price']} CR" for _, ship_info in purchasable_ships]
        options.append("Back")

        # Capture current screen
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print("SHIP VENDOR")
        print()
        print(f"Credits: {data['credits']}")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Select ship to purchase:", options, previous_content)

        if choice == len(options) - 1:
            # Back
            return

        # Show ship purchase confirmation
        ship_name_lower, ship_info = purchasable_ships[choice]
        price = int(ship_info['buy_price'])
        ship_name = ship_info['name']

        clear_screen()
        title("PURCHASE SHIP")
        print()
        print(f"Ship: {ship_name}")
        print(f"Class: {ship_info.get('class', 'Unknown')}")
        print(f"Description: {ship_info.get('description', 'No description available.')}")
        print()

        stats = ship_info.get('stats', {})
        print("Stats:")
        print(f"  DPS: {stats.get('DPS', 'N/A')}")
        print(f"  Shield: {stats.get('Shield', '?')}")
        print(f"  Hull: {stats.get('Hull', '?')}")
        print(f"  Energy: {stats.get('Energy', '?')}")
        print(f"  Speed: {stats.get('Speed', '?')}")
        print(f"  Warp Speed: {stats.get('Warp Speed', '?')}")
        print()
        print(f"Price: {price} CR")
        print(f"Your Credits: {data['credits']} CR")
        print()

        if data['credits'] < price:
            print("You don't have enough credits!")
            print()
            input("Press Enter to continue...")
            continue

        # Ask for ship nickname
        print("Enter a nickname for this ship (press Enter for default): ", end="")
        nickname = input().strip()
        if not nickname:
            nickname = ship_name

        # Process purchase
        data['credits'] -= price

        # Create new ship entry
        new_ship = {
            "id": str(uuid4()),
            "name": ship_name_lower,
            "nickname": nickname,
            "hull_hp": stats.get('Hull', 200),
            "shield_hp": stats.get('Shield', 200),
            "modules_installed": [],
        }

        data['ships'].append(new_ship)

        save_data(save_name, data)

        print()
        print(f"Purchased {ship_name} '{nickname}' for {price} CR")
        print("Your new ship is now available. Use 'Switch Ships' to select it.")
        print()
        input("Press Enter to continue...")


def switch_ships_menu(save_name, data):
    """Display a menu to switch current ship"""
    ships_data = load_ships_data()

    while True:
        clear_screen()
        title("SWITCH SHIPS")
        print()

        # Show all owned ships
        if not data["ships"]:
            print("  No ships available!")
            input("\n  Press Enter to continue...")
            return

        # Build menu options
        options = []
        for i, ship in enumerate(data["ships"]):
            ship_name = ship["name"]
            nickname = ship.get("nickname", ship_name.title())

            # Get ship stats from ships.json
            stats = get_ship_stats(ship_name)

            # Get current/max HP
            max_hull = stats.get("Hull", 200)
            max_shield = stats.get("Shield", 200)
            current_hull = ship.get("hull_hp", max_hull)
            current_shield = ship.get("shield_hp", max_shield)

            # Mark active ship
            active_marker = " [ACTIVE]" if i == data["active_ship"] else ""

            # Format option
            option = f"{nickname} ({ship_name.title()}){active_marker}"
            options.append(option)

        options.append("Back")

        # Display ship details before menu
        print("  Your Ships:")
        print("  " + "=" * 58)
        for i, ship in enumerate(data["ships"]):
            ship_name = ship["name"]
            nickname = ship.get("nickname", ship_name.title())
            stats = get_ship_stats(ship_name)

            max_hull = stats.get("Hull", 200)
            max_shield = stats.get("Shield", 200)
            current_hull = ship.get("hull_hp", max_hull)
            current_shield = ship.get("shield_hp", max_shield)

            active_marker = " ★" if i == data["active_ship"] else "  "

            print(f"{active_marker} {i+1}. {nickname} ({ship_name.title()})")
            print(f"     Hull: {current_hull}/{max_hull}  Shield: {current_shield}/{max_shield}")

            # Show key stats
            dps = stats.get("DPS", "N/A")
            speed = stats.get("Speed", "N/A")
            warp = stats.get("Warp Speed", "N/A")

            print(f"     DPS: {dps}  Speed: {speed}  Warp: {warp}")
            print()

        print("  " + "=" * 58)
        print()

        # Get user choice
        choice = arrow_menu("Select ship to make active", options)

        if choice == len(options) - 1:  # Back option
            return

        # Switch to selected ship
        if choice != data["active_ship"]:
            old_ship = data["ships"][data["active_ship"]]
            new_ship = data["ships"][choice]

            data["active_ship"] = choice
            save_data(save_name, data)

            clear_screen()
            title("SHIP SWITCHED")
            print()
            print(f"  Switched from {old_ship.get('nickname', old_ship['name'].title())} to {new_ship.get('nickname', new_ship['name'].title())}")
            print()
            input("  Press Enter to continue...")
        else:
            clear_screen()
            title("SHIP SELECTION")
            print()
            print(f"  {data['ships'][choice].get('nickname', data['ships'][choice]['name'].title())} is already your active ship.")
            print()
            input("  Press Enter to continue...")


def visit_observatory():
    """Display a random ASCII art from the observatory collection"""
    import random
    from pathlib import Path
    import json

    ascii_art_dir = Path(resource_path("ascii_art"))

    # Check if directory exists
    if not ascii_art_dir.exists():
        clear_screen()
        title("OBSERVATORY")
        print()
        print("Error: ASCII art directory not found.")
        input("Press Enter to continue...")
        return

    # Get all subdirectories with art.txt files
    art_collections = []
    for item in ascii_art_dir.iterdir():
        if item.is_dir():
            art_file = item / "art.txt"
            meta_file = item / "meta.json"
            if art_file.exists() and meta_file.exists():
                art_collections.append(item)

    if not art_collections:
        clear_screen()
        title("OBSERVATORY")
        print()
        print("No astronomical artwork available at this time.")
        input("Press Enter to continue...")
        return

    # Select a random art piece
    selected_art_dir = random.choice(art_collections)
    art_file = selected_art_dir / "art.txt"
    meta_file = selected_art_dir / "meta.json"

    # Load the ASCII art
    with open(art_file, 'r', encoding='utf-8') as f:
        art_content = f.read()

    # Load the metadata
    with open(meta_file, 'r') as f:
        metadata = json.load(f)

    # Display the art
    clear_screen()
    title("OBSERVATORY")
    print()
    print(art_content)
    print()
    print(f"Title: {metadata.get('title', 'Untitled')}")
    print(f"Artist: {metadata.get('Artist', 'Unknown')}")
    print()
    input("Press Enter to Exit")


def title(text, centered=False):
    print("=" * 60)
    if centered:
        total_padding = 60 - len(text)
        spacingL = " " * math.ceil(total_padding / 2)
        spacingR = " " * math.floor(total_padding / 2)
        print(f"{spacingL}{text}{spacingR}")
    else:
        print(f"  {text}")
    print("=" * 60)


def system_data(system_name):
    with open(resource_path('system_data.json'), 'r') as f:
        data = json.load(f)

    return data.get(system_name)


def new_game():
    """Start a new game with dialogue and player name input"""
    clear_screen()
    print("=" * 60)
    print()
    intro = [
        "Welcome to Starscape, the greatest adventure you'll ever",
        "live among the stars. Plagued with war and malicious drones,",
        "this vast galaxy contains wonders beyond belief,",
        "opportunities for profit, and loads of adventure.",
        "",
        "The galaxy was once filled with people like you. But one",
        "day, the player population slowly disappeared. You are the",
        "last player. You will meet no one else like you on your",
        "journey.",
        "",
        "You are the last player to clone out of the cloning bay",
        "for their first time. You have a lot to learn. With just a",
        "Stratos and 5,000 credits to your name, you're ready to",
        "begin the greatest adventure one could dream of. Go, make",
        "this truly a Starscape.",
        ""
    ]
    type_lines(intro)
    sleep(1)
    print("=" * 60)
    print()

    input("Press Enter to begin your journey...")

    clear_screen()
    title("NEW GAME")
    print()
    print("Pilot, what shall you be called?")

    player_name = input("Enter your pilot name: ").strip()

    if not player_name:
        print("\nPilot name cannot be empty!")
        input("Press Enter to continue...")
        return

    # Find unique save name by appending numbers if needed
    save_name = player_name
    save_dir = Path.home() / ".starscape_text_adventure" / "saves"
    counter = 1

    while (save_dir / save_name / "save.json").exists():
        save_name = f"{player_name}_{counter}"
        counter += 1

    # Create save with player's name
    data = default_data()
    data["player_name"] = player_name
    save_data(save_name, data)

    clear_screen()
    title(f"WELCOME, {player_name.upper()}")
    print()
    print(f"  Save '{save_name}' created successfully!")
    lines = [
        "",
        "You open your eyes, you see a glass tube around you.",
        "The tube opens and you step out. You've just been cloned",
        "for the first time. You awake with basic knowledge of the",
        "universe, how to survive, and how to pilot a spacecraft.",
        "",
        "The cloning facility is now shutting down, no longer",
        "cloning in new players. You are the last of your kind.",
        "From now on, these cloning tubes will only be used to",
        "revive you in case you die. And you WILL die. This is a",
        "dangerous galaxy. Tread cautiously, but don't let caution get",
        "in the way of adventure. Go, explore this vast starscape!",
        ""
        ]
    type_lines(lines)
    sleep(1)
    print("  You have been assigned:")
    print("    - Stratos (Starter Ship)")
    print("    - 5,000 Credits")
    print()
    input("Press Enter to continue...")

    game_loop(save_name, data)


def continue_game():
    """Load a save and continue it"""
    # List available saves
    save_dir = Path.home() / ".starscape_text_adventure" / "saves"
    if not save_dir.exists():
        clear_screen()
        title("CONTINUE GAME")
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    saves = [folder.name for folder in save_dir.iterdir()
             if folder.is_dir() and (folder / "save.json").exists()]

    if not saves:
        clear_screen()
        title("CONTINUE GAME")
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    # Add "Cancel" option
    options = saves + ["Cancel"]

    choice = arrow_menu("SELECT SAVE TO CONTINUE", options)

    # If Cancel was selected
    if choice == len(saves):
        return

    save_name = saves[choice]
    data = read_data(save_name)

    clear_screen()
    if data:
        game_loop(save_name, data)
    else:
        print("\nFailed to load save!")
        input("\nPress Enter to continue...")


def delete_save_screen():
    """List saves and delete the selected one after confirmation"""
    save_dir = Path.home() / ".starscape_text_adventure" / "saves"

    if not save_dir.exists():
        clear_screen()
        title("DELETE SAVE")
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    saves = [folder.name for folder in save_dir.iterdir()
             if folder.is_dir() and (folder / "save.json").exists()]

    if not saves:
        clear_screen()
        title("DELETE SAVE")
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    options = saves + ["Cancel"]
    choice = arrow_menu("SELECT SAVE TO DELETE", options)

    if choice == len(saves):  # Cancel
        return

    save_name = saves[choice]
    save_path = save_dir / save_name

    clear_screen()
    title("CONFIRM DELETE")
    print()
    print(f"This will permanently delete the save '{save_name}'.")
    print(f"Type '{save_name}' to confirm.")
    print()

    confirmation = input("> ").strip()

    if confirmation != save_name:
        print("\nConfirmation failed. Save was not deleted.")
        input("Press Enter to continue...")
        return

    # Delete save directory and contents
    for root, dirs, files in os.walk(save_path, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    os.rmdir(save_path)

    print(f"\nSave '{save_name}' deleted successfully.")
    input("Press Enter to continue...")


def animated_death_screen(save_name, data):
    """Animated death and cloning sequence with glitch effects"""
    import random

    # Update Discord presence to show death
    update_discord_presence(data=data, context="dead")

    GREEN = "\033[1;32m"
    DARK_GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    def type_text(text, delay=0.03, color=GREEN):
        """Print text with typing effect"""
        for char in text:
            print(color + char + RESET, end='', flush=True)
            sleep(delay)
        print()

    def glitch_line(length=60):
        """Generate a glitchy corrupted line"""
        chars = ['█', '▓', '▒', '░', '▀', '▄', '■', '□', '▪', '▫', '|', '/',
                 '\\', '-']
        return ''.join(random.choice(chars) for _ in range(length))

    def glitch_screen(lines=5):
        """Flash glitchy corruption"""
        for _ in range(lines):
            print(RED + glitch_line() + RESET)
            sleep(0.05)

    clear_screen()

    # Death message
    print()
    print()
    type_text("CRITICAL SYSTEM FAILURE", 0.05, RED)
    sleep(0.5)
    glitch_screen(3)
    sleep(0.3)

    type_text("Hull integrity: 0%", 0.04, RED)
    type_text("Life support: OFFLINE", 0.04, RED)
    sleep(0.5)

    # More glitches
    glitch_screen(4)
    sleep(0.3)

    type_text("Consciousness upload initiated...", 0.04, DARK_GREEN)
    sleep(0.5)

    # Progress bar for consciousness upload
    print(GREEN, end='')
    print("[", end='', flush=True)
    for i in range(30):
        print("█", end='', flush=True)
        sleep(0.05)
    print("] 100%" + RESET)
    sleep(0.3)

    type_text("Consciousness pattern secured.", 0.03, GREEN)
    sleep(0.4)

    # Glitch transition
    glitch_screen(5)

    type_text("Accessing cloning facility database...", 0.03, GREEN)
    sleep(0.6)
    type_text("Synthesizing biological components...", 0.03, GREEN)
    sleep(0.5)

    # DNA sequence effect
    print(GREEN, end='')
    bases = ['A', 'T', 'C', 'G']
    for _ in range(40):
        print(random.choice(bases), end='', flush=True)
        sleep(0.02)
    print(RESET)
    sleep(0.4)

    type_text("Neural pathways reconstructing...", 0.03, GREEN)
    sleep(0.5)

    # Flashing reconstruction
    for i in range(15):
        if i % 2 == 0:
            print(GREEN + "█" * 60 + RESET)
        else:
            print(" " * 60)
        sleep(0.1)

    clear_screen()

    type_text("Cloning process complete.", 0.04, GREEN)
    type_text("Memory restoration: 98.7% successful", 0.03, DARK_GREEN)
    type_text("Motor functions: ONLINE", 0.03, GREEN)
    type_text("Cognitive functions: ONLINE", 0.03, GREEN)
    sleep(0.5)

    print()
    type_text("Welcome back, pilot.", 0.04, GREEN)
    sleep(1)

    print()
    print(f"{RED}WARNING: All cargo has been lost.{RESET}")
    print(f"{DARK_GREEN}Location: The Citadel - Cloning Bay{RESET}")
    sleep(2)

    # Clean up, respawn, and pay cloning fee
    data["inventory"] = {}
    data["current_system"] = "The Citadel"
    data["docked_at"] = "The Citadel"
    data["credits"] = max(0, data["credits"] - 500)

    # Get the active ship before potentially removing it
    player_ship = get_active_ship(data)
    ship_name = player_ship.get("name", "").lower()

    # Check if the ship is a Stratos - if not, player loses their ship
    if ship_name != "stratos":
        print()
        print(f"{RED}Your {player_ship.get('nickname', 'ship')} was destroyed and cannot be recovered.{RESET}")
        sleep(1.5)

        # Remove the destroyed ship from the player's fleet
        active_idx = data.get("active_ship", 0)
        if active_idx < len(data["ships"]):
            data["ships"].pop(active_idx)

        # If player has no ships left, give them a basic Stratos
        if not data["ships"]:
            print(f"{DARK_GREEN}Emergency protocol: Issuing replacement Stratos...{RESET}")
            sleep(1)
            data["ships"].append({
                "id": str(uuid4()),
                "name": "stratos",
                "nickname": "Stratos",
                "hull_hp": 200,
                "shield_hp": 200,
                "modules_installed": [],
            })

        # Set active ship to first available ship
        data["active_ship"] = 0
        player_ship = get_active_ship(data)
    else:
        # Stratos is protected - restore it to full health
        print()
        print(f"{GREEN}Your Stratos has been recovered and repaired.{RESET}")
        sleep(1)

    # Restore ship to full health
    player_ship["hull_hp"] = get_max_hull(player_ship)
    player_ship["shield_hp"] = get_max_shield(player_ship)

    save_data(save_name, data)

    # Update presence - now docked at The Citadel after respawn
    update_discord_presence(data=data, context="docked")


def get_systems_within_jumps(start_system, max_jumps, all_systems_data):
    """BFS to find all systems within N jumps"""
    from collections import deque

    visited = {start_system: 0}  # system: jump_distance
    queue = deque([(start_system, 0)])

    while queue:
        current, jumps = queue.popleft()

        if jumps >= max_jumps:
            continue

        system_info = all_systems_data.get(current)
        if not system_info:
            continue

        for neighbor in system_info.get("Connections", []):
            if neighbor not in visited:
                visited[neighbor] = jumps + 1
                queue.append((neighbor, jumps + 1))

    return visited


def find_route_to_destination(start_system, end_system, all_systems_data):
    """Find shortest route from start to end system using BFS.
    Returns list of systems in order, or None if no route exists."""
    from collections import deque

    if start_system == end_system:
        return [start_system]

    visited = {start_system}
    queue = deque([(start_system, [start_system])])

    while queue:
        current, path = queue.popleft()

        system_info = all_systems_data.get(current)
        if not system_info:
            continue

        for neighbor in system_info.get("Connections", []):
            if neighbor == end_system:
                return path + [neighbor]

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None  # No route found


def fuzzy_match(query, text):
    """Simple fuzzy matching - returns True if all query chars appear in order in text"""
    query = query.lower()
    text = text.lower()
    query_idx = 0

    for char in text:
        if query_idx < len(query) and char == query[query_idx]:
            query_idx += 1

    return query_idx == len(query)


def search_systems(all_systems_data):
    """Search for systems by name or security level"""
    clear_screen()
    title("GALAXY SEARCH")
    print()
    print("Search by system name or security level")
    print("(Core, Secure, Contested, Unsecure, Wild)")
    print()

    query = input("Search: ").strip()

    if not query:
        return None

    matches = []

    for system_name, system_info in all_systems_data.items():
        # Skip hidden gates unless discovered
        if system_info.get("hidden", False):
            continue

        # Match by name
        if fuzzy_match(query, system_name):
            matches.append(system_name)
        # Match by security level
        elif fuzzy_match(query, system_info.get("SecurityLevel", "")):
            matches.append(system_name)

    if not matches:
        print(f"\nNo systems found matching '{query}'")
        input("Press Enter to continue...")
        return None

    # Show results with letter navigation
    print()
    print(f"Found {len(matches)} system(s):")
    print()

    letter_map = {}
    for i, system_name in enumerate(matches[:26]):  # Limit to 26 for a-z
        letter = chr(ord('a') + i)
        letter_map[letter] = system_name

        system_info = all_systems_data[system_name]
        security = system_info.get("SecurityLevel", "Unknown")
        color = get_security_color(security)

        print(f"  [{letter}] {color}{system_name}{RESET_COLOR} ({security})")

    print()
    print("Press a letter to view that system, or Enter to cancel")

    while True:
        key = get_key()
        if key == 'enter':
            return None
        elif key and key in letter_map:
            return letter_map[key]


def get_security_color(security_level):
    """Get color for security level"""
    match security_level:
        case "Core":
            return CORE_COLOR
        case "Secure":
            return SECURE_COLOR
        case "Contested":
            return CONTESTED_COLOR
        case "Unsecure":
            return UNSECURE_COLOR
        case "Wild":
            return WILD_COLOR
        case _:
            return RESET_COLOR


def get_key_with_shift():
    """Get a keypress and detect if shift is held (for letter keys)"""
    if os.name == 'nt':  # Windows
        import msvcrt
        key = msvcrt.getch()
        if key in [b'\xe0', b'\x00']:  # Arrow key prefix
            key = msvcrt.getch()
            if key == b'H':
                return 'up', False
            elif key == b'P':
                return 'down', False
        elif key == b'\r':
            return 'enter', False
        elif key == b'\x1b':
            return 'esc', False
        else:
            # Check if it's a letter
            try:
                char = key.decode('utf-8')
                # Uppercase means shift was held
                is_shift = char.isupper()
                return char.lower(), is_shift
            except:
                return None, False
    else:  # Unix/Linux/Mac
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':  # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'up', False
                    elif ch3 == 'B':
                        return 'down', False
                return 'esc', False
            elif ch == '\n' or ch == '\r':
                return 'enter', False
            else:
                # Check if shift was held (uppercase letter)
                is_shift = ch.isupper()
                return ch.lower(), is_shift
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None, False


def calculate_map_positions(center_system, systems_by_distance,
                            all_systems_data):
    """Calculate 2D positions for systems using a force-directed approach"""
    import random
    import math

    positions = {}

    # Center system at origin
    positions[center_system] = (0, 0)

    # Place systems at distances based on jump count
    for distance in range(1, 4):
        systems = systems_by_distance.get(distance, [])

        if not systems:
            continue

        # Arrange in a circle at this distance
        radius = distance * 8  # Scale factor for spacing
        angle_step = (2 * math.pi) / len(systems) if len(systems) > 0 else 0

        for i, system in enumerate(systems):
            angle = i * angle_step + random.uniform(-0.3, 0.3)  # Add jitter
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            positions[system] = (x, y)

    # Run a few iterations of force-directed adjustment
    for iteration in range(10):
        forces = {system: (0, 0) for system in positions}

        # Repulsion between all nodes
        for s1 in positions:
            for s2 in positions:
                if s1 == s2:
                    continue

                x1, y1 = positions[s1]
                x2, y2 = positions[s2]
                dx = x1 - x2
                dy = y1 - y2
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < 0.1:
                    dist = 0.1

                # Repulsion force
                force = 3.0 / (dist * dist)
                fx = (dx / dist) * force
                fy = (dy / dist) * force

                fx_old, fy_old = forces[s1]
                forces[s1] = (fx_old + fx, fy_old + fy)

        # Attraction along connections
        for system in positions:
            if system not in all_systems_data:
                continue

            for connected in all_systems_data[system].get("Connections", []):
                if connected not in positions:
                    continue

                x1, y1 = positions[system]
                x2, y2 = positions[connected]
                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < 0.1:
                    continue

                # Attraction force
                force = dist * 0.05
                fx = (dx / dist) * force
                fy = (dy / dist) * force

                fx_old, fy_old = forces[system]
                forces[system] = (fx_old + fx, fy_old + fy)

        # Apply forces (don't move center system)
        for system in positions:
            if system == center_system:
                continue

            fx, fy = forces[system]
            x, y = positions[system]
            positions[system] = (x + fx * 0.1, y + fy * 0.1)

    return positions


def draw_line(grid, x1, y1, x2, y2, char='·'):
    """Draw a line on the grid using Bresenham's algorithm"""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy

    while True:
        # Don't overwrite system markers
        if 0 <= y1 < len(grid) and 0 <= x1 < len(grid[0]):
            if grid[y1][x1] == ' ':
                grid[y1][x1] = char

        if x1 == x2 and y1 == y2:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy


def display_spatial_map(center_system, all_systems_data, current_system,
                        destination):
    """Display galaxy map as a node-based spatial graph"""
    clear_screen()

    # Get systems within 3 jumps
    systems_by_distance_dict = get_systems_within_jumps(center_system, 2,
                                                        all_systems_data)

    # Filter out undiscovered gates
    filtered_systems = {}
    for system, distance in systems_by_distance_dict.items():
        system_info = all_systems_data.get(system, {})
        # Include system if it's not hidden OR if it's a discovered gate
        if not system_info.get("hidden", False):
            filtered_systems[system] = distance

    systems_by_distance_dict = filtered_systems

    # Gates have one-way connections pointing to regular systems
    # We need to search ALL systems to find which gates connect to our visible systems
    additional_gates = {}

    # Search through all systems in the galaxy
    for sys_name, sys_info in all_systems_data.items():
        if sys_info.get("hidden", False):  # This is a hidden gate
            # Check if this gate connects to any of our visible systems
            for connected in sys_info.get("Connections", []):
                if connected in systems_by_distance_dict:
                    # This gate connects to a visible system!
                    if sys_name not in systems_by_distance_dict:
                        # Add it at distance+1 from the system it connects to
                        additional_gates[sys_name] = systems_by_distance_dict[connected] + 1
                    break  # Only need to find one connection

    # Merge additional gates into the main dictionary
    systems_by_distance_dict.update(additional_gates)

    # Organize by jump distance
    systems_by_distance = {0: [], 1: [], 2: [], 3: []}
    for system, distance in systems_by_distance_dict.items():
        if distance <= 3:  # Only include systems within 3 jumps
            systems_by_distance[distance].append(system)

    # Sort alphabetically within each distance
    for distance in systems_by_distance:
        systems_by_distance[distance].sort()

    # Calculate positions
    positions = calculate_map_positions(center_system, systems_by_distance,
                                        all_systems_data)

    # Convert to grid coordinates (terminal space)
    # Map dimensions
    MAP_WIDTH = 70
    MAP_HEIGHT = 24

    # Find bounds
    min_x = min(pos[0] for pos in positions.values())
    max_x = max(pos[0] for pos in positions.values())
    min_y = min(pos[1] for pos in positions.values())
    max_y = max(pos[1] for pos in positions.values())

    # Add padding
    range_x = max_x - min_x if max_x != min_x else 1
    range_y = max_y - min_y if max_y != min_y else 1

    # Convert positions to grid coordinates
    grid_positions = {}
    for system, (x, y) in positions.items():
        grid_x = int((x - min_x) / range_x * (MAP_WIDTH - 4) + 2)
        grid_y = int((y - min_y) / range_y * (MAP_HEIGHT - 4) + 2)
        grid_positions[system] = (grid_x, grid_y)

    # Create display grid
    grid = [[' ' for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

    # Draw connections first (so they appear behind nodes)
    for system in positions:
        if system not in all_systems_data:
            continue

        x1, y1 = grid_positions[system]

        for connected in all_systems_data[system].get("Connections", []):
            if connected not in grid_positions:
                continue

            x2, y2 = grid_positions[connected]

            # Determine line character based on security levels
            security1 = all_systems_data[system].get("SecurityLevel", "")
            security2 = all_systems_data[connected].get("SecurityLevel", "")

            # Use different characters for different connection types
            if "Unsecure" in [security1, security2] or "Wild" in [security1,
                                                                  security2]:
                line_char = '·'
            else:
                line_char = '─'

            draw_line(grid, x1, y1, x2, y2, line_char)

    # Assign letters and place system markers
    letter_map = {}
    letter_idx = 0

    all_systems = []
    for distance in range(4):
        all_systems.extend(systems_by_distance[distance])

    for system in all_systems:
        if letter_idx >= 26:
            break

        letter = chr(ord('a') + letter_idx)
        letter_map[letter] = system
        letter_idx += 1

        gx, gy = grid_positions[system]

        # Get color based on security
        security = all_systems_data[system].get("SecurityLevel", "Unknown")
        color = get_security_color(security)

        # Store letter with color and system info
        grid[gy][gx] = (letter, system, color)

    # Print header
    title("GALAXY MAP - SPATIAL VIEW")
    print(
        f"  Viewing: {get_security_color(all_systems_data[center_system]['SecurityLevel'])}{center_system}{RESET_COLOR}")
    if current_system != center_system:
        print(
            f"  Current: {get_security_color(all_systems_data[current_system]['SecurityLevel'])}{current_system}{RESET_COLOR}")
    if destination:
        print(
            f"  Destination: {get_security_color(all_systems_data[destination]['SecurityLevel'])}{destination}{RESET_COLOR}")
    print("=" * 60)
    print()

    # Print the grid
    for y in range(MAP_HEIGHT):
        line = ""
        for x in range(MAP_WIDTH):
            cell = grid[y][x]
            if isinstance(cell, tuple):
                letter, system, color = cell
                line += f"{color}{letter}{RESET_COLOR}"
            else:
                line += cell
        print(line)

    print()
    print("=" * 60)

    # Print legend with letters
    print("Systems:")
    col_width = 30
    systems_per_row = 2

    # Find next system in route if destination is set
    next_in_route = None
    if destination:
        route = find_route_to_destination(current_system, destination, all_systems_data)
        if route and len(route) > 1:
            next_in_route = route[1]

    for i in range(0, len(letter_map), systems_per_row):
        row_items = []
        for j in range(systems_per_row):
            idx = i + j
            if idx < len(letter_map):
                letters = list(letter_map.keys())
                letter = letters[idx]
                system = letter_map[letter]
                security = all_systems_data[system].get("SecurityLevel",
                                                        "Unknown")
                color = get_security_color(security)

                # Add markers
                markers = []
                if system == current_system:
                    markers.append("★")
                if system == destination:
                    markers.append("◆")
                if system == center_system:
                    markers.append("@")
                if system == next_in_route:
                    markers.append("\033[33m➜\033[0m")  # Yellow arrow for next in route
                marker_str = " ".join(markers) if markers else ""

                item = f"[{letter}] {color}{system}{RESET_COLOR}"

                if marker_str:
                    item += f" {marker_str}"
                row_items.append(item)

        # Print items in this row
        for item in row_items:
            # Strip ANSI codes for length calculation
            plain_item = item
            for code in [CORE_COLOR, SECURE_COLOR, CONTESTED_COLOR,
                         UNSECURE_COLOR, WILD_COLOR, RESET_COLOR]:
                plain_item = plain_item.replace(code, "")

            print(f"{item:<{col_width}}", end="")
        print()

    print()
    print(
        "  [a-z] Navigate | [SHIFT+letter] Set dest | [s] Search | [ESC] Exit")
    print("  Legend: ★ Current System  ◆ Destination  @ Viewing Center  \033[33m➜\033[0m Next in Route")
    print("=" * 60)

    return letter_map


def galaxy_map(save_name, data):
    """Interactive galaxy map interface"""
    # Update Discord presence for galaxy map
    update_discord_presence(data=data, context="galaxy_map")

    # Load all systems data
    with open(resource_path('system_data.json'), 'r') as f:
        all_systems_data = json.load(f)

    current_system = data["current_system"]
    center_system = current_system
    destination = data.get("destination", "")

    while True:
        letter_map = display_spatial_map(center_system, all_systems_data,
                                         current_system, destination)

        key, is_shift = get_key_with_shift()

        if key == 'esc':
            # Save destination before exiting
            data["destination"] = destination
            save_data(save_name, data)
            # Restore presence based on current state
            if data.get("docked_at"):
                update_discord_presence(data=data, context="docked")
            else:
                update_discord_presence(data=data, context="traveling")
            return
        elif key == 's' and not is_shift:
            # Search
            result = search_systems(all_systems_data)
            if result:
                center_system = result
        elif key and key in letter_map:
            selected_system = letter_map[key]

            if is_shift:
                # Toggle destination
                if destination == selected_system:
                    destination = ""
                else:
                    destination = selected_system
            else:
                # Navigate to system
                center_system = selected_system


def main():
    """Main debug menu"""
    # Initialize Discord Rich Presence
    init_discord_rpc()

    try:
        while True:
            # Update Discord status to show we're in main menu
            update_discord_presence(context="menu", data={})

            options = [
                "New Game",
                "Continue Game",
                "Delete Save",
                "Exit"
            ]

            logo_text = ("\033[1;33m\n" +
                r"  /$$$$$$  /$$$$$$$$ /$$$$$$  /$$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$  /$$$$$$$  /$$$$$$$$" + "\n" +
                r" /$$__  $$|__  $$__//$$__  $$| $$__  $$ /$$__  $$ /$$__  $$ /$$__  $$| $$__  $$| $$_____/" + "\n" +
                r"| $$  \__/   | $$  | $$  \ $$| $$  \ $$| $$  \__/| $$  \__/| $$  \ $$| $$  \ $$| $$      " + "\n" +
                r"|  $$$$$$    | $$  | $$$$$$$$| $$$$$$$/|  $$$$$$ | $$      | $$$$$$$$| $$$$$$$/| $$$$$   " + "\n" +
                r" \____  $$   | $$  | $$__  $$| $$__  $$ \____  $$| $$      | $$__  $$| $$____/ | $$__/   " + "\n" +
                r" /##  \ ##   | ##  | ##  | ##| ##  \ ## /##  \ ##| ##    ##| ##  | ##| ##      | ##      " + "\n" +
                r"|  ######/   | ##  | ##  | ##| ##  | ##|  ######/|  ######/| ##  | ##| ##      | ########" + "\n" +
                r" \______/    |__/  |__/  |__/|__/  |__/ \______/  \______/ |__/  |__/|__/      |________/" + "\n" +
                                                        RESET_COLOR
            )

            print(logo_text)

            choice = arrow_menu("Starscape: Text Adventure Edition", options, logo_text)

            if choice == 0:
                new_game()
            elif choice == 1:
                continue_game()
            elif choice == 2:
                delete_save_screen()
            elif choice == 3:
                clear_screen()
                print("Exiting...")
                break
    finally:
        # Clean up Discord connection when exiting
        close_discord_rpc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Exiting...")
        close_discord_rpc()
        sys.exit(0)
