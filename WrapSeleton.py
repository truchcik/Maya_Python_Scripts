# Wrap skeleton
# Select:
#   - 1 object: root -> expands hierarchy, builds Skeleton_Mesh only
#   - 3 objects: root, source mesh, target mesh -> full service (blendShape + wrap + move bones)
#
# 1 create mesh fitting bones
# 2 deforms mesh by delta between two cage meshes
# 3 fits bones to deformed mesh vtx positions

import maya.cmds as cmds
import maya.OpenMaya as om1
import maya.api.OpenMaya as om2

# -------------------------
# Helpers
# -------------------------

def _is_mesh_transform(x):
    """Transform with at least one mesh shape child (no ni=True assumptions)."""
    if not cmds.objExists(x):
        return False
    shapes = cmds.listRelatives(x, shapes=True, fullPath=True) or []
    return any(cmds.nodeType(s) == "mesh" for s in shapes)


def _get_first_mesh_shape(x):
    """Return first mesh shape under transform (fullPath)."""
    shapes = cmds.listRelatives(x, shapes=True, fullPath=True) or []
    for s in shapes:
        if cmds.nodeType(s) == "mesh":
            return s
    return None


def _list_hierarchy(root):
    """
    Return transform hierarchy starting at root.
    Skips: *_GRP and *Constraint1
    """
    root = str(root)
    out = [root]

    def walk(parent):
        if parent.endswith("_GRP"):
            return
        kids = cmds.listRelatives(parent, children=True, type="transform", fullPath=False) or []
        for k in kids:
            if k.endswith("Constraint1"):
                continue
            out.append(k)
            walk(k)

    walk(root)
    return out


def set_selection():
    """
    Expands selection  
    Returns: (bones, src, trg) where src/trg can be None
    """
    sel = cmds.ls(selection=True, long=False) or []

    if len(sel) == 1:
        bones = _list_hierarchy(sel[0])
        cmds.select(bones, r=True)
        print("1 obj selected. Skeleton only")
        return bones, None, None

    if len(sel) == 3:
        root, src, trg = sel[0], sel[-2], sel[-1]
        bones = _list_hierarchy(root)
        cmds.select(bones + [src, trg], r=True)
        print("3 objs selected. Full service")
        return bones, src, trg

    raise RuntimeError("Please select: (1) root OR (3) root + sourceMesh + targetMesh")


# -------------------------
# Build skeleton mesh (unconnected triangles)
# -------------------------

def make_skel_mesh(bones, name="Skeleton_Mesh"):
    """
    Create a mesh with verts at bone positions.
    Unconnected triangles to avoid merge issues (same as your original approach).
    Vertex order: first len(bones) verts correspond to bones.
    """
    # Gather world positions
    loc_pos = [cmds.xform(b, q=True, ws=True, t=True) for b in bones]
    verts = [om1.MPoint(p[0], p[1], p[2]) for p in loc_pos]

    # Pad to multiple of 3
    r = len(verts) % 3
    if r:
        verts.extend(verts[: (3 - r)])

    mesh_fn = om1.MFnMesh()
    tri = om1.MPointArray()
    tri.setLength(3)

    for t in range(len(verts) // 3):
        i = t * 3
        tri.set(verts[i], 0)
        tri.set(verts[i + 1], 1)
        tri.set(verts[i + 2], 2)
        mesh_fn.addPolygon(tri, False)

    # mesh_fn.fullPathName() is the shape; parent is transform
    shape = mesh_fn.fullPathName()
    parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
    if not parents:
        raise RuntimeError("Failed to find transform for created skeleton mesh.")
    tr = parents[0]

    if cmds.objExists(name):
        name = cmds.incrementName(name)
    tr = cmds.rename(tr, name)
    return tr


# -------------------------
# Delta deformation setup (blendshape + wrap)
# -------------------------

def def_by_delta(skel_mesh, src, trg, blend_name="skelBlend"):
    if not _is_mesh_transform(src):
        raise RuntimeError("Source mesh must be a mesh transform.")
    if not _is_mesh_transform(trg):
        raise RuntimeError("Target mesh must be a mesh transform.")

    # Keep your selection-driven order
    cmds.select([trg, src], r=True)
    blend_nodes = cmds.blendShape(automatic=True, name=blend_name, en=True) or []
    if not blend_nodes:
        raise RuntimeError("blendShape creation failed.")
    blend = blend_nodes[0]

    cmds.select([skel_mesh, src], r=True)
    cmds.CreateWrap()

    # Set first target weight to 1.0 (robust, avoids alias naming)
    cmds.blendShape(blend, e=True, weight=[(0, 1.0)])
    return blend


# -------------------------
# Fast vertex read + move bones
# -------------------------

def _mesh_world_points(mesh_transform):
    shape = _get_first_mesh_shape(mesh_transform)
    if not shape:
        raise RuntimeError(f"Mesh has no shape: {mesh_transform}")

    sel = om2.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    mfn = om2.MFnMesh(dag)

    pts = mfn.getPoints(om2.MSpace.kWorld)
    return [(p.x, p.y, p.z) for p in pts]


def move_bones_to_vertices(bones, skel_mesh):
    pts = _mesh_world_points(skel_mesh)
    n = min(len(bones), len(pts))  # padded verts may exceed bones

    for i in range(n):
        x, y, z = pts[i]
        cmds.xform(bones[i], ws=True, t=(x, y, z))


# -------------------------
# Run
# -------------------------

def run():
    cmds.undoInfo(openChunk=True)
    cmds.refresh(suspend=True)
    try:
        bones, src, trg = set_selection()

        print("Hierarchy parent:", bones[0])
        if src and trg:
            print("Source mesh:", src)
            print("Target mesh:", trg)

        skel_mesh = make_skel_mesh(bones)

        if src and trg:
            def_by_delta(skel_mesh, src, trg)
            move_bones_to_vertices(bones, skel_mesh)

        cmds.select(bones, r=True)

    finally:
        cmds.refresh(suspend=False)
        cmds.undoInfo(closeChunk=True)


run()
