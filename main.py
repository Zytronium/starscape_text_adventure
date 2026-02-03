"""
Starscape: Text Adventure Edition
A text-based recreation of the Roblox game Starscape by Zolar Keth
"""

import sys
import json
import os
from pathlib import Path

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

def display_menu(title, options, selected_index):
    """Display menu with highlighted selection"""
    clear_screen()
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

def arrow_menu(title, options):
    """Display menu with arrow key navigation, return selected index"""
    selected = 0

    while True:
        display_menu(title, options, selected)
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
        "v": 1,  # save version code.
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
        }
    }

def new_game():
    """Start a new game with dialogue and player name input"""
    clear_screen()
    print("=" * 60)
    print()
    print("  The year is 2847. Humanity has spread across the stars,")
    print("  but the frontier remains wild and dangerous.")
    print()
    print("  Three great factions wage endless war for control of")
    print("  contested space, while pirates and opportunists lurk")
    print("  in the shadows of unsecure systems.")
    print()
    print("  You are a freelance pilot, fresh out of the cloning bay")
    print("  with nothing but a basic Stratos fighter and a dream")
    print("  of making your fortune among the stars.")
    print()
    print("  Your journey begins at The Citadel, the safest station")
    print("  in Core space. What you do next is up to you...")
    print()
    print("=" * 60)
    print()

    input("Press Enter to begin your journey...")

    clear_screen()
    print("=" * 60)
    print("  NEW GAME")
    print("=" * 60)
    print()

    player_name = input("Enter your pilot name: ").strip()

    if not player_name:
        print("\nPilot name cannot be empty!")
        input("Press Enter to continue...")
        return

    save_name = input("Enter save name: ").strip()

    if not save_name:
        print("\nSave name cannot be empty!")
        input("Press Enter to continue...")
        return

    # Create save with player's name
    data = default_data()
    data["player_name"] = player_name
    save_data(save_name, data)

    clear_screen()
    print("=" * 60)
    print(f"  WELCOME, COMMANDER {player_name.upper()}")
    print("=" * 60)
    print()
    print(f"  Save '{save_name}' created successfully!")
    print()
    print("  You have been assigned:")
    print("    - Stratos Fighter")
    print("    - 5,000 Credits")
    print("    - Docking clearance at The Citadel")
    print()
    input("Press Enter to continue...")

    # TODO: Start game loop here
    # game_loop(save_name, data)

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

def load_and_print_save():
    """Load a save and print its information"""
    # List available saves
    save_dir = Path.home() / ".starscape_text_adventure" / "saves"
    if not save_dir.exists():
        clear_screen()
        print("=" * 60)
        print("  LOAD SAVE")
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
        print("  LOAD SAVE")
        print("=" * 60)
        print()
        print("No saves found!")
        input("Press Enter to continue...")
        return

    # Add "Cancel" option
    options = saves + ["Cancel"]

    choice = arrow_menu("SELECT SAVE TO LOAD", options)

    # If Cancel was selected
    if choice == len(saves):
        return

    save_name = saves[choice]
    data = read_data(save_name)

    clear_screen()
    if data:
        print("=" * 60)
        print(f"  SAVE DATA: {save_name}")
        print("=" * 60)
        print(json.dumps(data, indent=2))
    else:
        print("\nFailed to load save!")

    input("\nPress Enter to continue...")

def main():
    """Main debug menu"""
    while True:
        options = [
            "New Game",
            "[DEBUG] Load and Print Save",
            "Exit"
        ]

        choice = arrow_menu("Starscape: Text Adventure Edition", options)

        if choice == 0:
            new_game()
        elif choice == 1:
            load_and_print_save()
        elif choice == 2:
            clear_screen()
            print("Exiting...")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Exiting...")
        sys.exit(0)
