#!/usr/bin/env python3
"""
Ship Editor GUI
Allows adding and editing ships with crafting recipe validation and creation
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class ShipEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Ship Editor")
        self.root.geometry("800x900")

        # Ships that don't require crafting recipes
        self.recipe_exceptions = ["Stratos", "Spectator", "Spectator-X"]

        # Track if we're editing an existing ship
        self.editing_ship = None

        self.create_widgets()
        self.load_existing_ships()

    def load_existing_ships(self):
        """Load existing ships to populate the ship list"""
        try:
            ships_file = Path("ships.json")
            if ships_file.exists():
                with open(ships_file, 'r') as f:
                    data = json.load(f)
                    ships = data.get('ships', [])
                    self.ship_listbox.delete(0, tk.END)
                    for ship in ships:
                        name = ship.get('name', 'Unnamed')
                        self.ship_listbox.insert(tk.END, name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ships: {e}")

    def create_widgets(self):
        """Create the GUI widgets"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Ship List
        list_frame = ttk.Frame(notebook, padding="10")
        notebook.add(list_frame, text="Ship List")

        ttk.Label(list_frame, text="Existing Ships:",
                  font=('TkDefaultFont', 10, 'bold')).pack(pady=5)

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.ship_listbox = tk.Listbox(listbox_frame,
                                       yscrollcommand=scrollbar.set,
                                       height=15)
        self.ship_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.ship_listbox.yview)

        # Buttons for ship list
        list_button_frame = ttk.Frame(list_frame)
        list_button_frame.pack(pady=10)

        ttk.Button(list_button_frame, text="Edit Selected",
                   command=self.edit_selected_ship).pack(side=tk.LEFT, padx=5)
        ttk.Button(list_button_frame, text="Delete Selected",
                   command=self.delete_selected_ship).pack(side=tk.LEFT, padx=5)
        ttk.Button(list_button_frame, text="Check Recipe Status",
                   command=self.check_recipe_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(list_button_frame, text="Refresh List",
                   command=self.load_existing_ships).pack(side=tk.LEFT, padx=5)

        # Tab 2: Ship Editor
        editor_tab = ttk.Frame(notebook)
        notebook.add(editor_tab, text="Ship Editor")

        # Create canvas and scrollbar for editor
        editor_canvas = tk.Canvas(editor_tab)
        editor_scrollbar = ttk.Scrollbar(editor_tab, orient="vertical",
                                         command=editor_canvas.yview)
        editor_canvas.configure(yscrollcommand=editor_scrollbar.set)

        editor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        editor_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create frame inside canvas
        editor_frame = ttk.Frame(editor_canvas, padding="10")
        editor_canvas_window = editor_canvas.create_window((0, 0),
                                                           window=editor_frame,
                                                           anchor=tk.NW)

        # Configure grid
        editor_frame.columnconfigure(1, weight=1)

        # Bind configure event to update scrollregion
        def on_editor_frame_configure(event):
            editor_canvas.configure(scrollregion=editor_canvas.bbox("all"))

        editor_frame.bind("<Configure>", on_editor_frame_configure)

        # Bind canvas width to frame width
        def on_canvas_configure(event):
            editor_canvas.itemconfig(editor_canvas_window, width=event.width)

        editor_canvas.bind("<Configure>", on_canvas_configure)

        # Bind mouse wheel for scrolling
        def on_mousewheel(event):
            editor_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def bind_mousewheel(event):
            editor_canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(event):
            editor_canvas.unbind_all("<MouseWheel>")

        editor_canvas.bind("<Enter>", bind_mousewheel)
        editor_canvas.bind("<Leave>", unbind_mousewheel)

        row = 0

        # Ship Name
        ttk.Label(editor_frame, text="Ship Name:").grid(row=row, column=0,
                                                        sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(editor_frame, width=40)
        self.name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Description
        ttk.Label(editor_frame, text="Description:").grid(row=row, column=0,
                                                          sticky=tk.NW, pady=5)
        self.description_text = tk.Text(editor_frame, width=40, height=4)
        self.description_text.grid(row=row, column=1, sticky=(tk.W, tk.E),
                                   pady=5)
        row += 1

        # Ship Class
        ttk.Label(editor_frame, text="Ship Class:").grid(row=row, column=0,
                                                         sticky=tk.W, pady=5)
        self.class_var = tk.StringVar(value="Fighter")
        class_combo = ttk.Combobox(editor_frame, textvariable=self.class_var,
                                   values=["Starter", "Interceptor", "Fighter",
                                           "Miner", "Hauler", "Corvette",
                                           "Frigate", "Destroyer", "Special"],
                                   state="readonly", width=37)
        class_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Ship Stats Section
        (ttk.Separator(editor_frame, orient=tk.HORIZONTAL)
         .grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10))
        row += 1

        (ttk.Label(editor_frame, text="Ship Statistics:",
                  font=('TkDefaultFont', 10, 'bold'))
         .grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5))
        row += 1

        # DPS
        ttk.Label(editor_frame, text="DPS:").grid(row=row, column=0,
                                                  sticky=tk.W, pady=5)
        self.dps_entry = ttk.Entry(editor_frame, width=20)
        self.dps_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Shield
        ttk.Label(editor_frame, text="Shield:").grid(row=row, column=0,
                                                     sticky=tk.W, pady=5)
        self.shield_entry = ttk.Entry(editor_frame, width=20)
        self.shield_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Hull
        ttk.Label(editor_frame, text="Hull:").grid(row=row, column=0,
                                                   sticky=tk.W, pady=5)
        self.hull_entry = ttk.Entry(editor_frame, width=20)
        self.hull_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Shield Regen
        ttk.Label(editor_frame, text="Shield Regen:").grid(row=row, column=0,
                                                   sticky=tk.W, pady=5)
        self.regen_entry = ttk.Entry(editor_frame, width=20)
        self.regen_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Energy
        ttk.Label(editor_frame, text="Energy:").grid(row=row, column=0,
                                                     sticky=tk.W, pady=5)
        self.energy_entry = ttk.Entry(editor_frame, width=20)
        self.energy_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Speed
        ttk.Label(editor_frame, text="Speed:").grid(row=row, column=0,
                                                    sticky=tk.W, pady=5)
        self.speed_entry = ttk.Entry(editor_frame, width=20)
        self.speed_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Agility
        ttk.Label(editor_frame, text="Agility:").grid(row=row, column=0,
                                                      sticky=tk.W, pady=5)
        self.agility_entry = ttk.Entry(editor_frame, width=20)
        self.agility_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Warp Speed
        ttk.Label(editor_frame, text="Warp Speed:").grid(row=row, column=0,
                                                         sticky=tk.W, pady=5)
        self.warp_speed_entry = ttk.Entry(editor_frame, width=20)
        self.warp_speed_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Separator
        (ttk.Separator(editor_frame, orient=tk.HORIZONTAL)
         .grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10))
        row += 1

        # Warship Section
        (ttk.Label(editor_frame, text="Warship Settings:",
                  font=('TkDefaultFont', 10, 'bold'))
         .grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5))
        row += 1

        # Warship checkbox
        self.is_warship_var = tk.BooleanVar(value=False)
        warship_cb = ttk.Checkbutton(
            editor_frame,
            text="Is Warship  (enables turrets & warship combat mechanics)",
            variable=self.is_warship_var,
            command=self._toggle_turret_field)
        warship_cb.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        # Turrets field (shown only when warship is checked)
        self._turret_label = ttk.Label(editor_frame, text="Turrets:")
        self._turret_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.turrets_entry = ttk.Entry(editor_frame, width=20)
        self.turrets_entry.insert(0, "2")
        self.turrets_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        self._turret_row = row
        row += 1

        # Hide turret field initially
        self._turret_label.grid_remove()
        self.turrets_entry.grid_remove()

        # Crafting Recipe Section
        ttk.Label(editor_frame, text="Crafting Recipe:",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0,
                                                           columnspan=2,
                                                           sticky=tk.W, pady=5)
        row += 1

        # Recipe status label
        self.recipe_status_label = ttk.Label(editor_frame, text="",
                                             foreground="blue")
        self.recipe_status_label.grid(row=row, column=0, columnspan=2,
                                      sticky=tk.W, pady=5)
        row += 1

        # Recipe checkbox
        self.has_recipe_var = tk.BooleanVar(value=False)
        self.recipe_checkbox = ttk.Checkbutton(editor_frame,
                                               text="Create/Edit Recipe for this ship",
                                               variable=self.has_recipe_var,
                                               command=self.toggle_recipe_section)
        self.recipe_checkbox.grid(row=row, column=0, columnspan=2,
                                  sticky=tk.W, pady=5)
        row += 1

        # Recipe frame (initially hidden)
        self.recipe_frame = ttk.Frame(editor_frame)
        self.recipe_frame.grid(row=row, column=0, columnspan=2,
                               sticky=(tk.W, tk.E), pady=10)
        self.recipe_frame.grid_remove()  # Hide initially
        row += 1

        self.create_recipe_widgets()

        # Buttons
        ttk.Separator(editor_frame, orient=tk.HORIZONTAL).grid(row=row,
                                                               column=0,
                                                               columnspan=2,
                                                               sticky=(tk.W,
                                                                       tk.E),
                                                               pady=10)
        row += 1

        button_frame = ttk.Frame(editor_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Save Ship",
                   command=self.save_ship).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Form",
                   command=self.clear_form).pack(side=tk.LEFT, padx=5)

        # Bind name entry to check recipe status
        self.name_entry.bind('<KeyRelease>',
                             lambda e: self.check_current_recipe_status())

    def create_recipe_widgets(self):
        """Create widgets for the recipe section"""
        self.recipe_frame.columnconfigure(1, weight=1)

        row = 0

        # Crafting Time
        ttk.Label(self.recipe_frame, text="Crafting Time (seconds):").grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.time_entry = ttk.Entry(self.recipe_frame, width=20)
        self.time_entry.insert(0, "0")
        self.time_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Base materials
        ttk.Label(self.recipe_frame, text="Base Materials:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0,
                                                          columnspan=2,
                                                          sticky=tk.W, pady=5)
        row += 1

        self.base_materials = [
            "Korrelite", "Reknite", "Gellium", "Axnit",
            "Narcor", "Red Narcor", "Vexnium", "Water"
        ]

        self.material_entries = {}
        for material in self.base_materials:
            ttk.Label(self.recipe_frame, text=f"{material}:").grid(
                row=row, column=0, sticky=tk.W, pady=2, padx=(20, 0))
            entry = ttk.Entry(self.recipe_frame, width=15)
            entry.insert(0, "0")
            entry.grid(row=row, column=1, sticky=tk.W, pady=2)
            self.material_entries[material] = entry
            row += 1

        # Custom materials section
        ttk.Label(self.recipe_frame, text="Custom Materials:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0,
                                                          columnspan=2,
                                                          sticky=tk.W, pady=5)
        row += 1

        self.custom_materials_frame = ttk.Frame(self.recipe_frame)
        self.custom_materials_frame.grid(row=row, column=0, columnspan=2,
                                         sticky=(tk.W, tk.E), pady=5)
        row += 1

        self.custom_materials = []

        ttk.Button(self.recipe_frame, text="+ Add Custom Material",
                   command=self.add_custom_material).grid(row=row, column=0,
                                                          columnspan=2, pady=5)

    def _toggle_turret_field(self):
        """Show/hide the Turrets entry based on the warship checkbox."""
        if self.is_warship_var.get():
            self._turret_label.grid()
            self.turrets_entry.grid()
        else:
            self._turret_label.grid_remove()
            self.turrets_entry.grid_remove()

    def toggle_recipe_section(self):
        """Show/hide the recipe section"""
        if self.has_recipe_var.get():
            self.recipe_frame.grid()
        else:
            self.recipe_frame.grid_remove()

    def add_custom_material(self):
        """Add a custom material entry"""
        row_frame = ttk.Frame(self.custom_materials_frame)
        row_frame.pack(fill=tk.X, pady=2)

        ttk.Label(row_frame, text="Material:").pack(side=tk.LEFT, padx=(20, 5))
        name_entry = ttk.Entry(row_frame, width=20)
        name_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row_frame, text="Quantity:").pack(side=tk.LEFT, padx=5)
        qty_entry = ttk.Entry(row_frame, width=10)
        qty_entry.insert(0, "0")
        qty_entry.pack(side=tk.LEFT, padx=5)

        custom_entry = {
            'frame': row_frame,
            'name': name_entry,
            'quantity': qty_entry
        }

        remove_btn = ttk.Button(row_frame, text="Remove",
                                command=lambda: self.remove_custom_material(
                                    row_frame, custom_entry))
        remove_btn.pack(side=tk.LEFT, padx=5)

        self.custom_materials.append(custom_entry)

    def remove_custom_material(self, frame, custom_entry):
        """Remove a custom material entry"""
        frame.destroy()
        self.custom_materials.remove(custom_entry)

    def check_current_recipe_status(self):
        """Check if the current ship name has a recipe"""
        ship_name = self.name_entry.get().strip()
        if not ship_name:
            self.recipe_status_label.config(text="")
            return

        if ship_name in self.recipe_exceptions:
            self.recipe_status_label.config(
                text=f"✓ {ship_name} doesn't require a crafting recipe",
                foreground="green")
            return

        # Check if recipe exists
        has_recipe = self.check_ship_recipe(ship_name)
        if has_recipe:
            self.recipe_status_label.config(
                text=f"✓ Recipe exists in crafting.json",
                foreground="green")
        else:
            self.recipe_status_label.config(
                text=f"⚠ No recipe found - you should create one",
                foreground="orange")

    def check_ship_recipe(self, ship_name):
        """Check if a ship has a recipe in crafting.json"""
        try:
            crafting_file = Path("crafting.json")
            if not crafting_file.exists():
                return False

            with open(crafting_file, 'r') as f:
                recipes = json.load(f)

            if not isinstance(recipes, list):
                recipes = [recipes]

            for recipe in recipes:
                if recipe.get('name') == ship_name and recipe.get(
                        'type') == 'ship':
                    return True

            return False
        except:
            return False

    def load_ship_recipe(self, ship_name):
        """Load recipe data for a ship"""
        try:
            crafting_file = Path("crafting.json")
            if not crafting_file.exists():
                return None

            with open(crafting_file, 'r') as f:
                recipes = json.load(f)

            if not isinstance(recipes, list):
                recipes = [recipes]

            for recipe in recipes:
                if recipe.get('name') == ship_name and recipe.get(
                        'type') == 'ship':
                    return recipe

            return None
        except:
            return None

    def edit_selected_ship(self):
        """Load selected ship into editor"""
        selection = self.ship_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a ship to edit!")
            return

        ship_name = self.ship_listbox.get(selection[0])

        try:
            ships_file = Path("ships.json")
            if not ships_file.exists():
                messagebox.showerror("Error", "ships.json not found!")
                return

            with open(ships_file, 'r') as f:
                data = json.load(f)
                ships = data.get('ships', [])

            # Find the ship
            ship = None
            for s in ships:
                if s.get('name') == ship_name:
                    ship = s
                    break

            if not ship:
                messagebox.showerror("Error", f"Ship '{ship_name}' not found!")
                return

            # Clear form and load ship data
            self.clear_form()
            self.editing_ship = ship_name

            self.name_entry.insert(0, ship.get('name', ''))
            self.description_text.insert('1.0', ship.get('description', ''))
            self.class_var.set(ship.get('class', 'Fighter'))

            # Load stats
            stats = ship.get('stats', {})
            if 'DPS' in stats:
                self.dps_entry.insert(0, str(stats['DPS']))
            if 'Shield' in stats:
                self.shield_entry.insert(0, str(stats['Shield']))
            if 'Hull' in stats:
                self.hull_entry.insert(0, str(stats['Hull']))
            if 'Shield Regen' in stats:
                self.regen_entry.insert(0, str(stats['Shield Regen']))
            if 'Energy' in stats:
                self.energy_entry.insert(0, str(stats['Energy']))
            if 'Speed' in stats:
                self.speed_entry.insert(0, str(stats['Speed']))
            if 'Agility' in stats:
                self.agility_entry.insert(0, str(stats['Agility']))
            if 'Warp Speed' in stats:
                self.warp_speed_entry.insert(0, str(stats['Warp Speed']))

            # Load warship flag and Turrets
            if ship.get('warship', False):
                self.is_warship_var.set(True)
                self._toggle_turret_field()
                if 'Turrets' in stats:
                    self.turrets_entry.delete(0, tk.END)
                    self.turrets_entry.insert(0, str(int(stats['Turrets'])))

            # Check for recipe
            recipe = self.load_ship_recipe(ship_name)
            if recipe:
                self.has_recipe_var.set(True)
                self.toggle_recipe_section()

                # Load recipe data
                self.time_entry.delete(0, tk.END)
                self.time_entry.insert(0, str(recipe.get('time', 0)))

                materials = recipe.get('materials', {})

                # Load base materials
                for material in self.base_materials:
                    if material in materials:
                        self.material_entries[material].delete(0, tk.END)
                        self.material_entries[material].insert(0,
                                                               str(materials[
                                                                       material]))

                # Load custom materials
                for material, quantity in materials.items():
                    if material not in self.base_materials:
                        self.add_custom_material()
                        custom = self.custom_materials[-1]
                        custom['name'].insert(0, material)
                        custom['quantity'].delete(0, tk.END)
                        custom['quantity'].insert(0, str(quantity))

            self.check_current_recipe_status()

            # Switch to editor tab
            self.root.nametowidget('.!notebook').select(1)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ship: {e}")

    def delete_selected_ship(self):
        """Delete selected ship"""
        selection = self.ship_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a ship to delete!")
            return

        ship_name = self.ship_listbox.get(selection[0])

        if not messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete '{ship_name}'?\n\n"
                                   f"This will also delete its recipe if it exists."):
            return

        try:
            # Delete from ships.json
            ships_file = Path("ships.json")
            if ships_file.exists():
                with open(ships_file, 'r') as f:
                    data = json.load(f)

                ships = data.get('ships', [])
                data['ships'] = [s for s in ships if s.get('name') != ship_name]

                with open(ships_file, 'w') as f:
                    json.dump(data, f, indent=2)

            # Delete from crafting.json
            crafting_file = Path("crafting.json")
            if crafting_file.exists():
                with open(crafting_file, 'r') as f:
                    recipes = json.load(f)

                if not isinstance(recipes, list):
                    recipes = [recipes]

                recipes = [r for r in recipes if not (r.get('name') == ship_name
                                                      and r.get(
                            'type') == 'ship')]

                with open(crafting_file, 'w') as f:
                    json.dump(recipes, f, indent=2)

            # Delete from items.json
            items_file = Path("items.json")
            if items_file.exists():
                with open(items_file, 'r') as f:
                    data = json.load(f)

                items = data.get('items', [])
                data['items'] = [i for i in items if i.get('name') != ship_name]

                with open(items_file, 'w') as f:
                    json.dump(data, f, indent=2)

            self.load_existing_ships()
            messagebox.showinfo("Success",
                                f"Ship '{ship_name}' deleted successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete ship: {e}")

    def check_recipe_status(self):
        """Check recipe status for all ships"""
        try:
            ships_file = Path("ships.json")
            if not ships_file.exists():
                messagebox.showwarning("Warning", "ships.json not found!")
                return

            with open(ships_file, 'r') as f:
                data = json.load(f)
                ships = data.get('ships', [])

            missing_recipes = []
            for ship in ships:
                ship_name = ship.get('name', '')
                if ship_name not in self.recipe_exceptions:
                    if not self.check_ship_recipe(ship_name):
                        missing_recipes.append(ship_name)

            if missing_recipes:
                message = "The following ships are missing crafting recipes:\n\n"
                message += "\n".join(f"• {name}" for name in missing_recipes)
                messagebox.showwarning("Missing Recipes", message)
            else:
                messagebox.showinfo("Recipe Status",
                                    "All ships have crafting recipes!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to check recipes: {e}")

    def save_ship(self):
        """Save ship to ships.json"""
        # Validate inputs
        ship_name = self.name_entry.get().strip()
        if not ship_name:
            messagebox.showerror("Error", "Ship name is required!")
            return

        description = self.description_text.get('1.0', tk.END).strip()

        # Check if recipe is required
        if ship_name not in self.recipe_exceptions:
            existing_recipe = self.check_ship_recipe(ship_name)
            if not self.has_recipe_var.get() and not existing_recipe:
                if not messagebox.askyesno("Warning",
                                           f"'{ship_name}' requires a crafting recipe but none exists.\n\n"
                                           f"Do you want to continue without creating a recipe?"):
                    return

        # Create ship object
        ship = {
            "name": ship_name,
            "description": description,
            "class": self.class_var.get(),
            "stats": {}
        }

        # Add stats if provided
        if self.dps_entry.get().strip():
            try:
                ship['stats']['DPS'] = float(self.dps_entry.get())
            except ValueError:
                messagebox.showerror("Error", "DPS must be a number!")
                return

        if self.shield_entry.get().strip():
            try:
                ship['stats']['Shield'] = float(self.shield_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Shield must be a number!")
                return

        if self.hull_entry.get().strip():
            try:
                ship['stats']['Hull'] = float(self.hull_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Hull must be a number!")
                return

        if self.regen_entry.get().strip():
            try:
                ship['stats']['Shield Regen'] = float(self.regen_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Shield Regen must be a number!")
                return

        if self.energy_entry.get().strip():
            try:
                ship['stats']['Energy'] = float(self.energy_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Energy must be a number!")
                return

        if self.speed_entry.get().strip():
            try:
                ship['stats']['Speed'] = float(self.speed_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Speed must be a number!")
                return

        if self.agility_entry.get().strip():
            try:
                ship['stats']['Agility'] = float(self.agility_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Agility must be a number!")
                return

        if self.warp_speed_entry.get().strip():
            try:
                ship['stats']['Warp Speed'] = float(self.warp_speed_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Warp Speed must be a number!")
                return

        # Save warship flag and Turrets stat
        if self.is_warship_var.get():
            ship['warship'] = True
            turrets_str = self.turrets_entry.get().strip()
            if turrets_str:
                try:
                    ship['stats']['Turrets'] = int(turrets_str)
                except ValueError:
                    messagebox.showerror("Error", "Turrets must be a whole number!")
                    return
        else:
            # Remove warship flag and Turrets if unchecked
            ship.pop('warship', None)
            ship['stats'].pop('Turrets', None)

        # Save recipe if checkbox is checked
        if self.has_recipe_var.get():
            if not self.save_recipe(ship_name):
                return  # Recipe save failed

        # Save ship to ships.json
        try:
            ships_file = Path("ships.json")

            # Load existing ships
            ships_data = {"ships": []}
            if ships_file.exists():
                with open(ships_file, 'r') as f:
                    ships_data = json.load(f)

            # Check if ship exists
            updated = False
            for i, existing_ship in enumerate(ships_data['ships']):
                if existing_ship.get('name') == ship_name:
                    ships_data['ships'][i] = ship
                    updated = True
                    break

            if not updated:
                ships_data['ships'].append(ship)

            # Save to file
            with open(ships_file, 'w') as f:
                json.dump(ships_data, f, indent=2)

            # Also add to items.json
            self.create_ship_item(ship_name, description)

            action = "updated" if updated else "added"
            messagebox.showinfo("Success",
                                f"Ship '{ship_name}' {action} successfully!")

            self.load_existing_ships()
            self.editing_ship = None

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ship: {e}")

    def save_recipe(self, ship_name):
        """Save recipe for the ship"""
        try:
            time = float(self.time_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Crafting time must be a number!")
            return False

        # Collect materials
        materials = {}

        # Base materials
        for material, entry in self.material_entries.items():
            try:
                value = int(entry.get())
                if value > 0:
                    materials[material] = value
            except ValueError:
                messagebox.showerror("Error",
                                     f"Invalid quantity for {material}!")
                return False

        # Custom materials
        for custom in self.custom_materials:
            material_name = custom['name'].get().strip()
            if not material_name:
                continue

            try:
                value = int(custom['quantity'].get())
                if value > 0:
                    materials[material_name] = value
            except ValueError:
                messagebox.showerror("Error",
                                     f"Invalid quantity for {material_name}!")
                return False

        # Create recipe
        recipe = {
            "name": ship_name,
            "type": "ship",
            "time": time,
            "materials": materials
        }

        # Save to crafting.json
        try:
            crafting_file = Path("crafting.json")

            recipes = []
            if crafting_file.exists():
                with open(crafting_file, 'r') as f:
                    recipes = json.load(f)
                    if not isinstance(recipes, list):
                        recipes = [recipes]

            # Update or add recipe
            updated = False
            for i, existing_recipe in enumerate(recipes):
                if (existing_recipe.get('name') == ship_name and
                        existing_recipe.get('type') == 'ship'):
                    recipes[i] = recipe
                    updated = True
                    break

            if not updated:
                recipes.append(recipe)

            with open(crafting_file, 'w') as f:
                json.dump(recipes, f, indent=2)

            return True

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recipe: {e}")
            return False

    def create_ship_item(self, ship_name, description):
        """Create ship entry in items.json"""
        try:
            items_file = Path("items.json")

            items_data = {"items": []}
            if items_file.exists():
                with open(items_file, 'r') as f:
                    items_data = json.load(f)

            # Check if item exists
            item_exists = False
            for item in items_data['items']:
                if item['name'] == ship_name:
                    item_exists = True
                    # Update description if provided
                    if description:
                        item['description'] = description
                    break

            # Add new item if it doesn't exist
            if not item_exists:
                new_item = {
                    "name": ship_name,
                    "description": description,
                    "type": "Ship",
                    "sell_price": "",
                    "buy_price": ""
                }
                items_data['items'].append(new_item)

            with open(items_file, 'w') as f:
                json.dump(items_data, f, indent=2)

        except Exception as e:
            messagebox.showwarning("Warning",
                                   f"Ship saved but failed to update items.json: {e}")

    def clear_form(self):
        """Clear all form fields"""
        self.editing_ship = None
        self.name_entry.delete(0, tk.END)
        self.description_text.delete('1.0', tk.END)
        self.class_var.set("Fighter")
        self.dps_entry.delete(0, tk.END)
        self.shield_entry.delete(0, tk.END)
        self.hull_entry.delete(0, tk.END)
        self.regen_entry.delete(0, tk.END)
        self.energy_entry.delete(0, tk.END)
        self.speed_entry.delete(0, tk.END)
        self.agility_entry.delete(0, tk.END)
        self.warp_speed_entry.delete(0, tk.END)

        self.is_warship_var.set(False)
        self.turrets_entry.delete(0, tk.END)
        self.turrets_entry.insert(0, "2")
        self._toggle_turret_field()

        self.has_recipe_var.set(False)
        self.toggle_recipe_section()

        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, "0")

        for entry in self.material_entries.values():
            entry.delete(0, tk.END)
            entry.insert(0, "0")

        for custom in self.custom_materials[:]:
            custom['frame'].destroy()
        self.custom_materials.clear()

        self.recipe_status_label.config(text="")


def main():
    root = tk.Tk()
    app = ShipEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
