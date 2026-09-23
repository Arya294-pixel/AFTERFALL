#!/usr/bin/env python3

import json
import struct
import sys
from pathlib import Path


# ============================================================
# AFTERFALL MAP GENERATOR
# ============================================================

HEADER_SIZE = 60

MAGIC = b"AFMP"
VERSION = 1
FLAGS = 0
MAP_ID = 1

HEADER_FORMAT = "<4sHHIIIQQQQQ"

# 384-bit world-space location:
#
#   int64 start_x
#   int64 start_y
#   int64 start_z
#   int64 end_x
#   int64 end_y
#   int64 end_z
#
LOCATION_FORMAT = "<6q"

# 128-bit file range:
#
#   uint64 start
#   uint64 end
#
FILE_RANGE_FORMAT = "<QQ"


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

GROUPS_FILE = ROOT_DIR / "groups.json"
ISLAND_FILE = ROOT_DIR / "island.json"
OBJECT_FILE = ROOT_DIR / "object.json"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "afterfall.afmap"


# ============================================================
# JSON
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# Binary helpers
# ============================================================

def pack_location(start, end):
    return struct.pack(
        LOCATION_FORMAT,

        int(start[0]),
        int(start[1]),
        int(start[2]),

        int(end[0]),
        int(end[1]),
        int(end[2]),
    )


def pack_file_range(start, end):
    return struct.pack(
        FILE_RANGE_FORMAT,
        int(start),
        int(end),
    )


# ============================================================
# Bounds
# ============================================================

def island_bounds(island):
    """
    Get the island's 384-bit spatial bounds.

    If island.json eventually contains:

        "bounds": {
            "start_x": ...,
            "start_y": ...,
            "start_z": ...,
            "end_x": ...,
            "end_y": ...,
            "end_z": ...
        }

    those values will be used.

    For the current JSON format, bounds are derived from
    object/NPC/boss coordinates.
    """

    if "bounds" in island:
        bounds = island["bounds"]

        start = (
            bounds["start_x"],
            bounds["start_y"],
            bounds["start_z"],
        )

        end = (
            bounds["end_x"],
            bounds["end_y"],
            bounds["end_z"],
        )

        return start, end

    points = []

    for obj in island.get("objects", []):
        points.append(
            (
                int(obj["x"]),
                int(obj["y"]),
                int(obj["z"]),
            )
        )

    for npc in island.get("npcs", []):
        points.append(
            (
                int(npc["x"]),
                int(npc["y"]),
                int(npc["z"]),
            )
        )

    for boss in island.get("bosses", []):
        points.append(
            (
                int(boss["x"]),
                int(boss["y"]),
                int(boss["z"]),
            )
        )

    if not points:
        return (0, 0, 0), (0, 0, 0)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]

    start = (
        min(xs),
        min(ys),
        min(zs),
    )

    end = (
        max(xs),
        max(ys),
        max(zs),
    )

    return start, end


def group_bounds(islands):
    """
    Calculate the group's spatial bounds from its islands.
    """

    all_points = []

    for island in islands.values():

        start, end = island_bounds(island)

        all_points.append(start)
        all_points.append(end)

    if not all_points:
        return (0, 0, 0), (0, 0, 0)

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]

    start = (
        min(xs),
        min(ys),
        min(zs),
    )

    end = (
        max(xs),
        max(ys),
        max(zs),
    )

    return start, end


# ============================================================
# Object registry
# ============================================================

def build_object_registry(object_json):
    """
    Convert:

        {
            "1": "oak_tree",
            "2": "pine_tree"
        }

    into both lookup directions.
    """

    object_types = object_json["object_types"]

    id_to_name = {}
    name_to_id = {}

    for object_id, name in object_types.items():

        object_id = int(object_id)

        if object_id == 0:
            raise ValueError(
                "Object ID 0 is reserved and cannot be used."
            )

        id_to_name[object_id] = name
        name_to_id[name] = object_id

    return id_to_name, name_to_id


# ============================================================
# Island objects
# ============================================================

