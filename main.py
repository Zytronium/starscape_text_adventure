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

def display_menu(title, options, selected_index, previous_content=""):
    """Display menu with highlighted selection, preserving previous content"""
    clear_screen()

    # Re-print previous content if it exists
    if previous_content:
        print(previous_content, end='')
        print()  # Add spacing between content and menu

    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
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
        print("=" * 60)
        print("  CONTINUE GAME")
        print("=" * 60)
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

    print("=" * 60)
    print(f"  CURRENT SYSTEM: {system_name}")
    print("=" * 60)
    print(f"  SECURITY: {system["SecurityLevel"]}")
    print(f"  {system["Region"]} > {system["Sector"]}")
    print("=" * 60)
    print(f"  CREDITS: ¢{data["credits"]}")
    print("=" * 60)
    if system_name == "Gatinsir":
        sys.stdout = old_stdout
        clear_screen()

        print("=" * 60)
        print(f"  CURRENT SYSTEM: {system_name}")
        print("=" * 60)
        print(f"  SECURITY: {system["SecurityLevel"]}")
        print(f"  {system["Region"]} > {system["Sector"]}")
        print("=" * 60)
        print(f"  CREDITS: ¢{data["credits"]}")
        print("=" * 60)
        print()
        print("A fleet of pirates approaches! What will you do?")
        print("=" * 60)
        print("  ACTIONS MENU")
        print("=" * 60)
        print()
        print("  > Fight")
        print("    Warp to another system")
        print("    Ignore the fleet")
        print()
        print("  Use ↑/↓ arrows to navigate, Enter to select")
        sleep(0.5)

        clear_screen()

        print("=" * 60)
        print(f"  CURRENT SYSTEM: {system_name}")
        print("=" * 60)
        print(f"  SECURITY: {system["SecurityLevel"]}")
        print(f"  {system["Region"]} > {system["Sector"]}")
        print("=" * 60)
        print(f"  CREDITS: ¢{data["credits"]}")
        print("=" * 60)
        print()
        print("The fleet of pirates obliterated your ship! You died.")
        print()
        print("Cloning...")
        sleep(5)
        data["inventory"] = {}  # clear inventory | todo: erase this ship too unless its a stratos
        data["current_system"] = "The Citadel"
        save_data(save_name, data)
        return

    previous_content = content_buffer.getvalue()
    sys.stdout = old_stdout

    options = ["View status", "Warp to another system", "View inventory", "Dock at station", "Save", "Save and quit"]
    choice = arrow_menu("Select action:", options, previous_content)

    match choice:
        case 0:
            clear_screen()
            print("=" * 60)
            print("  STATUS")
            print("=" * 60)
            print("Not implemented yet")
            input("Press enter to continue...")
        case 1:
            warp_menu(system, save_name, data)
        case 2:
            clear_screen()
            print("=" * 60)
            print("  INVENTORY")
            print("=" * 60)
            print("Not implemented yet")
            input("Press enter to continue...")
        case 3:
            clear_screen()
            print("=" * 60)
            print("  STATION")
            print("=" * 60)
            print("Not implemented yet")
            input("Press enter to continue...")
        case 4:
            clear_screen()
            print("=" * 60)
            print("  SAVE GAME")
            print("=" * 60)
            print("Saving...")
            save_data(save_name, data)
            print("Game saved.")
            input("Press enter to continue...")
        case 5:
            clear_screen()
            print("=" * 60)
            print("  SAVE & QUIT")
            print("=" * 60)
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
    print("=" * 60)
    print("  WARP MENU")
    print("=" * 60)
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
    print("=" * 60)
    print("  NEW GAME")
    print("=" * 60)
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
    print("=" * 60)
    print(f"  WELCOME, {player_name.upper()}")
    print("=" * 60)
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

def create_default_save():
    """Create a default save with custom name"""
    clear_screen()
    print("=" * 60)
    print("  CREATE DEFAULT SAVE")
    print("=" * 60)
    print()

    save_name = input("Enter save name: ").strip()

    if not save_name:
        print("\nSave name cannot be empty!")
        input("Press Enter to continue...")
        return

    data = default_data()
    save_data(save_name, data)

    print(f"\nSave '{save_name}' created successfully!")
    input("Press Enter to continue...")


def continue_game():
    """Load a save and continue it"""
    # List available saves
    save_dir = Path.home() / ".starscape_text_adventure" / "saves"
    if not save_dir.exists():
        clear_screen()
        print("=" * 60)
        print("  CONTINUE GAME")
        print("=" * 60)
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    saves = [folder.name for folder in save_dir.iterdir()
             if folder.is_dir() and (folder / "save.json").exists()]

    if not saves:
        clear_screen()
        print("=" * 60)
        print("  CONTINUE GAME")
        print("=" * 60)
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
        print("=" * 60)
        print("  DELETE SAVE")
        print("=" * 60)
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    saves = [folder.name for folder in save_dir.iterdir()
             if folder.is_dir() and (folder / "save.json").exists()]

    if not saves:
        clear_screen()
        print("=" * 60)
        print("  DELETE SAVE")
        print("=" * 60)
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
    print("=" * 60)
    print("  CONFIRM DELETE")
    print("=" * 60)
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
