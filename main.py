"""
Starscape: Text Adventure Edition
A text-based recreation of the Roblox game Starscape by Zolar Keth
"""
import math
import random
import sys
import json
import os
import platform
import subprocess
import threading
from pathlib import Path
from io import StringIO
from time import sleep, time
from uuid import uuid4
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from colors import set_color, set_background_color, reset_color, get_color, get_background_color

# Discord Rich Presence support
try:
    from pypresence import Presence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# Music support
try:
    import pygame
    MUSIC_AVAILABLE = True
except ImportError:
    MUSIC_AVAILABLE = False

if not DISCORD_AVAILABLE:
    print("Warning: pypresence not installed. Discord Rich Presence disabled.\033[K")
    print("Install with: pip install pypresence\033[K")

if not MUSIC_AVAILABLE:
    print("Warning: pygame not installed. Audio disabled.\033[K")
    print("Install with: pip install pygame\033[K")

if not DISCORD_AVAILABLE or not MUSIC_AVAILABLE:
    sleep(3)

# Version codes
APP_VERSION_CODE = "0.1.3.2"  # 0.1.x = alpha; 0.2.x = beta; 1.x = release
SAVE_VERSION_CODE = 2         # Save format version code

# Color codes
CORE_COLOR = "\033[1;32m"     # lime
SECURE_COLOR = "\033[36m"     # cyan
CONTESTED_COLOR = "\033[33m"  # yellow/brown
UNSECURE_COLOR = "\033[31m"   # red
WILD_COLOR = "\033[35m"       # purple
RESET_COLOR = "\033[0m"       # reset

# Discord Application Client ID
DISCORD_CLIENT_ID = "1469089302578200799"

# Global Discord RPC instance
discord_rpc = None


class MusicManager:
    _AMBIANCE_FILES = [f"audio/Ambiance{i}.mp3" for i in range(1, 6)]
    _BATTLE_FILES   = [f"audio/Battle{i}.mp3"   for i in range(1, 3)]

    def __init__(self):
        self._lock = threading.Lock()
        self._current_track = None
        self._mode = None          # 'ambiance' | 'battle' | 'vex' | 'intro' | 'menu' | None
        self._ambiance_queue = []
        self._battle_queue   = []
        self._monitor_thread = None
        self._stop_monitor   = False
        # Per-mode volumes (0.0–1.0); loaded from settings on first use
        self._volumes = {'ambiance': 1.0, 'battle': 1.0, 'vex': 1.0,
                         'intro': 1.0, 'menu': 1.0}

        if MUSIC_AVAILABLE:
            pygame.mixer.init()


    def load_volumes(self):
        """Sync volume levels from the settings file."""
        try:
            settings = get_settings()
            self._volumes['ambiance'] = max(0.0, min(1.0,
                settings.get('ambiance_volume', 100) / 100.0))
            # Battle volume applies to both battle tracks and Vex
            bv = max(0.0, min(1.0, settings.get('battle_volume', 100) / 100.0))
            self._volumes['battle'] = bv
            self._volumes['vex']    = bv
        except Exception:
            pass

    def _vol(self):
        """Return the volume for the current mode."""
        return self._volumes.get(self._mode, 1.0)

    def _next_ambiance(self):
        """Return the next ambiance path, refilling & reshuffling when empty."""
        if not self._ambiance_queue:
            pool = self._AMBIANCE_FILES.copy()
            random.shuffle(pool)
            # Avoid immediately repeating the track that just finished
            if self._current_track and len(pool) > 1:
                just_played = self._current_track
                while pool[0] == just_played:
                    random.shuffle(pool)
            self._ambiance_queue = pool
        return self._ambiance_queue.pop(0)

    def _next_battle(self):
        """Return the next battle path, cycling randomly."""
        if not self._battle_queue:
            pool = self._BATTLE_FILES.copy()
            random.shuffle(pool)
            if self._current_track and len(pool) > 1:
                just_played = self._current_track
                while pool[0] == just_played:
                    random.shuffle(pool)
            self._battle_queue = pool
        return self._battle_queue.pop(0)

    def _load_and_play(self, filepath, fade_ms=1500, loops=0):
        """Load and start a track.  loops=0 means play once (monitor chains next)."""
        if not MUSIC_AVAILABLE:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms // 2)
            sleep(fade_ms / 2000)
            pygame.mixer.music.load(resource_path(filepath))
            pygame.mixer.music.set_volume(self._vol())
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self._current_track = filepath
        except Exception:
            pass

    def _monitor_loop(self):
        """Background daemon: when a queued track ends, play the next one."""
        while not self._stop_monitor:
            sleep(0.4)
            if not MUSIC_AVAILABLE:
                continue
            with self._lock:
                mode = self._mode
            if mode not in ('ambiance', 'battle'):
                continue
            if pygame.mixer.music.get_busy():
                continue
            # Track finished – queue the next one
            with self._lock:
                mode = self._mode          # re-check inside lock
                if mode == 'ambiance':
                    track = self._next_ambiance()
                elif mode == 'battle':
                    track = self._next_battle()
                else:
                    continue
            self._load_and_play(track, fade_ms=1000)

    def _ensure_monitor(self):
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_monitor = False
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True, name="MusicMonitor"
            )
            self._monitor_thread.start()


    def play_ambiance(self, fade_ms=2000):
        """Switch to shuffled ambiance music (loops forever via monitor)."""
        if not MUSIC_AVAILABLE:
            return
        self.load_volumes()
        self._ensure_monitor()
        with self._lock:
            self._mode = 'ambiance'
            track = self._next_ambiance()
        self._load_and_play(track, fade_ms)

    def play_battle(self, fade_ms=1000):
        """Switch to randomly-chained battle music."""
        if not MUSIC_AVAILABLE:
            return
        self.load_volumes()
        self._ensure_monitor()
        with self._lock:
            self._mode = 'battle'
            track = self._next_battle()
        self._load_and_play(track, fade_ms)

    def play_vex(self, fade_ms=1500):
        """Play Vex.mp3 on loop (Vexnium anomaly / crystalline combat)."""
        if not MUSIC_AVAILABLE:
            return
        self.load_volumes()
        self._ensure_monitor()
        with self._lock:
            self._mode = 'vex'
        self._load_and_play("audio/Vex.mp3", fade_ms=fade_ms, loops=-1)

    def play_intro(self, fade_ms=1500):
        """Play Intro.mp3 once (monitor stays idle until mode changes)."""
        if not MUSIC_AVAILABLE:
            return
        self.load_volumes()
        self._ensure_monitor()
        with self._lock:
            self._mode = 'intro'
            self._current_track = "audio/Intro.mp3"
        try:
            pygame.mixer.music.fadeout(fade_ms // 2)
            sleep(fade_ms / 2000)
            pygame.mixer.music.load(resource_path("audio/Intro.mp3"))
            pygame.mixer.music.set_volume(self._vol())
            pygame.mixer.music.play(loops=0, fade_ms=fade_ms)
        except Exception:
            pass

    def play(self, filepath, loops=-1, fade_ms=2000):
        """Play a specific file directly (e.g. Menu.ogg with infinite loop)."""
        if not MUSIC_AVAILABLE:
            return
        with self._lock:
            self._mode = 'menu'
            self._current_track = filepath
        try:
            pygame.mixer.music.fadeout(fade_ms // 2)
            sleep(fade_ms / 2000)
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.set_volume(self._vol())
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
        except Exception:
            pass

    def stop(self, fade_ms=2000):
        if not MUSIC_AVAILABLE:
            return
        with self._lock:
            self._mode = None
            self._current_track = None
        pygame.mixer.music.fadeout(fade_ms)

    def set_volume(self, volume: float):
        """Immediately change the volume of whatever is currently playing (0.0–1.0)."""
        if not MUSIC_AVAILABLE:
            return
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def is_playing(self):
        return MUSIC_AVAILABLE and pygame.mixer.music.get_busy()

# Global music instance
music = MusicManager()


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
        settings = get_settings()

        if settings.get("adaptive_discord_presence", True):
            discord_rpc.update(
                state="In Main Menu",
                details="Playing Starscape Text Adventure",
                large_text="Starscape: Text Adventure",
                start=int(time())
            )
        return True
    except Exception as e:
        print(f"Warning: Could not connect to Discord: {e}\033[K")
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
        return f"Docked at {docked_at}", security_text

    elif context == "combat":
        return "Engaged in combat", security_text

    elif context == "traveling":
        return f"Piloting a {ship_name}", security_text

    elif context == "mining":
        return "Mining asteroids", security_text

    elif context == "menu":
        return "Navigating menus", "In Main Menu"

    elif context == "galaxy_map":
        return "Viewing galaxy map", f"planning route in {current_system}"

    elif context == "station_menu":
        docked_at = data.get("docked_at", "a space station")
        return f"Managing affairs at {docked_at}", security_text

    elif context == "trading":
        return "Trading goods", security_text

    elif context == "outfitting":
        return "Outfitting ship", f"at {data.get('docked_at', 'station')}"

    # Default: flying around
    else:
        return f"Piloting a {ship_name}", security_text


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
        # Load settings to check if adaptive presence is enabled
        settings = get_settings()

        update_args = {
            "large_text": "Starscape: Text Adventure"
        }

        # Use adaptive presence if enabled in settings and data/context provided
        if settings.get("adaptive_discord_presence", True) and data and context:
            details, state = get_adaptive_presence(data, context)
        elif not settings.get("adaptive_discord_presence", True):
            # If adaptive presence is disabled, use simple generic presence
            if not details:
                details = "Playing Starscape Text Adventure"
            if not state and context == "menu":
                state = "In Main Menu"

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


def is_version_newer(new_version_code):
    """Checks if the given app version code is newer than the current known one"""
    if not isinstance(new_version_code, str):
        return False  # silently fail. This is a text adventure game after all.

    # Identical version codes
    if new_version_code == APP_VERSION_CODE:
        return False

    # Convert to integer lists
    new_version_split = [int(x) for x in new_version_code.split(".")]
    current_version_split = [int(x) for x in APP_VERSION_CODE.split(".")]

    # Pad the shorter list with zeros
    version_len = max(len(new_version_split), len(current_version_split))
    new_version_split += [0] * (version_len - len(new_version_split))
    current_version_split += [0] * (version_len - len(current_version_split))

    for i in range(version_len):
        if current_version_split[i] < new_version_split[i]:
            return True  # new version is newer
        elif current_version_split[i] > new_version_split[i]:
            return False  # new version is older

    # No difference found, though shouldn't happen here normally
    return False


def check_for_updates():
    """Check for updates and download/install if available"""
    clear_screen()
    title("CHECK FOR UPDATES")

    print("Checking for updates...\033[K")
    print()

    # Check if running as executable
    is_executable = hasattr(sys, '_MEIPASS')

    try:
        # Make API request to get version info
        api_url = "https://cdn.zytronium.dev/starscape_text_adventure/version_code"
        req = Request(api_url, headers={'User-Agent': 'Starscape-Text-Adventure'})

        with urlopen(req, timeout=10) as response:
            version_data = json.loads(response.read().decode())

        remote_app_version = version_data.get("app")

        if not remote_app_version:
            print("Error: Invalid response from update server.\033[K")
            input("\nPress Enter to return to menu...")
            return

        print(f"Current version: {APP_VERSION_CODE}\033[K")
        print(f"Latest version:  {remote_app_version}\033[K")
        print()

        # Check if update is available
        if not is_version_newer(remote_app_version):
            print("You are running the latest version!\033[K")
            input("\nPress Enter to return to menu...")
            return

        # Update available
        print("\033[1;32mA new version is available!\033[0m\033[K")
        print()

        # Detect OS
        system = platform.system()

        if system == "Darwin":  # macOS
            print("Unfortunately, automatic updates are not supported on macOS.\033[K")
            print("Please download and compile the latest version manually from:\033[K")
            print("https://github.com/Zytronium/starscape_text_adventure\033[K")
            input("\nPress Enter to return to menu...")
            return

        # Check if running as executable (can auto-update)
        if not is_executable:
            print("You are running from Python source.\033[K")
            print("Automatic updates are only available for compiled executables.\033[K")
            print("\nPlease download the latest version from:\033[K")
            print("https://github.com/Zytronium/starscape_text_adventure\033[K")
            input("\nPress Enter to return to menu...")
            return

        # Determine download URL based on OS
        if system == "Windows":
            download_url = "https://cdn.zytronium.dev/starscape_text_adventure/download/windows/starscape_text_adventure.exe"
            new_filename = "starscape_text_adventure_new.exe"
            update_script = "update.bat"
        elif system == "Linux":
            download_url = "https://cdn.zytronium.dev/starscape_text_adventure/download/linux/starscape_text_adventure"
            new_filename = "starscape_text_adventure_new"
            update_script = "update.sh"
        else:
            print(f"Automatic updates are not supported on {system}.\033[K")
            print("Please download and compile manually from:\033[K")
            print("https://github.com/Zytronium/starscape_text_adventure\033[K")
            input("\nPress Enter to return to menu...")
            return

        # Ask user if they want to update
        print("Would you like to download and install this update?\033[K")
        response = input("(y/n): ").strip().lower()

        if response != 'y':
            print("\nUpdate cancelled.\033[K")
            input("\nPress Enter to return to menu...")
            return

        print("\nDownloading update...\033[K")

        # Download the new version
        req = Request(download_url, headers={'User-Agent': 'Starscape-Text-Adventure'})

        # Get current executable path
        current_exe = sys.executable
        download_path = os.path.join(os.path.dirname(current_exe), new_filename)

        # Download with progress
        try:
            with urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 8192

                with open(download_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}%", end='', flush=True)

            print("\n\033[K")

            # Verify download completed
            if total_size > 0 and downloaded != total_size:
                raise Exception(f"Download incomplete: got {downloaded} bytes, expected {total_size}")

            # Verify file exists and has content
            if not os.path.exists(download_path):
                raise Exception("Downloaded file not found")

            file_size = os.path.getsize(download_path)
            if file_size == 0:
                raise Exception("Downloaded file is empty")

            print(f"Download complete! ({file_size:,} bytes)\033[K")

        except Exception as e:
            # Clean up failed download
            if os.path.exists(download_path):
                os.remove(download_path)
            raise Exception(f"Download failed: {e}")

        # Make executable on Linux
        if system == "Linux":
            os.chmod(download_path, 0o755)

        # Create update script
        script_path = os.path.join(os.path.dirname(current_exe), update_script)

        if system == "Windows":
            # Windows batch script
            script_content = f"""@echo off
echo Waiting for application to close...
timeout /t 3 /nobreak >nul
echo Installing update...
if exist "{current_exe}.old" del "{current_exe}.old"
if exist "{current_exe}" move "{current_exe}" "{current_exe}.old"
move "{download_path}" "{current_exe}"
if errorlevel 1 (
    echo ERROR: Failed to install update!
    pause
    exit /b 1
)
echo Update installed successfully!
timeout /t 2 /nobreak >nul
echo Starting application...
start "" "{current_exe}"
timeout /t 1 /nobreak >nul
del "%~f0"
"""
        else:  # Linux
            # Linux shell script
            script_content = f"""#!/bin/bash
echo "Waiting for application to close..."
sleep 3
echo "Installing update..."
if [ -f "{current_exe}" ]; then
    mv "{current_exe}" "{current_exe}.old"
fi
mv "{download_path}" "{current_exe}"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install update!"
    echo "Restoring backup..."
    if [ -f "{current_exe}.old" ]; then
        mv "{current_exe}.old" "{current_exe}"
    fi
    echo "Press Enter to exit..."
    read
    exit 1
fi
chmod +x "{current_exe}"
echo "Update installed successfully!"
sleep 1
echo "Starting application..."
setsid "{current_exe}" > /dev/null 2>&1 &
NEW_PID=$!
sleep 2
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "Application started successfully!"
    # Clean up old version
    rm -f "{current_exe}.old"
    # Clean up this script (must be last)
    rm -f "$0"
else
    echo "WARNING: Application may not have started correctly"
    sleep 2
    # Still clean up
    rm -f "{current_exe}.old"
    rm -f "$0"
fi
"""

        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make script executable on Linux
        if system == "Linux":
            os.chmod(script_path, 0o755)

        print("\nUpdate downloaded successfully!\033[K")
        print("The application will now close and the update will be installed.\033[K")
        print("\nPress Enter to continue...\033[K")
        input()

        # Close Discord RPC before exiting
        close_discord_rpc()

        # Launch update script and exit
        if system == "Windows":
            subprocess.Popen(['cmd', '/c', 'start', '/min', script_path],
                           shell=True,
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:  # Linux
            # Use nohup and detach properly
            subprocess.Popen(['/bin/bash', script_path],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           start_new_session=True)

        # Give the script time to start
        sleep(0.5)

        # Exit the application
        exit_game()

    except HTTPError as e:
        print(f"\nHTTP Error: {e.code} - {e.reason}\033[K")
        print("Could not connect to update server.\033[K")
        input("\nPress Enter to return to menu...")
    except URLError as e:
        print(f"\nNetwork Error: {e.reason}\033[K")
        print("Could not connect to update server.\033[K")
        input("\nPress Enter to return to menu...")
    except Exception as e:
        print(f"\nError checking for updates: {e}\033[K")
        input("\nPress Enter to return to menu...")

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
            print(f"  > {option}\033[K")
        else:
            print(f"    {option}\033[K")

    print()
    print("  Use ↑/↓ arrows to navigate, Enter to select\033[K")


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


def tabbed_interface(tab_names, tab_functions, initial_tab=0):
    """
    Reusable tabbed interface system

    Args:
        tab_names: List of tab names (e.g., ["Ships", "Assembly"])
        tab_functions: List of functions to call for each tab. Each function should:
            - Take save_name and data as parameters
            - Return True to continue showing tabs, False to exit
        initial_tab: Starting tab index (default 0)

    Returns:
        None
    """
    current_tab = initial_tab

    while True:
        # Display tabs at top
        clear_screen()

        # Draw ASCII tabs
        tab_line = "  "
        underline = "  "

        for i, name in enumerate(tab_names):
            tab_width = len(name) + 4

            if i == current_tab:
                # Active tab
                tab_line += f"┌{'─' * (tab_width - 2)}┐ "
                underline += f"│ {name} │ "
            else:
                # Inactive tab
                tab_line += f"┌{'─' * (tab_width - 2)}┐ "
                underline += f"│ {name} │ "

        print(tab_line)
        print(underline)

        # Draw bottom line for active tab, close line for others
        bottom_line = "  "
        for i, name in enumerate(tab_names):
            tab_width = len(name) + 4
            if i == current_tab:
                bottom_line += f"└{'─' * (tab_width - 2)}┘─"
            else:
                bottom_line += f"└{'─' * (tab_width - 2)}┘ "

        # Fill rest of line
        bottom_line += "─" * (60 - len(bottom_line))
        print(bottom_line)
        print()

        # Show tab hints
        tab_hints = "  "
        for i, name in enumerate(tab_names):
            tab_hints += f"[{i+1}] {name}  "
        print(tab_hints)
        print()

        # Call the current tab's function
        # The function should handle its own display and return True to continue, False to exit
        result = tab_functions[current_tab]()

        if result is False:
            # Exit the tabbed interface
            return
        elif isinstance(result, int):
            # Switch to specific tab
            current_tab = result
        else:
            pass
            # Check for tab switch input
            # This will be handled within each tab function by returning a tab index


def default_data():
    """Return default game data structure"""
    return {
        "v": SAVE_VERSION_CODE,  # save version code.
        "player_name": "Player",
        "credits": 2500,
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
        "scanned_systems": [],  # List of systems that have been scanned for anomalies
        "manufacturing_jobs": {},  # Active manufacturing jobs per station: {station_name: [job1, job2, ...]}
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


def load_crafting_data():
    """Load crafting recipe data from crafting.json"""
    with open(resource_path('crafting.json'), 'r') as f:
        crafting_data = json.load(f)
    return {recipe['name']: recipe for recipe in crafting_data}


def wrap_text(text, max_width=60):
    """Wrap text to a maximum width, breaking only at word boundaries"""
    if not text:
        return ""

    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        word_length = len(word)
        # +1 for the space before the word (except for first word)
        space_needed = word_length + (1 if current_line else 0)

        if current_length + space_needed <= max_width:
            current_line.append(word)
            current_length += space_needed
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length

    if current_line:
        lines.append(' '.join(current_line))

    return '\n'.join(lines)



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


def get_shield_regen(ship):
    """Get shield regen rate for a ship from ships.json or ship data

    Returns the shield regen stat from:
    1. Ship's 'shield_regen' field (for NPCs like drones/pirates)
    2. ships.json stats (for player ships)
    3. Default of 2 if not found
    """
    # Check if ship has shield_regen field (NPCs)
    if 'shield_regen' in ship:
        return ship['shield_regen']

    # Otherwise get from ships.json (player ships)
    stats = get_ship_stats(ship['name'])
    return stats.get('Shield Regen', 2)


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
        print(f"  {skill_name.title()} Skill Level Up! +{levels_gained} (now Level {current_level})\033[K")
        reset_color()

    xp_needed = xp_required_for_level(current_level)
    print(f"  +{xp_gained} {skill_name.title()} XP ({current_xp}/{xp_needed})\033[K")



def generate_enemy_fleet(security_level, data):
    """Generate an enemy fleet based on system security level and player progress

    Returns a fleet with either:
    - Small group: Single wave of weak enemies
    - Larger wave-based group: Multiple waves with escalating difficulty and command ships
    """
    combat_skill = data.get("skills", {}).get("combat", 0)

    # Determine encounter type based on security level
    # 75% small groups, 25% wave-based groups
    is_small_group = random.random() < 0.75

    if is_small_group:
        return generate_small_group(security_level, combat_skill)
    else:
        return generate_wave_group(security_level, combat_skill)


def generate_small_group(security_level, combat_skill):
    """Generate a small group of weak enemies (single wave)"""
    fleet = {
        "type": "",
        "size": 0,
        "ships": [],
        "total_firepower": 0,
        "warp_disruptor": False,
        "encounter_type": "small_group",
        "waves": None
    }

    skill_scaling = 1.0 + (combat_skill * 0.02)  # Weaker scaling for small groups

    match security_level:
        case "Secure":
            # 1-2 weak drones
            fleet["type"] = "Scattered Drones"
            fleet["size"] = random.randint(1, 2)
            base_hp = 20
            base_damage = 8
            ship_type = "Drone Scout"

        case "Contested" | "Unsecure":
            # 2-4 weak drones or 1-3 weak pirates
            if random.random() < 0.5:
                fleet["type"] = "Drone Patrol"
                fleet["size"] = random.randint(2, 4)
                base_hp = 35
                base_damage = 12
                ship_type = "Drone Fighter"
            else:
                fleet["type"] = "Pirate Scouts"
                fleet["size"] = random.randint(1, 3)
                base_hp = 60
                base_damage = 18
                ship_type = "Pirate Scout"

        case "Wild":
            # 4-6 drones or 3-5 pirates
            if random.random() < 0.5:
                fleet["type"] = "Drone Pack"
                fleet["size"] = random.randint(4, 6)
                base_hp = 45
                base_damage = 15
                ship_type = "Drone Fighter"
            elif random.random() < 0.5:
                fleet["type"] = "Drone Pack"
                fleet["size"] = random.randint(4, 6)
                base_hp = 45
                base_damage = 15
                ship_type = "Drone Fighter"
            elif random.random() < 0.5:
                fleet["type"] = "Pirate Patrol"
                fleet["size"] = random.randint(3, 5)
                base_hp = 75
                base_damage = 25
                ship_type = "Pirate Fighter"
            else:
                fleet["type"] = "Dread Pirate Patrol"
                fleet["size"] = random.randint(3, 4)
                base_hp = 115
                base_damage = 30
                ship_type = "Dread Pirate Fighter"


        case _:
            return None

    # Generate ships
    for i in range(fleet["size"]):
        max_hull = int(base_hp * skill_scaling)
        max_shield = int(base_hp * 0.4 * skill_scaling)

        # Determine shield regen based on ship type
        # Drones have shield_regen = 1, Pirates have shield_regen = 1.5
        if "Drone" in ship_type:
            shield_regen = 1.0
        elif "Pirate" in ship_type:
            shield_regen = 1.5
        else:
            shield_regen = 1.0  # Default for other types

        ship = {
            "name": f"{ship_type} #{i + 1}",
            "hull_hp": max_hull,
            "max_hull_hp": max_hull,
            "shield_hp": max_shield,
            "max_shield_hp": max_shield,
            "damage": int(base_damage * skill_scaling * random.uniform(0.9, 1.1)),
            "shield_regen": shield_regen
        }
        fleet["ships"].append(ship)
        fleet["total_firepower"] += ship["damage"]

    return fleet


def generate_wave_group(security_level, combat_skill):
    """Generate a wave-based enemy group with command ships"""
    fleet = {
        "type": "",
        "size": 0,
        "ships": [],
        "total_firepower": 0,
        "warp_disruptor": False,
        "encounter_type": "wave_group",
        "current_wave": 1,
        "total_waves": 0,
        "command_ship_wave": 0,
        "command_ship_type": "",
        "wave_progression": []  # Stores how many ships per wave
    }

    skill_scaling = 1.0 + (combat_skill * 0.025)

    match security_level:
        case "Secure":
            # Fireteams (2 waves) or Squadrons (3 waves)
            if random.random() < 0.6:
                # Fireteam: 2 waves + squad leader on wave 2
                fleet["type"] = "Drone Fireteam"
                fleet["total_waves"] = 2
                fleet["command_ship_wave"] = 2
                fleet["command_ship_type"] = "Squad Leader"
                fleet["wave_progression"] = [2, 3]  # 2 ships wave 1, 3 wave 2
                base_hp = 30
                base_damage = 10
                ship_type = "Drone"
            else:
                # Squadron: 3 waves + squad leader on wave 3
                fleet["type"] = "Drone Squadron"
                fleet["total_waves"] = 3
                fleet["command_ship_wave"] = 3
                fleet["command_ship_type"] = "Squad Leader"
                fleet["wave_progression"] = [2, 3, 4]
                base_hp = 35
                base_damage = 12
                ship_type = "Drone"

        case "Contested":
            # Squadrons (3 waves) or Fleets (4 waves)
            if random.random() < 0.5:
                # Squadron
                if random.random() < 0.5:
                    fleet["type"] = "Drone Squadron"
                    ship_type = "Drone"
                    base_hp = 50
                    base_damage = 15
                else:
                    fleet["type"] = "Pirate Squadron"
                    ship_type = "Pirate"
                    base_hp = 100
                    base_damage = 22
                fleet["total_waves"] = 3
                fleet["command_ship_wave"] = 3
                fleet["command_ship_type"] = "Squad Leader"
                fleet["wave_progression"] = [2, 3, 4]
            else:
                # Fleet: 4 waves + lieutenant/commander on wave 4
                if random.random() < 0.5:
                    fleet["type"] = "Drone Fleet"
                    ship_type = "Drone"
                    base_hp = 60
                    base_damage = 18
                    command_type = "Squad Lieutenant"
                else:
                    fleet["type"] = "Pirate Fleet"
                    ship_type = "Pirate"
                    base_hp = 110
                    base_damage = 28
                    command_type = "Squad Commander"
                fleet["total_waves"] = 4
                fleet["command_ship_wave"] = 4
                fleet["command_ship_type"] = command_type
                fleet["wave_progression"] = [2, 3, 4, 5]
                disruptor_chance = 0.3 if "Pirate" in fleet["type"] else 0.0
                if random.random() < disruptor_chance:
                    fleet["warp_disruptor"] = True

        case "Unsecure":
            # Squadrons (3 waves) or Fleets (4 waves)
            if random.random() < 0.4:
                # Squadron
                if random.random() < 0.5:
                    fleet["type"] = "Drone Squadron"
                    ship_type = "Drone"
                    base_hp = 65
                    base_damage = 20
                else:
                    fleet["type"] = "Pirate Squadron"
                    ship_type = "Pirate"
                    base_hp = 120
                    base_damage = 30
                fleet["total_waves"] = 3
                fleet["command_ship_wave"] = 3
                fleet["command_ship_type"] = "Squad Leader"
                fleet["wave_progression"] = [3, 4, 5]
            else:
                # Fleet: 4 waves + lieutenant/commander on wave 4
                if random.random() < 0.5:
                    fleet["type"] = "Drone Fleet"
                    ship_type = "Drone"
                    base_hp = 75
                    base_damage = 24
                    command_type = "Squad Lieutenant"
                else:
                    fleet["type"] = "Pirate Fleet"
                    ship_type = "Pirate"
                    base_hp = 130
                    base_damage = 35
                    command_type = "Squad Commander"
                fleet["total_waves"] = 4
                fleet["command_ship_wave"] = 4
                fleet["command_ship_type"] = command_type
                fleet["wave_progression"] = [3, 4, 5, 6]
                disruptor_chance = 0.4 if "Pirate" in fleet["type"] else 0.0
                if random.random() < disruptor_chance:
                    fleet["warp_disruptor"] = True

        case "Wild":
            # Fleets (4 waves) or Armadas (5 waves)
            if random.random() < 0.4:
                # Fleet: 4 waves
                if random.random() < 0.5:
                    fleet["type"] = "Drone Fleet"
                    ship_type = "Drone"
                    base_hp = 80
                    base_damage = 28
                    command_type = "Squad Lieutenant"
                else:
                    fleet["type"] = "Pirate Fleet"
                    ship_type = "Pirate"
                    base_hp = 150
                    base_damage = 40
                    command_type = "Squad Commander"
                fleet["total_waves"] = 4
                fleet["command_ship_wave"] = 4
                fleet["command_ship_type"] = command_type
                fleet["wave_progression"] = [4, 5, 6, 7]
                disruptor_chance = 0.5 if "Pirate" in fleet["type"] else 0.0
                if random.random() < disruptor_chance:
                    fleet["warp_disruptor"] = True
            else:
                # Armada: 5 waves + commander/captain on wave 5
                if random.random() < 0.5:
                    fleet["type"] = "Drone Armada"
                    ship_type = "Drone"
                    base_hp = 85
                    base_damage = 32
                    command_type = "Commander"
                else:
                    fleet["type"] = "Pirate Armada"
                    ship_type = "Pirate"
                    base_hp = 170
                    base_damage = 45
                    command_type = "Captain"
                fleet["total_waves"] = 5
                fleet["command_ship_wave"] = 5
                fleet["command_ship_type"] = command_type
                fleet["wave_progression"] = [4, 5, 6, 7, 8]
                disruptor_chance = 0.6 if "Pirate" in fleet["type"] else 0.0
                if random.random() < disruptor_chance:
                    fleet["warp_disruptor"] = True

        case _:
            # Default case (shouldn't happen in Core space)
            return None

    # Generate first wave ships
    # Store wave metadata for spawning subsequent waves
    fleet["wave_metadata"] = {
        "base_hp": base_hp,
        "base_damage": base_damage,
        "ship_type": ship_type,
        "skill_scaling": skill_scaling
    }
    generate_wave_ships(fleet, 1, base_hp, base_damage, ship_type, skill_scaling)

    return fleet


def generate_wave_ships(fleet, wave_num, base_hp, base_damage, ship_type, skill_scaling):
    """Generate ships for a specific wave"""
    num_ships = fleet["wave_progression"][wave_num - 1]

    # Is this the command ship wave?
    is_command_wave = (wave_num == fleet["command_ship_wave"])

    # Determine shield regen based on ship type
    # Drones have shield_regen = 1, Pirates have shield_regen = 1.5
    if "Drone" in ship_type:
        shield_regen = 1.0
    elif "Pirate" in ship_type:
        shield_regen = 1.5
    else:
        shield_regen = 1.0  # Default for other types

    for i in range(num_ships):
        # Last ship on command wave is the command ship
        is_command_ship = is_command_wave and (i == num_ships - 1)

        if is_command_ship:
            # Command ships are significantly stronger
            max_hull = int(base_hp * 2.5 * skill_scaling)
            max_shield = int(base_hp * 1.5 * skill_scaling)
            damage = int(base_damage * 2.0 * skill_scaling * random.uniform(0.95, 1.05))
            ship_name = f"{ship_type} {fleet['command_ship_type']}"
        else:
            max_hull = int(base_hp * skill_scaling)
            max_shield = int(base_hp * 0.5 * skill_scaling)
            damage = int(base_damage * skill_scaling * random.uniform(0.9, 1.1))
            ship_name = f"{ship_type} Fighter #{len(fleet['ships']) + 1}"

        ship = {
            "name": ship_name,
            "hull_hp": max_hull,
            "max_hull_hp": max_hull,
            "shield_hp": max_shield,
            "max_shield_hp": max_shield,
            "damage": damage,
            "is_command_ship": is_command_ship,
            "wave": wave_num,
            "shield_regen": shield_regen
        }
        fleet["ships"].append(ship)
        fleet["total_firepower"] += ship["damage"]
        fleet["size"] += 1


def spawn_next_wave(fleet):
    """Spawn the next wave of enemies for a wave-based encounter

    Returns True if a new wave was spawned, False if no more waves
    """
    if fleet.get("encounter_type") != "wave_group":
        return False

    if fleet["current_wave"] >= fleet["total_waves"]:
        return False

    # Move to next wave
    fleet["current_wave"] += 1

    # Get wave metadata
    metadata = fleet["wave_metadata"]
    generate_wave_ships(
        fleet,
        fleet["current_wave"],
        metadata["base_hp"],
        metadata["base_damage"],
        metadata["ship_type"],
        metadata["skill_scaling"]
    )

    return True


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
    print(" ⚠ HOSTILE CONTACT ⚠ \033[K")
    reset_color()
    print("=" * 60)
    print()
    print(f"  Fleet Type: {enemy_fleet['type']}\033[K")

    # Show wave info for wave-based groups
    if enemy_fleet.get("encounter_type") == "wave_group":
        print(f"  Encounter Type: Multi-wave assault\033[K")
        print(f"  Expected Waves: {enemy_fleet['total_waves']}\033[K")

    print(f"  Initial Ships: {len([s for s in enemy_fleet['ships'] if s.get('wave', 1) == 1])} ships\033[K")
    print(f"  Threat Level: ", end="")

    # Calculate threat level based on total firepower vs player ship
    player_ship = get_active_ship(data)
    max_hull = get_max_hull(player_ship)
    max_shield = get_max_shield(player_ship)
    threat_ratio = enemy_fleet["total_firepower"] / (max_hull + max_shield)

    if threat_ratio < 0.3:
        set_color("green")
        print("LOW\033[K")
    elif threat_ratio < 0.7:
        set_color("yellow")
        print("MODERATE\033[K")
    elif threat_ratio < 1.2:
        set_color("red")
        print("HIGH\033[K")
    else:
        set_color("red")
        set_color("blinking")
        print("EXTREME\033[K")
    reset_color()

    if enemy_fleet["warp_disruptor"]:
        print()
        set_color("red")
        print("  ⚠ WARP DISRUPTED ⚠\033[K")
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
    print(" ⚠ HOSTILE CONTACT ⚠ \033[K")
    reset_color()
    print("=" * 60)
    print()
    print(f"  Fleet Type: {enemy_fleet['type']}\033[K")

    if enemy_fleet.get("encounter_type") == "wave_group":
        print(f"  Encounter Type: Multi-wave assault\033[K")
        print(f"  Expected Waves: {enemy_fleet['total_waves']}\033[K")

    print(f"  Initial Ships: {len([s for s in enemy_fleet['ships'] if s.get('wave', 1) == 1])} ships\033[K")
    print(f"  Threat Level: ", end="")
    if threat_ratio < 0.3:
        print("LOW\033[K")
    elif threat_ratio < 0.7:
        print("MODERATE\033[K")
    elif threat_ratio < 1.2:
        print("HIGH\033[K")
    else:
        print("EXTREME\033[K")
    if enemy_fleet["warp_disruptor"]:
        print()
        print("  ⚠ WARP DISRUPTOR DETECTED ⚠\033[K")
    print()

    encounter_content = temp_buffer.getvalue()
    sys.stdout = old_stdout

    options = ["Fight!", "Attempt to Escape", "Ignore and Tank Damage"]
    choice = arrow_menu("What will you do?", options, previous_content + encounter_content)

    if choice == 0:
        # Fight
        result = combat_loop(enemy_fleet, system, save_name, data)
        music.play_ambiance()
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
        print("  ⚠ WARP DISRUPTOR DETECTED ⚠\033[K")
        print()
        print("  The enemy's warp disruption field prevents any escape!\033[K")
        print("  Your jump drive is completely disabled.\033[K")
        print()
        print("  You are forced into combat!\033[K")
        sleep(2)
        input("Press Enter to engage...")

        result = combat_loop(enemy_fleet, system, save_name, data, forced_combat=True)
        music.play_ambiance()
        return result

    # Base escape chance: 75%
    escape_chance = 0.75

    # Piloting skill increases escape chance
    escape_chance += min(piloting_skill * 0.05, 0.50)

    if random.random() < escape_chance:
        # Successful escape
        print("  Successfully escaped!\033[K")
        print()

        save_data(save_name, data)
        input("Press Enter to continue...")

        return "continue"
    else:
        # Failed escape - forced into combat
        print("  You reacted too slow!\033[K")
        print("  Enemy fleet has intercepted you!\033[K")
        print()
        input("Press Enter to engage in combat...")

        result = combat_loop(enemy_fleet, system, save_name, data, forced_combat=True)
        music.play_ambiance()
        return result


def ignore_enemies(enemy_fleet, system, save_name, data):
    """Ignore enemies and tank the damage"""
    clear_screen()
    title("IGNORING HOSTILE FLEET")
    print()

    player_ship = get_active_ship(data)

    print("  You continue on your course, ignoring the hostile fleet.\033[K")
    print("  They open fire on your ship!\033[K")
    print()
    sleep(1)

    # Calculate damage - 70% of total firepower
    total_damage = int(enemy_fleet["total_firepower"] * 0.7 * random.uniform(0.8, 1.2))

    print(f"  Incoming damage: {total_damage}\033[K")
    print()
    sleep(0.5)

    # Apply damage
    remaining_damage = total_damage

    if player_ship["shield_hp"] > 0:
        shield_damage = min(remaining_damage, player_ship["shield_hp"])
        player_ship["shield_hp"] -= shield_damage
        remaining_damage -= shield_damage
        max_shield = get_max_shield(player_ship)
        print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield} (-{shield_damage})\033[K")
        sleep(0.3)

    if remaining_damage > 0:
        player_ship["hull_hp"] -= remaining_damage
        max_hull = get_max_hull(player_ship)
        print(f"  Hull HP: {max(0, player_ship['hull_hp'])}/{max_hull} (-{remaining_damage})\033[K")
        sleep(0.3)

    print()

    if player_ship["hull_hp"] <= 0:
        print("  Your ship has been destroyed!\033[K")
        sleep(2.0)
        return "death"
    elif player_ship["hull_hp"] < get_max_hull(player_ship) * 0.2:
        set_color("red")
        print("  ⚠ WARNING: CRITICAL HULL DAMAGE ⚠\033[K")
        reset_color()
        print()

    print("  You've successfully passed through the hostile zone.\033[K")
    print()

    # No skill increase for ignoring
    save_data(save_name, data)
    input("Press Enter to continue...")
    return "continue"


def perform_evasive_maneuvers_turn(player_ship, piloting_skill, data):
    """Perform evasive maneuvers during a combat turn - recharge shields, skip attack"""
    clear_screen()
    title("MAKING EVASIVE MANEUVERS")
    print()

    print("  You make evasive maneuvers to avoid enemy fire, giving\033[K")
    print("  your shields time to recharge.\033[K")
    print()
    sleep(1)

    # Get ship stats
    ship_stats = get_ship_stats(player_ship['name'])
    ship_agility = ship_stats.get('Agility', 100)  # Default to 100 if not present
    max_shield = get_max_shield(player_ship)
    shield_regen_stat = get_shield_regen(player_ship)

    # Calculate shield recharge - base is shield_regen * 3
    base_recharge = shield_regen_stat * 3

    # Add bonus from agility (higher agility = better recharge)
    agility_bonus = (ship_agility / 100) * 10  # +10% per 100 agility

    # Add bonus from piloting skill
    piloting_bonus = piloting_skill * 2  # +2% per level

    # Add random factor (±20%)
    random_factor = random.uniform(0.8, 1.2)

    total_recharge = int(base_recharge * (1 + (agility_bonus + piloting_bonus) / 100) * random_factor)

    # Apply shield recharge
    old_shield = player_ship["shield_hp"]
    player_ship["shield_hp"] = min(player_ship["shield_hp"] + total_recharge, max_shield)
    actual_recharge = player_ship["shield_hp"] - old_shield

    if actual_recharge > 0:
        set_color("cyan")
        print(f"  Shields recharged: +{actual_recharge} HP\033[K")
        reset_color()
        print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield}\033[K")
    else:
        print("  Shields already at maximum capacity.\033[K")

    print()
    print("  You maintain evasive flight patterns to avoid incoming fire...\033[K")
    print()
    sleep(1)

    # Small piloting XP for using evasive maneuvers
    add_skill_xp(data, "piloting", 3)

    input("Press Enter to continue...")


def get_numpad_key(timeout=0.05):
    """Get numpad key press (1-9) with timeout

    Returns:
        int: Numpad number (4-9 as integers) or regular keys 1-9 for movement
        str: ' ' (space), 'tab', '1', '2', '3', 'q', 'e', 'esc', 'up', 'down', 'left', 'right' for special keys
    """
    if os.name == 'nt':  # Windows
        import msvcrt
        start = time()
        while time() - start < timeout:
            if msvcrt.kbhit():
                key = msvcrt.getch()

                # Check for special keys first
                if key == b'\x1b':  # Escape
                    return 'esc'
                elif key == b'\t':  # Tab
                    return 'tab'
                elif key == b' ':  # Space bar
                    return ' '
                elif key == b'\x00' or key == b'\xe0':  # Arrow or numpad
                    key2 = msvcrt.getch()
                    # Arrow keys
                    arrow_map = {
                        b'H': 'up',
                        b'P': 'down',
                        b'K': 'left',
                        b'M': 'right',
                    }
                    if key2 in arrow_map:
                        return arrow_map[key2]
                    # Numpad keys with NumLock on
                    numpad_map = {
                        b'O': 1, b'P': 2, b'Q': 3,  # Bottom row
                        b'K': 4, b'L': 5, b'M': 5,  # Middle row
                        b'G': 7, b'H': 8, b'I': 9,  # Top row
                    }
                    if key2 in numpad_map:
                        return numpad_map[key2]
                else:
                    # Regular number keys and letters
                    try:
                        char = key.decode('utf-8')
                        if char in '123456789':
                            if char in '123':  # These can be movement keys too
                                return char
                            return int(char)
                        elif char.lower() in 'qe':  # Firing mode keys (Q=focus, E=spread)
                            return char.lower()
                    except:
                        pass
            sleep(0.001)  # Check every 1ms for maximum responsiveness
        return None
    else:  # Unix/Linux/Mac
        import select
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # Disable canonical mode and echo WITHOUT touching OPOST output processing.
            # tty.setraw() would also clear OPOST, which breaks \n -> \r\n translation
            # and destroys the combat UI layout.  We only need raw *input*.
            new_settings = termios.tcgetattr(fd)
            new_settings[3] &= ~(termios.ICANON | termios.ECHO)  # lflags: raw input only
            new_settings[6][termios.VMIN] = 0   # non-blocking read
            new_settings[6][termios.VTIME] = 0  # no read timeout (select handles timing)
            # TCSANOW: apply immediately, no drain latency on every frame
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)

            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # Escape sequence
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.1)  # Increased timeout for Linux
                    if rlist:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            # Arrow key sequences - check if third char is available
                            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)  # Increased timeout
                            if rlist:
                                ch3 = sys.stdin.read(1)
                                arrow_map = {
                                    'A': 'up',
                                    'B': 'down',
                                    'C': 'right',
                                    'D': 'left',
                                }
                                if ch3 in arrow_map:
                                    return arrow_map[ch3]
                            return None  # Ignore other escape sequences
                    return 'esc'
                elif ch == '\t':
                    return 'tab'
                elif ch == ' ':  # Space bar
                    return ' '
                elif ch in '123456789':
                    if ch in '123':  # These can be movement keys too
                        return ch
                    return int(ch)
                elif ch.lower() in 'qe':  # Firing mode keys (Q=focus, E=spread)
                    return ch.lower()
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, old_settings)


