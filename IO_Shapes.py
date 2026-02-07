# IO meshes vtx positions Maya API and JSON
# - Import Position / Morph position use automatic reorder + partial match confirmations
# - If nothing selected: scans scene by vertex count and lets user pick matches (radio buttons)
# G:\nauka\Scripts_Python\Scripts_Python_Maya\PyMel\IO_Shapes

import json
import pymel.core as pm
import maya.cmds as cmds
import maya.api.OpenMaya as api


# ----------------------------
# JSON IO
# ----------------------------
def open_json(path):
    with open(path, "r") as f:
        return json.load(f)  # list(meshes) -> list(verts) -> [x,y,z]


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f)


# ----------------------------
# Mesh helpers
# ----------------------------
def _as_mesh_shape(node):
    n = pm.PyNode(node)
    if isinstance(n, pm.nodetypes.Mesh): return n
    if isinstance(n, pm.nodetypes.Transform):
        shapes = n.getShapes(noIntermediate=True)
        if shapes and isinstance(shapes[0], pm.nodetypes.Mesh): return shapes[0]
    raise RuntimeError("Node is not a mesh (or has no visible mesh shape): {}".format(node))


def mesh_vertex_count(mesh_or_transform):
    shp = _as_mesh_shape(mesh_or_transform)
    dag = api.MGlobal.getSelectionListByName(shp.name()).getDagPath(0)
    return api.MFnMesh(dag).numVertices


def set_positions(mesh_or_transform, posa):
    shp = _as_mesh_shape(mesh_or_transform)
    dag = api.MGlobal.getSelectionListByName(shp.name()).getDagPath(0)
    mfn = api.MFnMesh(dag)

    positions = mfn.getPoints()
    if len(positions) != len(posa):
        raise RuntimeError("Vertex count mismatch for {}: mesh={}, json={}".format(shp.name(), len(positions), len(posa)))

    new_pos = [p for p in positions]
    for i in range(len(posa)):
        new_pos[i][0], new_pos[i][1], new_pos[i][2] = posa[i][0], posa[i][1], posa[i][2]
    mfn.setPoints(new_pos)


def get_positions(mesh_or_transform):
    shp = _as_mesh_shape(mesh_or_transform)
    dag = api.MGlobal.getSelectionListByName(shp.name()).getDagPath(0)
    mfn = api.MFnMesh(dag)
    pts = mfn.getPoints()
    return [[pts[i][0], pts[i][1], pts[i][2]] for i in range(len(pts))]


# ----------------------------
# Confirm dialogs
# ----------------------------
def _scroll_confirm_matched_unmatched(matched_lines, unmatched_lines, title="Vertex Count Matching", header="Vertex count fits only for some meshes."):
    """
    matched_lines: list[str]
    unmatched_lines: list[str]
    Returns True if Continue, False otherwise.
    """
    def _ui():
        form = cmds.setParent(q=True)

        header_txt = cmds.text(label=header, align="left")
        counts_txt = cmds.text(label="Matched: {}    Unmatched: {}".format(len(matched_lines), len(unmatched_lines)), align="left")

        matched_lbl = cmds.text(label="Matched meshes", align="left")
        matched_list = cmds.textScrollList(numberOfRows=12, allowMultiSelection=True)
        if matched_lines: cmds.textScrollList(matched_list, e=True, append=matched_lines)

        unmatched_lbl = cmds.text(label="Unmatched meshes", align="left")
        unmatched_list = cmds.textScrollList(numberOfRows=12, allowMultiSelection=True)
        if unmatched_lines: cmds.textScrollList(unmatched_list, e=True, append=unmatched_lines)

        btn_continue = cmds.button(label="Continue", height=32, c=lambda *_: cmds.layoutDialog(dismiss="Continue"))
        btn_cancel = cmds.button(label="Cancel", height=32, c=lambda *_: cmds.layoutDialog(dismiss="Cancel"))

        cmds.formLayout(
            form, e=True,
            attachForm=[
                (header_txt, "top", 10), (header_txt, "left", 10), (header_txt, "right", 10),
                (counts_txt, "left", 10), (counts_txt, "right", 10),

                (matched_lbl, "left", 10),
                (unmatched_lbl, "right", 10),

                (matched_list, "left", 10),
                (unmatched_list, "right", 10),

                (btn_continue, "left", 10), (btn_continue, "bottom", 10),
                (btn_cancel, "right", 10), (btn_cancel, "bottom", 10),
            ],
            attachControl=[
                (counts_txt, "top", 6, header_txt),

                (matched_lbl, "top", 10, counts_txt),
                (unmatched_lbl, "top", 10, counts_txt),

                (matched_list, "top", 4, matched_lbl),
                (unmatched_list, "top", 4, unmatched_lbl),

                (matched_list, "bottom", 10, btn_continue),
                (unmatched_list, "bottom", 10, btn_continue),

                (btn_cancel, "left", 10, btn_continue),
            ],
            attachPosition=[
                (matched_lbl, "right", 5, 50),
                (matched_list, "right", 5, 50),

                (unmatched_lbl, "left", 5, 50),
                (unmatched_list, "left", 5, 50),

                (btn_continue, "right", 5, 50),
                (btn_cancel, "left", 5, 50),
            ]
        )

    result = cmds.layoutDialog(title=title, ui=_ui)
    return result == "Continue"


