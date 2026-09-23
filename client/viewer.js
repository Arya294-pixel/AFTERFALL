"use strict";


const MAP_PATH = "/afterfall.afmap";


const HEADER_SIZE = 60;


/*
    AFMAP header:

    0x00  4   magic
    0x04  2   version
    0x06  2   flags
    0x08  4   map_id
    0x0C  4   island_group_count
    0x10  4   chunk_count

    0x14  8   island_group_table_offset
    0x1C  8   chunk_table_offset
    0x24  8   terrain_section_offset
    0x2C  8   object_section_offset
    0x34  8   npc_section_offset
*/


function readInt64(view, offset) {
    return Number(
        view.getBigInt64(
            offset,
            true
        )
    );
}


function readUint64(view, offset) {
    return Number(
        view.getBigUint64(
            offset,
            true
        )
    );
}


function readBounds(view, offset) {

    return {
        start: {
            x: readInt64(view, offset),
            y: readInt64(view, offset + 8),
            z: readInt64(view, offset + 16)
        },

        end: {
            x: readInt64(view, offset + 24),
            y: readInt64(view, offset + 32),
            z: readInt64(view, offset + 40)
        }
    };
}


function readStringMagic(view) {

    let result = "";

    for (let i = 0; i < 4; i++) {

        result += String.fromCharCode(
            view.getUint8(i)
        );
    }

    return result;
}


function parseHeader(view) {

    const magic = readStringMagic(view);

    if (magic !== "AFMP") {
        throw new Error(
            `Invalid AFMAP magic: ${magic}`
        );
    }

    const header = {

        magic,

        version:
            view.getUint16(
                4,
                true
            ),

        flags:
            view.getUint16(
                6,
                true
            ),

        mapId:
            view.getUint32(
                8,
                true
            ),

        groupCount:
            view.getUint32(
                12,
                true
            ),

        chunkCount:
            view.getUint32(
                16,
                true
            ),

        groupTableOffset:
            readUint64(
                view,
                20
            ),

        chunkTableOffset:
            readUint64(
                view,
                28
            ),

        terrainSectionOffset:
            readUint64(
                view,
                36
            ),

        objectSectionOffset:
            readUint64(
                view,
                44
            ),

        npcSectionOffset:
            readUint64(
                view,
                52
            )
    };

    return header;
}


function readFileRange(view, offset) {

    return {
        start:
            readUint64(
                view,
                offset
            ),

        end:
            readUint64(
                view,
                offset + 8
            )
    };
}


function readObject(view, offset) {

    return {

        type:
            view.getUint16(
                offset,
                true
            ),

        x:
            readInt64(
                view,
                offset + 2
            ),

        y:
            readInt64(
                view,
                offset + 10
            ),

        z:
            readInt64(
                view,
                offset + 18
            )
    };
}


function parseIsland(view, range) {

    let offset = range.start;

    const bounds =
        readBounds(
            view,
            offset
        );

    offset += 48;


    /*
        Objects
    */

    const objectCount =
        view.getUint32(
            offset,
            true
        );

    offset += 4;

    const objects = [];

    for (
        let i = 0;
        i < objectCount;
        i++
    ) {

        objects.push(
            readObject(
                view,
                offset
            )
        );

        offset += 26;
    }


    /*
        NPCs
    */

    const npcCount =
        view.getUint32(
            offset,
            true
        );

    offset += 4;

    const npcs = [];

    for (
        let i = 0;
        i < npcCount;
        i++
    ) {

        npcs.push(
            readObject(
                view,
                offset
            )
        );

        offset += 26;
    }


    /*
        Bosses
    */

    const bossCount =
        view.getUint32(
            offset,
            true
        );

    offset += 4;

    const bosses = [];

    for (
        let i = 0;
        i < bossCount;
        i++
    ) {

        bosses.push(
            readObject(
                view,
                offset
            )
        );

        offset += 26;
    }


    if (offset !== range.end) {

        throw new Error(
            `Island parsing mismatch: ` +
            `${offset} !== ${range.end}`
        );
    }


    return {
        bounds,
        objects,
        npcs,
        bosses
    };
}


