import os
import re
import struct
import sys
import traceback
import xml.dom.minidom
from io import BytesIO

ANIMVERSION = 4

#ANIM format 4
# 'ANIM'
# Version (int)
# total num element refs (int)
# total num frames (int)
# total num events (int)
# Numanims (int)
#   animname (int, string)
#   validfacings (byte bit mask) (xxxx dlur)
#   rootsymbolhash int
#   frame rate (float)
#   num frames (int)
#       x, y, w, h : (all floats)
#       num events(int)
#           event hash
#       num elements(int)
#           symbol hash (int)
#           symbol frame (int)
#           folder hash (int)
#           mat a, b, c, d, tx, ty, tz: (all floats)
#
# num hashed strings (int)
#   hash (int)
#   original string (int, string)

FACING_RIGHT = 1 << 0
FACING_UP = 1 << 1
FACING_LEFT = 1 << 2
FACING_DOWN = 1 << 3
FACING_UPRIGHT = 1 << 4
FACING_UPLEFT = 1 << 5
FACING_DOWNRIGHT = 1 << 6
FACING_DOWNLEFT = 1 << 7


def strhash(str, hashcollection):
    hash = 0
    for c in str:
        v = ord(c.lower())
        hash = (v + (hash << 6) + (hash << 16) - hash) & 0xFFFFFFFF
    hashcollection[hash] = str
    return hash


def get_z_index(element):
    return int(element.attributes["z_index"].value)


EXPORT_DEPTH = 10
hashcollection = {}


def LocalExport(anim_node, outfile):
    name = anim_node.attributes["name"].value.encode('ascii')

    dirs = (re.search("(.*)_up\Z", name), re.search("(.*)_down\Z", name), re.search("(.*)_side\Z", name),
            re.search("(.*)_left\Z", name), re.search("(.*)_right\Z", name), re.search("(.*)_upside\Z", name),
            re.search("(.*)_downside\Z", name), re.search("(.*)_upleft\Z", name), re.search("(.*)_upright\Z", name),
            re.search("(.*)_downleft\Z", name), re.search("(.*)_downright\Z",
                                                          name), re.search("(.*)_45s\Z",
                                                                           name), re.search("(.*)_90s\Z", name))

    facingbyte = FACING_RIGHT | FACING_LEFT | FACING_UP | FACING_DOWN | FACING_UPLEFT | FACING_UPRIGHT | FACING_DOWNLEFT | FACING_DOWNRIGHT

    if dirs[0]:
        name = dirs[0].group(1)
        facingbyte = FACING_UP
    elif dirs[1]:
        name = dirs[1].group(1)
        facingbyte = FACING_DOWN
    elif dirs[2]:
        name = dirs[2].group(1)
        facingbyte = FACING_LEFT | FACING_RIGHT
    elif dirs[3]:
        name = dirs[3].group(1)
        facingbyte = FACING_LEFT
    elif dirs[4]:
        name = dirs[4].group(1)
        facingbyte = FACING_RIGHT
    elif dirs[5]:
        name = dirs[5].group(1)
        facingbyte = FACING_UPLEFT | FACING_UPRIGHT
    elif dirs[6]:
        name = dirs[6].group(1)
        facingbyte = FACING_DOWNLEFT | FACING_DOWNRIGHT
    elif dirs[7]:
        name = dirs[7].group(1)
        facingbyte = FACING_UPLEFT
    elif dirs[8]:
        name = dirs[8].group(1)
        facingbyte = FACING_UPRIGHT
    elif dirs[9]:
        name = dirs[9].group(1)
        facingbyte = FACING_DOWNLEFT
    elif dirs[10]:
        name = dirs[10].group(1)
        facingbyte = FACING_DOWNRIGHT
    elif dirs[11]:
        name = dirs[11].group(1)
        facingbyte = FACING_UPLEFT | FACING_UPRIGHT | FACING_DOWNLEFT | FACING_DOWNRIGHT
    elif dirs[12]:
        name = dirs[12].group(1)
        facingbyte = FACING_UP | FACING_DOWN | FACING_LEFT | FACING_RIGHT

    root = anim_node.attributes["root"].value.encode('ascii')
    num_frames = len(anim_node.getElementsByTagName("frame"))
    frame_rate = float(anim_node.attributes["framerate"].value)

    outfile.write(struct.pack(endianstring + 'i' + str(len(name)) + 's', len(name), name))
    outfile.write(struct.pack(endianstring + 'B', facingbyte))
    outfile.write(struct.pack(endianstring + 'I', strhash(root, hashcollection)))
    outfile.write(struct.pack(endianstring + 'fI', float(frame_rate), num_frames))
    for frame_node in anim_node.getElementsByTagName("frame"):
        outfile.write(
            struct.pack(endianstring + 'ffff', float(frame_node.attributes["x"].value),
                        float(frame_node.attributes["y"].value), float(frame_node.attributes["w"].value),
                        float(frame_node.attributes["h"].value)))
        num_events = len(frame_node.getElementsByTagName("event"))
        outfile.write(struct.pack(endianstring + 'I', num_events))

        for event_node in frame_node.getElementsByTagName("event"):
            outfile.write(
                struct.pack(endianstring + 'I',
                            strhash(event_node.attributes["name"].value.encode('ascii'), hashcollection)))

        elements = frame_node.getElementsByTagName("element")
        try:
            elements = sorted(elements, key=get_z_index)
        except:
            pass

        num_elements = len(elements)
        outfile.write(struct.pack(endianstring + 'I', num_elements))

        eidx = 0
        for element_node in elements:
            outfile.write(
                struct.pack(endianstring + 'I',
                            strhash(element_node.attributes["name"].value.encode('ascii'), hashcollection)))
            outfile.write(struct.pack(endianstring + 'I', int(element_node.attributes["frame"].value)))
            layername = element_node.attributes["layername"].value.encode('ascii').split('/')[-1]
            outfile.write(struct.pack(endianstring + 'I', strhash(layername, hashcollection)))

            z = (eidx / float(num_elements)) * float(EXPORT_DEPTH) - EXPORT_DEPTH * .5
            outfile.write(
                struct.pack(endianstring + 'fffffff', float(element_node.attributes["m_a"].value),
                            float(element_node.attributes["m_b"].value), float(element_node.attributes["m_c"].value),
                            float(element_node.attributes["m_d"].value), float(element_node.attributes["m_tx"].value),
                            float(element_node.attributes["m_ty"].value), z))

            eidx += 1


