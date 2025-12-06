def get_expression_names_from_dna(reader):
    """
    Returns a list of 'expression' names, using GUI controls
    as the expression layer.
    """
    expr_names = []
    gui_count = reader.getGUIControlCount()
    for i in range(gui_count):
        name = reader.getGUIControlName(i)
        expr_names.append(name)
    return expr_names

def compute_expression_deltas_from_dna(reader, raw_index):
    """
    Compute per-joint, per-channel deltas for a given RAW control index
    (e.g. raw_index=0 for CTRL_expressions.browDownL).

    Returns:
        deltas: list of length joint_count
                each element is a list of length rows_per_joint (9 in your case)
                deltas[j][k] is the coefficient for joint j, channel k.
    """
    joint_count = reader.getJointCount()
    row_count = reader.getJointRowCount()
    rows_per_joint = row_count // joint_count if joint_count else 0

    if rows_per_joint == 0:
        raise RuntimeError("rows_per_joint is zero; unexpected DNA data")

    # Initialize deltas[joint_index][var_index] = 0.0
    deltas = [[0.0 for _ in range(rows_per_joint)] for _ in range(joint_count)]

    joint_group_count = reader.getJointGroupCount()

    for g in range(joint_group_count):
        inputs = list(reader.getJointGroupInputIndices(g))
        if raw_index not in inputs:
            continue

        col = inputs.index(raw_index)  # column index for this raw control in this group

        outputs = list(reader.getJointGroupOutputIndices(g))
        values = list(reader.getJointGroupValues(g))

        rows = len(outputs)
        inputs_cnt = len(inputs)
        expected_vals = rows * inputs_cnt

        if len(values) != expected_vals:
            print("Warning: Group", g,
                  "values length", len(values),
                  "!= rows * inputs =", expected_vals,
                  "- skipping this group")
            continue

        for r in range(rows):
            global_row = int(outputs[r])
            if global_row < 0 or global_row >= row_count:
                continue

            joint_index = global_row // rows_per_joint
            var_index = global_row % rows_per_joint

            if joint_index < 0 or joint_index >= joint_count:
                continue

            coef = values[r * inputs_cnt + col]
            deltas[joint_index][var_index] += float(coef)

    return deltas


def apply_expression_translation_rotation(reader, joint_nodes, deltas,
                                          value=1.0,
                                          rot_scale=1.0):
    """
    Apply translation (channels 0-2) and rotation (channels 3-5) from DNA deltas

    - deltas: output of compute_expression_deltas_from_dna (joint_count x rows_per_joint)
    - value: expression intensity (0..1)
    - rot_scale: multiplier for rotation magnitude (for tuning, default 1.0)
    """
    joint_count = reader.getJointCount()
    if len(joint_nodes) != joint_count:
        raise RuntimeError("joint_nodes length != DNA jointCount")

    row_count = reader.getJointRowCount()
    rows_per_joint = row_count // joint_count if joint_count else 0

    if rows_per_joint < 6:
        raise RuntimeError("rows_per_joint < 6; cannot map 0-2 to T, 3-5 to R")

    neutral_tx = reader.getNeutralJointTranslationXs()
    neutral_ty = reader.getNeutralJointTranslationYs()
    neutral_tz = reader.getNeutralJointTranslationZs()

    for j in range(joint_count):
        maya_joint = joint_nodes[j]
        if not maya_joint or not cmds.objExists(maya_joint):
            continue

        # --- translation deltas ---
        dx = deltas[j][0] * value
        dy = deltas[j][1] * value
        dz = deltas[j][2] * value

        tx = float(neutral_tx[j]) + dx
        ty = float(neutral_ty[j]) + dy
        tz = float(neutral_tz[j]) + dz

        cmds.setAttr(maya_joint + ".translate", tx, ty, tz, type="double3")

        # --- rotation deltas ---
        rx = deltas[j][3] * value * rot_scale
        ry = deltas[j][4] * value * rot_scale
        rz = deltas[j][5] * value * rot_scale

        # Data in degrees
        # Neutral rotation stored in jointOrient; rotate is 0 in bind
        # so we can set rotate directly to "delta from neutral"
        cmds.setAttr(maya_joint + ".rotate", rx, ry, rz, type="double3")


def adjust_expression_deltas(deltas,
                             scale=1.0,
                             rot_scale=1.0,
                             transform=(1.0, 1.0, 1.0),
                             copy=True):
    """
    Adjusts per-joint expression deltas.

    Args:
        deltas: list[joint_index][channel_index], output of compute_expression_deltas_from_dna.
        scale: global scalar for the entire expression (strength).
        rot_scale: extra scalar applied only to rotation channels (3,4,5).
        transform: (sx, sy, sz) scaling applied per-axis to translation channels (0,1,2).
        copy: if True, return a new list; if False, modify deltas in-place.

    Returns:
        adjusted_deltas: same structure as input (joint_count x rows_per_joint).
    """

    if copy:
        # deep copy 2D list
        adjusted = [row[:] for row in deltas]
    else:
        adjusted = deltas

    sx, sy, sz = transform

    for j in range(len(adjusted)):
        row = adjusted[j]
        n = len(row)

        # --- translation channels 0,1,2 ---
        if n >= 1:
            row[0] = row[0] * scale * sx
        if n >= 2:
            row[1] = row[1] * scale * sy
        if n >= 3:
            row[2] = row[2] * scale * sz

        # --- rotation channels 3,4,5 ---
        if n >= 4:
            row[3] = row[3] * scale * rot_scale
        if n >= 5:
            row[4] = row[4] * scale * rot_scale
        if n >= 6:
            row[5] = row[5] * scale * rot_scale

        # --- remaining channels (6..n-1) ---
        if n > 6:
            for k in range(6, n):
                row[k] = row[k] * scale

    return adjusted
 
str = 1       
expr_names = get_expression_names_from_dna(reader)
expr_cnt = (len(expr_names))
cmds.select(joint_nodes)

for n in range(expr_cnt):
    print (n, expr_names[n])
    cmds.currentTime(n)
    
    delta = compute_expression_deltas_from_dna(reader, n)
    apply_expression_translation_rotation(reader, joint_nodes, delta, value=str,  rot_scale=str)
    cmds.setKeyframe()

#adj_delta = adjust_expression_deltas(delta,scale=str,rot_scale=str,transform=(-11, 2, 0),copy=True)
#apply_expression_translation_rotation(reader, joint_nodes, adj_delta, value=str,  rot_scale=str)