def build_object_data(island, name_to_id):
    """
    Current object record:

        uint16 type
        int64 x
        int64 y
        int64 z
    """

    objects = island.get("objects", [])

    data = bytearray()

    # Number of objects
    data += struct.pack(
        "<I",
        len(objects)
    )

    for obj in objects:

        obj_type = obj["type"]

        # island.json currently uses numeric IDs,
        # but names are also accepted.
        if isinstance(obj_type, str):

            if obj_type not in name_to_id:
                raise ValueError(
                    f"Unknown object type: {obj_type}"
                )

            object_id = name_to_id[obj_type]

        else:
            object_id = int(obj_type)

        if object_id == 0:
            raise ValueError(
                "Object ID 0 is reserved."
            )

        if not 0 < object_id <= 65535:
            raise ValueError(
                f"Invalid object ID: {object_id}"
            )

        data += struct.pack(
            "<Hqqq",
            object_id,
            int(obj["x"]),
            int(obj["y"]),
            int(obj["z"]),
        )

    return bytes(data)


# ============================================================
# NPC data
# ============================================================

def build_npc_data(island):
    """
    NPCs currently use their string type names.

    For the prototype we give each unique NPC type a local
    uint16 ID.

    A future NPC registry can replace this.
    """

    npcs = island.get("npcs", [])

    data = bytearray()

    data += struct.pack(
        "<I",
        len(npcs)
    )

    npc_ids = {}

    for npc in npcs:

        npc_type = str(npc["type"])

        if npc_type not in npc_ids:
            npc_ids[npc_type] = len(npc_ids) + 1

        npc_id = npc_ids[npc_type]

        data += struct.pack(
            "<Hqqq",
            npc_id,
            int(npc["x"]),
            int(npc["y"]),
            int(npc["z"]),
        )

    return bytes(data)


# ============================================================
# Boss data
# ============================================================

def build_boss_data(island):
    """
    Bosses currently use their string type names.

    For the prototype they receive local uint16 IDs.
    """

    bosses = island.get("bosses", [])

    data = bytearray()

    data += struct.pack(
        "<I",
        len(bosses)
    )

    boss_ids = {}

    for boss in bosses:

        boss_type = str(boss["type"])

        if boss_type not in boss_ids:
            boss_ids[boss_type] = len(boss_ids) + 1

        boss_id = boss_ids[boss_type]

        data += struct.pack(
            "<Hqqq",
            boss_id,
            int(boss["x"]),
            int(boss["y"]),
            int(boss["z"]),
        )

    return bytes(data)


# ============================================================
# Island
# ============================================================

def build_island(island, name_to_id):
    """
    Island:

        384-bit location

        uint32 object_count
        object records

        uint32 npc_count
        NPC records

        uint32 boss_count
        boss records
    """

    data = bytearray()

    start, end = island_bounds(island)

    # --------------------------------------------------------
    # Island location
    # --------------------------------------------------------

    data += pack_location(
        start,
        end
    )

    # --------------------------------------------------------
    # Objects
    # --------------------------------------------------------

    data += build_object_data(
        island,
        name_to_id
    )

    # --------------------------------------------------------
    # NPCs
    # --------------------------------------------------------

    data += build_npc_data(
        island
    )

    # --------------------------------------------------------
    # Bosses
    # --------------------------------------------------------

    data += build_boss_data(
        island
    )

    return bytes(data)


# ============================================================
# Main
# ============================================================

