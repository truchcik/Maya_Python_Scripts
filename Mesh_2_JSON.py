import json
import os
import maya.OpenMaya as om
import maya.cmds as cmds
import subprocess
import sys
import maya.api.OpenMaya as om2


FILENAME = "mesh_data.json"


def get_transform_and_shape_names(dagPath):
    """
    Given an MDagPath (usually from selection), return:
    - transform name (short name)
    - shape name (short name)
    """
    dp_shape = om.MDagPath(dagPath)
    dp_shape.extendToShape()
    shape_name = dp_shape.fullPathName().split("|")[-1]

    dp_transform = om.MDagPath(dagPath)  # original input
    transform_name = dp_transform.fullPathName().split("|")[-1]

    return transform_name, shape_name


def unlock_normals_and_harden_sharp_edges(mesh_transform_name, cos_threshold=0.999):
    """
    Unlocks vertex normals and converts sharp normal discontinuities to hard edges.
    Uses maya.api.OpenMaya for modern access to geometry.
    """
    if not cmds.objExists(mesh_transform_name):
        om.MGlobal.displayWarning(f"Mesh '{mesh_transform_name}' not found.")
        return

    # Unlock normals (remove fake smoothing)
    try:
        cmds.polyNormalPerVertex(mesh_transform_name, ufn=True)
    except Exception as e:
        om.MGlobal.displayWarning(f"Could not unlock normals on '{mesh_transform_name}': {e}")
        return

    # Get dag path to shape using api.OpenMaya
    sel = om2.MSelectionList()
    sel.add(mesh_transform_name)
    dag_path = sel.getDagPath(0)
    dag_path = dag_path.extendToShape()

    mesh = om2.MFnMesh(dag_path)
    edges_to_harden = []

    for edge_id in range(mesh.numEdges):
        try:
            v0, v1 = mesh.getEdgeVertices(edge_id)
            face_ids = mesh.getEdgeFaces(edge_id)

            if len(face_ids) != 2:
                continue  # skip border/non-manifold edges

            f0, f1 = face_ids

            n00 = mesh.getFaceVertexNormal(f0, v0).normalize()
            n01 = mesh.getFaceVertexNormal(f0, v1).normalize()
            n10 = mesh.getFaceVertexNormal(f1, v0).normalize()
            n11 = mesh.getFaceVertexNormal(f1, v1).normalize()

            dot_a = n00 * n10
            dot_b = n01 * n11

            if dot_a < cos_threshold or dot_b < cos_threshold:
                edges_to_harden.append(edge_id)
        except:
            continue

    if edges_to_harden:
        edge_strs = [f"{mesh_transform_name}.e[{i}]" for i in edges_to_harden]
        cmds.polySoftEdge(edge_strs, angle=0, ch=False)
        print(f"🧠 Converted {len(edges_to_harden)} sharp-normal edges to HARD edges.")
    else:
        print("✅ No sharp normal edges found to harden.")



def open_folder_with_file(filepath):
    folder = os.path.abspath(os.path.dirname(filepath))
    print (folder, filepath)
    if sys.platform.startswith("win"):
        subprocess.Popen(f'explorer "{folder}"')
    elif sys.platform.startswith("darwin"):
        subprocess.Popen(["open", folder])
    elif sys.platform.startswith("linux"):
        subprocess.Popen(["xdg-open", folder])
    else:
        om.MGlobal.displayWarning("Cannot open folder on this OS.")

def get_selected_dag_path():
    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)
    if sel.length() == 0:
        return None
    dagPath = om.MDagPath()
    sel.getDagPath(0, dagPath)
    return dagPath


def get_unique_name(base_name):
    if not cmds.objExists(base_name):
        return base_name
    i = 1
    while cmds.objExists(f"{base_name}_{i}"):
        i += 1
    return f"{base_name}_{i}"
  
def export_mesh_data(filepath):
    dagPath = get_selected_dag_path()
    if not dagPath:
        om.MGlobal.displayError("No mesh selected.")
        return

    dagPath.extendToShape()
    meshFn = om.MFnMesh(dagPath)
    
    transform, shape_name = get_transform_and_shape_names(dagPath)
    unlock_normals_and_harden_sharp_edges(transform)

    # Vertices
    points = om.MPointArray()
    meshFn.getPoints(points, om.MSpace.kObject)
    vertices = [[points[i].x, points[i].y, points[i].z] for i in range(points.length())]

    # Faces
    counts = om.MIntArray()
    indices = om.MIntArray()
    meshFn.getVertices(counts, indices)
    faces = []
    i = 0
    for c in counts:
        faces.append([int(indices[i + j]) for j in range(c)])
        i += c

    # UVs
    uArray = om.MFloatArray()
    vArray = om.MFloatArray()
    meshFn.getUVs(uArray, vArray)
    uvs = [[uArray[i], vArray[i]] for i in range(uArray.length())]

    uv_indices = []
    for face_id in range(meshFn.numPolygons()):
        uv_ids = []
        for i in range(meshFn.polygonVertexCount(face_id)):
            try:
                uv_id = meshFn.getPolygonUVid(face_id, i)
            except:
                uv_id = 0
            uv_ids.append(int(uv_id))
        uv_indices.append(uv_ids)

    # Shape and transform names
    shape_name = dagPath.fullPathName().split("|")[-1]
    transform = cmds.listRelatives(shape_name, parent=True, fullPath=False)[0]

    # Initialize face materials
    num_faces = meshFn.numPolygons()
    face_materials = ["lambert1"] * num_faces

    # Batch material assignment
    import re
    sg_nodes = cmds.listConnections(shape_name, type="shadingEngine") or []
    print(f"🔍 Found shading groups: {sg_nodes} on shape: {shape_name}")

    mat_to_faces = {}

    for sg in sg_nodes:
        conns = cmds.listConnections(f"{sg}.surfaceShader", d=False, s=True)
        mat = conns[0] if conns else "lambert1"

        members = cmds.sets(sg, q=True) or []
        for m in members:
            if not m.startswith(transform + ".f["):
                continue

            matches = re.finditer(r"\.f\[(\d+)(?::(\d+))?\]", m)
            for match in matches:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else start
                for i in range(start, end + 1):
                    if 0 <= i < num_faces:
                        face_materials[i] = mat
                        
    # Detect hard edges using MItMeshEdge
    edge_it = om.MItMeshEdge(dagPath)
    hard_edges = []
    
    while not edge_it.isDone():
        if edge_it.isSmooth() is False:
            hard_edges.append(edge_it.index())
        edge_it.next()

    # Save to file
    data = {
        "name": shape_name,
        "vertices": vertices,
        "faces": faces,
        "uvs": uvs,
        "uv_indices": uv_indices,
        "face_materials": face_materials,
        "hard_edges": hard_edges
    }

    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Exported mesh with {len(faces)} faces and materials → {filepath}")
    #open_folder_with_file(filepath)


