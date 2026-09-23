import struct
import sys


HEADER_SIZE = 60
ISLAND_COUNT = 5


def location(start, end):
    """384-bit world-space bounding box."""
    return struct.pack(
        "<6q",
        start[0],
        start[1],
        start[2],
        end[0],
        end[1],
        end[2],
    )


def file_range(start, end):
    """128-bit file range: 64-bit start + 64-bit end."""
    return struct.pack(
        "<QQ",
        start,
        end,
    )


if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <output.afmap>")
    sys.exit(1)


# --------------------------------------------------
# Header information
# --------------------------------------------------

magic = b"AFMP"
version = 1
flags = 0
map_id = 1

island_group_count = 1
chunk_count = 0

island_group_table_offset = HEADER_SIZE
chunk_table_offset = 0
terrain_section_offset = 0
object_section_offset = 0
npc_section_offset = 0


# --------------------------------------------------
# Island data
# --------------------------------------------------

islands = []

for i in range(ISLAND_COUNT):
    island_location = location(
        (i * 1000, 0, 0),
        (i * 1000 + 500, 500, 500),
    )

    island_data = f"ISLAND_{i + 1}".encode()

    islands.append({
        "location": island_location,
        "data": island_data,
    })


# --------------------------------------------------
# Group
# --------------------------------------------------

group_location = location(
    (0, 0, 0),
    (4500, 500, 500),
)

group = bytearray()

# Group location
group += group_location

# Number of islands in this group
group += struct.pack("<I", ISLAND_COUNT)

# Reserve island locations.
#
# We don't know the final offsets yet.
# Each entry is:
#
#     uint64 start
#     uint64 end
#
island_location_table_offset = len(group)

group += b"\x00" * (ISLAND_COUNT * 16)


# --------------------------------------------------
# Calculate where island data starts
# --------------------------------------------------

island_data_start = (
    HEADER_SIZE
    + len(group)
)

island_ranges = []

current_offset = island_data_start

for island in islands:
    start = current_offset

    island_size = (
        len(island["location"])
        + len(island["data"])
    )

    end = start + island_size

    island_ranges.append((start, end))

    current_offset = end


# --------------------------------------------------
# Fill island location table
# --------------------------------------------------

for i, (start, end) in enumerate(island_ranges):

    offset = island_location_table_offset + (i * 16)

    group[offset:offset + 16] = file_range(
        start,
        end,
    )


# --------------------------------------------------
# Final group
# --------------------------------------------------

group_data = bytes(group)


# --------------------------------------------------
# Header
# --------------------------------------------------

header = struct.pack(
    "<4sHHIIIQQQQQ",
    magic,
    version,
    flags,
    map_id,
    island_group_count,
    chunk_count,
    island_group_table_offset,
    chunk_table_offset,
    terrain_section_offset,
    object_section_offset,
    npc_section_offset,
)


# --------------------------------------------------
# Write file
# --------------------------------------------------

with open(sys.argv[1], "wb") as f:

    # Header
    f.write(header)

    # Group
    f.write(group_data)

    # Islands
    for island in islands:
        f.write(island["location"])
        f.write(island["data"])


print("Created:", sys.argv[1])
print("Header size:", len(header))
print("Group size:", len(group_data))

for i, (start, end) in enumerate(island_ranges, 1):
    print(
        f"Island {i}: "
        f"start={start}, "
        f"end={end}, "
        f"size={end - start}"
    )
