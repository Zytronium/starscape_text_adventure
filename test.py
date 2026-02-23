import json
from collections import deque

def system_data(system_name):
    with open('system_data.json', 'r') as f:
        data = json.load(f)
    return data.get(system_name)

# --- Setup ---
system_name = "Concord"
connections = system_data(system_name)["Connections"]  # 1-jump neighbors

# ORIGINAL METHOD (nested loops)
def original_method(system_name, connections):
    valid_locations = set()  # use a set to avoid duplicates

    for connection in connections:
        # within 1 jump
        s = system_data(connection)
        for c in s["Connections"]:
            # within 2 jumps
            valid_locations.add(c)
            s2 = system_data(c)
            for c2 in s2["Connections"]:
                # within 3 jumps
                s3 = system_data(c2)
                valid_locations.add(c2)
                for c3 in s3["Connections"]:
                    # within 4 jumps
                    valid_locations.add(c3)

    # remove all locations within 1 jump from current location
    # discard() is safe even if the item isn't present
    for connection in connections:
        valid_locations.discard(connection)
    # remove current location
    valid_locations.discard(system_name)

    return list(valid_locations)

# BFS METHOD
def bfs_method(system_name, connections):
    valid_locations = []
    visited = set(connections + [system_name])  # seed with 1-jump neighbors so we never loop back

    # connections are already 1 jump away, so start at depth 1
    queue = deque((c, 1) for c in connections)

    while queue:
        current, depth = queue.popleft()

        # only collect systems 2+ jumps away (skip direct neighbors)
        if depth >= 2:
            valid_locations.append(current)

        # stop expanding past 4 jumps
        if depth < 4:
            for neighbor in system_data(current)["Connections"]:
                if neighbor not in visited:
                    visited.add(neighbor)  # mark on enqueue, not on process
                    queue.append((neighbor, depth + 1))

    return valid_locations

# -------------------------------------------------------
# Run both and compare
# -------------------------------------------------------
print("Running original method...")
original = original_method(system_name, connections)
print("Running BFS method...")
bfs = bfs_method(system_name, connections)
print("Done.")
print()

print(f"Starting system: {system_name}")
print(f"Direct connections (1 jump): {connections}\n")

print(f"Original method ({len(original)} results): {sorted(original)}")
print(f"BFS method      ({len(bfs)} results): {sorted(bfs)}\n")

# Compare as sets (order doesn't matter, only membership)
orig_set = set(original)
bfs_set = set(bfs)

if orig_set == bfs_set:
    print("✅ Results match!")
else:
    print("❌ Results differ!")
    print(f"  In original but not BFS: {orig_set - bfs_set}")
    print(f"  In BFS but not original: {bfs_set - orig_set}")

# Check for duplicates
orig_dupes = len(original) != len(set(original))
bfs_dupes  = len(bfs) != len(set(bfs))
print(f"\nDuplicates in original: {orig_dupes} ({len(original) - len(set(original))} extra)")
print(f"Duplicates in BFS:      {bfs_dupes} ({len(bfs) - len(set(bfs))} extra)")