def calculate_arrow_position(current_pos, arrow_direction):
    """Calculate new position based on arrow key press

    Grid layout (like numpad):
    7 8 9
    4 5 6
    1 2 3

    Args:
        current_pos: Current position (1-9)
        arrow_direction: 'up', 'down', 'left', 'right'

    Returns:
        New position (1-9), or current_pos if movement not possible
    """
    # Define grid as rows (bottom to top)
    grid = [
        [1, 2, 3],  # Bottom row
        [4, 5, 6],  # Middle row
        [7, 8, 9],  # Top row
    ]

    # Find current position in grid
    current_row = None
    current_col = None
    for row_idx, row in enumerate(grid):
        if current_pos in row:
            current_row = row_idx
            current_col = row.index(current_pos)
            break

    if current_row is None:
        return current_pos

    # Calculate new position based on arrow direction
    new_row = current_row
    new_col = current_col

    if arrow_direction == 'up':
        new_row = min(current_row + 1, 2)  # Can't go above top row
    elif arrow_direction == 'down':
        new_row = max(current_row - 1, 0)  # Can't go below bottom row
    elif arrow_direction == 'left':
        new_col = max(current_col - 1, 0)  # Can't go past left edge
    elif arrow_direction == 'right':
        new_col = min(current_col + 1, 2)  # Can't go past right edge

    return grid[new_row][new_col]


def strip_ansi(text):
    """Remove ANSI color codes from text for length calculation"""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def box_line(content, width=60, border_color=None, text_color=None):
    """Format a line to fit exactly in a box with proper padding

    Args:
        content: The text content (may contain ANSI codes)
        width: Interior width of the box (default 60 for standard box)
        border_color: Color for the border characters (║) - optional
        text_color: Color for the text content - optional

    Returns:
        Formatted string: "║  content..." with proper padding "  ║"
    """
    # Strip ANSI codes to calculate actual display length
    display_text = strip_ansi(content)
    actual_length = len(display_text)

    # Calculate padding needed (account for the 2 spaces at start: "║  ")
    padding_needed = width - actual_length - 2

    # Apply text color if specified
    formatted_content = content
    if text_color:
        formatted_content = f"{get_color(text_color)}{content}{get_color('reset')}"

    # Build the line with optional border color
    if border_color:
        line = f"{get_color(border_color)}║{get_color('reset')}"
        line += f"  {formatted_content}{' ' * padding_needed}"
        line += f"{get_color(border_color)}║{get_color('reset')}"
        return line
    else:
        return f"║  {formatted_content}{' ' * padding_needed}║"


def is_warship(ship_name):
    """Check if a ship is a warship (Corvette, Frigate, or Destroyer)"""
    ship_lower = ship_name.lower()
    if 'corvette' in ship_lower or 'frigate' in ship_lower or 'destroyer' in ship_lower:
        return True
    warship_names = ['infinity', 'radix', 'chevron']
    return any(name in ship_lower for name in warship_names)


def get_turret_count(ship_name):
    """Get number of turrets for a warship"""
    ship_lower = ship_name.lower()
    if 'corvette' in ship_lower or 'infinity' in ship_lower or 'radix' in ship_lower or 'chevron' in ship_lower:
        return 2
    elif 'frigate' in ship_lower:
        return 3
    elif 'destroyer' in ship_lower:
        return 4
    return 2


def calculate_movement_time(ship_agility, from_pos, to_pos):
    """Calculate time to move between grid positions based on agility"""
    from_row, from_col = (from_pos - 1) // 3, (from_pos - 1) % 3
    to_row, to_col = (to_pos - 1) // 3, (to_pos - 1) % 3
    distance = max(abs(to_row - from_row), abs(to_col - from_col))
    base_time = 0.5 if distance == 1 else 0.7 if distance == 2 else 1.0
    agility_multiplier = 1.5 - (ship_agility / 200.0)
    return base_time * agility_multiplier


class Projectile:
    """Represents an enemy projectile"""
    def __init__(self, target_position, speed=1.0):
        self.target_position = target_position
        self.speed = speed
        self.progress = 0.0

    def update(self, delta_time):
        """Update projectile position"""
        self.progress += delta_time * self.speed
        return self.progress >= 1.0


class Turret:
    """Represents a warship turret"""
    def __init__(self, turret_id, cooldown=2.5):
        self.turret_id = turret_id
        self.cooldown = cooldown
        self.time_until_ready = 0
        self.target = None

    def update(self, delta_time):
        if self.time_until_ready > 0:
            self.time_until_ready -= delta_time

    def can_fire(self):
        return self.time_until_ready <= 0

    def fire(self):
        self.time_until_ready = self.cooldown


def combat_loop(enemy_fleet, system, save_name, data, forced_combat=False):
    """Main real-time combat system"""
    return realtime_combat_loop(enemy_fleet, system, save_name, data, forced_combat)


def generate_projectiles(alive_enemies, difficulty_multiplier=1.0):
    """Generate projectiles for the incoming fire phase"""
    projectiles = []
    num_projectiles = min(len(alive_enemies), int(5 * difficulty_multiplier))

    for _ in range(num_projectiles):
        target_pos = random.randint(1, 9)
        speed = random.uniform(5, 7.5)
        projectiles.append(Projectile(target_pos, speed))

    return projectiles