function parseGroup(view, range) {

    let offset = range.start;


    /*
        Group bounds
    */

    const bounds =
        readBounds(
            view,
            offset
        );

    offset += 48;


    /*
        Island count
    */

    const islandCount =
        view.getUint32(
            offset,
            true
        );

    offset += 4;


    /*
        Island location table
    */

    const islandRanges = [];

    for (
        let i = 0;
        i < islandCount;
        i++
    ) {

        islandRanges.push(
            readFileRange(
                view,
                offset
            )
        );

        offset += 16;
    }


    /*
        Island data
    */

    const islands = [];

    for (
        let i = 0;
        i < islandRanges.length;
        i++
    ) {

        islands.push(
            parseIsland(
                view,
                islandRanges[i]
            )
        );
    }


    if (offset > range.end) {

        throw new Error(
            "Group parsing exceeded group boundary."
        );
    }


    return {
        bounds,
        islandRanges,
        islands
    };
}


function renderMap(header, groups) {

    const mapElement =
        document.getElementById(
            "map"
        );

    mapElement.innerHTML = "";


    for (
        let groupIndex = 0;
        groupIndex < groups.length;
        groupIndex++
    ) {

        const group =
            groups[groupIndex];


        const groupTitle =
            document.createElement(
                "h2"
            );

        groupTitle.textContent =
            `Group ${groupIndex + 1}`;

        mapElement.appendChild(
            groupTitle
        );


        group.islands.forEach(
            (island, islandIndex) => {

                const element =
                    document.createElement(
                        "div"
                    );

                element.className =
                    "island";


                const title =
                    document.createElement(
                        "h3"
                    );

                title.textContent =
                    `Island ${islandIndex + 1}`;

                element.appendChild(
                    title
                );


                const bounds =
                    document.createElement(
                        "div"
                    );

                bounds.textContent =
                    `Bounds: ` +
                    `(${island.bounds.start.x}, ` +
                    `${island.bounds.start.y}, ` +
                    `${island.bounds.start.z}) → ` +
                    `(${island.bounds.end.x}, ` +
                    `${island.bounds.end.y}, ` +
                    `${island.bounds.end.z})`;

                element.appendChild(
                    bounds
                );


                const info =
                    document.createElement(
                        "div"
                    );

                info.textContent =
                    `Objects: ${island.objects.length} | ` +
                    `NPCs: ${island.npcs.length} | ` +
                    `Bosses: ${island.bosses.length}`;

                element.appendChild(
                    info
                );


                island.objects.forEach(
                    object => {

                        const objectElement =
                            document.createElement(
                                "div"
                            );

                        objectElement.className =
                            "object";

                        objectElement.textContent =
                            `Object ${object.type}: ` +
                            `(${object.x}, ` +
                            `${object.y}, ` +
                            `${object.z})`;

                        element.appendChild(
                            objectElement
                        );
                    }
                );


                mapElement.appendChild(
                    element
                );
            }
        );
    }
}


async function main() {

    const status =
        document.getElementById(
            "status"
        );

    try {

        const response =
            await fetch(
                MAP_PATH
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const buffer =
            await response.arrayBuffer();


        status.textContent =
            `Loaded ${buffer.byteLength} bytes`;

        status.className =
            "success";


        if (
            buffer.byteLength <
            HEADER_SIZE
        ) {

            throw new Error(
                "File is smaller than AFMAP header."
            );
        }


        const view =
            new DataView(
                buffer
            );


        const header =
            parseHeader(
                view
            );


        console.log(
            "AFMAP header:",
            header
        );


        /*
            Read group location table.
        */

        const groups = [];

        let offset =
            header.groupTableOffset;


        for (
            let i = 0;
            i < header.groupCount;
            i++
        ) {

            const range =
                readFileRange(
                    view,
                    offset
                );

            offset += 16;


            console.log(
                `Group ${i + 1}:`,
                range
            );


            groups.push(
                parseGroup(
                    view,
                    range
                )
            );
        }


        renderMap(
            header,
            groups
        );


        console.log(
            "Parsed groups:",
            groups
        );


    } catch (error) {

        console.error(
            error
        );


        status.textContent =
            `ERROR: ${error.message}`;

        status.className =
            "error";
    }
}


main();
