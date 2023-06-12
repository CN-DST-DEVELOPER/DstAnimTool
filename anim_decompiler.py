import os
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

dir = {
    FACING_UP:
    "_up",
    FACING_DOWN:
    "_down",
    FACING_LEFT | FACING_RIGHT:
    "_side",
    FACING_LEFT:
    "_left",
    FACING_RIGHT:
    "_right",
    FACING_UPLEFT | FACING_UPRIGHT:
    "_upside",
    FACING_DOWNLEFT | FACING_DOWNRIGHT:
    "_downside",
    FACING_UPLEFT:
    "_upleft",
    FACING_UPRIGHT:
    "_upright",
    FACING_DOWNLEFT:
    "_downleft",
    FACING_DOWNRIGHT:
    "_downright",
    FACING_UPLEFT | FACING_UPRIGHT | FACING_DOWNLEFT | FACING_DOWNRIGHT:
    "_45s",
    FACING_UP | FACING_DOWN | FACING_LEFT | FACING_RIGHT:
    "_90s",
    FACING_RIGHT | FACING_LEFT | FACING_UP | FACING_DOWN | FACING_UPLEFT | FACING_UPRIGHT | FACING_DOWNLEFT | FACING_DOWNRIGHT:
    ""
}


def strhash(str, hashcollection):
    hash = 0
    for c in str:
        v = ord(c.lower())
        hash = (v + (hash << 6) + (hash << 16) - hash) & 0xFFFFFFFF
    hashcollection[hash] = str
    return hash


def DecompileAnim(endianstring, anim, outfile):
    hashcollection = {}
    infile = BytesIO(anim)

    if infile.read(4).decode() != "ANIM" or struct.unpack(endianstring + 'i', infile.read(4))[0] != ANIMVERSION:
        sys.stderr.write("Error: Input file not match ANIMVERSION_" + str(ANIMVERSION))
        exit(-1)

    element_list = struct.unpack(endianstring + 'I', infile.read(4))[0]
    frame_list = struct.unpack(endianstring + 'I', infile.read(4))[0]
    event_list = struct.unpack(endianstring + 'I', infile.read(4))[0]
    anim_len = struct.unpack(endianstring + 'I', infile.read(4))[0]

    dom = xml.dom.minidom.Document()
    root_node = dom.createElement('Anims')
    dom.appendChild(root_node)

    for _ in range(anim_len):
        anim_node = dom.createElement('anim')
        root_node.appendChild(anim_node)

        anim_name_len = struct.unpack(endianstring + "i", infile.read(4))[0]
        anim_name = struct.unpack(endianstring + str(anim_name_len) + "s", infile.read(anim_name_len))[0]

        facingbyte = struct.unpack(endianstring + "B", infile.read(1))[0]
        anim_node.setAttribute('name', str(anim_name) + dir[facingbyte])

        hash = struct.unpack(endianstring + "I", infile.read(4))[0]
        frame_rate = struct.unpack(endianstring + "f", infile.read(4))[0]
        frames_num = struct.unpack(endianstring + "I", infile.read(4))[0]
        anim_node.setAttribute("root", hash)
        anim_node.setAttribute("framerate", str(frame_rate))
        anim_node.setAttribute("numframes", str(frames_num))

        if frames_num > 0:
            for _ in range(frames_num):
                frame_node = dom.createElement('frame')
                anim_node.appendChild(frame_node)

                x, y, w, h = struct.unpack(endianstring + "ffff", infile.read(16))
                frame_node.setAttribute("w", str(w))
                frame_node.setAttribute("h", str(h))
                frame_node.setAttribute("x", str(x))
                frame_node.setAttribute("y", str(y))

                frame_event_len = struct.unpack(endianstring + "I", infile.read(4))[0]
                for _ in range(0, frame_event_len):
                    frame_event_node = dom.createElement('event')
                    frame_node.appendChild(frame_event_node)
                    frame_event_name_hash = struct.unpack(endianstring + "I", infile.read(4))[0]
                    frame_event_node.setAttribute("name", frame_event_name_hash)

                element_num = struct.unpack(endianstring + "I", infile.read(4))[0]
                for i in range(element_num):
                    elements_node = dom.createElement('element')
                    frame_node.appendChild(elements_node)
                    element_name_hash = struct.unpack(endianstring + "I", infile.read(4))[0]
                    frameint = struct.unpack(endianstring + "I", infile.read(4))[0]
                    layernamehash = struct.unpack(endianstring + "I", infile.read(4))[0]
                    m_a, m_b, m_c, m_d, m_tx, m_ty, z = struct.unpack(endianstring + "fffffff", infile.read(28))
                    elements_node.setAttribute("name", element_name_hash)
                    elements_node.setAttribute("layername", layernamehash)
                    elements_node.setAttribute("frame", str(frameint))
                    elements_node.setAttribute("z_index", str(15 + i))
                    elements_node.setAttribute("m_a", str(m_a))
                    elements_node.setAttribute("m_b", str(m_b))
                    elements_node.setAttribute("m_c", str(m_c))
                    elements_node.setAttribute("m_d", str(m_d))
                    elements_node.setAttribute("m_tx", str(m_tx))
                    elements_node.setAttribute("m_ty", str(m_ty))
                    elements_node.setAttribute("z", str(z))

    hash_list = struct.unpack(endianstring + 'I', infile.read(4))[0]
    for _ in range(hash_list):
        hashid, hashlen = struct.unpack(endianstring + 'Ii', infile.read(8))
        hashstr = struct.unpack(endianstring + str(hashlen) + 's', infile.read(hashlen))[0]
        hashcollection[hashid] = hashstr

    node_list = root_node.getElementsByTagName("anim")
    for node in node_list:
        node.setAttribute("root", hashcollection[node.getAttribute("root")])
        frame_list = node.getElementsByTagName("frame")
        for frame in frame_list:
            event_list = frame.getElementsByTagName("event")
            for event in event_list:
                event.setAttribute("name", hashcollection[event.getAttribute("name")])
            element_list = frame.getElementsByTagName("element")
            for element in element_list:
                element.setAttribute("name", hashcollection[element.getAttribute("name")])
                element.setAttribute("layername", hashcollection[element.getAttribute("layername")])

    with open(os.path.join(workspace, "anim.xml"), "wb") as f:
        root_node.writexml(f, indent='', addindent='\t', newl='\n')


if __name__ == "__main__":
    workspace = sys.argv[1]
    anim_path = os.path.join(workspace, "anim.bin")
    if not os.path.exists(anim_path):
        sys.stderr.write("Error: There is no anim.bin under dictionary " + workspace + "\n")

    try:
        endianstring = "<"
        with open(anim_path, 'rb') as f:
            DecompileAnim(endianstring, f.read(), workspace)

    except:  # catch *all* exceptions
        e = sys.exc_info()[1]
        sys.stderr.write("Error Exporting {}\n".format(anim_path) + str(e) + "\n")
        traceback.print_exc(file=sys.stderr)
        exit(-1)
