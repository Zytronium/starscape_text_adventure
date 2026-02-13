# TODO: High Level Todo list

- add more items 
- add more ships
- add ship upgrades
- add drone battleships
- make NPC ships drop salvage instead of credits
- make pirate hotspot systems more likely to have pirates
- add tutorial
  - *incomprehensible screaming*

### Adding more ships and manufacturing
- [X] Create crafting.json that contains all crafting recipes for ships and items
- [X] Create a GUI tool that makes it easier to add recipes to crafting.json
- [ ] Replace the option to "switch ships" with a "ship terminal"
  - [ ] Displays all ships, select to view details, then select either "back," "switch," "rename," or "disassemble" (and in the future, "outfit" to manage upgrades and modules)
  - [ ] Colors ships names by tier
  - [ ] Contains 2nd tab for ship assembly
- [X] Add items for every ship so they can be assembled and disassembled
- [ ] Add an "Assemble" option when viewing a ship in inventory (1 of 2 ways to assemble)
- [ ] Implement Manufacturing Bay
  - Has 2 tabs: Items and Ships
  - Lets you select from a paginated list or search for item names
  - Select an item to view details and get 2 options: "back" and "craft" (if player has the materials to craft)
  - When you start crafting an item:
    - save a timestamp in user data for when the item started crafting.
    - Open manufacturing jobs screen that shows a progress bar for all currently crafting items and [ESC] to exit and let them craft in the background.
    - Only one item can craft at a time per location that items are being crafted at. Multiple items being crafted at the same station are queued.
    - Crafting can continue progress while the game is not running thanks to the timestamp saved.
    - When crafting is complete, the user may come either to The Citadel's manufacturing bay or the manufacturing bay where the player started the crafting process, and may collect the item.
    - When the user checks their manufacturing jobs, they will see live progress bars for each item, and if the number of seconds of crafting time has passed since the saved timestamp, then they may collect the new item.
    - 
