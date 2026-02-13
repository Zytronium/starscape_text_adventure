#!/usr/bin/env python3
"""
Crafting Recipe Editor GUI
Allows adding and editing crafting recipes with validation against items.json
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import os


class CraftingRecipeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Crafting Recipe Editor")
        self.root.geometry("700x800")

        # Base materials that appear by default
        self.base_materials = [
            "Korrelite", "Reknite", "Gellium", "Axnit",
            "Narcor", "Red Narcor", "Vexnium", "Water"
        ]

        # Load items.json for validation
        self.valid_items = self.load_items()

        # Track custom material entries
        self.custom_materials = []

        self.create_widgets()

    def load_items(self):
        """Load valid items from items.json"""
        items_file = Path("items.json")
        if items_file.exists():
            try:
                with open(items_file, 'r') as f:
                    data = json.load(f)
                    return {item['name'] for item in data.get('items', [])}
            except Exception as e:
                messagebox.showwarning("Warning",
                                       f"Could not load items.json: {e}\nValidation will be disabled.")
                return set()
        else:
            messagebox.showwarning("Warning",
                                   "items.json not found. Item validation will be disabled.")
            return set()

    def create_widgets(self):
        """Create the GUI widgets"""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Recipe Name
        ttk.Label(main_frame, text="Recipe Name:").grid(row=row, column=0,
                                                        sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Recipe Type
        ttk.Label(main_frame, text="Type:").grid(row=row, column=0, sticky=tk.W,
                                                 pady=5)
        self.type_var = tk.StringVar(value="ship")
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(type_frame, text="Ship", variable=self.type_var,
                        value="ship").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Item", variable=self.type_var,
                        value="item").pack(side=tk.LEFT, padx=5)
        row += 1

        # Crafting Time
        ttk.Label(main_frame, text="Crafting Time (seconds):").grid(row=row,
                                                                    column=0,
                                                                    sticky=tk.W,
                                                                    pady=5)
        self.time_entry = ttk.Entry(main_frame, width=20)
        self.time_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0,
                                                             columnspan=2,
                                                             sticky=(tk.W,
                                                                     tk.E),
                                                             pady=10)
        row += 1

        # Base Materials Section
        ttk.Label(main_frame, text="Base Materials:",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0,
                                                           columnspan=2,
                                                           sticky=tk.W, pady=5)
        row += 1

        # Create entries for base materials
        self.material_entries = {}
        for material in self.base_materials:
            ttk.Label(main_frame, text=f"{material}:").grid(row=row, column=0,
                                                            sticky=tk.W, pady=2,
                                                            padx=(20, 0))
            entry = ttk.Entry(main_frame, width=15)
            entry.insert(0, "0")
            entry.grid(row=row, column=1, sticky=tk.W, pady=2)
            self.material_entries[material] = entry
            row += 1

        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0,
                                                             columnspan=2,
                                                             sticky=(tk.W,
                                                                     tk.E),
                                                             pady=10)
        row += 1

        # Custom Materials Section
        ttk.Label(main_frame, text="Custom Materials:",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0,
                                                           columnspan=2,
                                                           sticky=tk.W, pady=5)
        row += 1

        # Frame to hold custom material entries
        self.custom_materials_frame = ttk.Frame(main_frame)
        self.custom_materials_frame.grid(row=row, column=0, columnspan=2,
                                         sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Add Custom Material Button
        ttk.Button(main_frame, text="+ Add Custom Material",
                   command=self.add_custom_material).grid(row=row, column=0,
                                                          columnspan=2, pady=10)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0,
                                                             columnspan=2,
                                                             sticky=(tk.W,
                                                                     tk.E),
                                                             pady=10)
        row += 1

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Save Recipe",
                   command=self.save_recipe).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Recipe",
                   command=self.load_recipe).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Recipe",
                   command=self.delete_recipe).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Form",
                   command=self.clear_form).pack(side=tk.LEFT, padx=5)

    def add_custom_material(self):
        """Add a new custom material entry"""
        row_frame = ttk.Frame(self.custom_materials_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Material name entry
        name_label = ttk.Label(row_frame, text="Material:")
        name_label.pack(side=tk.LEFT, padx=(20, 5))

        name_entry = ttk.Entry(row_frame, width=25)
        name_entry.pack(side=tk.LEFT, padx=5)

        # Quantity entry
        qty_label = ttk.Label(row_frame, text="Quantity:")
        qty_label.pack(side=tk.LEFT, padx=5)

        qty_entry = ttk.Entry(row_frame, width=10)
        qty_entry.insert(0, "0")
        qty_entry.pack(side=tk.LEFT, padx=5)

        # Warning label for validation
        warning_label = ttk.Label(row_frame, text="", foreground="orange")
        warning_label.pack(side=tk.LEFT, padx=5)

        # Remove button
        remove_btn = ttk.Button(row_frame, text="Remove",
                                command=lambda: self.remove_custom_material(
                                    row_frame, custom_entry))
        remove_btn.pack(side=tk.LEFT, padx=5)

        # Store the entries
        custom_entry = {
            'frame': row_frame,
            'name': name_entry,
            'quantity': qty_entry,
            'warning': warning_label
        }
        self.custom_materials.append(custom_entry)

        # Bind validation to the name entry
        name_entry.bind('<KeyRelease>',
                        lambda e: self.validate_material(custom_entry))

    def remove_custom_material(self, frame, custom_entry):
        """Remove a custom material entry"""
        frame.destroy()
        self.custom_materials.remove(custom_entry)

    def validate_material(self, custom_entry):
        """Validate material name against items.json"""
        material_name = custom_entry['name'].get().strip()

        if not material_name:
            custom_entry['warning'].config(text="")
            return

        if self.valid_items and material_name not in self.valid_items:
            custom_entry['warning'].config(text="⚠ Not found in items.json")
        else:
            custom_entry['warning'].config(text="")

    def save_recipe(self):
        """Save the recipe to crafting.json"""
        # Validate inputs
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Recipe name is required!")
            return

        try:
            time = float(self.time_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Crafting time must be a number!")
            return

        # Collect materials (only non-zero values)
        materials = {}

        # Base materials
        for material, entry in self.material_entries.items():
            try:
                value = int(entry.get())
                if value > 0:  # Only include non-zero values
                    materials[material] = value
            except ValueError:
                messagebox.showerror("Error",
                                     f"Invalid quantity for {material}!")
                return

        # Custom materials
        for custom in self.custom_materials:
            material_name = custom['name'].get().strip()
            if not material_name:
                continue

            try:
                value = int(custom['quantity'].get())
                if value > 0:  # Only include non-zero values
                    materials[material_name] = value
            except ValueError:
                messagebox.showerror("Error",
                                     f"Invalid quantity for {material_name}!")
                return

        # Create recipe object
        recipe = {
            "name": name,
            "type": self.type_var.get(),
            "time": time,
            "materials": materials
        }

        # Save to crafting.json
        try:
            crafting_file = Path("crafting.json")

            # Load existing recipes
            recipes = []
            if crafting_file.exists():
                with open(crafting_file, 'r') as f:
                    recipes = json.load(f)
                    # Ensure it's a list
                    if not isinstance(recipes, list):
                        recipes = [recipes]

            # Check if recipe with this name already exists
            updated = False
            for i, existing_recipe in enumerate(recipes):
                if existing_recipe.get('name') == name:
                    recipes[i] = recipe
                    updated = True
                    break

            # If not updated, append new recipe
            if not updated:
                recipes.append(recipe)

            # Save back to file
            with open(crafting_file, 'w') as f:
                json.dump(recipes, f, indent=2)

            action = "updated" if updated else "added"
            messagebox.showinfo("Success",
                                f"Recipe '{name}' {action} in crafting.json")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recipe: {e}")

    def load_recipe(self):
        """Load a recipe from crafting.json"""
        try:
            crafting_file = Path("crafting.json")

            if not crafting_file.exists():
                messagebox.showwarning("Warning", "crafting.json not found!")
                return

            with open(crafting_file, 'r') as f:
                recipes = json.load(f)

            # Ensure it's a list
            if not isinstance(recipes, list):
                recipes = [recipes]

            if not recipes:
                messagebox.showinfo("Info", "No recipes found in crafting.json")
                return

            # Create selection dialog
            selection_window = tk.Toplevel(self.root)
            selection_window.title("Select Recipe to Load")
            selection_window.geometry("400x300")

            ttk.Label(selection_window, text="Select a recipe to load:",
                      font=('TkDefaultFont', 10, 'bold')).pack(pady=10)

            # Create listbox
            listbox_frame = ttk.Frame(selection_window)
            listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            recipe_listbox = tk.Listbox(listbox_frame,
                                        yscrollcommand=scrollbar.set)
            recipe_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=recipe_listbox.yview)

            # Populate listbox
            for recipe in recipes:
                name = recipe.get('name', 'Unnamed')
                recipe_type = recipe.get('type', 'unknown')
                recipe_listbox.insert(tk.END, f"{name} ({recipe_type})")

            def load_selected():
                selection = recipe_listbox.curselection()
                if not selection:
                    messagebox.showwarning("Warning", "Please select a recipe!")
                    return

                selected_recipe = recipes[selection[0]]

                # Clear form first
                self.clear_form()

                # Load basic info
                self.name_entry.insert(0, selected_recipe.get('name', ''))
                self.type_var.set(selected_recipe.get('type', 'ship'))
                self.time_entry.insert(0, str(selected_recipe.get('time', 0)))

                # Load materials
                materials = selected_recipe.get('materials', {})

                # Load base materials
                for material in self.base_materials:
                    if material in materials:
                        self.material_entries[material].delete(0, tk.END)
                        self.material_entries[material].insert(0, str(
                            materials[material]))

                # Load custom materials
                for material, quantity in materials.items():
                    if material not in self.base_materials:
                        self.add_custom_material()
                        custom = self.custom_materials[-1]
                        custom['name'].insert(0, material)
                        custom['quantity'].delete(0, tk.END)
                        custom['quantity'].insert(0, str(quantity))
                        self.validate_material(custom)

                selection_window.destroy()
                messagebox.showinfo("Success", "Recipe loaded successfully")

            # Buttons
            button_frame = ttk.Frame(selection_window)
            button_frame.pack(pady=10)

            ttk.Button(button_frame, text="Load", command=load_selected).pack(
                side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel",
                       command=selection_window.destroy).pack(side=tk.LEFT,
                                                              padx=5)

            # Bind double-click to load
            recipe_listbox.bind('<Double-Button-1>', lambda e: load_selected())

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recipes: {e}")

    def delete_recipe(self):
        """Delete a recipe from crafting.json"""
        try:
            crafting_file = Path("crafting.json")

            if not crafting_file.exists():
                messagebox.showwarning("Warning", "crafting.json not found!")
                return

            with open(crafting_file, 'r') as f:
                recipes = json.load(f)

            # Ensure it's a list
            if not isinstance(recipes, list):
                recipes = [recipes]

            if not recipes:
                messagebox.showinfo("Info", "No recipes found in crafting.json")
                return

            # Create selection dialog
            selection_window = tk.Toplevel(self.root)
            selection_window.title("Delete Recipe")
            selection_window.geometry("400x300")

            ttk.Label(selection_window, text="Select a recipe to delete:",
                      font=('TkDefaultFont', 10, 'bold')).pack(pady=10)

            # Create listbox
            listbox_frame = ttk.Frame(selection_window)
            listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            recipe_listbox = tk.Listbox(listbox_frame,
                                        yscrollcommand=scrollbar.set)
            recipe_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=recipe_listbox.yview)

            # Populate listbox
            for recipe in recipes:
                name = recipe.get('name', 'Unnamed')
                recipe_type = recipe.get('type', 'unknown')
                recipe_listbox.insert(tk.END, f"{name} ({recipe_type})")

            def delete_selected():
                selection = recipe_listbox.curselection()
                if not selection:
                    messagebox.showwarning("Warning", "Please select a recipe!")
                    return

                selected_recipe = recipes[selection[0]]
                recipe_name = selected_recipe.get('name', 'Unnamed')

                # Confirm deletion
                if not messagebox.askyesno("Confirm Delete",
                                           f"Are you sure you want to delete '{recipe_name}'?"):
                    return

                # Remove the recipe
                recipes.pop(selection[0])

                # Save back to file
                with open(crafting_file, 'w') as f:
                    json.dump(recipes, f, indent=2)

                selection_window.destroy()
                messagebox.showinfo("Success",
                                    f"Recipe '{recipe_name}' deleted from crafting.json")

            # Buttons
            button_frame = ttk.Frame(selection_window)
            button_frame.pack(pady=10)

            ttk.Button(button_frame, text="Delete",
                       command=delete_selected).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel",
                       command=selection_window.destroy).pack(side=tk.LEFT,
                                                              padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete recipe: {e}")

    def clear_form(self):
        """Clear all form fields"""
        self.name_entry.delete(0, tk.END)
        self.type_var.set("ship")
        self.time_entry.delete(0, tk.END)

        # Reset base materials to 0
        for entry in self.material_entries.values():
            entry.delete(0, tk.END)
            entry.insert(0, "0")

        # Remove all custom materials
        for custom in self.custom_materials[:]:
            custom['frame'].destroy()
        self.custom_materials.clear()


def main():
    root = tk.Tk()
    app = CraftingRecipeEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