def _confirm_simple(message, title="Warning"):
    res = cmds.confirmDialog(title=title, message=message, button=["Continue", "Cancel"], defaultButton="Continue", cancelButton="Cancel", dismissString="Cancel")
    return res == "Continue"


# ----------------------------
# Matching / reorder logic with selection
# ----------------------------
def _selection_matches_json_in_order(sel, pos_list):
    if len(sel) != len(pos_list): return False
    for i, obj in enumerate(sel):
        if mesh_vertex_count(obj) != len(pos_list[i]): return False
    return True


def _full_reorder_to_match_json(sel, pos_list):
    """If possible, returns (True, reordered_sel). Requires len(sel)==len(pos_list)."""
    if len(sel) != len(pos_list): return False, sel
    targets = [len(p) for p in pos_list]
    counts = [mesh_vertex_count(o) for o in sel]
    used = [False] * len(sel)
    reordered = []
    for t in targets:
        found = -1
        for i, c in enumerate(counts):
            if not used[i] and c == t:
                found = i
                break
        if found == -1:
            return False, sel
        used[found] = True
        reordered.append(sel[found])
    return True, reordered


def _partial_match(sel, pos_list):
    """
    Returns list of pairs (json_index, mesh_obj) where vertex counts match.
    Greedy in JSON order; each mesh used at most once.
    """
    targets = [len(p) for p in pos_list]
    counts = [mesh_vertex_count(o) for o in sel]
    used = [False] * len(sel)

    pairs = []
    for j, t in enumerate(targets):
        found = -1
        for i, c in enumerate(counts):
            if not used[i] and c == t:
                found = i
                break
        if found != -1:
            used[found] = True
            pairs.append((j, sel[found]))
    return pairs


def resolve_mapping_with_user_confirm(sel, pos_list):
    """
    Implements:
    1) If order proper -> full apply
    2) If order improper but counts fit and can reorder -> ask confirm, reorder selection if continue
    3) If order improper and counts don't fit (or full reorder impossible) but some match -> ask confirm with matched/unmatched lists

    Returns:
      ("full", reordered_sel) or ("partial", pairs) or (None, None)
    """
    if not sel:
        return None, None

    # Rule 1
    if _selection_matches_json_in_order(sel, pos_list):
        return "full", sel

    # Rule 2
    if len(sel) == len(pos_list):
        ok, reordered = _full_reorder_to_match_json(sel, pos_list)
        if ok:
            if _confirm_simple("Selection succesfully reordered to fit JSON order. Continue?"):
                pm.select(reordered, r=True)
                return "full", reordered
            return None, None

    # Rule 3
    pairs = _partial_match(sel, pos_list)
    if not pairs:
        cmds.warning("No meshes could be matched to JSON by vertex count. Aborting.")
        return None, None

    matched_meshes = [obj for _, obj in pairs]
    matched_lines = ["{}  ->  JSON[{}] (vtx={})".format(obj.name(), j, len(pos_list[j])) for j, obj in pairs]
    unmatched_lines = [obj.name() for obj in sel if obj not in matched_meshes]

    if _scroll_confirm_matched_unmatched(matched_lines, unmatched_lines, title="Vertex Count Matching"):
        return "partial", pairs
    return None, None