def CompileAnim(endianstring, xmlstr, outfilename):
    doc = xml.dom.minidom.parseString(xmlstr)
    outfile = BytesIO()

    outfile.write(struct.pack(endianstring + 'cccci', 'A', 'N', 'I', 'M', ANIMVERSION))
    outfile.write(struct.pack(endianstring + 'I', len(doc.getElementsByTagName("element"))))
    outfile.write(struct.pack(endianstring + 'I', len(doc.getElementsByTagName("frame"))))
    outfile.write(struct.pack(endianstring + 'I', len(doc.getElementsByTagName("event"))))
    outfile.write(struct.pack(endianstring + 'I', len(doc.getElementsByTagName("anim"))))

    nodes = doc.getElementsByTagName("anim")
    for anim_node in nodes:
        LocalExport(anim_node, outfile)

    #write out a lookup table of the pre-hashed strings
    outfile.write(struct.pack(endianstring + 'I', len(hashcollection)))
    for hash_idx, name in hashcollection.iteritems():
        outfile.write(struct.pack(endianstring + 'I', hash_idx))
        outfile.write(struct.pack(endianstring + 'i' + str(len(name)) + 's', len(name), name))

    with open(outfilename, "wb") as f:
        f.write(outfile.getvalue())


if __name__ == "__main__":
    workspace = sys.argv[1]
    anim_path = os.path.join(workspace, "anim.xml")
    if not os.path.exists(anim_path):
        sys.stderr.write("Error: There is no anim.xml under dictionary " + workspace + "\n")

    try:
        endianstring = "<"
        with open(anim_path, 'rb') as f:
            CompileAnim(endianstring, f.read(), outfilename=os.path.join(workspace, "bin.bin"))

    except:  # catch *all* exceptions
        e = sys.exc_info()[1]
        sys.stderr.write("Error Exporting {}\n".format(anim_path) + str(e) + "\n")
        traceback.print_exc(file=sys.stderr)
        exit(-1)
