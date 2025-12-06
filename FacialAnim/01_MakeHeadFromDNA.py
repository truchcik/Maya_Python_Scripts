from PySide2.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog
)
from PySide2.QtCore import Qt

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds
import dna


def set_basemat(mesh_shape, material):
    sg = cmds.listConnections(material, type="shadingEngine")
    if not sg:
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=material + "SG")
        cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    else:
        sg = sg[0]
    cmds.sets(mesh_shape, e=True, forceElement=sg)


def load_dna_reader(dna_path):
    stream = dna.FileStream.create(dna_path,dna.AccessMode_Read,dna.OpenMode_Binary)
    reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    reader.read()    
    return reader, stream


def create_mesh_from_dna(reader, mesh_index=0):
    """
    Create meshes from a DNA reader
    Returns  shape MObject  
    """
    mesh_name = reader.getMeshName(mesh_index)
    # --- Vertex positions ---
    xs = reader.getVertexPositionXs(mesh_index)
    ys = reader.getVertexPositionYs(mesh_index)
    zs = reader.getVertexPositionZs(mesh_index)

    if not (len(xs) == len(ys) == len(zs)):
        raise RuntimeError("DNA vertex position arrays have mismatched lengths")

    points = om.MFloatPointArray()
    for x, y, z in zip(xs, ys, zs):
        points.append(om.MFloatPoint(float(x), float(y), float(z)))

    # --- Topology (faces) ---
    layout_pos_indices = reader.getVertexLayoutPositionIndices(mesh_index)

    face_count = reader.getFaceCount(mesh_index)
    poly_counts = om.MIntArray()
    poly_connects = om.MIntArray()

    for face_idx in range(face_count):
        layout_indices = reader.getFaceVertexLayoutIndices(mesh_index, face_idx)

        # layout_indices is a Python list
        poly_counts.append(len(layout_indices))

        for layout_idx in layout_indices:
            pos_index = int(layout_pos_indices[layout_idx])
            poly_connects.append(pos_index)

    # --- Create mesh---
    fn_mesh = om.MFnMesh()
    # Returns TRANSFORM when no parent
    xform_obj = fn_mesh.create(points, poly_counts, poly_connects)
    #cmds.rename(fn_mesh.name(), mesh_name)
   

    # parent shape 2 transform
    dag = om.MDagPath.getAPathTo(xform_obj)
    cmds.rename(dag, mesh_name)
    dag.extendToShape()
    shape_obj = dag.node()
    fn_mesh.setObject(shape_obj)

    return shape_obj


def apply_uv_from_dna(reader, mesh_obj, mesh_index=0, uv_set_name="map1"):
    """
    Read UV  from DNA and apply to mesh_obj
    """
    fn_mesh = om.MFnMesh(mesh_obj)

    # ----- Global UV coordinates -----
    uv_count = reader.getVertexTextureCoordinateCount(mesh_index)
    us = reader.getVertexTextureCoordinateUs(mesh_index)
    vs = reader.getVertexTextureCoordinateVs(mesh_index)

    u_array = om.MFloatArray()
    v_array = om.MFloatArray()
    for i in range(uv_count):
        u_array.append(float(us[i]))
        v_array.append(float(vs[i]))

    # ----- Ensure UV set exists -----
    existing_sets = fn_mesh.getUVSetNames()
    if uv_set_name not in existing_sets:
        uv_set_name = fn_mesh.createUVSet(uv_set_name)
    fn_mesh.setCurrentUVSetName(uv_set_name)

    if fn_mesh.numUVs(uv_set_name) > 0:
        fn_mesh.clearUVs(uv_set_name)

    fn_mesh.setUVs(u_array, v_array, uv_set_name)

    # ----- Per-face UV assignment -----
    face_count = reader.getFaceCount(mesh_index)
    layout_tex_indices = reader.getVertexLayoutTextureCoordinateIndices(mesh_index)

    uv_counts = om.MIntArray()
    uv_ids = om.MIntArray()

    for face_idx in range(face_count):
        layout_indices = reader.getFaceVertexLayoutIndices(mesh_index, face_idx)
        face_vert_count = len(layout_indices)
        uv_counts.append(face_vert_count)

        for layout_index in layout_indices:
            tex_idx = layout_tex_indices[layout_index]  # index into u_array/v_array
            uv_ids.append(int(tex_idx))

    fn_mesh.assignUVs(uv_counts, uv_ids, uv_set_name)