def draw_dodge_arena(player_pos, projectiles, combo, time_remaining):
    """Draw the dodging arena with projectiles"""
    # Move cursor to home position without clearing - prevents flashing
    print("\033[H", end="", flush=True)
    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("INCOMING ENEMY FIRE - DODGE!", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")
    print(box_line("", 60) + "\033[K")

    positions = [7, 8, 9, 4, 5, 6, 1, 2, 3]

    for i in range(3):
        row_content = " "
        for j in range(3):
            pos = positions[i * 3 + j]
            if pos == player_pos:
                set_color("green")
                row_content += "[★]"
                reset_color()
            else:
                row_content += f"[{pos}]"
            row_content += " "
        print(box_line(row_content, 60) + "\033[K")

    print(box_line("", 60) + "\033[K")
    print(box_line("━━━━━━━━━━ INCOMING PROJECTILES ━━━━━━━━━━━━", 60) + "\033[K")

    for i, proj in enumerate(projectiles[:3]):
        progress_bar = "█" * int(proj.progress * 10)
        arrow_display = f"{progress_bar}→"
        target_display = f"[{proj.target_position}]"
        spacing = " " * (15 - len(arrow_display))
        line_content = f"{arrow_display}{spacing}{target_display}"
        print(box_line(line_content, 60) + "\033[K")

    for _ in range(3 - min(len(projectiles), 3)):
        print(box_line("", 60) + "\033[K")

    print(box_line("", 60) + "\033[K")
    combo_display = f"COMBO: x{combo}"
    time_display = f"Time: {time_remaining:.1f}s"
    status_line = f"{combo_display:<25} {time_display:>31}"
    print(box_line(status_line, 60) + "\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line("[NUMPAD/ARROWS 1-9] Move", 60) + "\033[K")
    print("╚════════════════════════════════════════════════════════════╝\033[K")
    # Clear any remaining lines below (in case screen was larger before)
    print("\033[J", end="", flush=True)


def dodge_phase(player_ship, alive_enemies, combo, data):
    """Execute the incoming fire/dodging phase"""
    ship_stats = get_ship_stats(player_ship['name'])
    ship_agility = ship_stats.get('Agility', 100)

    difficulty = 1.0 + (len(alive_enemies) / 10.0)
    projectiles = generate_projectiles(alive_enemies, difficulty)

    phase_duration = 8.0  # Increased from 3.5 to make combat slower and more readable
    player_pos = 5
    is_moving = False
    move_target = 5
    move_start_time = 0
    move_duration = 0

    start_time = time()
    last_update = start_time
    hits = 0

    while time() - start_time < phase_duration:
        current_time = time()
        delta_time = current_time - last_update
        last_update = current_time
        time_remaining = phase_duration - (current_time - start_time)

        completed_projectiles = []
        for proj in projectiles:
            if proj.update(delta_time):
                completed_projectiles.append(proj)

        for proj in completed_projectiles:
            if proj.target_position == player_pos:
                hits += 1
            projectiles.remove(proj)

        if is_moving:
            if current_time - move_start_time >= move_duration:
                player_pos = move_target
                is_moving = False

        draw_dodge_arena(player_pos, projectiles, combo, time_remaining)

        key = get_numpad_key(timeout=0.05)

        if key and not is_moving:
            if isinstance(key, int) and 1 <= key <= 9:
                if key != player_pos:
                    move_target = key
                    move_start_time = current_time
                    move_duration = calculate_movement_time(ship_agility, player_pos, key)
                    is_moving = True
            elif key in ['up', 'down', 'left', 'right']:
                # Arrow key movement - calculate new position relative to current
                new_pos = calculate_arrow_position(player_pos, key)
                if new_pos != player_pos:
                    move_target = new_pos
                    move_start_time = current_time
                    move_duration = calculate_movement_time(ship_agility, player_pos, new_pos)
                    is_moving = True

    total_projectiles = len(generate_projectiles(alive_enemies, difficulty))
    successful_dodges = total_projectiles - hits
    dodge_percent = (successful_dodges / total_projectiles * 100) if total_projectiles > 0 else 100

    damage_per_hit = sum(enemy['damage'] for enemy in alive_enemies) / len(alive_enemies)
    damage_taken = int(damage_per_hit * hits)

    if hits == 0:
        new_combo = min(combo + 1, 4)
    elif dodge_percent >= 70:
        new_combo = combo
    else:
        new_combo = 1

    return new_combo, damage_taken, successful_dodges, total_projectiles


def assign_turret_targets(turrets, alive_enemies, assignment_mode="spread"):
    """Assign targets to turrets"""
    if assignment_mode == "focus":
        target = alive_enemies[0] if alive_enemies else None
        for turret in turrets:
            turret.target = target
    elif assignment_mode == "priority":
        sorted_enemies = sorted(alive_enemies, key=lambda e: e['hull_hp'] + e['shield_hp'])
        for i, turret in enumerate(turrets):
            turret.target = sorted_enemies[i % len(sorted_enemies)] if sorted_enemies else None
    else:
        for i, turret in enumerate(turrets):
            turret.target = alive_enemies[i % len(alive_enemies)] if alive_enemies else None


def apply_damage_to_enemy(enemy, damage):
    """Apply damage to an enemy ship"""
    if enemy['shield_hp'] > 0:
        shield_damage = min(damage, enemy['shield_hp'])
        enemy['shield_hp'] -= shield_damage
        damage -= shield_damage
    if damage > 0:
        enemy['hull_hp'] = max(0, enemy['hull_hp'] - damage)


def apply_damage_to_ship(ship, damage):
    """Apply damage to player ship"""
    if ship['shield_hp'] > 0:
        shield_damage = min(damage, ship['shield_hp'])
        ship['shield_hp'] -= shield_damage
        damage -= shield_damage
    if damage > 0:
        ship['hull_hp'] = max(0, ship['hull_hp'] - damage)


def manual_fire_phase(player_ship, alive_enemies, combo, data):
    """Manual fire phase for regular ships - hold SPACE to charge and fire

    Returns:
        tuple: (total_damage_dealt, xp_earned)
    """
    phase_duration = 10.0  # 10 seconds to fire - increased for better readability

    print("\033[H", end="", flush=True)
    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("WEAPONS READY - FIRE!", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line("HOLD [SPACE] TO FIRE WEAPONS", 60) + "\033[K")
    print(box_line("", 60) + "\033[K")

    ship_stats = get_ship_stats(player_ship['name'])
    base_dps = ship_stats.get('DPS', 120)

    # Charge system
    charge_level = 0.0  # 0.0 to 1.0
    charge_rate = 0.3   # Charge per second when holding space
    is_space_held = False

    start_time = time()
    last_update = start_time
    shots_fired = []

    while time() - start_time < phase_duration:
        current_time = time()
        delta_time = current_time - last_update
        last_update = current_time
        time_remaining = phase_duration - (current_time - start_time)

        # Check for space key being held
        is_space_held = False

        if os.name == 'nt':  # Windows
            import msvcrt
            # On Windows, check if space is currently held by checking the buffer repeatedly
            if msvcrt.kbhit():
                test_key = msvcrt.getch()
                if test_key == b' ':
                    is_space_held = True
                    # Keep checking if more space keys are in buffer (indicates holding)
                    while msvcrt.kbhit():
                        extra = msvcrt.getch()
                        if extra == b' ':
                            is_space_held = True
        else:  # Unix/Linux/Mac
            # For Unix, use get_numpad_key which reads from stdin
            key = get_numpad_key(timeout=0.01)
            if key == ' ':
                is_space_held = True

        # Update charge
        if is_space_held:
            charge_level = min(1.0, charge_level + (charge_rate * delta_time))

        # Auto-fire when fully charged
        if charge_level >= 1.0:
            # Fire at target
            targets = alive_enemies[:min(4, len(alive_enemies))]
            if targets:
                target = random.choice([t for t in targets if t['hull_hp'] > 0])
                if target:
                    damage = int(base_dps * 0.3 * combo * random.uniform(0.9, 1.1))
                    apply_damage_to_enemy(target, damage)
                    shots_fired.append((target['name'], damage))
                    charge_level = 0.0  # Reset charge

        # Draw UI
        print("\033[H", end="", flush=True)
        print("╔════════════════════════════════════════════════════════════╗\033[K")
        print(box_line("WEAPONS READY - FIRE!", 60) + "\033[K")
        print("╠════════════════════════════════════════════════════════════╣\033[K")
        print(box_line("", 60) + "\033[K")

        # Charge bar
        charge_bar_width = 40
        filled = int(charge_level * charge_bar_width)
        empty = charge_bar_width - filled
        charge_bar = "█" * filled + "░" * empty
        charge_percent = int(charge_level * 100)

        if charge_level >= 1.0:
            set_color("yellow")
            print(box_line(f"CHARGE: {charge_bar} {charge_percent}% FIRING!", 60) + "\033[K")
            reset_color()
        else:
            print(box_line(f"CHARGE: {charge_bar} {charge_percent}%", 60) + "\033[K")

        print(box_line("", 60) + "\033[K")
        print(box_line("HOLD [SPACE] TO CHARGE WEAPONS", 60) + "\033[K")
        print(box_line("", 60) + "\033[K")

        # Show recent hits
        recent_shots = shots_fired[-3:]
        for shot_name, shot_dmg in recent_shots:
            set_color("yellow")
            print(box_line(f"➤ Hit {shot_name[:30]} for {shot_dmg} dmg!", 60) + "\033[K")
            reset_color()

        for _ in range(3 - len(recent_shots)):
            print(box_line("", 60) + "\033[K")

        print(box_line("", 60) + "\033[K")
        print(box_line(f"Time remaining: {time_remaining:.1f}s", 60) + "\033[K")
        print(box_line("", 60) + "\033[K")
        print("╚════════════════════════════════════════════════════════════╝\033[K")
        # Clear any remaining lines
        print("\033[J", end="", flush=True)

        sleep(0.05)

    # Calculate total damage
    total_damage = sum(dmg for _, dmg in shots_fired)
    xp_earned = len(shots_fired) * 3 * combo

    return total_damage, xp_earned


def auto_fire_phase(player_ship, alive_enemies, combo, data, turrets=None, assignment_mode="spread"):
    """Execute the auto-fire phase"""
    phase_duration = 6.0  # Increased from 2.0 to make combat slower and more readable

    print("\033[H", end="", flush=True)
    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("AUTO-FIRE PHASE", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")

    total_damage = 0

    if turrets:
        print(box_line("", 60) + "\033[K")
        print(box_line(f"TURRET OPERATIONS - Mode: {assignment_mode.upper()}", 60))
        print(box_line("", 60) + "\033[K")

        assign_turret_targets(turrets, alive_enemies, assignment_mode)

        start_time = time()
        last_update = start_time

        while time() - start_time < phase_duration:
            current_time = time()
            delta_time = current_time - last_update
            last_update = current_time

            for turret in turrets:
                turret.update(delta_time)

                if turret.can_fire() and turret.target and turret.target in alive_enemies:
                    turret.fire()

                    ship_stats = get_ship_stats(player_ship['name'])
                    base_dps = ship_stats.get('DPS', 100)
                    damage = int(base_dps * 0.4 * combo)

                    apply_damage_to_enemy(turret.target, damage)
                    total_damage += damage

                    target_name = turret.target['name'][:20]
                    print(box_line(f"Turret {turret.turret_id + 1}: Firing at {target_name} ({damage} dmg)", 60) + "\033[K")
                    sleep(0.3)

            sleep(0.1)
    else:
        # Regular ship combat - fire at targets then wait for full phase duration
        print(box_line("", 60) + "\033[K")
        print(box_line("Weapons system online... Targeting...", 60) + "\033[K")
        print(box_line("", 60) + "\033[K")

        start_time = time()

        sleep(0.5)

        ship_stats = get_ship_stats(player_ship['name'])
        base_dps = ship_stats.get('DPS', 120)
        damage_per_shot = int(base_dps * 0.6 * combo)

        targets = alive_enemies[:min(4, len(alive_enemies))]

        for target in targets:
            if target in alive_enemies:
                apply_damage_to_enemy(target, damage_per_shot)
                total_damage += damage_per_shot

                target_name = target['name'][:25]
                set_color("yellow")
                print(box_line(f"➤ Hit {target_name} for {damage_per_shot} damage!", 60) + "\033[K")
                reset_color()
                sleep(0.3)

        # Wait for remaining phase time
        elapsed = time() - start_time
        remaining_time = phase_duration - elapsed
        if remaining_time > 0:
            print(box_line("", 60) + "\033[K")
            print(box_line("Weapons cooling down...", 60) + "\033[K")
            sleep(remaining_time)

    print(box_line("", 60) + "\033[K")
    print("╚════════════════════════════════════════════════════════════╝\033[K")
    # Clear any remaining lines
    print("\033[J", end="", flush=True)

    xp_earned = int(5 * combo)
    return total_damage, xp_earned


def positioning_phase(alive_enemies, current_target_idx, assignment_mode):
    """Brief positioning phase for target switching and mode changes"""
    print("\033[H", end="", flush=True)
    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("TACTICAL POSITIONING", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line("Quick tactical moment...", 60) + "\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line("[TAB] Change targeting mode", 60) + "\033[K")
    print(box_line("[1] Focused Fire   [2] Scatter Shot", 60) + "\033[K")
    print(box_line("", 60) + "\033[K")
    print("╚════════════════════════════════════════════════════════════╝\033[K")
    # Clear any remaining lines
    print("\033[J", end="", flush=True)

    start_time = time()
    phase_duration = 3.0  # Increased from 1.5 to make combat slower
    new_assignment_mode = assignment_mode

    while time() - start_time < phase_duration:
        key = get_numpad_key(timeout=0.05)

        if key == 'tab':
            modes = ["spread", "focus", "priority"]
            current_idx = modes.index(assignment_mode)
            new_assignment_mode = modes[(current_idx + 1) % len(modes)]
            set_color("cyan")
            print(f"\n  Mode changed to: {new_assignment_mode.upper()}\033[K")
            reset_color()
            sleep(0.3)
            break
        elif key == '1':
            new_assignment_mode = "focus"
            set_color("cyan")
            print("\n  FOCUSED FIRE activated!\033[K")
            reset_color()
            sleep(0.3)
            break
        elif key == '2':
            new_assignment_mode = "spread"
            set_color("cyan")
            print("\n  SCATTER SHOT activated!\033[K")
            reset_color()
            sleep(0.3)
            break

    return current_target_idx, new_assignment_mode


def wave_transition(player_ship, enemy_fleet, data, save_name):
    """Handle wave transition with repair and retreat options"""
    print("\033[H", end="", flush=True)
    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("WAVE TRANSITION", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")
    print(box_line("", 60) + "\033[K")

    print(box_line("Wave cleared! Preparing for next wave...", 60, text_color="yellow") + "\033[K")
    print(box_line("", 60) + "\033[K")

    max_shield = get_max_shield(player_ship)
    max_hull = get_max_hull(player_ship)
    shield_percent = (player_ship['shield_hp'] / max_shield * 100) if max_shield > 0 else 0
    hull_percent = (player_ship['hull_hp'] / max_hull * 100) if max_hull > 0 else 0

    print(box_line(f"Shield: {player_ship['shield_hp']:>4}/{max_shield:<4} ({shield_percent:>3.0f}%)", 60))
    print(box_line(f"Hull:   {player_ship['hull_hp']:>4}/{max_hull:<4} ({hull_percent:>3.0f}%)", 60))
    print(box_line("", 60) + "\033[K")

    shield_regen_stat = get_shield_regen(player_ship)
    regen_amount = int(shield_regen_stat * 3)
    old_shield = player_ship['shield_hp']
    player_ship['shield_hp'] = min(player_ship['shield_hp'] + regen_amount, max_shield)
    actual_regen = player_ship['shield_hp'] - old_shield

    if actual_regen > 0:
        print(box_line(f"Shields regenerating... +{actual_regen} HP", 60, text_color="cyan") + "\033[K")

    print(box_line("", 60) + "\033[K")

    if hull_percent < 30:
        set_color("red")
        print(box_line("⚠ HULL INTEGRITY CRITICAL! ⚠", 60) + "\033[K")
        reset_color()
        print(box_line("[R] Retreat available", 60) + "\033[K")

    print(box_line("", 60) + "\033[K")
    print(box_line("Next wave incoming...", 60) + "\033[K")
    print(box_line("", 60) + "\033[K")
    print("╚════════════════════════════════════════════════════════════╝\033[K")
    # Clear any remaining lines
    print("\033[J", end="", flush=True)

    for i in range(3, 0, -1):
        print(f"\n  {i}...", end="", flush=True)

        start = time()
        while time() - start < 1.0:
            key = get_numpad_key(timeout=0.05)
            if key == 'r':
                set_color("yellow")
                print("\n\n  Retreating from combat...\033[K")
                reset_color()
                sleep(1)
                return "retreat"

    print("\n\033[K")
    return "continue"


def realtime_combat_loop(enemy_fleet, system, save_name, data, forced_combat=False, structure=None):
    """New unified real-time combat system matching original design"""
    update_discord_presence(data=data, context="combat")
    if enemy_fleet.get('type') == 'Crystalline Guardians':
        music.play_vex()
    else:
        music.play_battle()

    player_ship = get_active_ship(data)
    combat_skill = data.get("skills", {}).get("combat", 0)
    piloting_skill = data.get("skills", {}).get("piloting", 0)

    # Combat state
    combo = 1
    total_damage_dealt = 0
    total_xp_earned = 0
    current_target_idx = 0
    display_offset = 0  # For scrolling through enemy list when > 3 enemies
    firing_mode = "focus"  # focus or spread
    player_energy = 80
    max_energy = 80

    # Combat briefing
    print("\033[H", end="", flush=True)

    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("COMBAT ENGAGED!", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line(f"Enemy Fleet: {enemy_fleet['type']}", 60) + "\033[K")
    print(box_line(f"Enemy Count: {enemy_fleet['size']}", 60) + "\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line("CONTROLS:", 60) + "\033[K")
    print(box_line("- HOLD [SPACE] to rapid fire", 60) + "\033[K")
    print(box_line("- [NUMPAD/ARROWS 1-9] to move position", 60) + "\033[K")
    print(box_line("- [Q] Focus Fire  [E] Spread Fire", 60) + "\033[K")
    print(box_line("- [TAB] Cycle Target", 60) + "\033[K")
    print(box_line("- HOLD [ESC] to charge warp escape (60% energy)", 60) + "\033[K")
    print(box_line("", 60) + "\033[K")
    print(box_line("Press Enter to begin combat...", 60) + "\033[K")
    print("╚════════════════════════════════════════════════════════════╝\033[K")
    # Clear any remaining lines
    print("\033[J", end="", flush=True)
    input()

    # Main combat loop - each iteration is one combat round
    combat_ongoing = True
    while combat_ongoing:
        alive_enemies = [ship for ship in enemy_fleet["ships"] if ship["hull_hp"] > 0]

        if not alive_enemies:
            # Check for wave transitions
            if enemy_fleet.get("encounter_type") == "wave_group":
                if enemy_fleet["current_wave"] < enemy_fleet["total_waves"]:
                    result = wave_transition(player_ship, enemy_fleet, data, save_name)
                    if result == "retreat":
                        add_skill_xp(data, "combat", total_xp_earned)
                        add_skill_xp(data, "piloting", total_xp_earned // 2)
                        save_data(save_name, data)
                        return "retreat"
                    spawn_next_wave(enemy_fleet)
                    continue

            # Victory! Calculate credit rewards
            # Calculate battle difficulty based on enemy stats
            total_enemy_firepower = 0
            total_enemy_hp = 0
            for ship in enemy_fleet["ships"]:
                total_enemy_firepower += ship.get('damage', 10)
                total_enemy_hp += ship.get('max_hull_hp', 100) + ship.get('max_shield_hp', 0)

            # Base credits from enemies
            base_credits = enemy_fleet['size'] * 50  # 50 credits per enemy
            # Bonus for firepower
            firepower_bonus = int(total_enemy_firepower * 2)
            # Bonus for total HP
            hp_bonus = int(total_enemy_hp * 0.1)
            # Combo bonus
            combo_bonus = int(combo * 25)

            total_credits = base_credits + firepower_bonus + hp_bonus + combo_bonus

            # Award credits to player
            if 'credits' not in data:
                data['credits'] = 0
            data['credits'] += total_credits

            # Award XP to player
            combat_levels_gained = add_skill_xp(data, "combat", total_xp_earned)
            piloting_xp_earned = total_xp_earned // 2
            piloting_levels_gained = add_skill_xp(data, "piloting", piloting_xp_earned)
            save_data(save_name, data)

            # Gather post-XP skill state for display
            combat_level = data["skills"]["combat"]
            combat_xp = data["skills"]["combat_xp"]
            combat_xp_needed = xp_required_for_level(combat_level)
            piloting_level = data["skills"]["piloting"]
            piloting_xp = data["skills"]["piloting_xp"]
            piloting_xp_needed = xp_required_for_level(piloting_level)

            # Victory screen with proper color management
            print("\n", end="")
            set_color("green")
            print("╔════════════════════════════════════════════════════════════╗\033[K")
            reset_color()
            print(box_line("VICTORY!", 60, border_color="green") + "\033[K")
            set_color("green")
            print("╠════════════════════════════════════════════════════════════╣\033[K")
            reset_color()
            print(box_line(f"Total damage dealt: {total_damage_dealt}", 60, border_color="green") + "\033[K")
            print(box_line(f"Max combo reached: x{combo}", 60, border_color="green") + "\033[K")
            print(box_line("", 60, border_color="green") + "\033[K")
            print(box_line("REWARDS:", 60, border_color="green") + "\033[K")
            print(box_line(f"Base credits: {base_credits} CR", 60, border_color="green", text_color="yellow") + "\033[K")
            print(box_line(f"Firepower bonus: +{firepower_bonus} CR", 60, border_color="green", text_color="yellow") + "\033[K")
            print(box_line(f"Difficulty bonus: +{hp_bonus} CR", 60, border_color="green", text_color="yellow") + "\033[K")
            print(box_line(f"Combo bonus: +{combo_bonus} CR", 60, border_color="green", text_color="yellow") + "\033[K")
            print(box_line("─" * 58, 60, border_color="green") + "\033[K")
            print(box_line(f"TOTAL EARNED: {total_credits} CR", 60, border_color="green", text_color="green") + "\033[K")
            print(box_line(f"Credits: {data['credits']} CR", 60, border_color="green", text_color="green") + "\033[K")
            print(box_line("", 60, border_color="green") + "\033[K")
            print(box_line("EXPERIENCE:", 60, border_color="green") + "\033[K")
            if combat_levels_gained > 0:
                print(box_line(f"  ★ COMBAT LEVEL UP! ({combat_level - combat_levels_gained} -> {combat_level})", 60, border_color="green", text_color="cyan") + "\033[K")
            print(box_line(f"  +{total_xp_earned} Combat XP  -  Level {combat_level} ({combat_xp}/{combat_xp_needed})", 60, border_color="green", text_color="yellow") + "\033[K")
            if piloting_levels_gained > 0:
                print(box_line(f"  ★ PILOTING LEVEL UP! ({piloting_level - piloting_levels_gained} -> {piloting_level})", 60, border_color="green", text_color="cyan") + "\033[K")
            print(box_line(f"  +{piloting_xp_earned} Piloting XP  -  Level {piloting_level} ({piloting_xp}/{piloting_xp_needed})", 60, border_color="green", text_color="yellow") + "\033[K")
            set_color("green")
            print("╚════════════════════════════════════════════════════════════╝\033[K")
            reset_color()

            input("\nPress Enter to continue...")
            return "victory"

        # Run unified combat round
        result = unified_combat_round(
            player_ship, alive_enemies, combo, firing_mode,
            player_energy, max_energy, current_target_idx, display_offset, data, enemy_fleet
        )

        combo = result['combo']
        firing_mode = result['firing_mode']
        player_energy = result['energy']
        current_target_idx = result['target_idx']
        display_offset = result['display_offset']
        total_damage_dealt += result['damage_dealt']
        total_xp_earned += result['xp_earned']

        # Check for warp escape
        if result.get('retreat', False):
            add_skill_xp(data, "combat", total_xp_earned)
            add_skill_xp(data, "piloting", total_xp_earned // 2)
            save_data(save_name, data)
            return "retreat"

        # Check player death
        if player_ship['hull_hp'] <= 0:
            set_color("red")
            print("\n╔════════════════════════════════════════════════════════════╗\033[K")
            print(box_line("SHIP DESTROYED", 60) + "\033[K")
            print("╠════════════════════════════════════════════════════════════╣\033[K")
            print(box_line("Your ship has been obliterated...", 60) + "\033[K")
            print("╚════════════════════════════════════════════════════════════╝\033[K")
            reset_color()
            sleep(2)
            return "death"

    return "victory"


def unified_combat_round(player_ship, alive_enemies, combo, firing_mode, player_energy, max_energy, current_target_idx, display_offset, data, enemy_fleet):
    """Unified combat round with simultaneous dodging and firing"""

    # State variables
    player_pos = 5  # Center position
    is_moving = False
    move_target = 5
    move_start_time = 0
    move_duration = 0

    ship_stats = get_ship_stats(player_ship['name'])
    ship_agility = ship_stats.get('Agility', 100)
    base_dps = ship_stats.get('DPS', 120)

    # Warp escape system
    warp_charging = False
    warp_charge_level = 0.0  # 0.0 to 1.0
    warp_charge_rate = 0.5  # Charge per second
    warp_charge_required = 1.0  # Full charge needed
    warp_energy_cost_percent = 0.6  # 60% of current energy

    # Projectile system - scale with fleet size and power
    projectiles = []
    next_projectile_spawn = time() + 0.5  # First projectiles spawn after half second

    # Calculate fleet power and size for scaling
    fleet_size = len(alive_enemies)
    avg_enemy_damage = sum(enemy.get('damage', 50) for enemy in alive_enemies) / max(1, fleet_size)

    # Check if this is a crystalline fleet (they get special treatment)
    is_crystalline = enemy_fleet.get('type') == 'Crystalline Guardians'

    if is_crystalline:
        # Crystalline entities fire in bursts of 3 per entity
        projectile_spawn_interval = 0.8  # Slightly slower than normal
        max_active_projectiles = fleet_size * 3  # 3 projectiles per entity
        total_projectiles_to_spawn = fleet_size * 15  # 15 projectiles per entity total
    else:
        # Scale with fleet size: 1-3 ships = slow, 4-7 ships = medium, 8+ ships = fast
        if fleet_size <= 3:
            projectile_spawn_interval = 1.2
            max_active_projectiles = 3
            total_projectiles_to_spawn = 12
        elif fleet_size <= 7:
            projectile_spawn_interval = 0.6  # Faster spawning
            max_active_projectiles = 6
            total_projectiles_to_spawn = 20
        else:  # 8+ ships
            projectile_spawn_interval = 0.25  # 4 per second for large fleets
            max_active_projectiles = min(12, fleet_size)
            total_projectiles_to_spawn = min(40, fleet_size * 4)

    projectiles_spawned = 0

    # Combat tracking
    damage_dealt = 0
    xp_earned = 0
    hits_taken = 0
    shots_fired = 0

    # Fire rate limiting
    last_shot_time = 0
    shot_cooldown = 0.7  # Increased to 0.7 seconds between shots
    weapon_heat = 0.0  # Weapon heat system (0.0 to 1.0)
    heat_per_shot = 0.3  # Heat added per shot
    heat_decay_rate = 0.4  # Heat lost per second when not firing

    # Energy regen
    energy_regen_rate = 5.0  # per second
    energy_cost_per_shot = 2

    # Shield regen (HP per second, from ship's Shield Regen stat)
    shield_regen_rate = get_shield_regen(player_ship)  # HP per second
    shield_regen_accumulator = 0.0  # Tracks partial seconds

    start_time = time()
    last_update = start_time

    # Make sure we have valid target
    if current_target_idx >= len(alive_enemies):
        current_target_idx = 0

    # Combat round runs until all projectiles are cleared
    while True:
        current_time = time()
        delta_time = current_time - last_update
        last_update = current_time

        # Continuously check which enemies are still alive (HP > 0)
        # This allows us to detect mid-round when the last enemy dies
        alive_enemies = [ship for ship in alive_enemies if ship.get('hull_hp', 0) > 0 or ship.get('shield_hp', 0) > 0]
        alive_enemy_count = len(alive_enemies)

        # Validate target index after filtering - prevent index out of range crashes
        if alive_enemy_count > 0 and current_target_idx >= alive_enemy_count:
            current_target_idx = alive_enemy_count - 1  # Target the last remaining enemy

        # DYNAMIC PROJECTILE SYSTEM:
        # - If no enemies left, clear all projectiles and end phase immediately
        # - Fewer enemies = fewer max projectiles (scales down as you destroy ships)
        if alive_enemy_count == 0:
            projectiles.clear()
            projectiles_spawned = total_projectiles_to_spawn  # Stop spawning
            # End the round immediately
            break

        # Spawn new projectiles (only if enemies alive)
        if alive_enemy_count > 0 and projectiles_spawned < total_projectiles_to_spawn and current_time >= next_projectile_spawn:
            if is_crystalline:
                # Crystalline entities fire in bursts of 3 per entity
                scaled_max_projectiles = alive_enemy_count * 3
            else:
                # Scale max projectiles based on alive enemies (fewer enemies = fewer projectiles)
                scaled_max_projectiles = min(max_active_projectiles, max(1, alive_enemy_count))

            # Calculate how many projectiles to spawn this cycle
            if is_crystalline:
                # Crystalline: spawn 3 projectiles per entity at once
                projectiles_to_spawn = min(alive_enemy_count * 3, scaled_max_projectiles - len(projectiles))
            else:
                # Normal: spawn 1 projectile
                projectiles_to_spawn = 1 if len(projectiles) < scaled_max_projectiles else 0

            for _ in range(projectiles_to_spawn):
                if len(projectiles) >= scaled_max_projectiles:
                    break

                # 2/3 of projectiles should target the player's current position
                # 1/3 should be random
                if random.random() < 0.67:  # 67% chance to target player
                    target_pos = player_pos
                else:
                    target_pos = random.randint(1, 9)

                # Set projectile speed based on fleet type
                if is_crystalline:
                    speed = random.uniform(0.5, 0.8)  # x2 faster than normal
                else:
                    # Scale speed slightly with fleet size
                    base_speed = 0.4 if fleet_size <= 3 else 0.5 if fleet_size <= 7 else 0.6
                    speed = random.uniform(base_speed, base_speed + 0.3)

                projectiles.append(Projectile(target_pos, speed))
                projectiles_spawned += 1

            next_projectile_spawn = current_time + projectile_spawn_interval

        # Update projectiles
        completed_projectiles = []
        for proj in projectiles:
            if proj.update(delta_time):
                completed_projectiles.append(proj)

        # Update player movement
        if is_moving:
            if current_time - move_start_time >= move_duration:
                player_pos = move_target
                is_moving = False

        # Check hits
        for proj in completed_projectiles:
            if proj.target_position == player_pos:
                # Hit! Apply damage based on fleet power
                # Use average enemy damage but scale with fleet size and power
                avg_damage = sum(enemy['damage'] for enemy in alive_enemies) / len(alive_enemies)

                # Scale damage based on fleet size (more enemies = slightly more damage per hit)
                fleet_multiplier = 1.0 + (len(alive_enemies) - 1) * 0.1  # +10% per additional enemy
                fleet_multiplier = min(fleet_multiplier, 2.0)  # Cap at 2x

                # Crystalline entities do more damage
                if is_crystalline:
                    fleet_multiplier *= 1.5

                damage_taken = int(avg_damage * fleet_multiplier)
                apply_damage_to_ship(player_ship, damage_taken)
                hits_taken += 1

                # Break combo on hit
                combo = 1
            projectiles.remove(proj)

        # Check if phase is complete (no more projectiles and all spawned)
        if not projectiles and projectiles_spawned >= total_projectiles_to_spawn:
            break

        # Regenerate energy
        player_energy = min(max_energy, player_energy + energy_regen_rate * delta_time)

        # Regenerate player shields (Shield Regen HP per 2 seconds)
        shield_regen_accumulator += delta_time
        if shield_regen_accumulator >= 2.0:
            seconds_elapsed = int(shield_regen_accumulator)
            shield_regen_accumulator -= seconds_elapsed
            max_shield = get_max_shield(player_ship)
            if player_ship['shield_hp'] < max_shield:
                regen_amount = shield_regen_rate * seconds_elapsed
                player_ship['shield_hp'] = min(player_ship['shield_hp'] + regen_amount, max_shield)

        # Decay weapon heat when not firing
        weapon_heat = max(0.0, weapon_heat - heat_decay_rate * delta_time)

        # Get input with full frame-time window to reliably catch single presses
        key = get_numpad_key(timeout=0.033)  # Full 33ms window = 100% of frame time at 30 FPS

        # Check if ESC is being held for warp escape
        if key == 'esc':
            warp_charging = True
        else:
            # If ESC was released before full charge, reset warp charge
            if warp_charging and warp_charge_level < warp_charge_required:
                warp_charge_level = 0.0
            warp_charging = False

        # Update warp charge
        if warp_charging:
            warp_charge_level = min(warp_charge_required, warp_charge_level + warp_charge_rate * delta_time)

            # Check if warp is fully charged
            if warp_charge_level >= warp_charge_required:
                # Calculate energy cost
                energy_cost = player_energy * warp_energy_cost_percent

                if player_energy >= energy_cost:
                    # Deduct energy
                    player_energy -= energy_cost

                    # Warp escape chance - based on agility and remaining energy
                    base_success_chance = 0.7  # 70% base chance
                    agility_bonus = (ship_agility - 100) / 500.0  # ±0.2 based on agility
                    energy_bonus = (player_energy / max_energy) * 0.1  # Up to 10% bonus for high energy

                    success_chance = base_success_chance + agility_bonus + energy_bonus
                    success_chance = max(0.3, min(0.95, success_chance))  # Clamp between 30% and 95%

                    if random.random() < success_chance:
                        # SUCCESS! Escape combat
                        print("\033[H", end="", flush=True)
                        set_color("cyan")
                        print("╔════════════════════════════════════════════════════════════╗\033[K")
                        print(box_line("WARP SUCCESSFUL!", 60) + "\033[K")
                        print("╠════════════════════════════════════════════════════════════╣\033[K")
                        reset_color()
                        print(box_line("Your ship warps away to another planet.", 60) + "\033[K")
                        print(box_line(f"Energy consumed: {int(energy_cost)}/{max_energy}", 60) + "\033[K")
                        set_color("cyan")
                        print("╚════════════════════════════════════════════════════════════╝\033[K")
                        reset_color()
                        # Clear any remaining lines below
                        print("\033[J", end="", flush=True)
                        sleep(2)

                        # Return special retreat result with updated energy
                        return {
                            'combo': combo,
                            'firing_mode': firing_mode,
                            'energy': player_energy,
                            'target_idx': current_target_idx,
                            'display_offset': display_offset,
                            'damage_dealt': damage_dealt,
                            'xp_earned': xp_earned,
                            'retreat': True
                        }
                    else:
                        # FAILURE! Take damage and reset charge
                        warp_charge_level = 0.0
                        warp_charging = False

                        # Take some damage from failed warp attempt
                        failure_damage = sum(enemy['damage'] for enemy in alive_enemies) // 4
                        apply_damage_to_ship(player_ship, int(failure_damage))

                        print("\033[H", end="", flush=True)
                        set_color("red")
                        print("╔════════════════════════════════════════════════════════════╗\033[K")
                        print(box_line("WARP FAILURE!", 60) + "\033[K")
                        print("╠════════════════════════════════════════════════════════════╣\033[K")
                        reset_color()
                        print(box_line("Warp jump failed! You took additional damage!", 60) + "\033[K")
                        print(box_line(f"Damage taken: {int(failure_damage)}", 60) + "\033[K")
                        set_color("red")
                        print("╚════════════════════════════════════════════════════════════╝\033[K")
                        reset_color()
                        sleep(1.5)

                        combo = 1  # Break combo
                else:
                    # Not enough energy
                    warp_charge_level = 0.0
                    warp_charging = False

        # Process ALL key inputs immediately
        if key and not warp_charging:  # Don't process other inputs while charging warp
            # Movement keys (numpad or regular 1-9)
            if isinstance(key, int) and 1 <= key <= 9 and not is_moving:
                if key != player_pos:
                    move_target = key
                    move_start_time = current_time
                    move_duration = calculate_movement_time(ship_agility, player_pos, key)
                    is_moving = True
            elif isinstance(key, str) and key in '123456789' and not is_moving:
                pos = int(key)
                if pos != player_pos:
                    move_target = pos
                    move_start_time = current_time
                    move_duration = calculate_movement_time(ship_agility, player_pos, pos)
                    is_moving = True
            elif key in ['up', 'down', 'left', 'right'] and not is_moving:
                # Arrow key movement - calculate new position relative to current
                new_pos = calculate_arrow_position(player_pos, key)
                if new_pos != player_pos:
                    move_target = new_pos
                    move_start_time = current_time
                    move_duration = calculate_movement_time(ship_agility, player_pos, new_pos)
                    is_moving = True

            # Space to fire (check this separately)
            if key == ' ':
                # Check cooldown, energy, and weapon heat
                if (current_time - last_shot_time >= shot_cooldown and
                    player_energy >= energy_cost_per_shot and
                    weapon_heat < 1.0):  # Can't fire if overheated

                    if firing_mode == "focus":
                        # Bounds check for target index
                        if current_target_idx < len(alive_enemies):
                            target = alive_enemies[current_target_idx]
                            damage = int(base_dps * 0.04 * combo * random.uniform(0.9, 1.1))  # Halved from 0.08
                            apply_damage_to_enemy(target, damage)
                            damage_dealt += damage
                            shots_fired += 1
                    elif firing_mode == "spread":
                        num_targets = min(3, len(alive_enemies))
                        targets = random.sample(alive_enemies, num_targets)
                        for target in targets:
                            damage = int(base_dps * 0.025 * combo * random.uniform(0.9, 1.1))  # Halved from 0.05
                            apply_damage_to_enemy(target, damage)
                            damage_dealt += damage
                        shots_fired += 1

                    player_energy -= energy_cost_per_shot
                    weapon_heat = min(1.0, weapon_heat + heat_per_shot)  # Add heat
                    last_shot_time = current_time

            # Firing mode switches (Q/E)
            if isinstance(key, str):
                key_lower = key.lower()
                if key_lower == 'q':
                    firing_mode = "focus"
                elif key_lower == 'e':
                    firing_mode = "spread"

            # Tab to cycle targets and scroll display
            if key == 'tab':
                if alive_enemies:  # Only cycle if there are enemies
                    current_target_idx = (current_target_idx + 1) % len(alive_enemies)

                    # Update display_offset to keep targeted enemy visible (within 3-slot window)
                    # If target moves beyond the visible window, scroll the display
                    if current_target_idx < display_offset:
                        # Target scrolled up - adjust display to show it
                        display_offset = current_target_idx
                    elif current_target_idx >= display_offset + 3:
                        # Target scrolled down beyond visible window - scroll display down
                        display_offset = current_target_idx - 2  # Keep target in middle/bottom of window

        # Draw UI AFTER all input is processed
        draw_unified_combat_ui(
            player_ship, player_pos, alive_enemies, projectiles,
            combo, firing_mode, player_energy, max_energy,
            current_target_idx, current_time - start_time, weapon_heat, display_offset,
            warp_charge_level, is_moving
        )

        sleep(0.033)  # ~30 FPS - slower, more relaxed pace

    # Calculate XP and combo updates
    dodge_rate = 1.0 - (hits_taken / max(1, total_projectiles_to_spawn))

    if hits_taken == 0:
        combo = min(combo + 1, 5)
    elif dodge_rate >= 0.7:
        combo = max(1, combo)  # Maintain combo
    else:
        combo = 1

    xp_earned = int((shots_fired * 2 + (total_projectiles_to_spawn - hits_taken) * 3) * combo)

    # Brief results display
    print("\033[H", end="", flush=True)
    print("╔════════════════════════════════════════════════════════════╗\033[K")
    print(box_line("ROUND COMPLETE", 60) + "\033[K")
    print("╠════════════════════════════════════════════════════════════╣\033[K")
    print(box_line(f"Hits Taken: {hits_taken}/{total_projectiles_to_spawn}", 60) + "\033[K")
    print(box_line(f"Damage Dealt: {damage_dealt}", 60) + "\033[K")
    print(box_line(f"Combo: x{combo}", 60) + "\033[K")
    print("╚════════════════════════════════════════════════════════════╝\033[K")
    # Clear any remaining lines
    print("\033[J", end="", flush=True)
    sleep(1.5)

    return {
        'combo': combo,
        'firing_mode': firing_mode,
        'energy': player_energy,
        'target_idx': current_target_idx,
        'display_offset': display_offset,
        'damage_dealt': damage_dealt,
        'xp_earned': xp_earned
    }


def draw_unified_combat_ui(player_ship, player_pos, alive_enemies, projectiles,
                           combo, firing_mode, energy, max_energy, target_idx, elapsed_time, weapon_heat, display_offset=0,
                           warp_charge_level=0.0, is_moving=False):
    """Draw the unified combat UI matching original design

    Args:
        display_offset: Starting index for displaying enemies (for scrolling when > 3 enemies)
        warp_charge_level: Current warp drive charge level (0.0 to 1.0)
        is_moving: Whether the player is currently moving to a new position
    """
    print("\033[H", end="", flush=True)

    # Get ship status
    max_shield = get_max_shield(player_ship)
    max_hull = get_max_hull(player_ship)
    shield_hp = player_ship['shield_hp']
    hull_hp = player_ship['hull_hp']

    # Header
    print("╔" + "═" * 76 + "╗" + "\033[K")
    print("║ COMBAT ZONE" + " " * 64 + "║" + "\033[K")

    # Shield and Hull bars
    shield_bar = create_health_bar(shield_hp, max_shield, 12, "cyan")
    hull_bar = create_health_bar(hull_hp, max_hull, 12, "red")
    shield_text = f"Shield: {shield_bar} {shield_hp}/{max_shield}"
    hull_text = f"Hull: {hull_bar} {hull_hp}/{max_hull}"

    # Calculate visual lengths
    shield_visual = len(strip_ansi(shield_text))
    hull_visual = len(strip_ansi(hull_text))

    # Padding between shield and hull
    middle_padding = 4
    # Calculate end padding (accounting for leading space + shield + middle + hull)
    line_content_len = 1 + shield_visual + middle_padding + hull_visual
    end_padding = " " * (76 - line_content_len)

    print(f"║ {shield_text}    {hull_text}{end_padding}║\033[K")

    print("╠" + "═" * 76 + "╣" + "\033[K")
    print("║" + " " * 76 + "║" + "\033[K")

    # Grid and Enemy List side by side
    positions = [[7, 8, 9], [4, 5, 6], [1, 2, 3]]

    # Get list of positions being targeted by projectiles that are close to hitting
    # Only highlight when projectile is in the final 2/3 of travel
    targeted_positions = set(proj.target_position for proj in projectiles if proj.progress >= 1/3)

    for row_idx, row in enumerate(positions):
        # Grid - build without padding first
        grid_str = " "
        for pos in row:
            if pos == player_pos:
                # Check if player's position is also being targeted
                if pos in targeted_positions:
                    # RED BACKGROUND with green star - player is in danger!
                    grid_str += "\033[41m\033[32m[★]\033[0m"  # Red bg + green text + reset
                else:
                    # Just green star - safe position
                    set_color("green")
                    grid_str += "[★]"
                    reset_color()
            elif pos in targeted_positions:
                # Use direct ANSI code for red background (100% guaranteed to work)
                grid_str += "\033[41m[X]\033[0m"  # Red background + reset
            else:
                grid_str += f"[{pos}]"
            grid_str += " "

        # Calculate visual length of grid
        grid_visual_len = len(strip_ansi(grid_str))

        # Enemy list - display up to 3 enemies starting from display_offset
        enemy_str = ""
        display_idx = row_idx + display_offset  # Actual index in alive_enemies list

        if display_idx < len(alive_enemies):
            enemy = alive_enemies[display_idx]
            # Only show alive enemies (those with HP > 0)
            enemy_hp = enemy.get('hull_hp', 0) + enemy.get('shield_hp', 0)
            if enemy_hp > 0:
                enemy_name = enemy['name'][:20]
                indicator = " ⚠ TARGETING" if display_idx == target_idx else ""
                enemy_str = f" ┃ {enemy_name} HP: {enemy_hp}{indicator}"
            else:
                enemy_str = " ┃"  # Dead enemy, show empty
        else:
            enemy_str = " ┃"
            enemy_str = " ┃"

        # Pad grid to exactly 21 visual characters (including leading space)
        grid_padding = " " * (21 - grid_visual_len)

        # Calculate padding for end of line
        enemy_visual_len = len(enemy_str)
        line_padding = " " * (76 - 21 - enemy_visual_len)

        line = f"║{grid_str}{grid_padding}{enemy_str}{line_padding}║"
        print(line)

    print("║" + " " * 76 + "║" + "\033[K")

    # Incoming projectiles section
    incoming_header = " " + "─" * 15 + " INCOMING " + "─" * 15
    incoming_visual_len = len(incoming_header)
    incoming_padding = " " * (76 - incoming_visual_len)
    print(f"║{incoming_header}{incoming_padding}║\033[K")

    # Show up to 4 projectiles with progress bars
    visible_projectiles = sorted(projectiles, key=lambda p: p.progress, reverse=True)[:4]
    for i in range(4):
        if i < len(visible_projectiles):
            proj = visible_projectiles[i]
            progress_filled = int(proj.progress * 15)
            progress_bar = "━" * progress_filled + "━" * (15 - progress_filled)
            set_color("red")
            line_content = f" ║ ━━━> [{proj.target_position}]"
            reset_color()
            # Visual length is without ANSI codes
            content_visual_len = len(" ║ ━━━> [X]")  # Fixed length
            padding = " " * (76 - content_visual_len)
            print(f"║{line_content}{padding}║\033[K")
        else:
            print("║ ║" + " " * 74 + "║")

    print("║" + " " * 76 + "║" + "\033[K")

    # Target and Energy info
    if alive_enemies:
        # Defensive bounds check - ensure target_idx is valid
        if target_idx >= len(alive_enemies):
            target_idx = len(alive_enemies) - 1

        target = alive_enemies[target_idx]
        target_name = target['name'][:25]
        target_line = f" Target: {target_name}"
        target_padding = " " * (76 - len(target_line))
        print(f"║{target_line}{target_padding}║\033[K")

    energy_bar = create_health_bar(int(energy), max_energy, 15, "yellow")
    energy_text = f" Energy: {energy_bar} {int(energy)}/{max_energy}"
    energy_visual_len = len(strip_ansi(energy_text))
    energy_padding = " " * (76 - energy_visual_len)
    print(f"║{energy_text}{energy_padding}║\033[K")

    # Weapon heat bar (shows cooldown)
    heat_bar_color = "red" if weapon_heat >= 0.9 else "yellow" if weapon_heat >= 0.6 else "green"
    weapon_heat_bar = create_health_bar(int(weapon_heat * 100), 100, 15, heat_bar_color)
    heat_status = "OVERHEATED!" if weapon_heat >= 1.0 else "READY" if weapon_heat < 0.3 else "COOLING"
    heat_text = f" Weapons: {weapon_heat_bar} {heat_status}"
    heat_visual_len = len(strip_ansi(heat_text))
    heat_padding = " " * (76 - heat_visual_len)
    print(f"║{heat_text}{heat_padding}║\033[K")

    # Warp Drive charge bar
    if warp_charge_level > 0.0:
        warp_bar_color = "green" if warp_charge_level >= 1.0 else "yellow"
        warp_bar = create_health_bar(int(warp_charge_level * 100), 100, 15, warp_bar_color)
        warp_status = "READY!" if warp_charge_level >= 1.0 else "CHARGING..."
        warp_text = f" Warp Drive: {warp_bar} {warp_status}"
        warp_visual_len = len(strip_ansi(warp_text))
        warp_padding = " " * (76 - warp_visual_len)
        print(f"║{warp_text}{warp_padding}║\033[K")

    # Movement status
    if is_moving:
        set_color("yellow")
        move_text = " MANEUVERING..."
        reset_color()
        move_visual_len = len(strip_ansi(move_text))
        move_padding = " " * (76 - move_visual_len)
        print(f"║{move_text}{move_padding}║\033[K")

    print("║" + " " * 76 + "║" + "\033[K")

    # Controls line (no cooldown indicator needed anymore)
    set_color("cyan")
    controls = " [SPACE] Fire  [NUMPAD] Dodge  [Q/E] Mode  [TAB] Target  [ESC] Warp"
    reset_color()
    controls_visual_len = len(strip_ansi(controls))
    controls_padding = " " * (76 - controls_visual_len)
    print(f"║{controls}{controls_padding}║\033[K")

    print("╠" + "═" * 76 + "╣" + "\033[K")

    # Status bar
    mode_display = firing_mode.upper()
    mode_color = "cyan" if firing_mode == "focus" else "green"  # Focus is cyan, Spread is green

    status_base = f" Time: {elapsed_time:.1f}s | Combo: x{combo} | Mode: "
    set_color(mode_color)
    status_line = status_base + mode_display
    reset_color()

    status_visual_len = len(strip_ansi(status_line))
    status_padding = " " * (76 - status_visual_len)
    print(f"║{status_line}{status_padding}║\033[K")
    print("╚" + "═" * 76 + "╝" + "\033[K")
    # Clear any remaining lines
    print("\033[J", end="", flush=True)



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
    """Player attacks enemies with distributed damage (max 4 targets)"""
    clear_screen()
    title("FIRING WEAPONS")
    print()

    # Limit to 4 targets max
    num_targets = min(len(enemies), 4)
    targets = enemies[:num_targets]

    # Base damage - scales with combat skill
    base_damage = 40 + (combat_skill * 2)
    damage_per_enemy = base_damage // num_targets

    if len(enemies) > 4:
        print(f"  Engaging {num_targets} of {len(enemies)} targets...\033[K")
    else:
        print(f"  Distributing {base_damage} damage across {num_targets} targets...\033[K")
    print()
    sleep(0.5)

    for enemy in targets:
        # Random variance
        damage = int(damage_per_enemy * random.uniform(0.85, 1.15))
        apply_damage_to_enemy_verbose(enemy, damage)
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

    print(f"  Targeting {enemy['name']}...\033[K")
    print()
    sleep(0.5)

    apply_damage_to_enemy_verbose(enemy, damage)

    print()
    input("Press Enter to continue...")


def apply_damage_to_enemy_verbose(enemy, damage):
    """Apply damage to an enemy ship (OLD SYSTEM - VERBOSE)"""
    remaining_damage = damage

    # Damage shields first
    if enemy["shield_hp"] > 0:
        shield_damage = min(remaining_damage, enemy["shield_hp"])
        enemy["shield_hp"] -= shield_damage
        remaining_damage -= shield_damage
        print(f"  Hit {enemy['name']}'s shields for {shield_damage} damage!\033[K")

    # Then damage hull
    if remaining_damage > 0:
        enemy["hull_hp"] -= remaining_damage
        print(f"  Hit {enemy['name']}'s hull for {remaining_damage} damage!\033[K")

        if enemy["hull_hp"] <= 0:
            enemy["hull_hp"] = 0
            set_color("green")
            print(f"  {enemy['name']} DESTROYED!\033[K")
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
        print(f"     Shield damaged: -{shield_damage} HP\033[K")
        reset_color()

    # Then damage hull
    if remaining_damage > 0:
        player_ship["hull_hp"] -= remaining_damage
        set_color("red")
        print(f"     Hull damaged: -{remaining_damage} HP\033[K")
        reset_color()

        # Check if ship is destroyed
        if player_ship["hull_hp"] <= 0:
            player_ship["hull_hp"] = 0
            return True

    return False


def attempt_retreat_from_combat(enemy_fleet, turn, forced_combat, data):
    """Attempt to retreat during combat"""
    clear_screen()
    title("ATTEMPTING RETREAT")
    print()

    if forced_combat and turn < 2:
        print("  You cannot retreat yet!\033[K")
        print("  The enemy has you locked down.\033[K")
        print(f"  You must fight for at least 1 turn. (Turn {turn}/1)\033[K")
        print()
        input("Press Enter to continue...")
        return "impossible"

    # Warp disruptor prevents retreat for first 5 turns
    if enemy_fleet["warp_disruptor"] and turn < 6:
        print("  ⚠ WARP DISRUPTOR ACTIVE ⚠\033[K")
        print()
        print("  The enemy's warp disruption field prevents retreat!\033[K")
        print(f"  You must fight for at least 5 turns. (Turn {turn}/5)\033[K")
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
        print("  Warp disruptor is weakening, but still interfering!\033[K")
        print()

    print("  Charging jump drive...\033[K")
    sleep(1)
    print("  Calculating escape vector...\033[K")
    sleep(1)
    print("  Attempting to disengage...\033[K")
    sleep(1)

    if random.random() < retreat_chance:
        print()
        print("  Successfully retreated from combat!\033[K")
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
            print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield} (-{shield_damage})\033[K")

        if damage_taken > 0:
            player_ship["hull_hp"] -= damage_taken
            max_hull = get_max_hull(player_ship)
            print(f"  Hull HP: {max(0, player_ship['hull_hp'])}/{max_hull} (-{damage_taken})\033[K")

        print()
        input("Press Enter to continue...")

        if player_ship["hull_hp"] <= 0:
            return "death"
        return "success"
    else:
        print()
        print("  Retreat failed!\033[K")
        print("  You took some damage while attempting to jump away!\033[K")
        print()
        sleep(1)

        # Take damage from enemy's opportunity attack
        player_ship = get_active_ship(data)
        damage_taken = int(enemy_fleet["total_firepower"] * 0.5 * random.uniform(0.8, 1.2))

        print(f"  Incoming damage: {damage_taken}\033[K")
        print()

        if player_ship["shield_hp"] > 0:
            shield_damage = min(damage_taken, player_ship["shield_hp"])
            player_ship["shield_hp"] -= shield_damage
            damage_taken -= shield_damage
            max_shield = get_max_shield(player_ship)
            print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield} (-{shield_damage})\033[K")

        if damage_taken > 0:
            player_ship["hull_hp"] -= damage_taken
            max_hull = get_max_hull(player_ship)
            print(f"  Hull HP: {max(0, player_ship['hull_hp'])}/{max_hull} (-{damage_taken})\033[K")

        print()
        if player_ship['hull_hp'] > 0:
            print("  You remain engaged in combat.\033[K")
        else:
            print("  Your ship was destroyed in the attempt!\033[K")
        print()
        input("Press Enter to continue...")

        if player_ship["hull_hp"] <= 0:
            return "death"
        return "failed"


def show_detailed_combat_stats(player_ship, enemy_fleet, data):
    """Show detailed stats during combat"""
    clear_screen()
    title("DETAILED COMBAT STATISTICS")
    print()

    max_shield = get_max_shield(player_ship)
    max_hull = get_max_hull(player_ship)

    print("YOUR SHIP:\033[K")
    print(f"  Name: {player_ship.get('nickname', 'Unknown')}\033[K")
    print(f"  Type: {player_ship.get('name', 'Unknown').title()}\033[K")
    print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield}\033[K")
    print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull}\033[K")
    print()

    print("YOUR SKILLS:\033[K")
    combat_level = data['skills']['combat']
    combat_xp = data['skills'].get('combat_xp', 0)
    combat_xp_needed = xp_required_for_level(combat_level)
    print(f"  Combat: Level {combat_level} ({combat_xp}/{combat_xp_needed} XP)\033[K")
    print(f"    - Damage Bonus: +{combat_level * 2}\033[K")

    piloting_level = data['skills']['piloting']
    piloting_xp = data['skills'].get('piloting_xp', 0)
    piloting_xp_needed = xp_required_for_level(piloting_level)
    print(f"  Piloting: Level {piloting_level} ({piloting_xp}/{piloting_xp_needed} XP)\033[K")
    print(f"    - Evasion Chance: {min(piloting_level * 2, 25)}%\033[K")
    print()

    print("ENEMY FLEET:\033[K")
    print(f"  Type: {enemy_fleet['type']}\033[K")
    print(f"  Total Ships: {enemy_fleet['size']}\033[K")
    alive_count = sum(1 for ship in enemy_fleet['ships'] if ship['hull_hp'] > 0)
    print(f"  Remaining: {alive_count}\033[K")
    print(f"  Warp Disruptor: {'ACTIVE' if enemy_fleet['warp_disruptor'] else 'None'}\033[K")
    print()

    print("ENEMY SHIPS:\033[K")
    for ship in enemy_fleet['ships']:
        if ship['hull_hp'] > 0:
            print(f"  • {ship['name']}\033[K")
            print(f"    Shield: {ship['shield_hp']}/{ship['max_shield_hp']}\033[K")
            print(f"    Hull: {ship['hull_hp']}/{ship['max_hull_hp']}\033[K")
            print(f"    Damage: {ship['damage']}\033[K")

    print()
    input("Press Enter to return to combat...")


def generate_anomalies(system_name, system_security, all_systems_data=None):
    """Generate random anomalies for a star system based on security level

    Args:
        system_name: Name of the system to generate anomalies for
        system_security: Security level of the system
        all_systems_data: Optional dict of all systems data (for wormhole generation)
    """
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

    # Define rarity tiers
    # Common: 50% chance, Uncommon: 30% chance, Rare: 15% chance, Very Rare: 5% chance
    rarity_weights = {
        "Common": 50,
        "Uncommon": 30,
        "Rare": 15,
        "VeryRare": 5
    }

    # Anomaly rarities (applies to all security levels where they can spawn)
    anomaly_rarities = {
        "AT": "Common",
        "BF": "Common",
        "AL": "Uncommon",
        "CM": "Uncommon",
        "DH": "Uncommon",
        "SP": "Uncommon",
        "MT": "Uncommon",
        # WH handled specially below
        "AA": "Rare",
        "FO": "Rare",
        "AN": "Rare",
        "VX": "VeryRare"
    }

    # Build weighted pool based on security level and rarity
    # Each anomaly gets a weight based on its rarity
    weighted_pool = []

    # Define which anomalies can appear in each security level
    security_anomalies = {
        "Secure": ["AT", "AL", "CM", "BF", "SP"],
        "Contested": ["AT", "AL", "AA", "CM", "BF", "DH", "SP", "MT"],
        "Unsecure": ["AT", "AL", "AA", "CM", "BF", "DH", "SP", "MT"],
        "Wild": ["AT", "AL", "AA", "AN", "VX", "CM", "BF", "DH", "SP", "MT", "FO"],
    }

    # Add wormholes based on security level with different rarities
    if system_security == "Wild":
        security_anomalies["Wild"].append("WH")
    elif system_security == "Unsecure":
        security_anomalies["Unsecure"].append("WH")
    elif system_security == "Secure":
        security_anomalies["Secure"].append("WH")

    available_anomalies = security_anomalies.get(system_security, [])

    # Build weighted pool
    for anomaly_type in available_anomalies:
        if anomaly_type == "WH":
            # Wormhole rarity varies by security
            if system_security == "Wild":
                weight = rarity_weights["Uncommon"]
            elif system_security == "Unsecure":
                weight = rarity_weights["Rare"]
            else:  # Secure
                weight = rarity_weights["VeryRare"]
        else:
            rarity = anomaly_rarities.get(anomaly_type, "Common")
            weight = rarity_weights.get(rarity, rarity_weights["Common"])

        # Add the anomaly type 'weight' times to the pool
        weighted_pool.extend([anomaly_type] * weight)

    for _ in range(num_anomalies):
        if weighted_pool:
            anomaly_type = random.choice(weighted_pool)

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
                "scanned": False,
                "timestamp": current_time,
                "duration": duration,
            }

            # For wormholes, add additional data
            if anomaly_type == "WH":
                # Generate a unique ID for this wormhole pair
                anomaly["wormhole_id"] = str(uuid4())
                anomaly["is_origin"] = True  # This is the origin end
                anomaly["destination_system"] = None  # Will be set when we create the pair

            anomalies.append(anomaly)

    return anomalies


def manage_system_anomalies(save_name, data, system_name):
    """Manage anomalies for a system: clean up expired ones and generate new ones if needed"""
    current_time = time()
    system = system_data(system_name)
    system_security = system.get("SecurityLevel", "Secure")

    # Load all systems data for wormhole generation
    try:
        with open(resource_path('system_data.json'), 'r') as f:
            all_systems_data = json.load(f)
    except:
        all_systems_data = {}

    # Initialize anomalies dict if needed
    if "anomalies" not in data:
        data["anomalies"] = {}

    # Initialize system visit tracking
    if "last_system_visit" not in data:
        data["last_system_visit"] = {}

    # Initialize wormhole tracking
    if "wormhole_pairs" not in data:
        data["wormhole_pairs"] = {}

    # Get existing anomalies for this system
    existing_anomalies = data["anomalies"].get(system_name, [])

    # Clean up expired anomalies (older than their duration)
    cleaned_anomalies = []
    for anomaly in existing_anomalies:
        anomaly_age = current_time - anomaly.get("timestamp", current_time)
        duration = anomaly.get("duration", 48 * 3600)

        if anomaly_age < duration:
            cleaned_anomalies.append(anomaly)
        elif anomaly.get("type") == "WH":
            # If wormhole expired, remove it from both sides
            wormhole_id = anomaly.get("wormhole_id")
            if wormhole_id and wormhole_id in data["wormhole_pairs"]:
                del data["wormhole_pairs"][wormhole_id]

    # Get last visit time
    last_visit = data["last_system_visit"].get(system_name, 0)
    time_since_visit = current_time - last_visit

    # Generate new anomalies if enough time has passed (every 12 hours, capped at 48 hours)
    if last_visit == 0:
        # First visit - generate anomalies
        new_anomalies = generate_anomalies(system_name, system_security, all_systems_data)
        cleaned_anomalies.extend(new_anomalies)
    elif time_since_visit >= 12 * 3600:
        # Generate anomalies for each 12-hour period, capped at 48 hours
        periods_elapsed = min(int(time_since_visit / (12 * 3600)), 4)  # Cap at 4 periods (48 hours)

        for _ in range(periods_elapsed):
            new_anomalies = generate_anomalies(system_name, system_security, all_systems_data)
            cleaned_anomalies.extend(new_anomalies)

    # Process wormholes & create pairs
    for anomaly in cleaned_anomalies:
        if anomaly.get("type") == "WH" and anomaly.get("is_origin") and anomaly.get("destination_system") is None:
            # This is a new wormhole that needs a pair
            wormhole_id = anomaly.get("wormhole_id")

            # Choose a random destination system (any system except the current one, and no Core systems)
            possible_destinations = [s for s in all_systems_data.keys()
                                   if s != system_name and all_systems_data[s].get("SecurityLevel") != "Core"]
            if possible_destinations:
                destination_system = random.choice(possible_destinations)

                # Set destination for this wormhole
                anomaly["destination_system"] = destination_system

                # Create the paired wormhole in the destination system
                paired_wormhole = {
                    "type": "WH",
                    "visited": False,
                    "scanned": False,
                    "timestamp": anomaly["timestamp"],
                    "duration": anomaly["duration"],
                    "wormhole_id": wormhole_id,
                    "is_origin": False,  # This is the destination end
                    "destination_system": system_name  # Points back to origin
                }

                # Add the paired wormhole to the destination system
                if destination_system not in data["anomalies"]:
                    data["anomalies"][destination_system] = []
                data["anomalies"][destination_system].append(paired_wormhole)

                # Track the wormhole pair
                data["wormhole_pairs"][wormhole_id] = {
                    "system1": system_name,
                    "system2": destination_system,
                    "timestamp": anomaly["timestamp"],
                    "duration": anomaly["duration"]
                }

    # Update system anomalies
    data["anomalies"][system_name] = cleaned_anomalies

    # Update last visit time
    data["last_system_visit"][system_name] = current_time

    save_data(save_name, data)

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
        print("  You need a System Probe to scan for anomalies!\033[K")
        print()
        print("  System Probes can be purchased from the General Marketplace\033[K")
        print("  at most space stations.\033[K")
        print()
        input("Press Enter to continue...")
        return

    # Consume the probe
    data["inventory"]["System Probe"] -= 1
    if data["inventory"]["System Probe"] <= 0:
        del data["inventory"]["System Probe"]

    current_system = data["current_system"]

    # Scan animation
    print("  Deploying System Probe...\033[K")
    sleep(0.5)
    print("  Scanning...\033[K")
    for i in range(3):
        print("  .", end="", flush=True)
        sleep(0.3)
    print()
    print()
    sleep(0.3)

    # Manage anomalies (cleanup expired + generate new if needed)
    manage_system_anomalies(save_name, data, current_system)

    # Mark all current anomalies in this system as scanned
    anomalies = data.get("anomalies", {}).get(current_system, [])
    for anomaly in anomalies:
        anomaly["scanned"] = True

    # Also mark this system as having been scanned at least once
    if "scanned_systems" not in data:
        data["scanned_systems"] = []
    if current_system not in data["scanned_systems"]:
        data["scanned_systems"].append(current_system)

    # Display results
    clear_screen()
    title("SCAN RESULTS")
    print()
    print(f"  System: {current_system}\033[K")
    system = system_data(current_system)
    system_security = system.get("SecurityLevel", "Secure")
    print(f"  Security: {system_security}\033[K")
    print()

    if not anomalies:
        print("  No anomalies detected in this system.\033[K")
    else:
        print(f"  {len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} detected:\033[K")
        print()

        # Load system data for wormhole destinations
        try:
            with open(resource_path('system_data.json'), 'r') as f:
                all_systems_data = json.load(f)
        except:
            all_systems_data = {}

        for i, anomaly in enumerate(anomalies):
            visited_str = " (Visited)" if anomaly.get("visited") else ""
            anomaly_name = get_anomaly_name(anomaly['type'])

            # Show duration and destination for wormholes
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

                # Show destination if available
                dest_system = anomaly.get("destination_system", "Unknown")
                if dest_system != "Unknown" and dest_system in all_systems_data:
                    dest_security = all_systems_data[dest_system].get("SecurityLevel", "Unknown")
                    dest_color = get_security_color(dest_security)
                    dest_str = f" → {dest_color}{dest_system}{RESET_COLOR}"
                else:
                    dest_str = ""

                print(f"    [{i+1}] {anomaly_name}{duration_str}{dest_str}{visited_str}\033[K")
            else:
                print(f"    [{i+1}] {anomaly_name}{visited_str}\033[K")

    print()
    save_data(save_name, data)
    input("Press Enter to continue...")


def visit_anomalies_menu(save_name, data):
    """Menu to visit discovered anomalies in current system"""
    current_system = data["current_system"]

    # Check if system has been scanned
    if current_system not in data.get("scanned_systems", []):
        clear_screen()
        title("ANOMALIES")
        print()
        print("  No anomalies have been scanned in this system yet.\033[K")
        print("  Use a System Probe to scan for anomalies.\033[K")
        print()
        input("Press Enter to continue...")
        return

    if current_system not in data.get("anomalies", {}):
        clear_screen()
        title("ANOMALIES")
        print()
        print("  No anomalies have been scanned in this system yet.\033[K")
        print("  Use a System Probe to scan for anomalies.\033[K")
        print()
        input("Press Enter to continue...")
        return

    anomalies = data["anomalies"][current_system]

    # Filter to only show scanned anomalies
    scanned_anomalies = [a for a in anomalies if a.get("scanned", False)]

    if not scanned_anomalies:
        clear_screen()
        title("ANOMALIES")
        print()
        print("  No anomalies have been scanned in this system yet.\033[K")
        print("  Use a System Probe to scan for anomalies.\033[K")
        print()
        input("Press Enter to continue...")
        return

    while True:
        # Re-check current system in case of wormhole transit
        current_system = data["current_system"]

        # Check if we still have anomalies in this system
        if current_system not in data.get("anomalies", {}):
            # System changed or no anomalies - exit menu
            return

        anomalies = data["anomalies"].get(current_system, [])
        scanned_anomalies = [a for a in anomalies if a.get("scanned", False)]

        if not scanned_anomalies:
            # No more scanned anomalies - exit menu
            return

        clear_screen()
        title(f"ANOMALIES - {current_system}")
        print()
        print(f"  {len(scanned_anomalies)} scanned anomal{'y' if len(scanned_anomalies) == 1 else 'ies'}:\033[K")
        print()

        options = []
        for i, anomaly in enumerate(scanned_anomalies):
            visited_str = " (Visited)" if anomaly.get("visited") else ""
            options.append(f"{get_anomaly_name(anomaly['type'])}{visited_str}")
        options.append("Back")

        choice = arrow_menu("Select anomaly to visit:", options)

        if choice == len(scanned_anomalies):
            return

        # Store current system before visiting
        system_before_visit = data["current_system"]

        # Visit the selected anomaly
        visit_anomaly(save_name, data, scanned_anomalies[choice])

        # Check if system changed (wormhole transit)
        if data["current_system"] != system_before_visit:
            # Player used a wormhole - exit anomaly menu
            return


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
    elif anomaly_type == "WH":
        visit_wormhole(save_name, data, anomaly)
    else:
        clear_screen()
        title(anomaly_name.upper())
        print()
        print(f"  {anomaly_name} visit not yet implemented.\033[K")
        print()
        input("Press Enter to continue...")


def visit_wormhole(save_name, data, anomaly):
    """Visit and interact with a wormhole"""
    # Load system data
    try:
        with open(resource_path('system_data.json'), 'r') as f:
            all_systems_data = json.load(f)
    except:
        all_systems_data = {}

    current_system = data["current_system"]
    destination_system = anomaly.get("destination_system", "Unknown")

    while True:
        # Capture current screen for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        clear_screen()
        title("WORMHOLE")
        print()
        print("  You approach the wormhole... What a spectacular sight!\033[K")
        print("  Even the fabric of space-time appears distorted here.\033[K")
        print()

        # Calculate remaining time
        current_time = time()
        anomaly_age = current_time - anomaly.get("timestamp", current_time)
        duration = anomaly.get("duration", 48 * 3600)
        remaining_time = duration - anomaly_age

        # Show if already scanned
        if anomaly.get("wormhole_scanned", False):
            # Get destination security
            dest_security = all_systems_data.get(destination_system, {}).get("SecurityLevel", "Unknown")
            dest_color = get_security_color(dest_security)

            print(f"  Scan Data:\033[K")
            print(f"    Destination: {dest_color}{destination_system}{RESET_COLOR}\033[K")
            print(f"    Security Level: {dest_color}{dest_security}{RESET_COLOR}\033[K")

            # Format remaining time
            if remaining_time > 0:
                hours_left = int(remaining_time / 3600)
                if hours_left >= 24:
                    days_left = hours_left / 24
                    if days_left >= 7:
                        print(f"    Stability: ~{int(days_left/7)} week{'s' if int(days_left/7) != 1 else ''} remaining\033[K")
                    else:
                        print(f"    Stability: ~{int(days_left)} day{'s' if int(days_left) != 1 else ''} remaining\033[K")
                else:
                    print(f"    Stability: ~{hours_left} hour{'s' if hours_left != 1 else ''} remaining\033[K")
            else:
                print(f"    Stability: Collapsing soon!\033[K")
            print()


        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        options = []
        if not anomaly.get("wormhole_scanned", False):
            options.append("Scan Wormhole")
        options.append("Enter Wormhole")
        options.append("Leave")

        choice = arrow_menu("What do you want to do?", options, previous_content)

        # Handle choice based on dynamic menu
        scan_option_present = not anomaly.get("wormhole_scanned", False)

        if scan_option_present and choice == 0:
            # Scan wormhole (only available if not yet scanned)
            clear_screen()
            title("WORMHOLE SCAN")
            print()
            print("  Initiating deep-space scan...\033[K")
            sleep(0.5)
            print("  Analyzing gravitational distortions...\033[K")
            for i in range(3):
                print("  .", end="", flush=True)
                sleep(0.4)
            print()
            print()
            sleep(0.3)

            # Mark as scanned
            anomaly["wormhole_scanned"] = True
            save_data(save_name, data)

            # Get destination info
            dest_security = all_systems_data.get(destination_system, {}).get("SecurityLevel", "Unknown")
            dest_color = get_security_color(dest_security)

            print(f"  Scan complete!\033[K")
            print()
            print(f"  Destination: {dest_color}{destination_system}{RESET_COLOR}\033[K")
            print(f"  Security Level: {dest_color}{dest_security}{RESET_COLOR}\033[K")

            # Format remaining time
            if remaining_time > 0:
                hours_left = int(remaining_time / 3600)
                if hours_left >= 24:
                    days_left = hours_left / 24
                    if days_left >= 7:
                        print(f"  Estimated Stability: ~{int(days_left/7)} week{'s' if int(days_left/7) != 1 else ''}\033[K")
                    else:
                        print(f"  Estimated Stability: ~{int(days_left)} day{'s' if int(days_left) != 1 else ''}\033[K")
                else:
                    print(f"  Estimated Stability: ~{hours_left} hour{'s' if hours_left != 1 else ''}\033[K")
            else:
                set_color("red")
                print(f"  Warning: Wormhole is highly unstable!\033[K")
                reset_color()

            print()
            input("Press Enter to continue...")

        elif (scan_option_present and choice == 1) or (not scan_option_present and choice == 0):
            # Enter wormhole
            if destination_system == "Unknown" or destination_system not in all_systems_data:
                clear_screen()
                title("WORMHOLE")
                print()
                print("  Error: Unable to establish stable connection!\033[K")
                print()
                input("Press Enter to continue...")
                continue

            clear_screen()
            title("WORMHOLE TRANSIT")
            print()
            print("  Engaging wormhole transit sequence...\033[K")
            sleep(0.5)
            print("  Entering event horizon...\033[K")
            sleep(0.7)
            print("  Space-time displacement in progress...\033[K")
            print()
            for i in range(4):
                print("  .", end="", flush=True)
                sleep(0.5 + i * 0.25)
            print()
            sleep(0.5)

            # Check if player is docked
            if data.get("docked_at"):
                clear_screen()
                title("WORMHOLE")
                print()
                print("  Error: Cannot transit while docked!\033[K")
                print("         How did you even manage to attempt this?\033[K")
                print()
                input("Press Enter to continue...")
                continue

            # Travel to destination
            data["current_system"] = destination_system

            # Clear destination if it was the system we just reached
            if data.get("destination") == destination_system:
                data["destination"] = ""

            save_data(save_name, data)

            print()
            dest_security = all_systems_data.get(destination_system, {}).get("SecurityLevel", "Unknown")
            dest_color = get_security_color(dest_security)
            print(f"  Arrived at: {dest_color}{destination_system}{RESET_COLOR}\033[K")
            print(f"  Security Level: {dest_color}{dest_security}{RESET_COLOR}\033[K")
            print()
            input("Press Enter to continue...")

            # Update Discord presence
            update_discord_presence(data=data, context="traveling")
            return

        else:
            # Leave (last option in both cases)
            return


def mine_anomaly(save_name, data, anomaly):
    """Mine ores from an ore-bearing anomaly"""
    anomaly_type = anomaly["type"]
    anomaly_name = get_anomaly_name(anomaly_type)

    update_discord_presence(data=data, context="mining")

    # Vexnium anomalies get their own atmospheric track
    if anomaly_type == "VX":
        music.play_vex()

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
        print("  ⚠ WARNING: Crystalline entities detected!\033[K")
        print()
        print("  This anomaly is guarded by hostile crystalline life forms.\033[K")
        print("  They will attack if you attempt to mine here.\033[K")
        print()
        print("  Proceed with caution.\033[K")
        print()
        input("Press Enter to continue...")

    # Mining loop
    while asteroids:
        clear_screen()
        title(f"{anomaly_name.upper()} - MINING")
        print()
        print(f"  {len(asteroids)} asteroid{'s' if len(asteroids) != 1 else ''} remaining\033[K")
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
            if anomaly_type == "VX":
                music.play_ambiance()
            return

        # Mine the selected asteroid
        result = mine_asteroid(save_name, data, asteroids[choice], vexnium_guarded)

        if result == "death":
            if anomaly_type == "VX":
                music.play_ambiance()
            animated_death_screen(save_name, data)
            return
        elif result == "escaped":
            if anomaly_type == "VX":
                music.play_ambiance()
            save_data(save_name, data)
            return
        elif result in ["completed", "skipped"]:
            # Remove the depleted or skipped asteroid
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

        if anomaly_type == "VX":
            music.play_ambiance()
        clear_screen()
        title("ANOMALY DEPLETED")
        print()
        print(f"  {anomaly_name} has been fully mined.\033[K")
        print("  The anomaly has dissipated.\033[K")
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
        print("  ⚠ WARNING: This ship is not designed for mining!\033[K")
        reset_color()
        print()
        print(f"  Your {player_ship.get('nickname', player_ship['name'].title())} ({ship_class})\033[K")
        print("  is poorly equipped for mining operations.\033[K")
        print()
        print("  Mining will be extremely slow and inefficient.\033[K")
        print("  Consider using a Miner-class ship for better results.\033[K")
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
        print("⚠ CRYSTALLINE GUARDIAN ATTACK ⚠\033[K")
        reset_color()
        print("=" * 60)
        print()
        print("  The crystalline guardians are attacking!\033[K")
        print()
        sleep(1)

        # Generate crystalline enemy fleet
        enemy_fleet = {
            "type": "Crystalline Guardians",
            "size": random.randint(2, 4),
            "warp_disruptor": False,
            "total_firepower": 800,
            "ships": []
        }

        for i in range(enemy_fleet["size"]):
            entity = {
                "name": f"Crystalline Guardian {i+1}",
                "shield_hp": 150,
                "max_shield_hp": 150,
                "hull_hp": 600,
                "max_hull_hp": 600,
                "damage": 180,  # Increased from 125
            }
            enemy_fleet["ships"].append(entity)

        system = system_data(data["current_system"])
        result = combat_loop(enemy_fleet, system, save_name, data, forced_combat=True)
        music.play_ambiance()

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
        print(f"  Ore: {ore_name}\033[K")
        print(f"  Ship: {player_ship.get('nickname', player_ship['name'].title())} ({ship_class})\033[K")
        print(f"  Mining Skill: Level {mining_skill}\033[K")
        print()

        # Display ore and stability status
        ore_percent = (remaining_ore / total_quantity) * 100
        stability_color = get_stability_color(stability)

        print(f"  Ore Remaining: {int(remaining_ore)}/{total_quantity} ({ore_percent:.1f}%)\033[K")
        print(f"  Asteroid Stability: {stability_color}{stability:.1f}%{RESET_COLOR}\033[K")
        print()

        # Stability bar
        stability_bar_width = 40
        stability_filled = int((stability / 100) * stability_bar_width)
        stability_empty = stability_bar_width - stability_filled
        stability_bar = f"[{stability_color}{'█' * stability_filled}{'░' * stability_empty}{RESET_COLOR}]"
        print(f"  {stability_bar}\033[K")
        print()

        print("=" * 60)
        print()
        print("  Select Mining Laser Intensity:\033[K")
        print()
        print("  [1] Minimum    - Safest, slowest      (+5% stability)\033[K")
        print("  [2] Low        - Safe, slow           (neutral)\033[K")
        print("  [3] Medium     - Balanced             (-5% stability)\033[K")
        print("  [4] High       - Fast, risky          (-10% stability)\033[K")
        print("  [5] Maximum    - Fastest, dangerous   (-20% stability)\033[K")
        print()
        print("  [ESC] Stop mining and leave\033[K")
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
        print(f"  Firing mining laser at intensity {intensity}...\033[K")
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
                print(f"  Gas Pocket Exposed!\033[K")
                reset_color()
                print(f"     Lost {ore_lost:.1f} units of ore\033[K")
                print(f"     Stability decreased by {stability_lost:.1f}%\033[K")

                if ship_damage > 0:
                    ship_destroyed = apply_damage_to_player(player_ship, ship_damage)
                    if ship_destroyed:
                        print()
                        set_color("red")
                        set_color("blinking")
                        print("     ⚠ CRITICAL: SHIP DESTROYED ⚠\033[K")
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
                print(f"  Dense Mineral Formation Uncovered!\033[K")
                reset_color()
                print(f"     Bonus: +{bonus_ore:.1f} units of {ore_name}\033[K")
                print()
                input("Press Enter to continue...")

            elif event_type == "collision":
                ore_lost = event_data["ore_lost"]
                recoverable = event_data["recoverable"]

                remaining_ore -= ore_lost

                set_color("yellow")
                print(f"  Asteroid Collision!\033[K")
                reset_color()
                print(f"     {ore_lost:.1f} units of ore broke off\033[K")
                print(f"     {recoverable:.1f} units are recoverable if you act fast!\033[K")
                print()
                print("  [A] Act fast to recover ore\033[K")
                print("  [Any other key] Continue mining\033[K")
                print()

                key = get_key()
                if key == 'a':
                    # Quick time event - player has to spam a key
                    print()
                    set_color("cyan")
                    print("  Quickly press SPACE to recover ore!\033[K")
                    reset_color()
                    print()

                    recovered = 0
                    start_time = time()
                    presses = 0

                    while time() - start_time < 3:
                        key = get_key()
                        if key == ' ':
                            presses += 1
                            print(f"  Press #{presses}\033[K")

                    recovery_rate = min(1.0, presses / 10)
                    recovered = recoverable * recovery_rate
                    ore_extracted += recovered

                    print()
                    print(f"  Recovered {recovered:.1f} units! ({recovery_rate * 100:.0f}%)\033[K")
                    print()
                    sleep(1.5)

            elif event_type == "artifact":
                artifact_destroyed = event_data["destroyed"]

                if artifact_destroyed:
                    set_color("red")
                    print(f"  Ancient Artifact Vaporized!\033[K")
                    reset_color()
                    print(f"     The high-intensity laser destroyed a valuable artifact!\033[K")
                    print()
                    input("Press Enter to continue...")
                else:
                    set_color("green")
                    print(f"  Ancient Artifact Uncovered!\033[K")
                    reset_color()
                    print(f"     Added to inventory: Ancient Artifact\033[K")
                    print(f"     This can be sold for a high price!\033[K")
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
                    print(f"  MINE DETONATED!\033[K")
                    reset_color()
                    print(f"     Asteroid destroyed - all remaining ore lost\033[K")
                    print()

                    if ship_destroyed:
                        set_color("red")
                        set_color("blinking")
                        print("     ⚠ CRITICAL: SHIP DESTROYED ⚠\033[K")
                        reset_color()
                        print()
                        input("Press Enter to continue...")
                        return "death"

                    input("Press Enter to continue...")
                elif mine_defused:
                    set_color("green")
                    print(f"  Mine successfully defused!\033[K")
                    reset_color()
                    print()
                    input("Press Enter to continue...")
                else:
                    set_color("yellow")
                    print(f"  You decided to skip this asteroid to avoid the mine\033[K")
                    reset_color()
                    print()
                    sleep(1.5)

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
                        levels_gained = add_skill_xp(data, "mining",
                                                     total_xp_gained)
                        new_level = data["skills"]["mining"]
                        new_xp = data["skills"]["mining_xp"]

                        clear_screen()
                        title("MINING COMPLETE")
                        print()
                        print(f"  Collected {ore_collected}x {ore_name}!\033[K")
                        print()

                        display_xp_gain("mining", total_xp_gained,
                                        levels_gained, new_level, new_xp)

                        print()
                        save_data(save_name, data)
                        sleep(1)
                        input("Press Enter to continue...")

                    return "skipped"


        # Update ore amounts
        if vaporized > 0:
            set_color("yellow")
            print(f"  ⚠ {vaporized:.1f} units vaporized by high-intensity laser\033[K")
            reset_color()
            print()
            sleep(1)

        print(f"  Extracted: {ore_extracted:.1f} units of {ore_name}\033[K")
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
            print("  " + "=" * 56 + "\033[K")
            print("  ⚠ ⚠ ⚠  CRITICAL STABILITY FAILURE  ⚠ ⚠ ⚠\033[K")
            print("  " + "=" * 56 + "\033[K")
            reset_color()
            print()
            sleep(1)

            set_color("red")
            print("  The asteroid is exploding!\033[K")
            reset_color()
            print()
            sleep(1)

            # Massive ship damage
            explosion_damage = int(player_ship["hull_hp"] * 0.6)
            ship_destroyed = apply_damage_to_player(player_ship, explosion_damage)

            print(f"  ⚠ All remaining ore vaporized\033[K")
            print()

            if ship_destroyed:
                set_color("red")
                set_color("blinking")
                print("  ⚠ CRITICAL: SHIP DESTROYED ⚠\033[K")
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
        print(f"  Collected {ore_collected}x {ore_name}!\033[K")
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

    if ore_name == "Water Ice":
        event_chances["gas_pocket"] *= 3

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
        event_chances["proximity_mine"] *= 2.0
    elif security_level == "Unsecure":
        event_chances["proximity_mine"] *= 1.5
    elif security_level in ["Contested"]:
        event_chances["proximity_mine"] *= 1.2
    elif security_level == "Secure":
        event_chances["proximity_mine"] = 0.0
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
        print("  " + "=" * 56 + "\033[K")
        print("  ⚠ ⚠ ⚠  PROXIMITY MINE DETECTED  ⚠ ⚠ ⚠\033[K")
        print("  " + "=" * 56 + "\033[K")
        reset_color()
        print()
        sleep(1)

        print("  This asteroid has an explosive mine attached!\033[K")
        print()
        print("  What do you want to do?\033[K")
        print()
        print("  [D] Attempt to defuse the mine (risky)\033[K")
        print("  [S] Skip this asteroid entirely\033[K")
        print()

        choice = None
        while choice not in ['d', 's']:
            choice = get_key()

        if choice == 'd':
            # Defuse attempt
            mining_skill = data.get("skills", {}).get("mining", 0)
            success_chance = max(0.8, 0.5 + (mining_skill * 0.03))  # 50% base, +3% per level, caps at 80%

            print()
            set_color("cyan")
            print("  Attempting to defuse...\033[K")
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
        print("  Process ores and salvage into refined materials\033[K")
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
            print("  You don't have any items that can be refined.\033[K")
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
        print(f"Item: {item_name}\033[K")
        print(f"Available: {quantity}\033[K")
        print()

        if item_name == "Metal Scraps":
            print("Metal Scraps have a 20% chance to refine into a random material.\033[K")
            print("Higher tier materials are rarer.\033[K")
            print()
            print(f"How many would you like to process? (0 to cancel, Enter for max [{quantity}]): ", end="")
        else:
            print(f"Refines into: {material} (x{yield_amount} per ore)\033[K")
            print()
            print(f"How many would you like to refine? (0 to cancel, Enter for max [{quantity}]): ", end="")

        try:
            user_input = input().strip()

            # Default to max if Enter is pressed
            if user_input == "":
                amount = quantity
            else:
                amount = int(user_input)
            if amount <= 0:
                continue
            if amount > quantity:
                print()
                print("You don't have that many!\033[K")
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
                print(f"Processed {amount} Metal Scraps\033[K")
                print(f"Successful refines: {successful_refines} ({int(successful_refines/amount*100)}%)\033[K")

                if materials_gained:
                    print()
                    print("Materials gained:\033[K")
                    for mat, qty in materials_gained.items():
                        if mat not in data["inventory"]:
                            data["inventory"][mat] = 0
                        data["inventory"][mat] += qty
                        print(f"  +{qty}x {mat}\033[K")
                else:
                    print("No materials recovered.\033[K")

            else:
                # Standard ore refinement
                total_yield = amount * yield_amount

                if material not in data["inventory"]:
                    data["inventory"][material] = 0
                data["inventory"][material] += total_yield

                print()
                print(f"Refined {amount}x {item_name}\033[K")
                print(f"Produced: {total_yield}x {material}\033[K")

            print()
            save_data(save_name, data)
            input("Press Enter to continue...")

        except ValueError:
            print()
            print("Invalid input!\033[K")
            print()
            input("Press Enter to continue...")


def visit_manufacturing_bay(save_name, data):
    """Visit the Manufacturing Bay to craft items and ships"""
    # Ensure manufacturing_jobs exists in save data
    if "manufacturing_jobs" not in data:
        data["manufacturing_jobs"] = {}

    while True:
        # Capture content for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        title("MANUFACTURING BAY")
        print()

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Show options
        options = ["Craft Items", "Craft Ships", "View Manufacturing Jobs", "Back"]
        choice = arrow_menu("Select:", options, previous_content)

        if choice == 0:
            manufacturing_craft_menu(save_name, data, "item")
        elif choice == 1:
            manufacturing_craft_menu(save_name, data, "ship")
        elif choice == 2:
            view_manufacturing_jobs(save_name, data)
        elif choice == 3:
            return


def manufacturing_craft_menu(save_name, data, craft_type):
    """Show craftable items or ships with pagination and search"""
    crafting_data = load_crafting_data()
    items_data = load_items_data()
    ships_data = load_ships_data()

    # Filter recipes by type
    recipes = {name: recipe for name, recipe in crafting_data.items()
               if recipe.get('type') == craft_type}

    if not recipes:
        clear_screen()
        title(f"MANUFACTURING - {craft_type.upper()}S")
        print()
        print(f"No {craft_type}s available for crafting.\033[K")
        print()
        input("Press Enter to continue...")
        return

    # Sort recipes alphabetically
    sorted_recipes = sorted(recipes.items(), key=lambda x: x[0])

    page_size = 10
    current_page = 0

    while True:
        # Pagination
        max_page = (len(sorted_recipes) - 1) // page_size
        current_page = min(current_page, max_page)
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(sorted_recipes))
        page_recipes = sorted_recipes[start_idx:end_idx]

        # Capture content for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        # Build display
        title(f"MANUFACTURING - {craft_type.upper()}S")
        print()
        print(f"Page {current_page + 1}/{max_page + 1}\033[K")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Build options
        options = []
        for name, recipe in page_recipes:
            materials = recipe.get('materials', {})
            time_str = f"{recipe.get('time', 0):.0f}s"

            # Check if player has materials
            has_all_materials = True
            has_some_materials = False
            for mat_name, mat_qty in materials.items():
                inventory_qty = data.get('inventory', {}).get(mat_name, 0)
                storage_qty = data.get('storage', {}).get(mat_name, 0)
                player_qty = inventory_qty + storage_qty

                if player_qty < mat_qty:
                    has_all_materials = False
                if player_qty > 0:
                    has_some_materials = True

            # Color item name based on material availability
            # Green if has all, yellow if has some, red if has none
            if has_all_materials:
                color = CORE_COLOR
            elif has_some_materials:
                color = CONTESTED_COLOR  # Yellow/orange
            else:
                color = UNSECURE_COLOR  # Red
            options.append(f"{color}{name}{RESET_COLOR} ({time_str})")

        # Add navigation options
        if current_page > 0:
            options.append("[←] Previous Page")
        if current_page < max_page:
            options.append("[→] Next Page")
        options.append("Back")

        choice = arrow_menu("Select item to view:", options, previous_content)

        # Handle navigation choices
        if choice >= len(page_recipes):
            # It's a navigation option
            nav_option = options[choice]
            if "Previous Page" in nav_option:
                current_page -= 1
            elif "Next Page" in nav_option:
                current_page += 1
            elif "Back" in nav_option:
                return
        else:
            # Player selected an item
            name, recipe = page_recipes[choice]
            show_craft_details(save_name, data, name, recipe, items_data, ships_data)


def show_craft_details(save_name, data, item_name, recipe, items_data, ships_data):
    """Show details about a craftable item and option to craft it"""
    # Capture content for display
    content_buffer = StringIO()
    old_stdout = sys.stdout
    sys.stdout = content_buffer

    # Build display
    title(f"CRAFT: {item_name}")
    print()

    # Show item info
    item_info = items_data.get(item_name, {})
    item_type = recipe.get('type', 'Unknown').title()
    print(f"Name: {item_name}\033[K")
    print(f"Type: {item_type}\033[K")

    # Show description
    if recipe.get('type') == 'ship':
        ship_info = ships_data.get(item_name.lower(), {})
        desc = ship_info.get('description', 'No description available.')
        wrapped_desc = wrap_text(desc, 60)
        print(f"Description: {wrapped_desc}\033[K")

        # Show ship stats
        stats = ship_info.get('stats', {})
        if stats:
            print()
            print("Ship Stats:\033[K")
            for stat_name, stat_value in stats.items():
                print(f"  {stat_name}: {stat_value}\033[K")
    else:
        desc = item_info.get('description', 'No description available.')
        wrapped_desc = wrap_text(desc, 60)
        print(f"Description: {wrapped_desc}\033[K")

    print()

    # Show crafting time
    craft_time = recipe.get('time', 0)
    print(f"Crafting Time: {craft_time:.0f} seconds\033[K")
    print()

    # Show required materials
    print("Required Materials:\033[K")
    materials = recipe.get('materials', {})
    has_all_materials = True

    for mat_name, mat_qty in materials.items():
        inventory_qty = data.get('inventory', {}).get(mat_name, 0)
        storage_qty = data.get('storage', {}).get(mat_name, 0)
        player_qty = inventory_qty + storage_qty

        if player_qty >= mat_qty:
            print(f"  ✓ {mat_name}: {mat_qty} (You have: {player_qty})\033[K")
        else:
            print(f"  x {mat_name}: {mat_qty} (You have: {player_qty})\033[K")
            has_all_materials = False

    print()
    print("=" * 60)

    previous_content = content_buffer.getvalue()
    sys.stdout = old_stdout

    # Show options
    if has_all_materials:
        options = ["Craft", "Back"]
    else:
        options = ["Back"]

    choice = arrow_menu("Select:", options, previous_content)

    if choice == 0 and has_all_materials:
        # Start crafting
        item_type = recipe.get('type', 'item')

        # For items (not ships), ask for quantity
        if item_type != 'ship':
            # Calculate max quantity based on materials
            max_quantity = float('inf')
            materials = recipe.get('materials', {})
            for mat_name, mat_qty in materials.items():
                inventory_qty = data.get('inventory', {}).get(mat_name, 0)
                storage_qty = data.get('storage', {}).get(mat_name, 0)
                player_qty = inventory_qty + storage_qty
                max_quantity = min(max_quantity, player_qty // mat_qty)

            max_quantity = int(max_quantity)

            clear_screen()
            title(f"CRAFT: {item_name}")
            print()
            print(f"How many would you like to craft? (Max: {max_quantity})\033[K")
            print("Press Enter for 1, or type a number:\033[K")
            print()

            try:
                quantity_input = input("> ").strip()
                if quantity_input == "":
                    quantity = 1
                else:
                    quantity = int(quantity_input)
                    if quantity < 1:
                        quantity = 1
                    elif quantity > max_quantity:
                        quantity = max_quantity
            except ValueError:
                quantity = 1
        else:
            # Ships are crafted one at a time
            quantity = 1

        start_crafting(save_name, data, item_name, recipe, quantity)


def start_crafting(save_name, data, item_name, recipe, quantity=1):
    """Start crafting an item (can queue multiple jobs)"""
    # Get current station
    station = data.get('docked_at', 'The Citadel')

    # Consume materials for all items (from inventory first, then storage)
    materials = recipe.get('materials', {})
    for mat_name, mat_qty in materials.items():
        total_needed = mat_qty * quantity
        remaining_qty = total_needed

        # First consume from inventory
        inventory_qty = data.get('inventory', {}).get(mat_name, 0)
        consume_from_inventory = min(inventory_qty, remaining_qty)
        if consume_from_inventory > 0:
            data['inventory'][mat_name] -= consume_from_inventory
            if data['inventory'][mat_name] <= 0:
                del data['inventory'][mat_name]
            remaining_qty -= consume_from_inventory

        # Then consume from storage if needed
        if remaining_qty > 0:
            storage_qty = data.get('storage', {}).get(mat_name, 0)
            consume_from_storage = min(storage_qty, remaining_qty)
            if consume_from_storage > 0:
                data['storage'][mat_name] -= consume_from_storage
                if data['storage'][mat_name] <= 0:
                    del data['storage'][mat_name]
                remaining_qty -= consume_from_storage

    # Create multiple crafting jobs
    if station not in data['manufacturing_jobs']:
        data['manufacturing_jobs'][station] = []

    for i in range(quantity):
        job = {
            "item": item_name,
            "station": station,
            "start_time": time(),
            "craft_time": recipe.get('time', 0),
            "type": recipe.get('type', 'item')
        }
        data['manufacturing_jobs'][station].append(job)

    save_data(save_name, data)

    clear_screen()
    title("CRAFTING STARTED")
    print()
    if quantity == 1:
        print(f"Started crafting: {item_name}\033[K")
    else:
        print(f"Started crafting: {item_name} x{quantity}\033[K")
        print(f"Queued {quantity} manufacturing jobs\033[K")
    print(f"Location: {station}\033[K")
    print(f"Time per item: {recipe.get('time', 0):.0f} seconds\033[K")
    if quantity > 1:
        print(f"Total time: {recipe.get('time', 0) * quantity:.0f} seconds\033[K")
    print()
    print("You can check progress in 'View Manufacturing Jobs'.\033[K")
    print("Crafting will continue even when you're not at this station.\033[K")
    print()
    input("Press Enter to continue...")


def view_manufacturing_jobs(save_name, data):
    """View all active manufacturing jobs with live-updating progress bars"""
    # Ensure manufacturing_jobs exists
    if "manufacturing_jobs" not in data:
        data["manufacturing_jobs"] = {}

    # Check for completed jobs and allow collection
    current_station = data.get('docked_at', '')

    # Helper function to get keyboard input with timeout (non-blocking)
    def get_key_nonblocking(timeout=0.125):
        """Get a key with timeout, returns None if no key pressed"""
        if os.name == 'nt':  # Windows
            import msvcrt
            import time as time_module
            start = time_module.time()
            while time_module.time() - start < timeout:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\x1b':  # Escape
                        return 'esc'
                    elif key == b'\r':  # Enter
                        return 'enter'
                    else:
                        try:
                            return key.decode('utf-8').lower()
                        except:
                            pass
                sleep(0.01)
            return None
        else:  # Unix/Linux/Mac
            import select
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                rlist, _, _ = select.select([sys.stdin], [], [], timeout)
                if rlist:
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':  # Escape
                        # Check if it's actually escape or an arrow key
                        rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
                        if rlist:
                            ch2 = sys.stdin.read(1)
                            if ch2 == '[':
                                sys.stdin.read(1)  # Consume the direction
                                return None  # Ignore arrow keys
                        return 'esc'
                    elif ch == '\n' or ch == '\r':
                        return 'enter'
                    else:
                        return ch.lower()
                return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    while True:
        current_time = time()

        # Collect all jobs from all stations and group by item+station
        job_groups = {}  # Key: (item_name, station), Value: list of jobs

        for station, jobs in data['manufacturing_jobs'].items():
            for job in jobs:
                key = (job['item'], station)
                if key not in job_groups:
                    job_groups[key] = []
                job_groups[key].append(job)

        if not job_groups:
            clear_screen()
            title("MANUFACTURING JOBS")
            print()
            print("  No active manufacturing jobs.\033[K")
            print()
            input("Press Enter to continue...")
            return

        # Process job groups
        all_groups = []
        for (item_name, station), jobs in job_groups.items():
            # Calculate stats for the group
            total_jobs = len(jobs)
            completed_jobs = 0
            total_progress = 0

            for job in jobs:
                elapsed = current_time - job['start_time']
                progress = min(100, (elapsed / job['craft_time']) * 100)
                total_progress += progress
                if elapsed >= job['craft_time']:
                    completed_jobs += 1

            avg_progress = total_progress / total_jobs
            all_complete = (completed_jobs == total_jobs)
            can_collect = (station == current_station or station == 'The Citadel') and all_complete

            all_groups.append({
                'item_name': item_name,
                'station': station,
                'jobs': jobs,
                'count': total_jobs,
                'completed_count': completed_jobs,
                'avg_progress': avg_progress,
                'all_complete': all_complete,
                'can_collect': can_collect
            })

        # Sort groups: collectable first, then by progress
        all_groups.sort(key=lambda g: (not g['can_collect'], -g['avg_progress']))

        # Display jobs with live updating
        clear_screen()
        title("MANUFACTURING JOBS")
        print()
        print("Active Jobs:\033[K")
        print()

        for i, group in enumerate(all_groups):
            item_name = group['item_name']
            station = group['station']
            count = group['count']
            completed_count = group['completed_count']
            avg_progress = group['avg_progress']
            all_complete = group['all_complete']
            can_collect = group['can_collect']

            # Progress bar
            bar_width = 30
            filled = int((avg_progress / 100) * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Item display with count
            item_display = f"{item_name}"
            if count > 1:
                item_display += f" x{count}"

            status = ""
            if can_collect:
                status = " [READY TO COLLECT]"
            elif all_complete:
                status = f" [Complete - at {station}]"
            elif completed_count > 0:
                status = f" [{completed_count}/{count} done]"

            print(f"{chr(ord('a') + i)}) {item_display} - {station}\033[K")
            print(f"   [{bar}] {avg_progress:.1f}%{status}\033[K")
            print()

        print("=" * 60)
        print()
        print("[a-z] Select job | [ESC] Back\033[K")
        print()

        # Wait for input with timeout for live updating
        key = get_key_nonblocking(timeout=0.125)

        if key == 'esc':
            return
        elif key and len(key) == 1 and key.isalpha():
            # User selected a job group
            idx = ord(key) - ord('a')
            if 0 <= idx < len(all_groups):
                selected_group = all_groups[idx]
                if selected_group['can_collect']:
                    # Collect all items in the group
                    collect_crafted_items_group(save_name, data, selected_group)
                    # After collecting, continue the loop to refresh
                else:
                    # Show details about the group
                    show_job_group_details(selected_group)
                    # After showing details, continue the loop to refresh


def collect_crafted_items_group(save_name, data, group):
    """Collect all completed crafted items in a group"""
    item_name = group['item_name']
    station = group['station']
    jobs = group['jobs']
    count = group['count']
    item_type = jobs[0]['type'] if jobs else 'item'

    # Remove all jobs from queue
    for job in jobs:
        data['manufacturing_jobs'][station] = [j for j in data['manufacturing_jobs'][station] if j != job]
    if not data['manufacturing_jobs'][station]:
        del data['manufacturing_jobs'][station]

    # Give player all the items
    if item_name not in data['inventory']:
        data['inventory'][item_name] = 0
    data['inventory'][item_name] += count

    clear_screen()
    if item_type == 'ship':
        title("SHIPS CRAFTED")
        print()
        if count == 1:
            print(f"✓ {item_name} ship item has been added to your inventory!\033[K")
        else:
            print(f"✓ {item_name} x{count} ship items have been added to your inventory!\033[K")
        print(f"  You can assemble them from the Ship Terminal or form your inventory.\033[K")
    else:
        title("ITEMS CRAFTED")
        print()
        if count == 1:
            print(f"✓ {item_name} has been added to your inventory!\033[K")
        else:
            print(f"✓ {item_name} x{count} have been added to your inventory!\033[K")

    save_data(save_name, data)
    print()
    input("Press Enter to continue...")


def show_job_group_details(group):
    """Show details about a group of manufacturing jobs"""
    item_name = group['item_name']
    station = group['station']
    count = group['count']
    completed_count = group['completed_count']
    avg_progress = group['avg_progress']
    jobs = group['jobs']

    clear_screen()
    title("JOB GROUP DETAILS")
    print()
    print(f"Item: {item_name}\033[K")
    if count > 1:
        print(f"Quantity: {count}\033[K")
    print(f"Location: {station}\033[K")
    print(f"Average Progress: {avg_progress:.1f}%\033[K")
    print(f"Completed: {completed_count}/{count}\033[K")
    print()

    # Show individual job progress if there are multiple
    if count > 1:
        print("Individual Jobs:\033[K")
        current_time = time()
        for i, job in enumerate(jobs, 1):
            elapsed = current_time - job['start_time']
            progress = min(100, (elapsed / job['craft_time']) * 100)
            remaining = max(0, job['craft_time'] - elapsed)

            status = "Complete" if elapsed >= job['craft_time'] else f"{remaining:.0f}s remaining"
            print(f"  {i}. Progress: {progress:.1f}% - {status}\033[K")
        print()

    if group['all_complete']:
        print("Status: All jobs complete! Return to this station to collect.\033[K")
    else:
        print("Status: In Progress\033[K")

    print()
    input("Press Enter to continue...")


def collect_crafted_item(save_name, data, job_info):
    """Collect a completed crafted item"""
    job = job_info['job']
    station = job_info['station']
    item_name = job['item']
    item_type = job['type']

    # Remove job from queue
    data['manufacturing_jobs'][station] = [j for j in data['manufacturing_jobs'][station] if j != job]
    if not data['manufacturing_jobs'][station]:
        del data['manufacturing_jobs'][station]

    # Give player the item
    if item_name not in data['inventory']:
        data['inventory'][item_name] = 0
    data['inventory'][item_name] += 1

    clear_screen()
    if item_type == 'ship':
        title("SHIP CRAFTED")
        print()
        print(f"✓ {item_name} ship item has been added to your inventory!\033[K")
        print(f"  You can assemble it from the Ship Terminal or from your inventory.\033[K")
    else:
        title("ITEM CRAFTED")
        print()
        print(f"✓ {item_name} has been added to your inventory!\033[K")

    save_data(save_name, data)
    print()
    input("Press Enter to continue...")


def show_job_details(job_info):
    """Show details about a manufacturing job that isn't ready yet"""
    job = job_info['job']
    station = job_info['station']
    progress = job_info['progress']
    elapsed = job_info['elapsed']

    remaining = job['craft_time'] - elapsed

    clear_screen()
    title("JOB DETAILS")
    print()
    print(f"Item: {job['item']}\033[K")
    print(f"Location: {station}\033[K")
    print(f"Progress: {progress:.1f}%\033[K")
    print(f"Time Remaining: {remaining:.0f} seconds\033[K")
    print()

    if job_info['is_complete']:
        print("Status: Complete! Return to this station to collect.\033[K")
    else:
        print("Status: In Progress\033[K")

    print()
    input("Press Enter to continue...")


def game_loop(save_name, data):
    clear_screen()
    if data["v"] < SAVE_VERSION_CODE:
        title("CONTINUE GAME")
        print()
        print("ERROR: Save file is of an older data format.\033[K")
        print("       No migration method has been programmed.\033[K")
        print("       This save file can therefore not be loaded.\033[K")
        print()
        input("Press Enter to return to main menu")
        return

    # Set initial presence based on whether player is docked
    if data.get("docked_at"):
        update_discord_presence(data=data, context="docked")
    else:
        update_discord_presence(data=data, context="traveling")

    # Start ambiance music for gameplay
    music.play_ambiance()

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
        print(f"  ⚬ ANOMALOUS SIGNATURE DETECTED ⚬\033[K")
        print(f"  New system discovered: {gate_name}\033[K")
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
            print(f"  Destination: {dest_color}{destination}{RESET_COLOR} ({jumps} jump{'s' if jumps != 1 else ''})\033[K")

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
            print(f"  Destination: {get_security_color(all_systems_data[destination].get('SecurityLevel', 'Unknown'))}{destination}{RESET_COLOR} (Arrived!)\033[K")
        else:
            # No route found
            print(f"  Destination: {destination} (No route found)\033[K")

    title(f"CREDITS: ¢{data["credits"]}")

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

    if system_name == "Gatinsir":
        sys.stdout = old_stdout
        clear_screen()

        title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
        print(f"  {system["Region"]} > {system["Sector"]}")
        title(f"CREDITS: ¢{data["credits"]}")
        print()
        print("=" * 60)
        print("  ", end="")
        set_color("red")
        set_color("blinking")
        set_color("reverse")
        print(" ⚠ HOSTILE CONTACT ⚠ \033[K")
        reset_color()
        print("=" * 60)
        print()
        print("A fleet of pirates approaches!\033[K")
        title("What will you do?")
        print()
        print("  > Fight!\033[K")
        print("    Attempt to Escape\033[K")
        print("    Ignore and Tank Damage\033[K")
        print()
        print("  Use ↑/↓ arrows to navigate, Enter to select\033[K")
        sleep(0.75)

        clear_screen()

        title(f"CURRENT SYSTEM: {system_name}  [{system["SecurityLevel"].upper()}]")
        print(f"  {system["Region"]} > {system["Sector"]}")
        title(f"CREDITS: ¢{data["credits"]}")
        print()
        print("The fleet of pirates obliterated your ship! You died.\033[K")
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
            print("Saving...\033[K")
            close_discord_rpc()
            save_data(save_name, data)
            print("Game saved.\033[K")
            input("Press Enter to exit...")
            exit_game(False)


def view_status_screen(data):
    """Display player status including ship and skills"""
    clear_screen()
    title("STATUS")
    print()

    player_ship = get_active_ship(data)
    max_shield = get_max_shield(player_ship)
    max_hull = get_max_hull(player_ship)

    # Regenerate shields slightly when checking status (shield_regen * 1)
    shield_regen = int(get_shield_regen(player_ship) * 1)
    if player_ship["shield_hp"] < max_shield:
        player_ship["shield_hp"] = min(player_ship["shield_hp"] + shield_regen, max_shield)

    print("PILOT INFORMATION:\033[K")
    print(f"  Name: {data['player_name']}\033[K")
    print(f"  Credits: ¢{data['credits']}\033[K")
    print()

    print("ACTIVE SHIP:\033[K")
    print(f"  Name: {player_ship.get('nickname', 'Unknown')}\033[K")
    print(f"  Type: {player_ship.get('name', 'Unknown').title()}\033[K")
    print(f"  Shield HP: {player_ship['shield_hp']}/{max_shield}\033[K")
    shield_percent = int((player_ship['shield_hp'] / max_shield) * 100)
    print(f"  Shield: [{create_health_bar(player_ship['shield_hp'], max_shield, 30, 'cyan')}] {shield_percent}%\033[K")
    print(f"  Hull HP: {player_ship['hull_hp']}/{max_hull}\033[K")
    hull_percent = int((player_ship['hull_hp'] / max_hull) * 100)
    print(f"  Hull:   [{create_health_bar(player_ship['hull_hp'], max_hull, 30, 'red')}] {hull_percent}%\033[K")
    print()

    print("SKILLS:\033[K")
    combat_level = data['skills']['combat']
    combat_xp = data['skills'].get('combat_xp', 0)
    combat_xp_needed = xp_required_for_level(combat_level)
    print(f"  Combat: Level {combat_level} ({combat_xp}/{combat_xp_needed} XP)\033[K")
    print(f"    - Increases damage dealt\033[K")
    print(f"    - Reduces damage taken\033[K")
    print(f"    - Current damage bonus: +{combat_level * 2}\033[K")
    print()

    piloting_level = data['skills']['piloting']
    piloting_xp = data['skills'].get('piloting_xp', 0)
    piloting_xp_needed = xp_required_for_level(piloting_level)
    print(f"  Piloting: Level {piloting_level} ({piloting_xp}/{piloting_xp_needed} XP)\033[K")
    print(f"    - Increases evasion chance in combat\033[K")
    print(f"    - Improves escape success rate\033[K")
    print(f"    - Current evasion chance: {min(piloting_level * 2, 25)}%\033[K")
    print()

    # Ship status warnings
    if player_ship['hull_hp'] < max_hull * 0.3:
        set_color("red")
        print("⚠ WARNING: Hull damage detected! Visit a repair bay soon.\033[K")
        reset_color()
        print()

    if player_ship['shield_hp'] < max_shield * 0.5:
        set_color("yellow")
        print("⚠ NOTICE: Shields need recharging.\033[K")
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
    shield_regen = int(get_shield_regen(player_ship) * 1)
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
                print(f"[ASCII art file {random_file} not found]\033[K")

            print()
            print(f"Press Enter to return to {previous_system}\033[K")
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
            print("[Gate ASCII art not found]\033[K")
            print()
            print("     ═══════════════════════════\033[K")
            print("    ║                           ║\033[K")
            print("    ║     ANCIENT STARGATE      ║\033[K")
            print("    ║                           ║\033[K")
            print("     ═══════════════════════════\033[K")

        print()
        print(f"Press Enter to return to {previous_system}\033[K")

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

    print("┌" + "—" * 58 + "┐")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print(f"|{spacingL2}{system_color}{connected_systems[choice]}{RESET_COLOR}{spacingR2}|\033[K")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("|" + " " * 58 + "|")
    print("└" + "—" * 58 + "┘")
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
        print("This system does not have any orbital stations.\033[K")
        print("You cannot dock here.\033[K")
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
        options.append("Open Ship Terminal")
        option_actions.append("ship_terminal")

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

        if action == "manufacturing":
            visit_manufacturing_bay(save_name, data)
            continue

        if action == "ship_terminal":
            ship_terminal(save_name, data)
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
            print("Saving...\033[K")
            save_data(save_name, data)
            close_discord_rpc()
            print("Game saved.\033[K")
            input("Press Enter to exit...")
            exit_game(False)

        # All other options - not implemented yet
        clear_screen()
        title(options[choice].upper().replace("VISIT ", ""))
        print()
        print("Not implemented yet\033[K")
        input("Press Enter to continue...")


def visit_repair_bay(save_name, data):
    """Repair ship hull and shields"""
    clear_screen()
    title("REPAIR BAY")
    print()

    player_ship = get_active_ship(data)
    max_hull = get_max_hull(player_ship)

    hull_damage = max_hull - player_ship["hull_hp"]

    print(f"Ship: {player_ship.get('nickname', 'Unknown')}\033[K")
    print()
    print(f"Hull HP:   {player_ship['hull_hp']}/{max_hull}\033[K")
    print()

    if hull_damage == 0:
        print("Your ship is already in perfect condition!\033[K")
        print()
        input("Press Enter to continue...")
        return

    # Perform free repair
    player_ship["hull_hp"] = max_hull

    print("Hull fully repaired!\033[K")
    print()

    save_data(save_name, data)
    input("Press Enter to continue...")


def visit_marketplace(save_name, data):
    """Visit the General Marketplace to buy and sell items"""
    items_data = load_items_data()

    while True:
        # Capture content for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        title("GENERAL MARKETPLACE")
        print()
        print(f"  Credits: {data['credits']}\033[K")

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Show tabs
        options = ["Buy Items", "Sell Items", "Cancel"]
        choice = arrow_menu("Select:", options, previous_content)

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
        # Get all buyable items (items with buy_price specified)
        buyable_items = []
        for item_name, item_info in items_data.items():
            # Don't allow buying ships in the marketplace
            if item_info.get('type') == 'Ship':
                continue
            if item_info.get('buy_price') and item_info['buy_price'] != "":
                buyable_items.append((item_name, item_info))

        # Sort by price
        buyable_items.sort(key=lambda x: int(x[1]['buy_price']))

        if not buyable_items:
            clear_screen()
            title("MARKETPLACE - BUY")
            print()
            print("No items available for purchase.\033[K")
            print()
            input("Press Enter to continue...")
            return

        # Capture current screen for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print("MARKETPLACE - BUY\033[K")
        print()
        print(f"Credits: {data['credits']}\033[K")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Display items
        options = []
        for item_name, item_info in buyable_items:
            price = item_info['buy_price']
            item_type = item_info.get('type', 'Unknown')
            # Get current inventory count
            inv_count = data.get('inventory', {}).get(item_name, 0)
            options.append(f"{item_name} - {price} CR ({item_type}) [Own: {inv_count}]")

        options.append("Back")

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
        print(f"Item: {item_name}\033[K")
        print(f"Type: {item_info.get('type', 'Unknown')}\033[K")
        desc = item_info.get('description', 'No description available.')
        print(f"Description: {wrap_text(desc, 60)}\033[K")
        print()
        print(f"Price: {price} CR\033[K")
        print(f"Your Credits: {data['credits']} CR\033[K")
        print()

        if data['credits'] < price:
            print("You don't have enough credits!\033[K")
            print()
            input("Press Enter to continue...")
            continue

        # Calculate max affordable quantity
        max_affordable = data['credits'] // price

        # Ask how many to buy
        print(f"Enter quantity to purchase (0 to cancel, Enter for max [{max_affordable}]): ", end="")
        try:
            user_input = input().strip()

            # Default to max affordable if Enter is pressed
            if user_input == "":
                quantity = max_affordable
                total_cost = price * quantity

                # Confirm purchase of max quantity
                print()
                print(f"Purchase {quantity}x {item_name} for {total_cost} CR?\033[K")
                print(f"(This will use {int(total_cost/data['credits']*100)}% of your credits)\033[K")
                print()
                confirm = input("Confirm? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            else:
                quantity = int(user_input)
                total_cost = price * quantity

            if quantity <= 0:
                continue

            if data['credits'] < total_cost:
                print()
                print("You don't have enough credits for that quantity!\033[K")
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
            print(f"Purchased {quantity}x {item_name} for {total_cost} CR\033[K")
            print()
            input("Press Enter to continue...")

        except ValueError:
            print()
            print("Invalid input!\033[K")
            print()
            input("Press Enter to continue...")


def marketplace_sell(save_name, data, items_data):
    """Sell items to marketplace"""
    while True:
        # Capture current screen for display
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print("MARKETPLACE - SELL\033[K")
        print()
        print(f"Credits: {data['credits']}\033[K")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Ask whether to sell from inventory or storage
        options = [
            "Sell from Inventory",
            "Sell from Storage",
            "Back"
        ]

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
            print(f"Your {source_name} is empty.\033[K")
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
            print(f"No sellable items in your {source_name}.\033[K")
            print()
            input("Press Enter to continue...")
            continue

        # Sort by sell price (descending)
        sellable_items.sort(key=lambda x: int(x[1]['sell_price']), reverse=True)

        # Display items
        while True:
            # Capture current screen for display
            content_buffer = StringIO()
            old_stdout = sys.stdout
            sys.stdout = content_buffer

            print(f"MARKETPLACE - SELL FROM {source_name.upper()}\033[K")
            print()
            print(f"Credits: {data['credits']}\033[K")
            print()
            print("=" * 60)

            previous_content = content_buffer.getvalue()
            sys.stdout = old_stdout

            options = []
            for item_name, item_info, quantity in sellable_items:
                price = item_info['sell_price']
                item_type = item_info.get('type', 'Unknown')
                options.append(f"{item_name} - {price} CR ({item_type}) [Have: {quantity}]")

            options.append("Back")

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
            print(f"Item: {item_name}\033[K")
            print(f"Type: {item_info.get('type', 'Unknown')}\033[K")
            desc = item_info.get('description', 'No description available.')
            print(f"Description: {wrap_text(desc, 60)}\033[K")
            print()
            print(f"Sell Price: {price} CR (each)\033[K")
            print(f"Available: {available_quantity}\033[K")
            print(f"Your Credits: {data['credits']} CR\033[K")
            print()

            # Ask how many to sell
            print(f"Enter quantity to sell (0 to cancel, Enter for max [{available_quantity}]): ", end="")
            try:
                user_input = input().strip()

                # Default to max if Enter is pressed
                if user_input == "":
                    quantity = available_quantity
                else:
                    quantity = int(user_input)
                if quantity <= 0:
                    continue

                if quantity > available_quantity:
                    print()
                    print("You don't have that many!\033[K")
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

                # Update sellable_items list
                sellable_items = [(n, i, q - quantity if n == item_name else q)
                                 for n, i, q in sellable_items]
                sellable_items = [(n, i, q) for n, i, q in sellable_items if q > 0]

                save_data(save_name, data)

                print()
                print(f"Sold {quantity}x {item_name} for {total_value} CR\033[K")
                print()
                input("Press Enter to continue...")

                # If no more items to sell, go back
                if not sellable_items:
                    break

            except ValueError:
                print()
                print("Invalid input!\033[K")
                print()
                input("Press Enter to continue...")


def view_inventory(data):
    """View current inventory"""
    clear_screen()
    title("INVENTORY")
    print()

    inventory = data.get('inventory', {})

    if not inventory:
        print("Your inventory is empty.\033[K")
    else:
        print("Current Inventory:\033[K")
        print("=" * 60)

        # Load items data to show descriptions
        items_data = load_items_data()

        # Sort items by name
        sorted_items = sorted(inventory.items())

        for item_name, quantity in sorted_items:
            item_info = items_data.get(item_name, {})
            item_type = item_info.get('type', 'Unknown')
            print(f"  {item_name} x{quantity} ({item_type})\033[K")
            if item_info.get('description'):
                desc = item_info['description']
                wrapped_desc = wrap_text(desc, 60)
                # Indent each line
                for line in wrapped_desc.split('\n'):
                    print(f"    {line}\033[K")

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
        print("INVENTORY:\033[K")
        if not inventory:
            print("  Empty\033[K")
        else:
            for item_name, quantity in sorted(inventory.items()):
                print(f"  {item_name} x{quantity}\033[K")

        print()
        print("STORAGE:\033[K")
        if not storage:
            print("  Empty\033[K")
        else:
            for item_name, quantity in sorted(storage.items()):
                print(f"  {item_name} x{quantity}\033[K")

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

        print("GLOBAL STORAGE\033[K")
        print()
        print("=" * 60)
        print("INVENTORY:\033[K")
        if not inventory:
            print("  Empty\033[K")
        else:
            for item_name, quantity in sorted(inventory.items()):
                print(f"  {item_name} x{quantity}\033[K")

        print()
        print("STORAGE:\033[K")
        if not storage:
            print("  Empty\033[K")
        else:
            for item_name, quantity in sorted(storage.items()):
                print(f"  {item_name} x{quantity}\033[K")

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
            view_item_details(data, save_name)
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
        print(f"Your {source_key} is empty!\033[K")
        print()
        input("Press Enter to continue...")
        return

    while True:
        clear_screen()
        title(f"TRANSFER: {source_key.upper()} → {dest_key.upper()}")
        print()

        # Display source items
        print(f"{source_key.upper()}:\033[K")
        print("=" * 60)

        sorted_items = sorted(source.items())

        for i, (item_name, quantity) in enumerate(sorted_items):
            print(f"  [{i+1}] {item_name} x{quantity}\033[K")

        print()
        print("=" * 60)

        options = [f"{item_name} (x{quantity})" for item_name, quantity in sorted_items]
        options.append("Back")

        # Capture current screen
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print(f"TRANSFER: {source_key.upper()} → {dest_key.upper()}\033[K")
        print()
        print(f"{source_key.upper()}:\033[K")
        print("=" * 60)
        for i, (item_name, quantity) in enumerate(sorted_items):
            print(f"  [{i+1}] {item_name} x{quantity}\033[K")
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
        print(f"Item: {item_name}\033[K")
        print(f"Available: {available_quantity}\033[K")
        print()
        print(f"Enter quantity to transfer (0 to cancel, Enter for max [{available_quantity}]): ", end="")

        try:
            user_input = input().strip()

            # Default to max if Enter is pressed
            if user_input == "":
                quantity = available_quantity
            else:
                quantity = int(user_input)

            if quantity <= 0:
                continue

            if quantity > available_quantity:
                print()
                print("You don't have that many!\033[K")
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
            print(f"Transferred {quantity}x {item_name} to {dest_key}\033[K")
            print()
            input("Press Enter to continue...")

        except ValueError:
            print()
            print("Invalid input!\033[K")
            print()
            input("Press Enter to continue...")


def view_item_details(data, save_name=None):
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
        print("No items to display.\033[K")
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
        print(f"Name: {item_name}\033[K")
        print(f"Type: {item_info.get('type', 'Unknown')}\033[K")
        desc = item_info.get('description', 'No description available.')
        print(f"Description: {wrap_text(desc, 60)}\033[K")
        print()

        inv_qty = data.get('inventory', {}).get(item_name, 0)
        stor_qty = data.get('storage', {}).get(item_name, 0)

        print(f"In Inventory: {inv_qty}\033[K")
        print(f"In Storage: {stor_qty}\033[K")
        print(f"Total: {inv_qty + stor_qty}\033[K")
        print()

        if item_info.get('sell_price') and item_info['sell_price'] != "":
            print(f"Sell Price: {item_info['sell_price']} CR\033[K")
        if item_info.get('buy_price') and item_info['buy_price'] != "":
            print(f"Buy Price: {item_info['buy_price']} CR\033[K")

        print()

        # If this is a ship item and we have save_name, offer to assemble it
        if item_info.get('type') == 'Ship' and save_name and (inv_qty > 0 or stor_qty > 0):
            print("[A] Assemble Ship  [Enter] Continue\033[K")
            print()
            key = get_key()
            if key == 'a':
                assemble_ship_from_item(save_name, data, item_name)
                # Refresh all_items after assembly
                all_items = {}
                for item_name_refresh, quantity in data.get('inventory', {}).items():
                    all_items[item_name_refresh] = all_items.get(item_name_refresh, 0) + quantity
                for item_name_refresh, quantity in data.get('storage', {}).items():
                    all_items[item_name_refresh] = all_items.get(item_name_refresh, 0) + quantity
        else:
            input("Press Enter to continue...")


def visit_ship_vendor(save_name, data):
    """Visit ship vendor to buy ships"""
    ships_data = load_ships_data()
    items_data = load_items_data()

    while True:
        clear_screen()
        title("SHIP VENDOR")
        print()
        print(f"Credits: {data['credits']}\033[K")
        print()
        print("=" * 60)

        # Get all purchasable ships (ship items with buy_price specified in items.json)
        purchasable_ships = []
        for ship_name_lower, ship_info in ships_data.items():
            ship_name = ship_info['name']
            # Look up the ship in items.json to get pricing
            ship_item = items_data.get(ship_name)
            if ship_item and ship_item.get('buy_price') and ship_item['buy_price'] != "":
                purchasable_ships.append((ship_name_lower, ship_info, ship_item))

        # Sort by price
        purchasable_ships.sort(key=lambda x: int(x[2]['buy_price']))

        if not purchasable_ships:
            print("No ships available for purchase.\033[K")
            print()
            input("Press Enter to continue...")
            return

        # Display ships
        print("Available Ships:\033[K")
        print()

        for ship_name_lower, ship_info, ship_item in purchasable_ships:
            price = ship_item['buy_price']
            ship_class = ship_info.get('class', 'Unknown')
            ship_name = ship_info['name']

            print(f"  {ship_name} ({ship_class}) - {price} CR\033[K")
            desc = ship_info.get('description', '')
            if desc:
                wrapped_desc = wrap_text(desc, 60)
                # Indent each line
                for line in wrapped_desc.split('\n'):
                    print(f"    {line}\033[K")

            stats = ship_info.get('stats', {})
            print(f"    Stats: DPS {stats.get('DPS', '?')} | Shield {stats.get('Shield', '?')} | Hull {stats.get('Hull', '?')}\033[K")
            print(f"           Speed {stats.get('Speed', '?')} | Warp {stats.get('Warp Speed', '?')}\033[K")
            print()

        print("=" * 60)

        options = [f"{ship_info['name']} - {ship_item['buy_price']} CR" for _, ship_info, ship_item in purchasable_ships]
        options.append("Back")

        # Capture current screen
        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print("SHIP VENDOR\033[K")
        print()
        print(f"Credits: {data['credits']}\033[K")
        print()
        print("=" * 60)

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        choice = arrow_menu("Select ship to purchase:", options, previous_content)

        if choice == len(options) - 1:
            # Back
            return

        # Show ship purchase confirmation
        ship_name_lower, ship_info, ship_item = purchasable_ships[choice]
        price = int(ship_item['buy_price'])
        ship_name = ship_info['name']

        clear_screen()
        title("PURCHASE SHIP")
        print()
        print(f"Ship: {ship_name}\033[K")
        print(f"Class: {ship_info.get('class', 'Unknown')}\033[K")
        desc = ship_info.get('description', 'No description available.')
        print(f"Description: {wrap_text(desc, 60)}\033[K")
        print()

        stats = ship_info.get('stats', {})
        print("Stats:\033[K")
        print(f"  DPS: {stats.get('DPS', 'N/A')}\033[K")
        print(f"  Shield: {stats.get('Shield', '?')}\033[K")
        print(f"  Hull: {stats.get('Hull', '?')}\033[K")
        print(f"  Energy: {stats.get('Energy', '?')}\033[K")
        print(f"  Speed: {stats.get('Speed', '?')}\033[K")
        print(f"  Warp Speed: {stats.get('Warp Speed', '?')}\033[K")
        print()
        print(f"Price: {price} CR\033[K")
        print(f"Your Credits: {data['credits']} CR\033[K")
        print()

        if data['credits'] < price:
            print("You don't have enough credits!\033[K")
            print()
            input("Press Enter to continue...")
            continue

        # Process purchase
        data['credits'] -= price

        # Add ship item to inventory
        if 'inventory' not in data:
            data['inventory'] = {}

        if ship_name not in data['inventory']:
            data['inventory'][ship_name] = 0
        data['inventory'][ship_name] += 1

        save_data(save_name, data)

        print()
        print(f"Purchased {ship_name} for {price} CR\033[K")
        print(f"The {ship_name} item has been added to your inventory.\033[K")
        print("You can assemble it to create a usable ship.\033[K")
        print()
        input("Press Enter to continue...")


def ship_terminal(save_name, data):
    """Ship Terminal with tabs for viewing/managing ships and assembling new ones"""
    current_tab = 0

    def draw_tabs(current):
        """Draw ASCII art tabs"""
        tabs = ["Ships", "Assembly"]
        tab_line = "  "
        name_line = "  "

        for i, name in enumerate(tabs):
            if i == current:
                # Active tab (looks raised)
                tab_line += "┌─────────┐ "
                name_line += f"│ {name:^7} │ "
            else:
                # Inactive tab
                tab_line += "┌─────────┐ "
                name_line += f"│ {name:^7} │ "

        print(tab_line)
        print(name_line)

        # Bottom border
        border = "  "
        for i, name in enumerate(tabs):
            if i == current:
                border += "└─────────┘─"
            else:
                border += "└─────────┘ "
        border += "─" * (60 - len(border))
        print(border)
        print()
        print("  [1] Ships     [2] Assembly\033[K")
        print("=" * 60)
        print()

    while True:
        if current_tab == 0:
            # Ships tab - view and manage owned ships
            result = ship_list_tab(save_name, data)
            if result == 'exit':
                return
            elif result == 'tab_2':
                current_tab = 1
        elif current_tab == 1:
            # Assembly tab - assemble ships from inventory
            result = ship_assembly_tab(save_name, data)
            if result == 'exit':
                return
            elif result == 'tab_1':
                current_tab = 0


def ship_list_tab(save_name, data):
    """Ships tab - view and manage owned ships"""
    ships_data = load_ships_data()

    while True:
        clear_screen()
        print()
        print("  ┌─────────┐ ┌──────────┐\033[K")
        print("  │  Ships  │ │ Assembly │\033[K")
        print("  └─────────┴─┴──────────┴─────────────────────────────────\033[K")
        print()
        print("  [1] Ships     [2] Assembly\033[K")
        print("=" * 60)
        print()

        # Show all owned ships
        if not data["ships"]:
            print("  No ships available!\033[K")
            print()
            print("  Options: [2] Assembly  [ESC] Back\033[K")
            print()

            key = get_key()
            if key == '2':
                return 'tab_2'
            elif key == 'esc':
                return 'exit'
            continue

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
        print("  Your Ships:\033[K")
        print("  " + "=" * 58 + "\033[K")
        for i, ship in enumerate(data["ships"]):
            ship_name = ship["name"]
            nickname = ship.get("nickname", ship_name.title())
            stats = get_ship_stats(ship_name)

            max_hull = stats.get("Hull", 200)
            max_shield = stats.get("Shield", 200)
            current_hull = ship.get("hull_hp", max_hull)
            current_shield = ship.get("shield_hp", max_shield)

            active_marker = " ★" if i == data["active_ship"] else "  "

            print(f"{active_marker} {i+1}. {nickname} ({ship_name.title()})\033[K")
            print(f"     Hull: {current_hull}/{max_hull}  Shield: {current_shield}/{max_shield}\033[K")

            # Show key stats
            dps = stats.get("DPS", "N/A")
            speed = stats.get("Speed", "N/A")
            warp = stats.get("Warp Speed", "N/A")

            print(f"     DPS: {dps}  Speed: {speed}  Warp: {warp}\033[K")
            print()

        print("  " + "=" * 58 + "\033[K")
        print()

        # Get user choice with custom key handling
        from io import StringIO
        import sys

        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        # Recreate the screen content
        print()
        print("  ┌─────────┐ ┌──────────┐\033[K")
        print("  │  Ships  │ │ Assembly │\033[K")
        print("  └─────────┴─┴──────────┴─────────────────────────────────\033[K")
        print()
        print("  [1] Ships     [2] Assembly\033[K")
        print("=" * 60)
        print()

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        selected = 0
        while True:
            display_menu("Select ship to view details", options, selected, previous_content)
            key = get_key()

            if key == 'up':
                selected = (selected - 1) % len(options)
            elif key == 'down':
                selected = (selected + 1) % len(options)
            elif key == '1':
                # Already on Ships tab
                continue
            elif key == '2':
                return 'tab_2'
            elif key == 'esc' or (key == 'enter' and selected == len(options) - 1):
                return 'exit'
            elif key == 'enter':
                # View ship details
                choice = selected
                break

        # Show ship details and actions
        result = view_ship_details(save_name, data, choice)
        if result == 'tab_2':
            return 'tab_2'


def view_ship_details(save_name, data, ship_index):
    """View details of a specific ship and provide action options"""
    ship = data["ships"][ship_index]
    ship_name = ship["name"]
    nickname = ship.get("nickname", ship_name.title())
    stats = get_ship_stats(ship_name)

    while True:
        clear_screen()
        title("SHIP DETAILS")
        print()
        print(f"Nickname: {nickname}\033[K")
        print(f"Model: {ship_name.title()}\033[K")
        print()

        # Get ship info from ships.json
        ships_data = load_ships_data()
        ship_info = ships_data.get(ship_name.lower(), {})

        print(f"Class: {ship_info.get('class', 'Unknown')}\033[K")
        desc = ship_info.get('description', 'No description available.')
        print(f"Description: {wrap_text(desc, 60)}\033[K")
        print()

        # HP status
        max_hull = stats.get("Hull", 200)
        max_shield = stats.get("Shield", 200)
        current_hull = ship.get("hull_hp", max_hull)
        current_shield = ship.get("shield_hp", max_shield)

        print(f"Hull: {current_hull}/{max_hull}\033[K")
        print(f"Shield: {current_shield}/{max_shield}\033[K")
        print()

        # Stats
        print("Stats:\033[K")
        print(f"  DPS: {stats.get('DPS', 'N/A')}\033[K")
        print(f"  Shield: {stats.get('Shield', 'N/A')}\033[K")
        print(f"  Hull: {stats.get('Hull', 'N/A')}\033[K")
        print(f"  Energy: {stats.get('Energy', 'N/A')}\033[K")
        print(f"  Speed: {stats.get('Speed', 'N/A')}\033[K")
        print(f"  Agility: {stats.get('Agility', 'N/A')}\033[K")
        print(f"  Warp Speed: {stats.get('Warp Speed', 'N/A')}\033[K")
        print()

        # Status
        if ship_index == data["active_ship"]:
            print("Status: ACTIVE ★\033[K")
        else:
            print("Status: Docked\033[K")
        print()
        print("=" * 60)
        print()

        # Capture current screen content for arrow_menu
        from io import StringIO
        import sys

        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        # Recreate the screen content
        title("SHIP DETAILS")
        print()
        print(f"Nickname: {nickname}\033[K")
        print(f"Model: {ship_name.title()}\033[K")
        print()
        print(f"Class: {ship_info.get('class', 'Unknown')}\033[K")
        desc = ship_info.get('description', 'No description available.')
        print(f"Description: {wrap_text(desc, 60)}\033[K")
        print()
        print(f"Hull: {current_hull}/{max_hull}\033[K")
        print(f"Shield: {current_shield}/{max_shield}\033[K")
        print()
        print("Stats:\033[K")
        print(f"  DPS: {stats.get('DPS', 'N/A')}\033[K")
        print(f"  Shield: {stats.get('Shield', 'N/A')}\033[K")
        print(f"  Hull: {stats.get('Hull', 'N/A')}\033[K")
        print(f"  Energy: {stats.get('Energy', 'N/A')}\033[K")
        print(f"  Speed: {stats.get('Speed', 'N/A')}\033[K")
        print(f"  Agility: {stats.get('Agility', 'N/A')}\033[K")
        print(f"  Warp Speed: {stats.get('Warp Speed', 'N/A')}\033[K")
        print()
        if ship_index == data["active_ship"]:
            print("Status: ACTIVE ★\033[K")
        else:
            print("Status: Docked\033[K")
        print()
        print("=" * 60)
        print()

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        # Action options
        options = []
        if ship_index != data["active_ship"]:
            options.append("Switch to this ship")
        if ship_name == "stratos":
            options.extend(["Rename ship", "Back"])
        else:
            options.extend(["Rename ship", "Disassemble ship", "Back"])

        choice = arrow_menu("Select action:", options, previous_content)

        if options[choice] == "Switch to this ship":
            # Switch to this ship
            old_ship = data["ships"][data["active_ship"]]
            data["active_ship"] = ship_index
            save_data(save_name, data)

            clear_screen()
            title("SHIP SWITCHED")
            print()
            print(f"  Switched from {old_ship.get('nickname', old_ship['name'].title())} to {nickname}\033[K")
            print()
            input("  Press Enter to continue...")
            return

        elif options[choice] == "Rename ship":
            # Rename ship
            clear_screen()
            title("RENAME SHIP")
            print()
            print(f"Current name: {nickname}\033[K")
            print()
            print("Enter new nickname (press Enter to cancel): ", end="")
            new_nickname = input().strip()

            if new_nickname:
                data["ships"][ship_index]["nickname"] = new_nickname
                save_data(save_name, data)

                clear_screen()
                title("SHIP RENAMED")
                print()
                print(f"Ship renamed to: {new_nickname}\033[K")
                print()
                input("Press Enter to continue...")
                return

        elif options[choice] == "Disassemble ship":
            # Disassemble ship (return to inventory)
            if ship_index == data["active_ship"]:
                clear_screen()
                title("CANNOT DISASSEMBLE")
                print()
                print("You cannot disassemble your active ship!\033[K")
                print("Please switch to another ship first.\033[K")
                print()
                input("Press Enter to continue...")
                continue

            clear_screen()
            title("DISASSEMBLE SHIP")
            print()
            print(f"Are you sure you want to disassemble {nickname}?\033[K")
            print(f"This will return the {ship_name.title()} item to your inventory.\033[K")
            print()
            print("Type 'yes' to confirm, or anything else to cancel: ", end="")
            confirmation = input().strip().lower()

            if confirmation == 'yes':
                # Get proper ship name for item
                ships_data = load_ships_data()
                proper_ship_name = ships_data.get(ship_name.lower(), {}).get('name', ship_name.title())

                # Add ship item to inventory
                if 'inventory' not in data:
                    data['inventory'] = {}
                if proper_ship_name not in data['inventory']:
                    data['inventory'][proper_ship_name] = 0
                data['inventory'][proper_ship_name] += 1

                # Remove ship from ships list
                data['ships'].pop(ship_index)

                # Adjust active ship index if needed
                if data["active_ship"] >= len(data["ships"]) and len(data["ships"]) > 0:
                    data["active_ship"] = len(data["ships"]) - 1

                save_data(save_name, data)

                clear_screen()
                title("SHIP DISASSEMBLED")
                print()
                print(f"{nickname} has been disassembled.\033[K")
                print(f"The {proper_ship_name} item has been added to your inventory.\033[K")
                print()
                input("Press Enter to continue...")
                return

        elif options[choice] == "Back":
            return


def ship_assembly_tab(save_name, data):
    """Assembly tab - assemble ships from inventory or storage"""
    items_data = load_items_data()
    ships_data = load_ships_data()

    while True:
        clear_screen()
        print()
        print("  ┌─────────┐ ┌──────────┐\033[K")
        print("  │  Ships  │ │ Assembly │\033[K")
        print("  └─────────┴─┴──────────┴─────────────────────────────────\033[K")
        print()
        print("  [1] Ships     [2] Assembly\033[K")
        print("=" * 60)
        print()

        # Get all ship items from inventory and storage
        ship_items = {}

        for item_name, quantity in data.get('inventory', {}).items():
            item_info = items_data.get(item_name, {})
            if item_info.get('type') == 'Ship':
                ship_items[item_name] = ship_items.get(item_name, {'inv': 0, 'stor': 0})
                ship_items[item_name]['inv'] = quantity

        for item_name, quantity in data.get('storage', {}).items():
            item_info = items_data.get(item_name, {})
            if item_info.get('type') == 'Ship':
                ship_items[item_name] = ship_items.get(item_name, {'inv': 0, 'stor': 0})
                ship_items[item_name]['stor'] = quantity

        if not ship_items:
            print("  No ship items available to assemble.\033[K")
            print()
            print("  You can purchase ships from the Ship Vendor.\033[K")
            print()
            print("  Options: [1] Ships  [ESC] Back\033[K")
            print()

            key = get_key()
            if key == '1':
                return 'tab_1'
            elif key == 'esc':
                return 'exit'
            continue

        # Display available ship items
        print("  Available Ship Items:\033[K")
        print("  " + "=" * 58 + "\033[K")

        sorted_ships = sorted(ship_items.items())
        for item_name, quantities in sorted_ships:
            inv_qty = quantities['inv']
            stor_qty = quantities['stor']
            total = inv_qty + stor_qty

            print(f"  • {item_name}\033[K")
            print(f"    Inventory: {inv_qty}  |  Storage: {stor_qty}  |  Total: {total}\033[K")

        print("  " + "=" * 58 + "\033[K")
        print()

        # Build options
        options = [f"{name} (Total: {qty['inv'] + qty['stor']})" for name, qty in sorted_ships]
        options.append("Back")

        # Get user choice with custom key handling
        from io import StringIO
        import sys

        content_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = content_buffer

        print()
        print("  ┌─────────┐ ┌──────────┐\033[K")
        print("  │  Ships  │ │ Assembly │\033[K")
        print("  └─────────┴─┴──────────┴─────────────────────────────────\033[K")
        print()
        print("  [1] Ships     [2] Assembly\033[K")
        print("=" * 60)
        print()

        previous_content = content_buffer.getvalue()
        sys.stdout = old_stdout

        selected = 0
        while True:
            display_menu("Select ship to assemble", options, selected, previous_content)
            key = get_key()

            if key == 'up':
                selected = (selected - 1) % len(options)
            elif key == 'down':
                selected = (selected + 1) % len(options)
            elif key == '1':
                return 'tab_1'
            elif key == '2':
                # Already on Assembly tab
                continue
            elif key == 'esc' or (key == 'enter' and selected == len(options) - 1):
                return 'exit'
            elif key == 'enter':
                choice = selected
                break

        # Assemble the selected ship
        ship_name = sorted_ships[choice][0]
        assemble_ship_from_item(save_name, data, ship_name)


def assemble_ship_from_item(save_name, data, ship_name):
    """Assemble a ship from an item in inventory or storage"""
    items_data = load_items_data()
    ships_data = load_ships_data()

    # Check quantities
    inv_qty = data.get('inventory', {}).get(ship_name, 0)
    stor_qty = data.get('storage', {}).get(ship_name, 0)

    if inv_qty + stor_qty == 0:
        print("No ship items available!\033[K")
        return

    clear_screen()
    title("ASSEMBLE SHIP")
    print()
    print(f"Ship: {ship_name}\033[K")

    # Get ship info
    ship_name_lower = ship_name.lower()
    ship_info = ships_data.get(ship_name_lower, {})
    stats = ship_info.get('stats', {})

    print(f"Class: {ship_info.get('class', 'Unknown')}\033[K")
    desc = ship_info.get('description', 'No description available.')
    print(f"Description: {wrap_text(desc, 60)}\033[K")
    print()

    # Show stats
    print("Stats:\033[K")
    print(f"  DPS: {stats.get('DPS', 'N/A')}\033[K")
    print(f"  Shield: {stats.get('Shield', 'N/A')}\033[K")
    print(f"  Hull: {stats.get('Hull', 'N/A')}\033[K")
    print(f"  Speed: {stats.get('Speed', 'N/A')}\033[K")
    print(f"  Warp Speed: {stats.get('Warp Speed', 'N/A')}\033[K")
    print()

    print(f"Available: {inv_qty} in inventory, {stor_qty} in storage\033[K")
    print()

    # Ask for source
    if inv_qty > 0 and stor_qty > 0:
        print("Assemble from: [1] Inventory  [2] Storage  [ESC] Cancel\033[K")
        key = get_key()
        if key == '1':
            source = 'inventory'
        elif key == '2':
            source = 'storage'
        else:
            return
    elif inv_qty > 0:
        source = 'inventory'
    else:
        source = 'storage'

    # Ask for nickname
    print()
    print("Enter a nickname for this ship (press Enter for default): ", end="")
    nickname = input().strip()
    if not nickname:
        nickname = ship_name

    # Remove item from source
    if source not in data:
        data[source] = {}

    data[source][ship_name] -= 1
    if data[source][ship_name] <= 0:
        del data[source][ship_name]

    # Create assembled ship
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

    clear_screen()
    title("SHIP ASSEMBLED")
    print()
    print(f"Successfully assembled {ship_name} '{nickname}'!\033[K")
    print("Your new ship is ready to use.\033[K")
    print()
    input("Press Enter to continue...")


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
        print("Error: ASCII art directory not found.\033[K")
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
        print("No astronomical artwork available at this time.\033[K")
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
    print(f"Title: {metadata.get('title', 'Untitled')}\033[K")
    print(f"Artist: {metadata.get('Artist', 'Unknown')}\033[K")
    print()
    input("Press Enter to Exit")


def title(text, centered=False):
    print("=" * 60)
    if centered:
        total_padding = 60 - len(text)
        spacingL = " " * math.ceil(total_padding / 2)
        spacingR = " " * math.floor(total_padding / 2)
        print(f"{spacingL}{text}{spacingR}\033[K")
    else:
        print(f"  {text}\033[K")
    print("=" * 60)


def system_data(system_name):
    with open(resource_path('system_data.json'), 'r') as f:
        data = json.load(f)

    return data.get(system_name)


def new_game():
    """Start a new game with dialogue and player name input"""

    # Play intro music for new-game experience
    music.play_intro()

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
        "Stratos and 2,500 credits to your name, you're ready to",
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
    print("Pilot, what shall you be called?\033[K")

    player_name = input("Enter your pilot name: ").strip()

    if not player_name:
        print("\nPilot name cannot be empty!\033[K")
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
    print(f"  Save '{save_name}' created successfully!\033[K")
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
    print("  You have been assigned:\033[K")
    print("    - Stratos (Starter Ship)\033[K")
    print("    - 2,500 Credits\033[K")
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
        print("No saves found!\033[K")
        input("Press Enter to continue...")
        return

    saves = [folder.name for folder in save_dir.iterdir()
             if folder.is_dir() and (folder / "save.json").exists()]

    if not saves:
        clear_screen()
        title("CONTINUE GAME")
        print()
        print("No saves found!\033[K")
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
        print("\nFailed to load save!\033[K")
        input("\nPress Enter to continue...")


def delete_save_screen():
    """List saves and delete the selected one after confirmation"""
    save_dir = Path.home() / ".starscape_text_adventure" / "saves"

    if not save_dir.exists():
        clear_screen()
        title("DELETE SAVE")
        print()
        print("No saves found!\033[K")
        input("Press Enter to continue...")
        return

    saves = [folder.name for folder in save_dir.iterdir()
             if folder.is_dir() and (folder / "save.json").exists()]

    if not saves:
        clear_screen()
        title("DELETE SAVE")
        print()
        print("No saves found!\033[K")
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
    print(f"This will permanently delete the save '{save_name}'.\033[K")
    print(f"Type '{save_name}' to confirm.\033[K")
    print()

    confirmation = input("> ").strip()

    if confirmation != save_name:
        print("\nConfirmation failed. Save was not deleted.\033[K")
        input("Press Enter to continue...")
        return

    # Delete save directory and contents
    for root, dirs, files in os.walk(save_path, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    os.rmdir(save_path)

    print(f"\nSave '{save_name}' deleted successfully.\033[K")
    input("Press Enter to continue...")


def get_settings():
    """Load settings from file, or return defaults if file doesn't exist"""
    settings_path = Path.home() / ".starscape_text_adventure" / "settings.json"

    # Default settings
    default_settings = {
        "display_startup_dialog": True,
        "adaptive_discord_presence": True,
        "ambiance_volume": 100,
        "battle_volume": 100,
    }

    # Load existing settings or use defaults
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            # Ensure all default keys exist
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            return settings
        except:
            return default_settings.copy()
    else:
        return default_settings.copy()


def settings_screen():
    """Settings menu for configuring game options"""
    settings_path = Path.home() / ".starscape_text_adventure" / "settings.json"

    # Default settings
    default_settings = {
        "display_startup_dialog": True,
        "adaptive_discord_presence": True,
        "ambiance_volume": 100,
        "battle_volume": 100,
    }

    # Load existing settings or create defaults
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            # Ensure all default keys exist
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
        except:
            settings = default_settings.copy()
    else:
        settings = default_settings.copy()

    # Save settings to file
    def save_settings():
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)

    def volume_bar(pct):
        """Render a compact ASCII volume bar for a 0-100 percentage."""
        filled = pct // 5          # 20 segments total
        empty  = 20 - filled
        return f"[{'█' * filled}{'░' * empty}] {pct:3d}%"

    def edit_volume(label, key):
        """Interactive left/right slider for a volume setting. Returns on Enter."""
        while True:
            clear_screen()
            title(f"SETTINGS  ›  {label.upper()}")
            print()
            print(f"  {label}\033[K")
            print()
            print(f"  {volume_bar(settings[key])}\033[K")
            print()
            print("  ◄ / ► or ← / →  Change by 5%\033[K")
            print("  [ / ]            Change by 1%\033[K")
            print("  Enter            Confirm\033[K")
            print()

            key_pressed = get_key()
            if key_pressed in ('right', 'd'):
                settings[key] = min(100, settings[key] + 5)
            elif key_pressed in ('left', 'a'):
                settings[key] = max(0, settings[key] - 5)
            elif key_pressed == ']':
                settings[key] = min(100, settings[key] + 1)
            elif key_pressed == '[':
                settings[key] = max(0, settings[key] - 1)
            elif key_pressed == 'enter':
                # Apply immediately to currently-playing music
                music.load_volumes()
                music.set_volume(music._vol())
                return

    # Patch get_key to recognise left/right arrow in the volume editor.
    # (The existing get_key already returns 'up'/'down'; we need 'left'/'right'.)
    # We shadow it locally with an extended version.
    _orig_get_key = get_key

    def get_key_extended():
        """get_key extended with left/right arrow support."""
        if os.name == 'nt':
            import msvcrt
            key = msvcrt.getch()
            if key in [b'\xe0', b'\x00']:
                key2 = msvcrt.getch()
                if key2 == b'H': return 'up'
                if key2 == b'P': return 'down'
                if key2 == b'K': return 'left'
                if key2 == b'M': return 'right'
            elif key == b'\r':  return 'enter'
            elif key == b'\x1b': return 'esc'
            else:
                try: return key.decode('utf-8').lower()
                except: return None
        else:
            import termios, tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A': return 'up'
                        if ch3 == 'B': return 'down'
                        if ch3 == 'C': return 'right'
                        if ch3 == 'D': return 'left'
                    return 'esc'
                elif ch in ('\n', '\r'): return 'enter'
                else: return ch.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # Temporarily replace module-level get_key so edit_volume uses the richer version
    import builtins
    _saved = globals().get('get_key')
    globals()['get_key'] = get_key_extended

    try:
        while True:
            # Build menu options based on current settings
            startup_dialog_status   = "ON"  if settings["display_startup_dialog"]    else "OFF"
            discord_presence_status = "ON"  if settings["adaptive_discord_presence"] else "OFF"
            av = volume_bar(settings["ambiance_volume"])
            bv = volume_bar(settings["battle_volume"])

            options = [
                f"Display dialog on startup:        {startup_dialog_status}",
                f"Adaptive Discord rich presence:   {discord_presence_status}",
                f"Ambiance music volume:  {av}",
                f"Battle music volume:    {bv}",
                "Reset settings to default",
                "Save and exit to menu",
            ]

            choice = arrow_menu("SETTINGS", options)

            if choice == 0:
                settings["display_startup_dialog"] = not settings["display_startup_dialog"]

            elif choice == 1:
                settings["adaptive_discord_presence"] = not settings["adaptive_discord_presence"]

            elif choice == 2:
                edit_volume("Ambiance music volume", "ambiance_volume")

            elif choice == 3:
                edit_volume("Battle music volume (also applies to Vex)", "battle_volume")

            elif choice == 4:
                # Reset settings to default
                clear_screen()
                title("RESET SETTINGS")
                print()
                print("This will reset all settings to their default values.\033[K")
                print("Type 'RESET' to confirm.\033[K")
                print()

                confirmation = input("> ").strip()

                if confirmation == "RESET":
                    settings = default_settings.copy()
                    music.load_volumes()
                    music.set_volume(music._vol())
                    print("\nSettings reset to default.\033[K")
                    input("Press Enter to continue...")
                else:
                    print("\nReset cancelled.\033[K")
                    input("Press Enter to continue...")

            elif choice == 5:
                # Save and exit
                save_settings()
                return
    finally:
        globals()['get_key'] = _saved


def jukebox_screen():
    """Full-featured jukebox: browse and play the game soundtrack with live controls."""
    if not MUSIC_AVAILABLE:
        clear_screen()
        title("JUKEBOX")
        print()
        print("  Audio is not available (pygame not installed).\033[K")
        print()
        input("  Press Enter to return to menu...")
        return

    # ── Load metadata ──────────────────────────────────────────────────────────
    metadata_map: dict = {}
    try:
        with open(resource_path("audio/metadata.json"), "r") as _f:
            for _item in json.load(_f):
                metadata_map[_item["ref"]] = _item
    except Exception:
        pass

    def get_meta(ref: str):
        m = metadata_map.get(ref, {})
        return m.get("title", ref), m.get("artist", "Unknown")

    # ── Discover audio files ───────────────────────────────────────────────────
    audio_dir = resource_path("audio")
    try:
        audio_files = sorted(
            f for f in os.listdir(audio_dir)
            if f.lower().endswith((".mp3", ".ogg", ".wav"))
        )
    except Exception:
        audio_files = []

    if not audio_files:
        clear_screen()
        title("JUKEBOX")
        print("\n  No audio files found.\n")
        input("  Press Enter to return...")
        return

    # ── Get song duration via mutagen (optional dep) ───────────────────────────
    def get_duration(filepath: str):
        try:
            from mutagen.mp3 import MP3
            return MP3(filepath).info.length
        except Exception:
            pass
        try:
            from mutagen.oggvorbis import OggVorbis
            return OggVorbis(filepath).info.length
        except Exception:
            pass
        try:
            from mutagen import File as MFile
            mf = MFile(filepath)
            if mf and mf.info:
                return mf.info.length
        except Exception:
            pass
        return None

    # ── Non-blocking raw key reader ────────────────────────────────────────────
    # IMPORTANT: must use os.read(fd, 1) — NOT sys.stdin.read(1) — because
    # Python's TextIOWrapper may buffer the full escape sequence (\x1b[A) on the
    # first read, leaving the subsequent select() seeing an empty OS buffer and
    # incorrectly timing out, causing arrow keys to be mis-read as ESC.
    def _read_key_nonblocking(timeout: float = 0.08):
        """Return a key name or None; never blocks longer than *timeout* seconds."""
        if os.name == 'nt':
            import msvcrt
            deadline = time() + timeout
            while time() < deadline:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b'\xe0', b'\x00'):
                        key2 = msvcrt.getch()
                        if key2 == b'H': return 'up'
                        if key2 == b'P': return 'down'
                        if key2 == b'K': return 'left'
                        if key2 == b'M': return 'right'
                        return None
                    if key == b'\r':  return 'enter'
                    if key == b'\x1b': return 'esc'
                    try: return key.decode('utf-8').lower()
                    except: return None
                sleep(0.01)
            return None
        else:
            import termios, tty, select as _sel
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                # ── First byte ────────────────────────────────────────────────
                r, _, _ = _sel.select([fd], [], [], timeout)
                if not r:
                    return None
                ch = os.read(fd, 1)      # raw read — bypasses Python's buffer
                if ch == b'\x1b':
                    # ── Try to read the rest of the escape sequence ────────────
                    r2, _, _ = _sel.select([fd], [], [], 0.05)
                    if r2:
                        ch2 = os.read(fd, 1)
                        if ch2 == b'[':
                            r3, _, _ = _sel.select([fd], [], [], 0.05)
                            if r3:
                                ch3 = os.read(fd, 1)
                                if ch3 == b'A': return 'up'
                                if ch3 == b'B': return 'down'
                                if ch3 == b'C': return 'right'
                                if ch3 == b'D': return 'left'
                    return 'esc'
                if ch in (b'\n', b'\r'): return 'enter'
                try:
                    return ch.decode('utf-8').lower()
                except Exception:
                    return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # ── Visual helpers ─────────────────────────────────────────────────────────
    BAR_WIDTH = 42

    _GRAD_COLORS = [
        "\033[96m",   # bright cyan
        "\033[94m",   # bright blue
        "\033[95m",   # bright magenta
        "\033[96m",   # bright cyan (smoother cycle)
        "\033[36m",   # cyan
        "\033[34m",   # blue
    ]

    def _animated_progress_bar(fraction: float, width: int, t: float) -> str:
        """Animated colour-wave progress bar; t drives the animation phase."""
        filled = int(max(0.0, min(1.0, fraction)) * width)
        bar = ""
        wave_speed = 1.5
        wave_width = len(_GRAD_COLORS)
        for i in range(width):
            if i < filled:
                phase = (i / max(width, 1) * wave_width + t * wave_speed) % wave_width
                color = _GRAD_COLORS[int(phase)]
                bar += color + "█" + RESET_COLOR
            else:
                bar += "\033[90m░\033[0m"
        return f"[{bar}\033[0m]"

    def _volume_bar(vol: float, width: int = 20) -> str:
        filled = int(vol * width)
        bar = ""
        for i in range(width):
            if i < filled:
                if vol > 0.7:
                    bar += "\033[1;32m█\033[0m"
                elif vol > 0.4:
                    bar += "\033[1;33m█\033[0m"
                else:
                    bar += "\033[1;31m█\033[0m"
            else:
                bar += "\033[90m░\033[0m"
        return f"[{bar}]"

    def _fmt_time(secs) -> str:
        if secs is None or secs < 0:
            return "--:--"
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"

    # ── Mutable playback state ─────────────────────────────────────────────────
    state = {
        "selected":    0,
        "current_idx": None,
        "paused":      False,
        "volume":      0.8,
        "start_time":  0.0,
        "song_offset": 0.0,
        "duration":    None,
        "in_player":   False,
    }

    def _elapsed() -> float:
        if state["paused"]:
            return state["song_offset"]
        return state["song_offset"] + (time() - state["start_time"])

    def _fraction() -> float:
        d = state["duration"]
        if d and d > 0:
            return min(1.0, _elapsed() / d)
        return 0.0

    def _play(idx: int, seek_to: float = 0.0):
        fp = resource_path(f"audio/{audio_files[idx]}")
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(fp)
            pygame.mixer.music.set_volume(state["volume"])
            pygame.mixer.music.play()
            if seek_to > 0.0:
                try:
                    pygame.mixer.music.set_pos(seek_to)
                except Exception:
                    pass
            state["current_idx"] = idx
            state["paused"]      = False
            state["start_time"]  = time()
            state["song_offset"] = seek_to
            state["duration"]    = get_duration(fp)
            state["in_player"]   = True
        except Exception:
            pass

    def _seek(delta: float):
        new_pos = max(0.0, _elapsed() + delta)
        if state["duration"]:
            new_pos = min(new_pos, state["duration"] - 0.5)
        _play(state["current_idx"], seek_to=new_pos)

    SEEK_STEP   = 5.0
    VOLUME_STEP = 0.05

    sys.stdout.write("\033[?25l")   # hide cursor
    sys.stdout.flush()

    try:
        while True:
            t_now = time()

            # Auto-advance when a song ends naturally
            if (state["in_player"]
                    and state["current_idx"] is not None
                    and not state["paused"]
                    and not pygame.mixer.music.get_busy()):
                next_idx = (state["current_idx"] + 1) % len(audio_files)
                _play(next_idx)
                state["selected"] = next_idx

            # ──────────────────────────────────────────────────────────────────
            # SONG LIST VIEW
            # ──────────────────────────────────────────────────────────────────
            if not state["in_player"]:
                sys.stdout.write("\033[H\033[J")

                print("=" * 60)
                print("  ♫  JUKEBOX\033[K")
                print("=" * 60)
                print()
                print("  \033[90mSelect a song and press ENTER to play it.\033[0m\033[K")
                print()

                visible  = 15
                sel      = state["selected"]
                n        = len(audio_files)
                list_top = max(0, min(sel - visible // 2, n - visible))
                list_bot = min(list_top + visible, n)

                for i in range(list_top, list_bot):
                    ref  = audio_files[i]
                    stit, sart = get_meta(ref)
                    is_playing = (i == state["current_idx"])
                    play_icon  = " \033[1;33m♪\033[0m" if is_playing else "  "

                    if i == sel:
                        marker     = "\033[1;36m>\033[0m"
                        title_col  = "\033[1;37m"
                        artist_col = "\033[37m"
                    else:
                        marker     = " "
                        title_col  = ""
                        artist_col = "\033[90m"

                    t_trunc = stit[:34]
                    a_trunc = sart[:22]
                    print(
                        f"  {marker} {title_col}{t_trunc:<34}\033[0m"
                        f" {artist_col}{a_trunc:<22}\033[0m"
                        f"{play_icon}\033[K"
                    )

                print()
                if list_top > 0:
                    print(f"  \033[90m  ↑ {list_top} more above\033[0m\033[K")
                if list_bot < n:
                    print(f"  \033[90m  ↓ {n - list_bot} more below\033[0m\033[K")

                print()
                if state["current_idx"] is not None:
                    ct, _ = get_meta(audio_files[state["current_idx"]])
                    icon  = "⏸" if state["paused"] else "▶"
                    print(f"  {icon} \033[1;36m{ct}\033[0m\033[K")
                print()
                print("  \033[90m↑↓ Navigate  │  ENTER Play  │  [p] Player View  │  ESC Back\033[0m\033[K")
                sys.stdout.flush()

                key = _read_key_nonblocking(0.10)

                if key == 'up':
                    state["selected"] = (sel - 1) % n
                elif key == 'down':
                    state["selected"] = (sel + 1) % n
                elif key == 'enter':
                    _play(sel)
                elif key == 'p' and state["current_idx"] is not None:
                    state["in_player"] = True
                elif key == 'esc':
                    break

            # ──────────────────────────────────────────────────────────────────
            # NOW-PLAYING VIEW
            # ──────────────────────────────────────────────────────────────────
            else:
                idx  = state["current_idx"]
                ref  = audio_files[idx]
                stit, sart = get_meta(ref)
                elapsed = _elapsed()
                frac    = _fraction()
                dur     = state["duration"]

                sys.stdout.write("\033[H\033[J")

                print("=" * 60)
                print("  ♫  NOW PLAYING\033[K")
                print("=" * 60)
                print()

                state_icon = "⏸" if state["paused"] else "♪"
                print(f"  {state_icon}  \033[1;37m{stit}\033[0m\033[K")
                print(f"     \033[90m{sart}\033[0m\033[K")
                print()
                print(f"     \033[90mTrack {idx + 1} of {len(audio_files)}\033[0m\033[K")
                print()

                bar      = _animated_progress_bar(frac, BAR_WIDTH, t_now)
                time_str = _fmt_time(elapsed) + " / " + (_fmt_time(dur) if dur else "--:--")
                print(f"  {bar}\033[K")
                print(f"  \033[90m{time_str}\033[0m\033[K")
                print()

                arrow_l = "\033[1;36m◄◄\033[0m"
                arrow_r = "\033[1;36m▶▶\033[0m"
                print(f"  {arrow_l} -5s  Seek  +5s {arrow_r}   \033[90m(← / →)\033[0m\033[K")
                print()

                vbar    = _volume_bar(state["volume"])
                vol_pct = int(state["volume"] * 100)
                print(f"  Volume: {vbar}  \033[1m{vol_pct}%\033[0m\033[K")
                print()

                pause_label = "[p] Resume" if state["paused"] else "[p] Pause "
                print(f"  \033[90m{pause_label}  │  [n] Next  │  [s] Song List  │  ESC Back\033[0m\033[K")
                sys.stdout.flush()

                key = _read_key_nonblocking(0.08)

                if key == 'up':
                    state["volume"] = min(1.0, state["volume"] + VOLUME_STEP)
                    pygame.mixer.music.set_volume(state["volume"])
                elif key == 'down':
                    state["volume"] = max(0.0, state["volume"] - VOLUME_STEP)
                    pygame.mixer.music.set_volume(state["volume"])
                elif key == 'right':
                    _seek(+SEEK_STEP)
                elif key == 'left':
                    _seek(-SEEK_STEP)
                elif key == 'p':
                    if state["paused"]:
                        pygame.mixer.music.unpause()
                        state["start_time"] = time()
                        state["paused"]     = False
                    else:
                        state["song_offset"] = _elapsed()
                        pygame.mixer.music.pause()
                        state["paused"]      = True
                elif key == 'n':
                    nxt = (state["current_idx"] + 1) % len(audio_files)
                    _play(nxt)
                    state["selected"] = nxt
                elif key == 's':
                    state["in_player"] = False
                elif key == 'esc':
                    state["in_player"] = False

    finally:
        sys.stdout.write("\033[?25h")   # restore cursor
        sys.stdout.flush()
        music.play(resource_path("audio/Menu.ogg"))


def about_screen():
    clear_screen()
    title("ABOUT")
    print(f"Game version code: {APP_VERSION_CODE}\033[K")
    print(f"Save format code: {SAVE_VERSION_CODE}\033[K")
    print()
    print("Starscape Text Adventure is a text-based game based on the\033[K")
    print("Roblox game, Starscape, by Zolar Keth, aka Ethan Witt.\033[K")
    print("Almost all of the game mechanics are the same between these\033[K")
    print("two games, besides the fact that this one is purely\033[K")
    print("text-based.\033[K")
    print()
    print("In Starscape, you get to wander around a vast galaxy with\033[K")
    print("over 4,500 procedurally generated star systems. You can\033[K")
    print("do just about anything from fighting ancient drones to\033[K")
    print("mining materials to build a new ship. Oh, and unlike in\033[K")
    print("the Roblox version of Starscape, mining is actually fun.\033[K")
    print()
    print("This game is open-source and can be found on GitHub at\033[K")
    set_color("cyan")
    print("https://github.com/Zytronium/starscape_text_adventure.\033[K")
    reset_color()
    print()
    print("Need help finding information about the game? While this\033[K")
    print("version doesn't have its own wiki, it shares a enough\033[K")
    print("game mechanics with Roblox Starscape that their wiki may\033[K")
    print("prove useful. Visit the Roblox Starscape wiki here:\033[K")
    set_color("cyan")
    print("https://starscape-roblox.fandom.com/wiki/Starscape_Wiki\033[K")
    reset_color()
    print()

    input("Press Enter to return to main menu...")


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
            print(RED + glitch_line() + RESET + "\033[K")
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
    print("] 100%" + RESET + "\033[K")
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
            print(GREEN + "█" * 60 + RESET + "\033[K")
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
    print(f"{RED}WARNING: All cargo has been lost.{RESET}\033[K")
    print(f"{DARK_GREEN}Location: The Citadel - Cloning Bay{RESET}\033[K")
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
        print(f"{RED}Your {player_ship.get('nickname', 'ship')} was destroyed and cannot be recovered.{RESET}\033[K")
        sleep(1.5)

        # Remove the destroyed ship from the player's fleet
        active_idx = data.get("active_ship", 0)
        if active_idx < len(data["ships"]):
            data["ships"].pop(active_idx)

        # If player has no ships left, give them a basic Stratos
        if not data["ships"]:
            print(f"{DARK_GREEN}Emergency protocol: Issuing replacement Stratos...{RESET}\033[K")
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
        print(f"{GREEN}Your Stratos has been recovered and repaired.{RESET}\033[K")
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


def find_nearest_by_security(current_system, all_systems_data):
    """Find the nearest system of each security class from the current location"""
    from collections import deque

    clear_screen()
    title("FIND NEAREST BY SECURITY CLASS")
    print()
    print("Select a security class to find the nearest system:\033[K")
    print()

    security_classes = ["Core", "Secure", "Contested", "Unsecure", "Wild"]

    # Display menu
    for i, sec_class in enumerate(security_classes):
        letter = chr(ord('a') + i)
        color = get_security_color(sec_class)
        print(f"  [{letter}] {color}{sec_class}{RESET_COLOR}\033[K")

    print()
    print("Press a letter to search, or Enter to cancel\033[K")

    while True:
        key = get_key()
        if key == 'enter':
            return None
        elif key and key.isalpha():
            idx = ord(key.lower()) - ord('a')
            if 0 <= idx < len(security_classes):
                selected_security = security_classes[idx]
                break

    # BFS to find nearest system of selected security class
    visited = set()
    queue = deque([(current_system, 0, [current_system])])
    nearest_system = None
    nearest_distance = float('inf')

    while queue:
        system, distance, path = queue.popleft()

        if system in visited:
            continue
        visited.add(system)

        system_info = all_systems_data.get(system)
        if not system_info:
            continue

        # Skip hidden systems
        if system_info.get("hidden", False):
            continue

        # Check if this system matches the security class
        if system_info.get("SecurityLevel") == selected_security and system != current_system:
            if distance < nearest_distance:
                nearest_system = system
                nearest_distance = distance
                # Found the nearest one, we can stop
                break

        # Add neighbors to queue
        for neighbor in system_info.get("Connections", []):
            if neighbor not in visited:
                queue.append((neighbor, distance + 1, path + [neighbor]))

    # Display result
    clear_screen()
    title("SEARCH RESULT")
    print()

    if nearest_system:
        color = get_security_color(selected_security)
        print(f"Nearest {color}{selected_security}{RESET_COLOR} system:\033[K")
        print(f"  {color}{nearest_system}{RESET_COLOR}\033[K")
        print(f"  Distance: {nearest_distance} jump(s)\033[K")
        print()
        print("Press Enter to view this system on the map\033[K")
        get_key()
        return nearest_system
    else:
        print(f"No {selected_security} systems found in the galaxy.\033[K")
        print()
        input("Press Enter to continue...")
        return None


def search_systems(all_systems_data):
    """Search for systems by name or security level"""
    clear_screen()
    title("GALAXY SEARCH")
    print()
    print("Search by system name or security level\033[K")
    print("(Core, Secure, Contested, Unsecure, Wild)\033[K")
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
        print(f"\nNo systems found matching '{query}'\033[K")
        input("Press Enter to continue...")
        return None

    # Show results with letter navigation
    print()
    print(f"Found {len(matches)} system(s):\033[K")
    print()

    letter_map = {}
    for i, system_name in enumerate(matches[:26]):  # Limit to 26 for a-z
        letter = chr(ord('a') + i)
        letter_map[letter] = system_name

        system_info = all_systems_data[system_name]
        security = system_info.get("SecurityLevel", "Unknown")
        color = get_security_color(security)

        print(f"  [{letter}] {color}{system_name}{RESET_COLOR} ({security})\033[K")

    print()
    print("Press a letter to view that system, or Enter to cancel\033[K")

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
    # Skip letters used for controls
    reserved_keys = {'s', 'f'}  # Search, Find by security
    letter_map = {}
    letter_idx = 0

    all_systems = []
    for distance in range(4):
        all_systems.extend(systems_by_distance[distance])

    for system in all_systems:
        # Find next available letter (skip reserved keys)
        while letter_idx < 26:
            letter = chr(ord('a') + letter_idx)
            letter_idx += 1
            if letter not in reserved_keys:
                break
        else:
            # Ran out of letters
            break

        letter_map[letter] = system

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
    print("Systems:\033[K")
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
        "  [a-z] Navigate | [SHIFT+letter] Set dest | [s] Search | [f] Find by security | [ESC] Exit")
    print("  Legend: ★ Current System  ◆ Destination  @ Viewing Center  \033[33m➜\033[0m Next in Route\033[K")
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
        elif key == 'f' and not is_shift:
            # Find nearest by security class
            result = find_nearest_by_security(current_system, all_systems_data)
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


def exit_game(close_rpc=True):
    if close_rpc:
        close_discord_rpc()
    if MUSIC_AVAILABLE:
        music.stop()
    sys.exit(0)


def main():
    """Main debug menu"""
    # Load settings
    settings = get_settings()

    # Initialize Discord Rich Presence
    init_discord_rpc()

    # Display startup dialog if enabled in settings
    if settings.get("display_startup_dialog", True):
        startup_lines = [
            "Initializing neural interface...",
            "Loading galaxy data...",
            "Fetching user save files...",
            "Starting Starscape simulation...",
            "",
            "\033[1;32m✓ System ready!\033[0m"
        ]

        clear_screen()
        type_lines(startup_lines)

    music.play(resource_path("audio/Menu.ogg"))

    try:
        while True:
            # Update Discord status to show we're in main menu
            update_discord_presence(context="menu", data={})

            options = [
                "New Game",
                "Continue Game",
                "Delete Save",
                "Settings",
                "Jukebox",
                "About",
                "Check For Updates",
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

            match choice:
                case 0:
                    new_game()
                case 1:
                    continue_game()
                case 2:
                    delete_save_screen()
                case 3:
                    settings_screen()
                case 4:
                    jukebox_screen()
                case 5:
                    about_screen()
                case 6:
                    check_for_updates()
                case 7:
                    clear_screen()
                    print("Exiting...\033[K")
                    break
    finally:
        # Clean up Discord connection when exiting
        close_discord_rpc()
        print("Game exited.\033[K")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Exiting...\033[K")
        exit_game()