# ----------------------------
# Scene scan + chooser with no selection
# ----------------------------
def _list_scene_mesh_transforms():
    meshes = pm.ls(type="mesh", noIntermediate=True)
    xforms = []
    seen = set()
    for m in meshes:
        p = m.getParent()
        if p and p not in seen:
            seen.add(p)
            xforms.append(p)
    return xforms


def _build_candidates_by_vtx(scene_meshes):
    """
    Returns dict vtx_count -> list of transform nodes
    """
    buckets = {}
    for m in scene_meshes:
        try:
            c = mesh_vertex_count(m)
        except Exception:
            continue
        buckets.setdefault(c, []).append(m)
    return buckets


def choose_scene_matches_for_json(pos_list):
    """
    If nothing selected:
    - Scan scene for meshes matching JSON entries by vertex count
    - If 0 matches: warn, return None
    - Else show UI:
        JSON[i] vtx=N
        candidates (radio buttons if >1) + Skip
    Returns list of pairs (json_index, mesh_obj) chosen by user, or None if canceled.
    """
    scene_meshes = _list_scene_mesh_transforms()
    if not scene_meshes:
        cmds.warning("No meshes found in scene.")
        return None

    buckets = _build_candidates_by_vtx(scene_meshes)
    targets = [(i, len(pos_list[i])) for i in range(len(pos_list))]

    any_match = any(vtx in buckets for _, vtx in targets)
    if not any_match:
        cmds.warning("No meshes in scene match JSON vertex counts.")
        return None

    # Build UI controls per JSON entry
    radio_collections = {}   # json_index -> collection
    radio_buttons = {}       # json_index -> dict(label -> button)
    has_any_candidate = {}

    def _ui():
        form = cmds.setParent(q=True)

        title_txt = cmds.text(label="No selection detected. Choose scene meshes matching JSON by vertex count.", align="left")
        hint_txt = cmds.text(label="For each JSON entry: pick one fitting mesh (or Skip).", align="left")

        scroll = cmds.scrollLayout(childResizable=True)
        inner = cmds.columnLayout(adjustableColumn=True)

        for j, vtx in targets:
            cands = buckets.get(vtx, [])
            has_any_candidate[j] = bool(cands)

            frame = cmds.frameLayout(label="JSON[{}]    vtx={}".format(j, vtx), collapsable=True, collapse=False, marginHeight=6, marginWidth=8)
            cmds.columnLayout(adjustableColumn=True)

            # include Skip
            col = cmds.radioCollection()
            radio_collections[j] = col
            rb_map = {}
            rb_skip = cmds.radioButton(label="Skip")
            rb_map["Skip"] = rb_skip

            if not cands:
                cmds.text(label="No fitting meshes found.", align="left")
                cmds.radioCollection(col, e=True, select=rb_skip)
            elif len(cands) == 1:
                name = cands[0].name()
                rb = cmds.radioButton(label=name)
                rb_map[name] = rb
                cmds.radioCollection(col, e=True, select=rb)  # auto pick only match
            else:
                # multiple -> radio list
                # default select 1st candidate
                for idx, obj in enumerate(cands):
                    name = obj.name()
                    rb = cmds.radioButton(label=name)
                    rb_map[name] = rb
                    if idx == 0:
                        cmds.radioCollection(col, e=True, select=rb)

            radio_buttons[j] = rb_map

            cmds.setParent("..")  # column
            cmds.setParent("..")  # frame

        cmds.setParent("..")  # inner
        cmds.setParent("..")  # scroll

        btn_continue = cmds.button(label="Continue", height=32, c=lambda *_: cmds.layoutDialog(dismiss="Continue"))
        btn_cancel = cmds.button(label="Cancel", height=32, c=lambda *_: cmds.layoutDialog(dismiss="Cancel"))

        cmds.formLayout(
            form, e=True,
            attachForm=[
                (title_txt, "top", 10), (title_txt, "left", 10), (title_txt, "right", 10),
                (hint_txt, "left", 10), (hint_txt, "right", 10),
                (scroll, "left", 10), (scroll, "right", 10),
                (btn_continue, "left", 10), (btn_continue, "bottom", 10),
                (btn_cancel, "right", 10), (btn_cancel, "bottom", 10),
            ],
            attachControl=[
                (hint_txt, "top", 6, title_txt),
                (scroll, "top", 10, hint_txt),
                (scroll, "bottom", 10, btn_continue),
                (btn_cancel, "left", 10, btn_continue),
            ],
            attachPosition=[
                (btn_continue, "right", 5, 50),
                (btn_cancel, "left", 5, 50),
            ]
        )

    result = cmds.layoutDialog(title="Scene Match Finder", ui=_ui)
    if result != "Continue":
        return None

    # Build chosen pairs
    name_to_node = {m.name(): m for m in scene_meshes}
    pairs = []
    for j, vtx in targets:
        if not has_any_candidate.get(j):
            continue
        sel_btn = cmds.radioCollection(radio_collections[j], q=True, select=True)
        if not sel_btn:
            continue
        label = cmds.radioButton(sel_btn, q=True, label=True)
        if label == "Skip":
            continue
        node = name_to_node.get(label)
        if node:
            pairs.append((j, node))

    if not pairs:
        cmds.warning("Nothing chosen (all skipped). Aborting.")
        return None

    return pairs


