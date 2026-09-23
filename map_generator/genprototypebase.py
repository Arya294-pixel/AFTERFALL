import struct
import sys

magic = b"AFMP"
version = 1
flags = 0
map_id = 1
island_group_count = 1
chunk_count = 0

island_group_table_offset = 60
chunk_table_offset = 0
terrain_section_offset = 0
object_section_offset = 0
npc_section_offset = 0

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

print(header)
print("Header size:", len(header))

with open(sys.argv[1], "wb") as f:
    f.write(header)
