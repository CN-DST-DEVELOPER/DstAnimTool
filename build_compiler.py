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


def CompileBuild(endianstring, xmlstr, outfilename):
    hashcollection = {}

    doc = xml.dom.minidom.parseString(xmlstr)
    outfile = BytesIO()

    outfile.write(struct.pack(endianstring + 'cccci', 'B', 'I', 'L', 'D', BUILDVERSION))

    outfile.write(struct.pack(endianstring + 'I', len(doc.getElementsByTagName("Symbol"))))
    outfile.write(struct.pack(endianstring + 'I', len(doc.getElementsByTagName("Frame"))))

    build_name = doc.getElementsByTagName("Build")[0].attributes["name"].value.encode('ascii')
    build_name = os.path.splitext(build_name)[0]
    outfile.write(struct.pack(endianstring + 'i' + str(len(build_name)) + 's', len(build_name), build_name))

    texture_nodes = doc.getElementsByTagName('Texture')

    #write out the number of atlases:
    outfile.write(struct.pack(endianstring + 'I', len(texture_nodes)))
    for texture_node in texture_nodes:
        tex_name = texture_node.getAttribute("filename").encode('ascii')
        outfile.write(struct.pack(endianstring + 'i' + str(len(tex_name)) + 's', len(tex_name), tex_name))

    symbol_nodes = doc.getElementsByTagName("Symbol")

    for symbol_node in symbol_nodes:  #doc.getElementsByTagName("Symbol"):
        if symbol_node.hasAttribute("namehash"):
            outfile.write(struct.pack(endianstring + 'I', int(symbol_node.getAttribute("namehash"))))
        else:
            symbol_name = symbol_node.attributes["name"].value.encode('ascii')
            outfile.write(struct.pack(endianstring + 'I', strhash(symbol_name, hashcollection)))
        outfile.write(struct.pack(endianstring + 'I', len(symbol_node.getElementsByTagName("Frame"))))

        for frame_node in symbol_node.getElementsByTagName("Frame"):
            framenum = int(frame_node.attributes["framenum"].value)
            duration = int(frame_node.attributes["duration"].value)

            w = float(frame_node.attributes["w"].value)
            h = float(frame_node.attributes["h"].value)
            x = float(frame_node.attributes["x"].value)
            y = float(frame_node.attributes["y"].value)

            outfile.write(struct.pack(endianstring + 'I', framenum))
            outfile.write(struct.pack(endianstring + 'I', duration))
            outfile.write(struct.pack(endianstring + 'ffff', x, y, w, h))

            alphaidx = int(frame_node.attributes["alphaidx"].value)
            alphacount = int(frame_node.attributes["alphacount"].value)

            outfile.write(struct.pack(endianstring + 'I', alphaidx))
            outfile.write(struct.pack(endianstring + 'I', alphacount))

    alphaverts = doc.getElementsByTagName("Alphavert")
    outfile.write(struct.pack(endianstring + 'I', len(alphaverts)))
    for vert in alphaverts:
        outfile.write(
            struct.pack(endianstring + 'ffffff', float(vert.attributes["x"].value), float(vert.attributes["y"].value),
                        float(vert.attributes["z"].value), float(vert.attributes["u"].value),
                        float(vert.attributes["v"].value), float(vert.attributes["w"].value)))

    if len(hashcollection):
        outfile.write(struct.pack(endianstring + 'I', len(hashcollection)))
        for hash_idx, tex_name in hashcollection.iteritems():
            outfile.write(struct.pack(endianstring + 'I', hash_idx))
            outfile.write(struct.pack(endianstring + 'i' + str(len(tex_name)) + 's', len(tex_name), tex_name))

    with open(outfilename, "wb") as f:
        f.write(outfile.getvalue())


if __name__ == "__main__":
    workspace = sys.argv[1]
    build_path = os.path.join(workspace, "build.xml")
    if not os.path.exists(build_path):
        sys.stderr.write("Error: There is no build.xml under dictionary " + workspace + "\n")

    try:
        endianstring = "<"
        with open(build_path, 'rb') as f:
            CompileBuild(endianstring, f.read(), outfilename=os.path.join(workspace, "build.bin"))

    except:
        e = sys.exc_info()[1]
        sys.stderr.write("Error Exporting {}\n".format(build_path) + str(e) + "\n")
        traceback.print_exc(file=sys.stderr)
        exit(-1)
