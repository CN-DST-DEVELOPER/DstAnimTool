import os
import struct
import sys
import traceback
import xml.dom.minidom
from io import BytesIO

BUILDVERSION = 6

#BUILD format 6
# 'BILD'
# Version (int)
# total symbols;
# total frames;
# build name (int, string)
# num materials
#   material texture name (int, string)
#for each symbol:
#   symbol hash (int)
#   num frames (int)
#       frame num (int)
#       frame duration (int)
#       bbox x,y,w,h (floats)
#       vb start index (int)
#       num verts (int)

# num vertices (int)
#   x,y,z,u,v,w (all floats)
#
# num hashed strings (int)
#   hash (int)
#   original string (int, string)


def strhash(str, hashcollection):
    hash = 0
    for c in str:
        v = ord(c.lower())
        hash = (v + (hash << 6) + (hash << 16) - hash) & 0xFFFFFFFF
    hashcollection[hash] = str
    return hash


def DecompileBuild(endianstring, build, workspace):
    hashcollection = {}
    infile = BytesIO(build)

    if infile.read(4).decode() != "BILD" or struct.unpack(endianstring + 'i', infile.read(4))[0] != BUILDVERSION:
        sys.stderr.write("Error: Input file not match BUILDVERSION_" + BUILDVERSION)
        exit(-1)

    dom = xml.dom.minidom.Document()
    root_node = dom.createElement('root')
    build_root_node = dom.createElement('Build')
    root_node.appendChild(build_root_node)

    symbol_len = struct.unpack(endianstring + 'I', infile.read(4))[0]
    frame_len_total = struct.unpack(endianstring + 'I', infile.read(4))[0]
    build_name_len = struct.unpack(endianstring + "i", infile.read(4))[0]
    build_name = struct.unpack(endianstring + str(build_name_len) + 's', infile.read(build_name_len))[0]
    build_root_node.setAttribute("name", build_name.decode())

    atlases_len = struct.unpack(endianstring + 'I', infile.read(4))[0]
    for _ in range(atlases_len):
        atlas_node = dom.createElement('Atlas')
        root_node.appendChild(atlas_node)
        texture_node = dom.createElement('Texture')
        atlas_node.appendChild(texture_node)
        namelen = struct.unpack(endianstring + "i", infile.read(4))[0]
        name = struct.unpack(endianstring + str(namelen) + 's', infile.read(namelen))[0]
        texture_node.setAttribute("filename", name.decode())
        build_root_node.appendChild(texture_node.cloneNode(True))

    for _ in range(symbol_len):
        symbol_node = dom.createElement('Symbol')
        build_root_node.appendChild(symbol_node)
        symbol_name_hash = struct.unpack(endianstring + 'I', infile.read(4))[0]
        symbol_node.setAttribute("namehash", str(symbol_name_hash))
        frame_len = struct.unpack(endianstring + 'I', infile.read(4))[0]
        for frame_idx in range(frame_len):
            frame_node = dom.createElement('Frame')
            symbol_node.appendChild(frame_node)
            framenum = struct.unpack(endianstring + 'I', infile.read(4))[0]
            frame_node.setAttribute("framenum", str(framenum))
            duration = struct.unpack(endianstring + 'I', infile.read(4))[0]
            frame_node.setAttribute("duration", str(duration))
            x, y, w, h = struct.unpack(endianstring + "ffff", infile.read(16))
            frame_node.setAttribute("w", str(w))
            frame_node.setAttribute("h", str(h))
            frame_node.setAttribute("x", str(x))
            frame_node.setAttribute("y", str(y))
            alphaidx = struct.unpack(endianstring + 'I', infile.read(4))[0]
            frame_node.setAttribute("alphaidx", str(alphaidx))
            alphacount = struct.unpack(endianstring + 'I', infile.read(4))[0]
            frame_node.setAttribute("alphacount", str(alphacount))

    atlas_nodes = root_node.getElementsByTagName('Atlas')

    alphavertslen = struct.unpack(endianstring + 'I', infile.read(4))[0]
    for _ in range(alphavertslen // 6):
        u1 = v1 = 1
        u2 = v2 = 0
        w = 0
        for _ in range(6):
            x, y, z, u, v, w = struct.unpack(endianstring + "ffffff", infile.read(24))
            alphavert_node = dom.createElement("Alphavert")
            alphavert_node.setAttribute("x", str(x))
            alphavert_node.setAttribute("y", str(y))
            alphavert_node.setAttribute("z", str(z))
            alphavert_node.setAttribute("u", str(u))
            alphavert_node.setAttribute("v", str(v))
            alphavert_node.setAttribute("w", str(w))
            build_root_node.appendChild(alphavert_node)
            u1 = min(u1, u)
            u2 = max(u2, u)
            v1 = min(v1, v)
            v2 = max(v2, v)
        for atlas_node in atlas_nodes:
            texture_node = atlas_node.getElementsByTagName("Texture")[0]
            if texture_node.getAttribute("filename") == "atlas-" + str(int(w)) + ".tex":
                elements_node = atlas_node.getElementsByTagName("Elements")
                if not len(elements_node):
                    elements_node = dom.createElement('Elements')
                    atlas_node.appendChild(elements_node)
                else:
                    elements_node = elements_node[0]
                element_node = dom.createElement('Element')
                element_node.setAttribute("name", str(len(elements_node.getElementsByTagName("Element"))) + ".tex")
                element_node.setAttribute("u1", str(u1))
                element_node.setAttribute("u2", str(u2))
                element_node.setAttribute("v1", str(v1))
                element_node.setAttribute("v2", str(v2))
                elements_node.appendChild(element_node)

    try:
        hash_list = struct.unpack(endianstring + 'I', infile.read(4))[0]
        for _ in range(hash_list):
            hash_id, hash_len = struct.unpack(endianstring + 'Ii', infile.read(8))
            hash_str = struct.unpack(endianstring + str(hash_len) + 's', infile.read(hash_len))[0]
            hashcollection[str(hash_id)] = hash_str

        node_list = build_root_node.getElementsByTagName("Symbol")

        for node in node_list:
            hash_id = node.getAttribute("namehash")
            if hashcollection[hash_id]:
                node.removeAttribute("namehash")
                node.setAttribute("name", hashcollection[hash_id])
    except:
        pass

    with open(os.path.join(workspace, "build.xml"), "wb") as f:
        build_root_node.writexml(f, indent='', addindent='\t', newl='\n')

    for atlas_root in root_node.getElementsByTagName('Atlas'):
        texture_node = atlas_root.getElementsByTagName("Texture")[0]
        with open(os.path.join(workspace, texture_node.getAttribute("filename")[:-4] + ".xml"), "wb") as f:
            atlas_root.writexml(f)


if __name__ == "__main__":
    workspace = sys.argv[1]
    build_path = os.path.join(workspace, "build.bin")
    if not os.path.exists(build_path):
        sys.stderr.write("Error: There is no anim.bin under dictionary " + workspace + "\n")

    try:
        endianstring = "<"
        with open(build_path, 'rb') as f:
            DecompileBuild(endianstring, f.read(), workspace)

    except:  # catch *all* exceptions
        e = sys.exc_info()[1]
        sys.stderr.write("Error Exporting {}\n".format(build_path) + str(e) + "\n")
        traceback.print_exc(file=sys.stderr)
        exit(-1)