# ----------------------------
# Morph
# ----------------------------
def morph_one_mesh(obj, posa):
    dup = pm.duplicate(obj, rr=True)[0]
    set_positions(dup, posa)
    pm.select(dup, r=True)
    pm.select(obj, add=True)
    morph = pm.blendShape(automatic=1, n='blendFromXsi', en=1)
    pm.blendShape(morph, edit=True, w=[(0, 1)])
    pm.delete(dup)


# ----------------------------
# Main
# ----------------------------
path = r'G:\nauka\xsi2maya\pos.json'

wybor = cmds.confirmDialog(
    title='Morph Tool',
    message='Choose',
    button=['Import Position', 'Export Position', 'Morph position', 'CANCEL'],
    defaultButton='Import Position',
    cancelButton='CANCEL',
    dismissString='CANCEL'
)

if wybor == 'Import Position':
    pos = open_json(path)
    sel = list(pm.selected())

    if sel:
        mode, data = resolve_mapping_with_user_confirm(sel, pos)
        if mode == "full":
            for k, obj in enumerate(data):
                set_positions(obj, pos[k])
        elif mode == "partial":
            for j, obj in data:
                set_positions(obj, pos[j])
    else:
        pairs = choose_scene_matches_for_json(pos)
        if pairs:
            for j, obj in pairs:
                set_positions(obj, pos[j])

if wybor == 'Morph position':
    pos = open_json(path)
    sel = list(pm.selected())

    if sel:
        mode, data = resolve_mapping_with_user_confirm(sel, pos)
        if mode == "full":
            for k, obj in enumerate(data):
                morph_one_mesh(obj, pos[k])
        elif mode == "partial":
            for j, obj in data:
                morph_one_mesh(obj, pos[j])
    else:
        pairs = choose_scene_matches_for_json(pos)
        if pairs:
            for j, obj in pairs:
                morph_one_mesh(obj, pos[j])

if wybor == 'Export Position':
    sel = list(pm.selected())
    if not sel:
        cmds.warning("Export requires a selection.")
    else:
        posAll = [get_positions(obj) for obj in sel]
        save_json(posAll, path)
        print('Positions saved to', path)