def import_mesh_data(filepath):
    if not os.path.exists(filepath):
        om.MGlobal.displayError(f"File not found: {filepath}")
        return

    with open(filepath, "r") as f:
        data = json.load(f)

    base_name = data.get("name", "ImportedMesh")
    mesh_name = get_unique_name(base_name)

    vertices = data["vertices"]
    faces = data["faces"]
    uvs = data.get("uvs", [])
    uv_indices = data.get("uv_indices", [])
    face_materials = data.get("face_materials", [])
    hard_edges = data.get("hard_edges", [])
    material_name = data.get("material", "lambert1")

    # Create geometry
    points = om.MPointArray()
    for v in vertices:
        points.append(om.MPoint(*v))

    face_counts = om.MIntArray()
    face_connects = om.MIntArray()
    for face in faces:
        face_counts.append(len(face))
        for idx in face:
            face_connects.append(idx)

    meshFn = om.MFnMesh()
    new_obj = meshFn.create(points.length(), face_counts.length(), points, face_counts, face_connects)
    meshFn.setName(mesh_name)

    # Assign UVs
    if uvs and uv_indices:
        uArray = om.MFloatArray()
        vArray = om.MFloatArray()
        for uv in uvs:
            uArray.append(uv[0])
            vArray.append(uv[1])
        meshFn.setUVs(uArray, vArray)

        face_vertex_counts = om.MIntArray()
        uv_flattened = om.MIntArray()
        for uv_face in uv_indices:
            face_vertex_counts.append(len(uv_face))
            for uv_id in uv_face:
                uv_flattened.append(uv_id)
        meshFn.assignUVs(face_vertex_counts, uv_flattened)

    meshFn.updateSurface()

    # Get shape + transform names
    shape = meshFn.name()
    transform = cmds.listRelatives(shape, parent=True, fullPath=False)[0]

    # Restore hard edges
    if hard_edges:
        edge_strs = [f"{transform}.e[{i}]" for i in hard_edges]
        cmds.polySoftEdge(edge_strs, angle=0, ch=False)

    # Restore material assignments
    if face_materials:
        from collections import defaultdict

        mat_to_faces = defaultdict(list)
        for face_id, mat in enumerate(face_materials):
            if not cmds.objExists(mat):
                mat = "lambert1"
            mat_to_faces[mat].append(face_id)

        def compress_face_ids(face_ids):
            face_ids = sorted(set(face_ids))
            ranges = []
            start = prev = face_ids[0]
            for i in face_ids[1:]:
                if i == prev + 1:
                    prev = i
                else:
                    ranges.append(f"{start}:{prev}" if start != prev else f"{start}")
                    start = prev = i
            ranges.append(f"{start}:{prev}" if start != prev else f"{start}")
            return ranges

        for mat, face_ids in mat_to_faces.items():
            sg_name = f"{mat}SG"
            if not cmds.objExists(sg_name):
                sg_list = cmds.listConnections(mat, type='shadingEngine')
                if sg_list:
                    sg_name = sg_list[0]
                else:
                    sg_name = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg_name)
                    cmds.connectAttr(f"{mat}.outColor", f"{sg_name}.surfaceShader", force=True)

            face_ranges = compress_face_ids(face_ids)
            component_strs = [f"{transform}.f[{r}]" for r in face_ranges]
            for r in component_strs:
                cmds.sets(r, edit=True, forceElement=sg_name)
    else:
        # fallback: assign whole mesh to one material
        if not cmds.objExists(material_name):
            material_name = "lambert1"
        sg_name = f"{material_name}SG"
        if not cmds.objExists(sg_name):
            sg_list = cmds.listConnections(material_name, type='shadingEngine')
            if sg_list:
                sg_name = sg_list[0]
            else:
                sg_name = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg_name)
                cmds.connectAttr(f"{material_name}.outColor", f"{sg_name}.surfaceShader", force=True)
        cmds.sets(transform, edit=True, forceElement=sg_name)

    om.MGlobal.displayInfo(f"✅ Mesh '{mesh_name}' imported with materials and hard edges.")



# Entry point: Export if selection exists, otherwise import
if get_selected_dag_path():
    export_mesh_data(FILENAME)
else:
    import_mesh_data(FILENAME)