def create_joint_hierarchy_from_dna(reader, joint_name_prefix="dna_"):
    """
    Create joint hierarchy the DNA
    return list with joint names
    """

    joint_count = reader.getJointCount()

    # --- read all joint data from DNA ---
    txs = reader.getNeutralJointTranslationXs()
    tys = reader.getNeutralJointTranslationYs()
    tzs = reader.getNeutralJointTranslationZs()

    rxs = reader.getNeutralJointRotationXs()
    rys = reader.getNeutralJointRotationYs()
    rzs = reader.getNeutralJointRotationZs()

    parent_indices_raw = [reader.getJointParentIndex(j) for j in range(joint_count)]
    raw_names = [reader.getJointName(j) for j in range(joint_count)]

    safe_names = [
        (joint_name_prefix + (name or ("joint_%d" % i))).replace(":", "_")
        for i, name in enumerate(raw_names)
    ]

    # Normalize parent indices:
    # - self-parent (parent_idx == i) → treat as root (-1)
    # - invalid indices (out of range) → root (-1)
    parent_indices = []
    for i, p in enumerate(parent_indices_raw):
        if p == i or p < 0 or p >= joint_count:
            parent_indices.append(-1)
        else:
            parent_indices.append(p)

    # result: maya joint names, None until created
    joint_nodes = [None] * joint_count

    # set of joints that still need to be created
    remaining = set(range(joint_count))

    while remaining:
        progress = False

        for j in list(remaining):
            parent_idx = parent_indices[j]

            # Can we create this joint now?
            if parent_idx < 0 or joint_nodes[parent_idx] is not None:
                name = safe_names[j]
                tx = float(txs[j])
                ty = float(tys[j])
                tz = float(tzs[j])

                rx = float(rxs[j])
                ry = float(rys[j])
                rz = float(rzs[j])

                # --- create joint with no parent first ---
                cmds.select(clear=True)
                jnt = cmds.joint(name=name)

                # If it has a parent, parent it explicitly now
                if parent_idx >= 0:
                    parent_joint = joint_nodes[parent_idx]
                    cmds.parent(jnt, parent_joint)

                # Now set LOCAL transforms (DNA neutral pose)
                cmds.setAttr(jnt + ".translate", tx, ty, tz, type="double3")
                cmds.setAttr(jnt + ".jointOrient", rx, ry, rz, type="double3")

                joint_nodes[j] = jnt
                remaining.remove(j)
                progress = True

        if not progress:
            # Something pathological (cycle). Make the rest roots so we don't hang.
            for j in remaining:
                name = safe_names[j]
                tx = float(txs[j])
                ty = float(tys[j])
                tz = float(tzs[j])
                rx = float(rxs[j])
                ry = float(rys[j])
                rz = float(rzs[j])

                cmds.select(clear=True)
                jnt = cmds.joint(name=name)
                cmds.setAttr(jnt + ".translate", tx, ty, tz, type="double3")
                cmds.setAttr(jnt + ".jointOrient", rx, ry, rz, type="double3")

                joint_nodes[j] = jnt

            remaining.clear()

    return joint_nodes