def main():

    print("AFTERFALL Map Generator")
    print("========================")

    # --------------------------------------------------------
    # Load configuration
    # --------------------------------------------------------

    groups_json = load_json(
        GROUPS_FILE
    )

    islands_json = load_json(
        ISLAND_FILE
    )

    object_json = load_json(
        OBJECT_FILE
    )

    groups = groups_json["groups"]
    islands = islands_json["islands"]

    _, name_to_id = build_object_registry(
        object_json
    )

    # --------------------------------------------------------
    # Current format:
    #
    # groups.json only contains group names.
    #
    # Therefore all current islands belong to group 1.
    # --------------------------------------------------------

    if len(groups) != 1:
        raise ValueError(
            "Current generator expects exactly one island group."
        )

    group_id = next(iter(groups))

    group_name = groups[group_id]

    island_ids = list(islands.keys())

    # --------------------------------------------------------
    # Build island binary data
    # --------------------------------------------------------

    island_data = {}

    for island_id in island_ids:

        island_data[island_id] = build_island(
            islands[island_id],
            name_to_id
        )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    island_group_count = len(groups)
    chunk_count = 0

    island_group_table_offset = HEADER_SIZE

    chunk_table_offset = 0
    terrain_section_offset = 0
    object_section_offset = 0
    npc_section_offset = 0

    header = struct.pack(
        HEADER_FORMAT,

        MAGIC,
        VERSION,
        FLAGS,
        MAP_ID,

        island_group_count,
        chunk_count,

        island_group_table_offset,
        chunk_table_offset,
        terrain_section_offset,
        object_section_offset,
        npc_section_offset,
    )

    if len(header) != HEADER_SIZE:
        raise RuntimeError(
            f"Header is {len(header)} bytes, "
            f"expected {HEADER_SIZE}."
        )

    # --------------------------------------------------------
    # Group location table
    #
    # One 128-bit file range per group.
    # --------------------------------------------------------

    group_table_size = (
        len(groups) * 16
    )

    group_start = (
        HEADER_SIZE +
        group_table_size
    )

    # --------------------------------------------------------
    # Build group
    # --------------------------------------------------------

    group_start_location, group_end_location = group_bounds(
        islands
    )

    group = bytearray()

    # 384-bit group location
    group += pack_location(
        group_start_location,
        group_end_location
    )

    # Number of islands
    group += struct.pack(
        "<I",
        len(island_ids)
    )

    # Reserve island location table
    island_table_offset = len(group)

    group += (
        b"\x00" *
        (len(island_ids) * 16)
    )

    # --------------------------------------------------------
    # Calculate island ranges
    # --------------------------------------------------------

    first_island_offset = (
        group_start +
        len(group)
    )

    island_ranges = []

    current_offset = first_island_offset

    for island_id in island_ids:

        data = island_data[island_id]

        start = current_offset
        end = start + len(data)

        island_ranges.append(
            (
                island_id,
                start,
                end
            )
        )

        current_offset = end

    # --------------------------------------------------------
    # Fill island location table
    # --------------------------------------------------------

    for index, (_, start, end) in enumerate(
        island_ranges
    ):

        offset = (
            island_table_offset +
            index * 16
        )

        group[
            offset:
            offset + 16
        ] = pack_file_range(
            start,
            end
        )

    # --------------------------------------------------------
    # Append islands
    # --------------------------------------------------------

    for island_id, _, _ in island_ranges:

        group += island_data[
            island_id
        ]

    group_data = bytes(group)

    # --------------------------------------------------------
    # Group range
    # --------------------------------------------------------

    group_end = (
        group_start +
        len(group_data)
    )

    group_range = pack_file_range(
        group_start,
        group_end
    )

    # --------------------------------------------------------
    # Write
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "wb"
    ) as file:

        # Header
        file.write(header)

        # Group location table
        file.write(group_range)

        # Group
        file.write(group_data)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("Generated:")
    print(
        f"  {OUTPUT_FILE}"
    )

    print()
    print("Map:")
    print(
        f"  Groups : {len(groups)}"
    )

    print(
        f"  Islands: {len(islands)}"
    )

    print()
    print(
        f"Group {group_id}: {group_name}"
    )

    print(
        f"  Start: {group_start}"
    )

    print(
        f"  End  : {group_end}"
    )

    print()

    for island_id, start, end in island_ranges:

        island = islands[island_id]

        print(
            f"Island {island_id}: "
            f"{island['name']}"
        )

        print(
            f"  Start: {start}"
        )

        print(
            f"  End  : {end}"
        )

        print(
            f"  Size : {end - start}"
        )

    print()
    print(
        f"Header size: {len(header)} bytes"
    )

    print(
        f"File size  : {OUTPUT_FILE.stat().st_size} bytes"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()
