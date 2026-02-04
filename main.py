"""
Starscape: Text Adventure Edition
A text-based recreation of the Roblox game Starscape by Zolar Keth
"""
import math
import sys
import json
import os
from pathlib import Path
from io import StringIO
from time import sleep

VERSION_CODE = 1
CORE_COLOR = "\033[1;32m"     # lime
SECURE_COLOR = "\033[36m"     # cyan
CONTESTED_COLOR = "\033[33m"  # orange/brown
UNSECURE_COLOR = "\033[31m"   # red
WILD_COLOR = "\033[35m"       # purple
RESET_COLOR = "\033[0m"       # reset

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
        "ships_owned": [
            {
                "id": "stratos",
                "name": "Stratos",
                "hull_hp": 200,
                "shield_hp": 200,
                "modules_installed": [],
            }
        ],
        "inventory": {},
        "storage": {},
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
        }
    }


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

    while True:
        main_screen(save_name, data)


def main_screen(save_name, data):
    system_name = data["current_system"]
    system = system_data(system_name)

    # Capture the screen content before showing the menu
    content_buffer = StringIO()
    old_stdout = sys.stdout
    sys.stdout = content_buffer

    title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
    # print(f"  SECURITY: {system["SecurityLevel"]}")
    print(f"  {system["Region"]} > {system["Sector"]}")
    title(f"CREDITS: ¢{data["credits"]}")
    if system_name == "Gatinsir":
        sys.stdout = old_stdout
        clear_screen()

        title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
        # print(f"  SECURITY: {system["SecurityLevel"]}")
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
        # print(f"  SECURITY: {system["SecurityLevel"]}")
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
               "Dock at station", "Map", "Save", "Save and quit"]
    choice = arrow_menu("Select action:", options, previous_content)

    match choice:
        case 0:
            clear_screen()
            title("STATUS")
            print("Not implemented yet")
            input("Press enter to continue...")
        case 1:
            warp_menu(system, save_name, data)
        case 2:
            clear_screen()
            title("INVENTORY")
            print("Not implemented yet")
            input("Press enter to continue...")
        case 3:
            station_screen(system, save_name, data)
        case 4:
            galaxy_map(save_name, data)
        case 5:
            clear_screen()
            title("SAVE GAME")
            print("Saving...")
            save_data(save_name, data)
            print("Game saved.")
            input("Press enter to continue...")
        case 6:
            clear_screen()
            title("  SAVE & QUIT")
            print("Saving...")
            save_data(save_name, data)
            print("Game saved.")
            input("Press enter to exit...")
            sys.exit(0)


def warp_menu(system, save_name, data):
    connected_systems = system["Connections"]
    options = connected_systems + [f"{UNSECURE_COLOR}x{RESET_COLOR} Cancel"]

    i = 0
    for system in connected_systems:
        security_level = system_data(system)["SecurityLevel"]

        match security_level:
            case "Core":
                options[i] = f"{CORE_COLOR}⬤ {system}{RESET_COLOR}"
            case "Secure":
                options[i] = f"{SECURE_COLOR}⬤ {system}{RESET_COLOR}"
            case "Contested":
                options[i] = f"{CONTESTED_COLOR}⬤ {system}{RESET_COLOR}"
            case "Unsecure":
                options[i] = f"{UNSECURE_COLOR}⬤ {system}{RESET_COLOR}"
            case "Wild":
                options[i] = f"{WILD_COLOR}⬤ {system}{RESET_COLOR}"
        i += 1

    clear_screen()
    title("WARP MENU")
    choice = arrow_menu("Select system to warp to", options)

    # If Cancel was selected
    if choice == len(connected_systems):
        return

    clear_screen()
    print("=" * 60)
    print("|" + " " * 58 + "|")
    print(f"| Warping to {connected_systems[choice]}...{" " * (58 - len(connected_systems[choice]) - 15)}|")
    print("|" + " " * 58 + "|")
    print("=" * 60)
    sleep(2)

    data["current_system"] = connected_systems[choice]
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

    total_padding = 58 - len(connected_systems[choice])
    spacingL = " " * math.ceil(total_padding / 2)
    spacingR = " " * math.floor(total_padding / 2)

    print("—" * 60)
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print(f"|{spacingL}{system_color}{connected_systems[choice]}{RESET_COLOR}{spacingR}|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("—" * 60)
    sleep(2)


def station_screen(system, save_name, data):
    clear_screen()
    title("STATION")
    print("Not implemented yet")
    input("Press enter to continue...")


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
    with open('system_data.json', 'r') as f:
        data = json.load(f)

    return data.get(system_name)


def new_game():
    """Start a new game with dialogue and player name input"""
    clear_screen()
    print("============================================================")
    print()
    print("Welcome to Starscape, the greatest adventure you'll ever")
    print("live among the stars. Plagued with war and malicious drones,")
    print("this vast galaxy contains wonders beyond belief,")
    print("opportunities for profit, and loads of adventure.")
    print()
    print("The galaxy was once filled with people like you. But one")
    print("day, the player population slowly disappeared. You are the")
    print("last player. You will meet no one else like you on your")
    print("journey.")
    print()
    print("You are the last player to clone out of the cloning bay")
    print("for their first time. You have a lot to learn. With just a")
    print("Stratos and 5,000 credits to your name, you're ready to")
    print("begin the greatest adventure one could dream of. Go, make")
    print("this truly a Starscape.")
    print()
    print("============================================================")
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
    print()
    print("You open your eyes, you see a glass tube around you.")
    print("The tube opens and you step out. You've just been cloned")
    print("for the first time. You awake with basic knowledge of the")
    print("universe, how to survive, and how to pilot a spacecraft.")
    print()
    print("The cloning facility is now shutting down, no longer")
    print("cloning in new players. You are the last of your kind.")
    print("From now on, these cloning tubes will only be used to")
    print("revive you in case you die. And you WILL die. This is a")
    print("dangerous galaxy. Tread cautiously, but don't let caution get")
    print("in the way of adventure. Go, explore this vast starscape!")
    print()
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
            os.remove(Path(root) / file)
        for d in dirs:
            os.rmdir(Path(root) / d)
    os.rmdir(save_path)

    print(f"\nSave '{save_name}' deleted successfully.")
    input("Press Enter to continue...")


def animated_death_screen(save_name, data):
    """Animated death and cloning sequence with glitch effects"""
    import random

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

    # Clean up and respawn
    data["inventory"] = {}
    data["current_system"] = "The Citadel"
    save_data(save_name, data)


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
    systems_by_distance_dict = get_systems_within_jumps(center_system, 3,
                                                        all_systems_data)

    # Organize by jump distance
    systems_by_distance = {0: [], 1: [], 2: [], 3: []}
    for system, distance in systems_by_distance_dict.items():
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
    print("  Legend: ★ Current System  ◆ Destination  @ Viewing Center")
    print("=" * 60)

    return letter_map


def galaxy_map(save_name, data):
    """Interactive galaxy map interface"""
    # Load all systems data
    with open('system_data.json', 'r') as f:
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
    while True:
        options = [
            "New Game",
            "Continue Game",
            "Delete Save",
            "Exit"
        ]

        choice = arrow_menu("Starscape: Text Adventure Edition", options)

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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Exiting...")
        sys.exit(0)