def apply_skin_from_dna(reader, mesh_obj, mesh_index=0, joint_nodes=None,
                        skin_cluster_name=None):
    """
    Create skinCluster on mesh_obj  with skin weights from DNA
    """
    # 1) Ensure we have joints in correct index order
    if joint_nodes is None:
        joint_nodes = create_joint_hierarchy_from_dna(reader, joint_name_prefix="dna_")

    if not joint_nodes:
        raise RuntimeError("apply_skin_from_dna: joint_nodes list is empty")

    influence_count = len(joint_nodes)

    # 2) Figure out mesh transform name from mesh_obj
    fn_mesh = om.MFnMesh(mesh_obj)
    mesh_shape = fn_mesh.name()
    mesh_transform = cmds.listRelatives(mesh_shape, parent=True, fullPath=True)[0]

    # 3) Remove any existing skinClusters on this mesh
    history = cmds.listHistory(mesh_transform) or []
    existing_skin = cmds.ls(history, type="skinCluster")
    for sc in existing_skin:
        cmds.delete(sc)

    # 4) Create a new skinCluster (no name override to avoid deformer-name errors)
    #    IMPORTANT: turn OFF auto-normalization; we'll set exact DNA weights
    max_infl = int(reader.getMaximumInfluencePerVertex(mesh_index))

    skin_cluster = cmds.skinCluster(
        joint_nodes,
        mesh_transform,
        tsb=True,
        maximumInfluences=max_infl,
        normalizeWeights=0,   # <-- no auto-normalization
    )[0]

    # Optionally rename AFTER creation
    if skin_cluster_name:
        if cmds.objExists(skin_cluster_name):
            skin_cluster_name = cmds.rename(skin_cluster, skin_cluster_name + "#")
        else:
            skin_cluster_name = cmds.rename(skin_cluster, skin_cluster_name)
        skin_cluster = skin_cluster_name

    # 5) Build MFnSkinCluster wrapper
    sel = om.MSelectionList()
    sel.add(skin_cluster)
    skin_obj = sel.getDependNode(0)
    fn_skin = oma.MFnSkinCluster(skin_obj)

    # MDagPath for mesh shape
    sel = om.MSelectionList()
    sel.add(mesh_shape)
    mesh_path = sel.getDagPath(0)

    vert_count = fn_mesh.numVertices

    # 6) Prepare a component containing ALL vertices
    comp_fn = om.MFnSingleIndexedComponent()
    comp = comp_fn.create(om.MFn.kMeshVertComponent)
    comp_fn.addElements(list(range(vert_count)))

    # 7) Influence indices: 0..influence_count-1 (DNA joint index == skin influence index)
    influence_indices = om.MIntArray()
    for i in range(influence_count):
        influence_indices.append(i)

    # 8) Build full weight matrix: [vert0_inf0, vert0_inf1, ..., vert1_inf0, ...]
    total_weights = influence_count * vert_count
    weights = om.MDoubleArray(total_weights, 0.0)

    for vtx_id in range(vert_count):
        weights_view = reader.getSkinWeightsValues(mesh_index, vtx_id)
        joints_view = reader.getSkinWeightsJointIndices(mesh_index, vtx_id)

        # len() works both for Python lists and DNA's array views
        if len(weights_view) == 0:
            continue

        base = vtx_id * influence_count

        for j_idx, w in zip(joints_view, weights_view):
            j_idx = int(j_idx)
            if 0 <= j_idx < influence_count:
                weights[base + j_idx] = float(w)

    # 9) Apply all weights at once, NO normalization
    fn_skin.setWeights(
        mesh_path,
        comp,
        influence_indices,
        weights,
        False  # normalize=False
    )

    return skin_cluster



class DnaLoaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose DNA file")

        # --- Widgets ---
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)

        browse_btn = QPushButton("Browse...")

        self.load_uv_cb = QCheckBox("LoadUV")
        self.load_skin_cb = QCheckBox("LoadSkin")
        self.load_uv_cb.setChecked(True) 

        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        # --- Layout: file row ---
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("DNA file:"))
        file_layout.addWidget(self.path_edit)
        file_layout.addWidget(browse_btn)

        # --- Layout: checkboxes ---
        check_layout = QHBoxLayout()
        check_layout.addWidget(self.load_uv_cb)
        check_layout.addWidget(self.load_skin_cb)
        check_layout.addStretch()

        # --- Layout: buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        # --- Main layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(file_layout)
        main_layout.addLayout(check_layout)
        main_layout.addLayout(btn_layout)

        # --- Signals ---
        browse_btn.clicked.connect(self.on_browse)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose DNA file",
            START_FOLDER,
            "DNA files (*.dna);;All files (*.*)"
        )
        if path:
            self.path_edit.setText(path)

    def get_values(self):
        """
        Returns:
            (path: str, load_uv: bool, load_skin: bool)
        """
        return (
            self.path_edit.text(),
            self.load_uv_cb.isChecked(),
            self.load_skin_cb.isChecked()
        )


def choose_file():
    
    app = QApplication.instance()
    app_created = False
    if app is None:
        app = QApplication([])
        app_created = True
        app.setQuitOnLastWindowClosed(False)

    dlg = DnaLoaderDialog()
    result = dlg.exec()
    
    values = None
    if result == QDialog.Accepted:
        values = dlg.get_values()

    if app_created:

        app.quit()

    return values

START_FOLDER = r"E:\000W4\03_Heads"

if __name__ == "__main__":
    result = choose_file()
    
print("Result:", result)    
reader, stream = load_dna_reader(result[0])
joint_nodes = create_joint_hierarchy_from_dna(reader, joint_name_prefix="dna_")

for n in range(9):
    mesh_obj = create_mesh_from_dna(reader, mesh_index=n)
    set_basemat(mesh_shape=om.MFnMesh(mesh_obj).name(), material="standardSurface1")    
    if result[1]: uvs =  apply_uv_from_dna(reader, mesh_obj, mesh_index=n, uv_set_name="map1")
    if result[2]: skin_cluster = apply_skin_from_dna(reader, mesh_obj, mesh_index=n, joint_nodes=joint_nodes)

dna.FileStream.destroy(stream)
cmds.viewFit()
