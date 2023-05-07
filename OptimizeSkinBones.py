#OptimizeBones
#Removes all deformers except in main_skeleton from skinning  for selected mesh
#G:\nauka\Scripts_Python\Scripts_Python_Maya\PyMel\SKIN\OptimizeBones.py

import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm



def get_skin_cluster(node):
	for history_node in pm.listHistory(node):
		if isinstance(history_node, pm.nodetypes.SkinCluster):return history_node
	return 'None'


def get_skinFn(clusterName):
	selList = OpenMaya.MSelectionList()
	selList.add(clusterName)
	clusterNode = OpenMaya.MObject()
	selList.getDependNode(0, clusterNode)
	skinFn = OpenMayaAnim.MFnSkinCluster(clusterNode)
	return skinFn
	


def get_weights(skinFn,kompresuj = False):
	# get the MPlug for the weightList and weights attributes
	wlPlug = skinFn.findPlug('weightList')
	wPlug = skinFn.findPlug('weights')
	wlAttr = wlPlug.attribute()
	wAttr = wPlug.attribute()
	wInfIds = OpenMaya.MIntArray()	
	# get the MDagPath for all influence
	infDags = OpenMaya.MDagPathArray()
	skinFn.influenceObjects(infDags)	
	# create a dictionary whose key is the MPlug indice id and 
	# whose value is the influence list id
	infIds = {}
	fixIds = {} # z jakiegos powodu do wczytywania potrzebuje odwrotnosci infIds
	infs = []
	for x in xrange(infDags.length()):
		infPath = str(infDags[x].fullPathName())
		if inf_mode == 'short_names': infPath = infPath.split('|')[-1]
		infId = int(skinFn.indexForInfluenceObject(infDags[x]))
		infIds[infId] = x
		fixIds[x] = infId
		infs.append(infPath)
	# the weights are stored in dictionary, the key is the vertId, 
	# the value is another dictionary whose key is the influence id and 
	# value is the weight for that influence
	weights = {}
	for vId in xrange(wlPlug.numElements()):
		vWeights = {}
		# tell the weights attribute which vertex id it represents
		wPlug.selectAncestorLogicalIndex(vId, wlAttr)		
		# get the indice of all non-zero weights for this vert
		wPlug.getExistingArrayAttributeIndices(wInfIds)	
		# create a copy of the current wPlug
		infPlug = OpenMaya.MPlug(wPlug)
		for infId in wInfIds:
			# tell the infPlug it represents the current influence id
			infPlug.selectAncestorLogicalIndex(infId, wAttr)			
			# add this influence and its weight to this verts weights
			try:
				if kompresuj: vWeights[infIds[infId]] = round(infPlug.asDouble(),5)
				else: vWeights[infIds[infId]] = infPlug.asDouble()
				
			except KeyError:
				# assumes a removed influence
				pass
		weights[vId] = vWeights
	return weights, infs, infIds, fixIds
	
	
def set_weights(clusterName, infs, weights, no_skin):
	
	def zero_weights(clusterName, infs):
		#Zero all skins
		for inf in infs: cmds.setAttr(str(inf)+'.liw')
		skinNorm = cmds.getAttr('%s.normalizeWeights' % clusterName)
		if skinNorm != 0: cmds.setAttr('%s.normalizeWeights' % clusterName, 0)
		cmds.skinPercent(clusterName, shapeName, nrm=False, prw=100)
		if skinNorm != 0:
			cmds.setAttr('%s.normalizeWeights' % clusterName, skinNorm)	
					
	zero_weights(clusterName, infs)

	for vertId, weightData in weights.items():
		wlAttr = '%s.weightList[%s]' % (clusterName, vertId)
		#print 'vertId =', vertId
		for infId, infValue in weightData.items():			
			try:
				#print '    infIds[infId] =', infIds[infId], joints[int(infIds[infId])],'   infValue =', infValue				
				if no_skin: wAttr = '.weights[%s]' % infId
				else: wAttr = '.weights[%s]' % infIds[infId]
				#print '       ', wlAttr, wAttr, infValue
				cmds.setAttr(wlAttr + wAttr, infValue)
			except: pass
			
			
			

def get_hierarchy(mainBone):	
	def hierarchyTree(mainBone, allChildren):
		children = pm.listRelatives(mainBone, c=True)
		children = [ str(x.name() ) for x in children if str(x.name()) not in main_skeleton]
		if children:
				for c in children: allChildren.append(c)
				for child in children:hierarchyTree(child, allChildren)   
	
	allChildren = []
	hierarchyTree(str(mainBone), allChildren)
	
	allChildren = [x for x in allChildren if x in weight_data['infs']] #zbieram tylko te dzieci które są w wagach
	return allChildren	


#weights	{vert index:{influence id : weight}, vert index 2 {}, ...}
#infs		tablica kosci
#infIds     dict mapuje id istniejącego deformera mesha w id deformera z binda {index w meshu(str) : index w meshu podczas binda (int), ...}
#weights	dict [vert index(int) : {deformer index(int) : weight(float), ...}

sciezka1 = 		r'G:\nauka\Scripts_Python\Scripts_Python_Maya\PyMel\_FAST_SKIN_WRK\data'
inf_mode = 		'short_names'	#Zapisuje deformery tylko jako nazwy np 'Hips'.'long_names' jako hierarchie np 'Skeleton|Root|Hips'
kompresuj = 	False			#Pełna precyzja wag. True przycina je do 5 miejsc po przecinku
anim_skeleton  = ['Hips','Spine','Spine1','Spine2','Spine3','Neck','Neck1','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase','LeftInHandThumb','LeftHandThumb1','LeftHandThumb2','LeftInHandIndex','LeftHandIndex1','LeftHandIndex2','LeftHandIndex3','LeftInHandMiddle','LeftHandMiddle1','LeftHandMiddle2','LeftHandMiddle3','LeftInHandRing','LeftHandRing1','LeftHandRing2','LeftHandRing3','LeftInHandPinky','LeftHandPinky1','LeftHandPinky2','LeftHandPinky3','RightInHandThumb','RightHandThumb1','RightHandThumb2','RightInHandIndex','RightHandIndex1','RightHandIndex2','RightHandIndex3','RightInHandMiddle','RightHandMiddle1','RightHandMiddle2','RightHandMiddle3','RightInHandRing','RightHandRing1','RightHandRing2','RightHandRing3','RightInHandPinky','RightHandPinky1','RightHandPinky2','RightHandPinky3']
csfLOD1_skeleton = ['Hips', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase', 'r_calf_0_JNT', 'r_thigh_1_JNT', 'r_thigh_0_JNT', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'l_calf_0_JNT', 'l_thigh_1_JNT', 'l_thigh_0_JNT', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand', 'RightInHandPinky', 'RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3', 'RightInHandRing', 'RightHandRing1', 'RightHandRing2', 'RightHandRing3', 'RightInHandMiddle', 'RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3', 'RightInHandIndex', 'RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3', 'RightInHandThumb', 'RightHandThumb1', 'RightHandThumb2', 'r_Wrist_2_JNT', 'r_Wrist_1_JNT', 'r_Wrist_0_JNT', 'r_SHL_1_JNT', 'r_SHL_0_JNT', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'LeftInHandPinky', 'LeftHandPinky1', 'LeftHandPinky2', 'LeftHandPinky3', 'LeftInHandRing', 'LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3', 'LeftInHandMiddle', 'LeftHandMiddle1', 'LeftHandMiddle2', 'LeftHandMiddle3', 'LeftInHandIndex', 'LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3', 'LeftInHandThumb', 'LeftHandThumb1', 'LeftHandThumb2', 'l_Wrist_2_JNT', 'l_Wrist_1_JNT', 'l_Wrist_0_JNT', 'l_SHL_1_JNT', 'l_SHL_0_JNT', 'Neck', 'Neck1', 'Head']
csf_skeleton =  ['Hips', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'LeftShoulder', 'LeftArm', 'l_SHL_0_JNT', 'l_deltoid_top_top_out_JNT', 'l_deltoid_top_bot_out_JNT', 'l_deltoid_front_top_out_JNT', 'l_deltoid_front_bot_out_JNT', 'l_deltoid_back_top_out_JNT', 'l_deltoid_back_bot_out_JNT', 'l_triceps_mscl_JNT', 'l_biceps_A_mscl_JNT', 'LeftForeArm', 'l_Wrist_0_JNT', 'l_Wrist_1_JNT', 'l_Wrist_2_JNT', 'l_wrist_A_mscl_JNT', 'l_wrist_B_mscl_JNT', 'l_wrist_C_mscl_JNT', 'LeftHand', 'LeftHandThumb1', 'LeftHandThumb2', 'l_thumb_side_mscl_JNT', 'LeftInHandIndex', 'LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3', 'l_ind_knuckle_B_top_mscl_JNT', 'l_ind_knuckle_top_mscl_JNT', 'l_ind_knuckle_bot_mscl_JNT', 'l_thumb_thumb_A_bot_mscl_JNT', 'l_thumb_thumb_A_top_mscl_JNT', 'LeftInHandMiddle', 'LeftHandMiddle1', 'LeftHandMiddle2', 'LeftHandMiddle3', 'l_mid_knuckle_B_top_mscl_JNT', 'l_mid_knuckle_top_mscl_JNT', 'l_mid_knuckle_bot_mscl_JNT', 'LeftInHandRing', 'LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3', 'l_ring_knuckle_B_top_mscl_JNT', 'l_ring_knuckle_top_mscl_JNT', 'l_ring_knuckle_bot_mscl_JNT', 'LeftInHandPinky', 'LeftHandPinky1', 'LeftHandPinky2', 'LeftHandPinky3', 'l_pinky_knuckle_B_top_mscl_JNT', 'l_pinky_knuckle_top_mscl_JNT', 'l_pinky_knuckle_bot_mscl_JNT', 'l_pinkyBase_A_bot_mscl_JNT', 'l_elbow_bend_A_mscl_JNT', 'l_elbow_bend_B_mscl_JNT', 'l_elbow_back_mscl_JNT', 'l_butterfly_top_CRV_bot_out_JNT', 'RightShoulder', 'RightArm', 'r_SHL_0_JNT', 'r_deltoid_top_top_out_JNT', 'r_deltoid_top_bot_out_JNT', 'r_deltoid_front_top_out_JNT', 'r_deltoid_front_bot_out_JNT', 'r_deltoid_back_top_out_JNT', 'r_deltoid_back_bot_out_JNT', 'r_triceps_mscl_JNT', 'r_biceps_A_mscl_JNT', 'RightForeArm', 'r_Wrist_0_JNT', 'r_Wrist_1_JNT', 'r_Wrist_2_JNT', 'r_wrist_A_mscl_JNT', 'r_wrist_B_mscl_JNT', 'r_wrist_C_mscl_JNT', 'RightHand', 'RightHandThumb1', 'RightHandThumb2', 'r_thumb_side_mscl_JNT', 'RightInHandIndex', 'RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3', 'r_ind_knuckle_B_top_mscl_JNT', 'r_ind_knuckle_top_mscl_JNT', 'r_ind_knuckle_bot_mscl_JNT', 'r_thumb_thumb_A_bot_mscl_JNT', 'r_thumb_thumb_A_top_mscl_JNT', 'RightInHandMiddle', 'RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3', 'r_mid_knuckle_B_top_mscl_JNT', 'r_mid_knuckle_top_mscl_JNT', 'r_mid_knuckle_bot_mscl_JNT', 'RightInHandRing', 'RightHandRing1', 'RightHandRing2', 'RightHandRing3', 'r_ring_knuckle_B_top_mscl_JNT', 'r_ring_knuckle_top_mscl_JNT', 'r_ring_knuckle_bot_mscl_JNT', 'RightInHandPinky', 'RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3', 'r_pinky_knuckle_B_top_mscl_JNT', 'r_pinky_knuckle_top_mscl_JNT', 'r_pinky_knuckle_bot_mscl_JNT', 'r_pinkyBase_A_bot_mscl_JNT', 'r_elbow_bend_A_mscl_JNT', 'r_elbow_bend_B_mscl_JNT', 'r_elbow_back_mscl_JNT', 'r_butterfly_top_CRV_top_out_JNT', 'Neck', 'Neck1', 'Head', 'l_sternocleidomastoid_top_mscl_JNT', 'r_sternocleidomastoid_top_mscl_JNT', 'l_sternocleidomastoid_bot_mscl_JNT', 'r_sternocleidomastoid_bot_mscl_JNT', 'r_latissimusDorsi_mscl_JNT', 'l_latissimusDorsi_mscl_JNT', 'r_trapezius_top_mscl_JNT', 'l_chest_front_A_bot_out_JNT', 'l_chest_front_B_top_out_JNT', 'l_chest_front_B_bot_out_JNT', 'l_chest_front_C_top_out_JNT', 'l_chest_front_C_bot_out_JNT', 'l_scapula_A_top_out_JNT', 'l_scapula_A_bot_out_JNT', 'r_chest_front_A_bot_out_JNT', 'r_chest_front_B_top_out_JNT', 'r_chest_front_B_bot_out_JNT', 'r_chest_front_C_top_out_JNT', 'r_chest_front_C_bot_out_JNT', 'r_scapula_A_top_out_JNT', 'r_scapula_A_bot_out_JNT', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'l_calf_0_JNT', 'l_lowLeg_back_B_mscl_JNT', 'l_lowLeg_back_A_mscl_JNT', 'l_knee_mscl_JNT', 'l_thigh_0_JNT', 'l_thigh_1_JNT', 'l_leg_back_B_mscl_JNT', 'l_leg_back_A_mscl_JNT', 'l_leg_groin_mscl_JNT', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase', 'r_calf_0_JNT', 'r_lowLeg_back_A_mscl_JNT', 'r_lowLeg_back_B_mscl_JNT', 'r_knee_mscl_JNT', 'r_thigh_0_JNT', 'r_thigh_1_JNT', 'r_leg_back_B_mscl_JNT', 'r_leg_back_A_mscl_JNT', 'r_leg_groin_mscl_JNT', 'l_leg_buttock_mscl_JNT', 'r_leg_buttock_mscl_JNT']
csfr_skeleton =  ['Hips', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'LeftShoulder', 'LeftArm', 'l_SHL_0_JNT', 'l_deltoid_top_top_out_JNT', 'l_deltoid_top_bot_out_JNT', 'l_deltoid_front_top_out_JNT', 'l_deltoid_front_bot_out_JNT', 'l_deltoid_back_top_out_JNT', 'l_deltoid_back_bot_out_JNT', 'l_triceps_mscl_JNT', 'l_biceps_A_mscl_JNT', 'LeftForeArm', 'l_Wrist_0_JNT', 'l_Wrist_1_JNT', 'l_Wrist_2_JNT', 'l_wrist_A_mscl_JNT', 'l_wrist_B_mscl_JNT', 'l_wrist_C_mscl_JNT', 'LeftHand', 'LeftHandThumb1', 'LeftHandThumb2', 'l_thumb_side_mscl_JNT', 'LeftInHandIndex', 'LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3', 'l_ind_knuckle_B_top_mscl_JNT', 'l_ind_knuckle_top_mscl_JNT', 'l_ind_knuckle_bot_mscl_JNT', 'l_thumb_thumb_A_bot_mscl_JNT', 'l_thumb_thumb_A_top_mscl_JNT', 'LeftInHandMiddle', 'LeftHandMiddle1', 'LeftHandMiddle2', 'LeftHandMiddle3', 'l_mid_knuckle_B_top_mscl_JNT', 'l_mid_knuckle_top_mscl_JNT', 'l_mid_knuckle_bot_mscl_JNT', 'LeftInHandRing', 'LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3', 'l_ring_knuckle_B_top_mscl_JNT', 'l_ring_knuckle_top_mscl_JNT', 'l_ring_knuckle_bot_mscl_JNT', 'LeftInHandPinky', 'LeftHandPinky1', 'LeftHandPinky2', 'LeftHandPinky3', 'l_pinky_knuckle_B_top_mscl_JNT', 'l_pinky_knuckle_top_mscl_JNT', 'l_pinky_knuckle_bot_mscl_JNT', 'l_pinkyBase_A_bot_mscl_JNT', 'l_elbow_bend_A_mscl_JNT', 'l_elbow_bend_B_mscl_JNT', 'l_elbow_back_mscl_JNT', 'l_butterfly_top_CRV_bot_out_JNT', 'RightShoulder', 'RightArm', 'r_SHL_0_JNT', 'r_deltoid_top_top_out_JNT', 'r_deltoid_top_bot_out_JNT', 'r_deltoid_front_top_out_JNT', 'r_deltoid_front_bot_out_JNT', 'r_deltoid_back_top_out_JNT', 'r_deltoid_back_bot_out_JNT', 'r_triceps_mscl_JNT', 'r_biceps_A_mscl_JNT', 'RightForeArm', 'r_Wrist_0_JNT', 'r_Wrist_1_JNT', 'r_Wrist_2_JNT', 'r_wrist_A_mscl_JNT', 'r_wrist_B_mscl_JNT', 'r_wrist_C_mscl_JNT', 'RightHand', 'RightHandThumb1', 'RightHandThumb2', 'r_thumb_side_mscl_JNT', 'RightInHandIndex', 'RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3', 'r_ind_knuckle_B_top_mscl_JNT', 'r_ind_knuckle_top_mscl_JNT', 'r_ind_knuckle_bot_mscl_JNT', 'r_thumb_thumb_A_bot_mscl_JNT', 'r_thumb_thumb_A_top_mscl_JNT', 'RightInHandMiddle', 'RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3', 'r_mid_knuckle_B_top_mscl_JNT', 'r_mid_knuckle_top_mscl_JNT', 'r_mid_knuckle_bot_mscl_JNT', 'RightInHandRing', 'RightHandRing1', 'RightHandRing2', 'RightHandRing3', 'r_ring_knuckle_B_top_mscl_JNT', 'r_ring_knuckle_top_mscl_JNT', 'r_ring_knuckle_bot_mscl_JNT', 'RightInHandPinky', 'RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3', 'r_pinky_knuckle_B_top_mscl_JNT', 'r_pinky_knuckle_top_mscl_JNT', 'r_pinky_knuckle_bot_mscl_JNT', 'r_pinkyBase_A_bot_mscl_JNT', 'r_elbow_bend_A_mscl_JNT', 'r_elbow_bend_B_mscl_JNT', 'r_elbow_back_mscl_JNT', 'r_butterfly_top_CRV_top_out_JNT', 'Neck', 'Neck1', 'Head', 'l_J_eye_brows_rowA_0_JNT', 'l_J_eye_brows_rowA_0_twk_JNT', 'l_J_eye_brows_rowA_1_JNT', 'l_J_eye_brows_rowA_2_JNT', 'l_J_eye_brows_rowA_3_JNT', 'l_J_eye_brows_rowB_0_JNT', 'l_J_eye_brows_rowB_1_JNT', 'l_J_eye_brows_rowB_2_JNT', 'l_J_eye_brows_rowB_3_JNT', 'l_J_eye_brows_rowC_0_JNT', 'l_J_eye_brows_rowC_1_JNT', 'l_J_eye_brows_rowC_2_JNT', 'l_J_eye_check_rowA_0_JNT', 'l_J_eye_check_rowA_1_JNT', 'l_J_eye_check_rowB_0_JNT', 'l_J_eye_check_rowC_0_JNT', 'l_J_eye_check_rowC_1_JNT', 'l_J_eye_check_rowD_0_JNT', 'l_J_eye_check_rowD_1_JNT', 'l_J_eye_check_rowE_0_JNT', 'l_J_eye_lid_corner_inside_0_JNT', 'l_J_eye_lid_up_rowD_4_JNT', 'l_J_eye_lid_dn_rowA_1_JNT', 'l_J_eye_lid_dn_rowA_2_JNT', 'l_J_eye_lid_dn_rowB_0_JNT', 'l_J_eye_lid_dn_rowB_1_JNT', 'l_J_eye_lid_dn_rowB_2_JNT', 'l_J_eye_lid_up_rowA_1_JNT', 'l_J_eye_lid_up_rowA_2_JNT', 'l_J_eye_lid_up_rowA_0_JNT', 'l_J_eye_lid_up_rowA_3_JNT', 'l_J_eye_lid_up_rowB_0_JNT', 'l_J_eye_lid_up_rowB_1_JNT', 'l_J_eye_lid_up_rowB_2_JNT', 'l_J_eye_lid_up_rowC_0_JNT', 'l_J_eye_lid_up_rowC_1_JNT', 'l_J_eye_lid_up_rowC_2_JNT', 'l_J_eye_lid_up_rowC_3_JNT', 'l_J_eye_lid_up_rowD_1_JNT', 'l_J_eye_lid_up_rowD_2_JNT', 'l_J_eye_lid_up_rowD_3_JNT', 'l_J_eye_nose_rowA_0_JNT', 'l_J_eye_nose_rowA_1_JNT', 'l_J_eye_nose_rowA_2_JNT', 'l_J_eye_nose_rowA_3_JNT', 'l_J_jaw_ear_0_JNT', 'l_J_jaw_ear_1_JNT', 'l_J_jaw_ear_2_JNT', 'l_J_jaw_nosabial_rowA_0_JNT', 'l_J_jaw_nosabial_rowA_1_JNT', 'l_J_jaw_nosabial_rowB_0_JNT', 'l_J_jaw_nosabial_rowB_1_JNT', 'l_J_jaw_nosabial_rowC_0_JNT', 'l_J_jaw_nosabial_rowC_1_JNT', 'l_J_mug_lip_up_0_JNT', 'l_J_mug_lip_up_inside_0_JNT', 'l_J_mug_lip_up_1_JNT', 'l_J_mug_lip_up_inside_1_JNT', 'l_J_mug_lip_up_2_JNT', 'l_J_mug_lip_up_inside_2_JNT', 'l_J_mug_lip_up_3_JNT', 'l_J_mug_mouth_rowA_0_JNT', 'l_J_mug_mouth_rowA_1_JNT', 'l_J_mug_mouth_rowA_2_JNT', 'l_J_mug_mouth_rowA_3_JNT', 'l_J_mug_mouth_rowB_0_JNT', 'l_J_mug_mouth_rowB_1_JNT', 'l_J_mug_mouth_rowB_2_JNT', 'l_J_mug_mouth_rowB_3_JNT', 'l_J_nose_nosabial_rowA_0_JNT', 'l_J_nose_nosabial_rowB_0_JNT', 'l_J_nose_nosabial_rowB_1_JNT', 'l_J_nose_nosabial_rowC_0_JNT', 'l_J_nose_nosabial_rowC_1_JNT', 'mid_J_eye_brows_rowB_0_JNT', 'mid_J_eye_brows_rowC_0_JNT', 'mid_J_eye_brows_rowD_0_JNT', 'mid_J_eye_nose_rowA_0_JNT', 'mid_J_mug_nose_tip_rowA_0_JNT', 'mid_J_mug_nose_tip_rowB_0_JNT', 'l_J_mug_nose_nostril_0_JNT', 'r_J_mug_nose_nostril_0_JNT', 'mid_J_nose_nosabial_rowB_0_JNT', 'r_J_eye_brows_rowA_0_JNT', 'r_J_eye_brows_rowA_0_twk_JNT', 'r_J_eye_brows_rowA_1_JNT', 'r_J_eye_brows_rowA_2_JNT', 'r_J_eye_brows_rowA_3_JNT', 'r_J_eye_brows_rowB_0_JNT', 'r_J_eye_brows_rowB_1_JNT', 'r_J_eye_brows_rowB_2_JNT', 'r_J_eye_brows_rowB_3_JNT', 'r_J_eye_brows_rowC_0_JNT', 'r_J_eye_brows_rowC_1_JNT', 'r_J_eye_brows_rowC_2_JNT', 'r_J_eye_check_rowA_0_JNT', 'r_J_eye_check_rowA_1_JNT', 'r_J_eye_check_rowB_0_JNT', 'r_J_eye_check_rowC_0_JNT', 'r_J_eye_check_rowC_1_JNT', 'r_J_eye_check_rowD_0_JNT', 'r_J_eye_check_rowD_1_JNT', 'r_J_eye_check_rowE_0_JNT', 'r_J_eye_lid_corner_inside_0_JNT', 'r_J_eye_lid_up_rowD_4_JNT', 'r_J_eye_lid_dn_rowA_1_JNT', 'r_J_eye_lid_dn_rowA_2_JNT', 'r_J_eye_lid_dn_rowB_0_JNT', 'r_J_eye_lid_dn_rowB_1_JNT', 'r_J_eye_lid_dn_rowB_2_JNT', 'r_J_eye_lid_up_rowA_1_JNT', 'r_J_eye_lid_up_rowA_2_JNT', 'r_J_eye_lid_up_rowA_0_JNT', 'r_J_eye_lid_up_rowA_3_JNT', 'r_J_eye_lid_up_rowB_0_JNT', 'r_J_eye_lid_up_rowB_1_JNT', 'r_J_eye_lid_up_rowB_2_JNT', 'r_J_eye_lid_up_rowC_0_JNT', 'r_J_eye_lid_up_rowC_1_JNT', 'r_J_eye_lid_up_rowC_2_JNT', 'r_J_eye_lid_up_rowC_3_JNT', 'r_J_eye_lid_up_rowD_1_JNT', 'r_J_eye_lid_up_rowD_2_JNT', 'r_J_eye_lid_up_rowD_3_JNT', 'r_J_eye_nose_rowA_0_JNT', 'r_J_eye_nose_rowA_1_JNT', 'r_J_eye_nose_rowA_2_JNT', 'r_J_eye_nose_rowA_3_JNT', 'r_J_jaw_ear_0_JNT', 'r_J_jaw_ear_1_JNT', 'r_J_jaw_ear_2_JNT', 'r_J_jaw_nosabial_rowA_0_JNT', 'r_J_jaw_nosabial_rowA_1_JNT', 'r_J_jaw_nosabial_rowB_0_JNT', 'r_J_jaw_nosabial_rowB_1_JNT', 'r_J_jaw_nosabial_rowC_0_JNT', 'r_J_jaw_nosabial_rowC_1_JNT', 'r_J_mug_mouth_rowB_0_JNT', 'r_J_mug_mouth_rowB_1_JNT', 'r_J_mug_mouth_rowB_2_JNT', 'r_J_mug_mouth_rowB_3_JNT', 'r_J_nose_nosabial_rowA_0_JNT', 'r_J_nose_nosabial_rowB_0_JNT', 'r_J_nose_nosabial_rowB_1_JNT', 'r_J_nose_nosabial_rowC_0_JNT', 'r_J_nose_nosabial_rowC_1_JNT', 'r_J_mug_mouth_rowA_3_JNT', 'r_J_mug_mouth_rowA_2_JNT', 'r_J_mug_mouth_rowA_1_JNT', 'r_J_mug_mouth_rowA_0_JNT', 'r_J_mug_lip_up_3_JNT', 'r_J_mug_lip_up_2_JNT', 'r_J_mug_lip_up_inside_2_JNT', 'r_J_mug_lip_up_1_JNT', 'r_J_mug_lip_up_inside_1_JNT', 'r_J_mug_lip_up_0_JNT', 'r_J_mug_lip_up_inside_0_JNT', 'l_J_eye_lid_dn_rowA_0_JNT', 'l_J_eye_lid_dn_rowA_3_JNT', 'r_J_eye_lid_dn_rowA_0_JNT', 'r_J_eye_lid_dn_rowA_3_JNT', 'mid_J_jaw_JNT', 'l_J_jaw_nosabial_rowA_2_JNT', 'l_J_jaw_nosabial_rowA_3_JNT', 'l_J_jaw_nosabial_rowB_2_JNT', 'l_J_jaw_nosabial_rowB_3_JNT', 'l_J_jaw_nosabial_rowB_4_JNT', 'l_J_jaw_nosabial_rowC_2_JNT', 'l_J_jaw_nosabial_rowC_3_JNT', 'l_J_jaw_nosabial_rowD_0_JNT', 'l_J_jaw_rowA_0_JNT', 'l_J_jaw_rowB_0_JNT', 'l_J_jaw_rowB_1_JNT', 'l_J_jaw_rowB_2_JNT', 'l_J_jaw_throat_rowA_0_JNT', 'l_J_mug_chin_rowA_0_JNT', 'l_J_mug_chin_rowA_1_JNT', 'l_J_mug_chin_rowA_2_JNT', 'l_J_mug_lip_corner_inside_dn_0_JNT', 'l_J_mug_lip_corner_inside_up_0_JNT', 'l_J_mug_lip_dn_0_JNT', 'l_J_mug_lip_dn_inside_0_JNT', 'l_J_mug_lip_dn_1_JNT', 'l_J_mug_lip_dn_inside_1_JNT', 'l_J_mug_lip_dn_2_JNT', 'l_J_mug_lip_dn_inside_2_JNT', 'l_J_mug_lip_dn_3_JNT', 'l_J_mug_mouth_rowA_4_JNT', 'l_J_mug_mouth_rowA_5_JNT', 'l_J_mug_mouth_rowA_6_JNT', 'l_J_mug_mouth_rowB_4_JNT', 'l_J_mug_mouth_rowB_5_JNT', 'mid_J_jaw_nosabial_rowB_0_JNT', 'mid_J_jaw_throat_rowA_0_JNT', 'mid_J_mug_chin_rowA_0_JNT', 'mid_J_mug_chin_rowA_1_JNT', 'r_J_jaw_nosabial_rowA_2_JNT', 'r_J_jaw_nosabial_rowA_3_JNT', 'r_J_jaw_nosabial_rowB_2_JNT', 'r_J_jaw_nosabial_rowB_3_JNT', 'r_J_jaw_nosabial_rowB_4_JNT', 'r_J_jaw_nosabial_rowC_2_JNT', 'r_J_jaw_nosabial_rowC_3_JNT', 'r_J_jaw_nosabial_rowD_0_JNT', 'r_J_jaw_rowA_0_JNT', 'r_J_jaw_rowB_0_JNT', 'r_J_jaw_rowB_1_JNT', 'r_J_jaw_rowB_2_JNT', 'r_J_jaw_throat_rowA_0_JNT', 'r_J_mug_chin_rowA_0_JNT', 'r_J_mug_chin_rowA_1_JNT', 'r_J_mug_chin_rowA_2_JNT', 'r_J_mug_lip_corner_inside_dn_0_JNT', 'r_J_mug_lip_corner_inside_up_0_JNT', 'r_J_mug_lip_dn_0_JNT', 'r_J_mug_lip_dn_inside_0_JNT', 'r_J_mug_lip_dn_1_JNT', 'r_J_mug_lip_dn_inside_1_JNT', 'r_J_mug_lip_dn_2_JNT', 'r_J_mug_lip_dn_inside_2_JNT', 'r_J_mug_lip_dn_3_JNT', 'r_J_mug_mouth_rowA_4_JNT', 'r_J_mug_mouth_rowA_5_JNT', 'r_J_mug_mouth_rowA_6_JNT', 'r_J_mug_mouth_rowB_4_JNT', 'r_J_mug_mouth_rowB_5_JNT', 'l_J_jaw_rowC_0_JNT', 'l_J_neck_rowA_0_JNT', 'l_J_jaw_rowC_1_JNT', 'r_J_jaw_rowC_1_JNT', 'r_J_jaw_rowC_0_JNT', 'r_J_neck_rowA_0_JNT', 'l_J_jaw_throat_rowB_0_JNT', 'l_J_neck_rowA_1_JNT', 'mid_J_jaw_throat_rowB_0_JNT', 'r_J_jaw_throat_rowB_0_JNT', 'r_J_neck_rowA_1_JNT', 'l_sternocleidomastoid_bot_mscl_JNT', 'l_J_neck_rowA_2_JNT', 'l_J_neck_throat_rowA_0_JNT', 'r_sternocleidomastoid_bot_mscl_JNT', 'r_J_neck_rowA_2_JNT', 'r_J_neck_throat_rowA_0_JNT', 'mid_J_neck_throat_rowA_0_JNT', 'r_J_neck_rowB_0_JNT', 'l_J_neck_rowB_0_JNT', 'r_latissimusDorsi_mscl_JNT', 'l_latissimusDorsi_mscl_JNT', 'r_trapezius_top_mscl_JNT', 'l_chest_front_A_bot_out_JNT', 'l_chest_front_B_top_out_JNT', 'l_chest_front_B_bot_out_JNT', 'l_chest_front_C_top_out_JNT', 'l_chest_front_C_bot_out_JNT', 'l_scapula_A_top_out_JNT', 'l_scapula_A_bot_out_JNT', 'r_chest_front_A_bot_out_JNT', 'r_chest_front_B_top_out_JNT', 'r_chest_front_B_bot_out_JNT', 'r_chest_front_C_top_out_JNT', 'r_chest_front_C_bot_out_JNT', 'r_scapula_A_top_out_JNT', 'r_scapula_A_bot_out_JNT', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'l_calf_0_JNT', 'l_lowLeg_back_B_mscl_JNT', 'l_lowLeg_back_A_mscl_JNT', 'l_knee_mscl_JNT', 'l_thigh_0_JNT', 'l_thigh_1_JNT', 'l_leg_back_B_mscl_JNT', 'l_leg_back_A_mscl_JNT', 'l_leg_groin_mscl_JNT', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase', 'r_calf_0_JNT', 'r_lowLeg_back_A_mscl_JNT', 'r_lowLeg_back_B_mscl_JNT', 'r_knee_mscl_JNT', 'r_thigh_0_JNT', 'r_thigh_1_JNT', 'r_leg_back_B_mscl_JNT', 'r_leg_back_A_mscl_JNT', 'r_leg_groin_mscl_JNT', 'l_leg_buttock_mscl_JNT', 'r_leg_buttock_mscl_JNT']

#choose bones to preserve
#anim_skeleton = bare 62 bones used for animation
#	all below are missing RightInHandThumb and LeftInHandThumb
#csfLOD1_skeleton = 78 bones for LOD1 (62 + twisters on limbs and hips deformers)
#csf_skeleton = 178 bones - full deformers without facial skeleton
#csfr_skeleton = 
main_skeleton = anim_skeleton

sel_child_highlight = pm.selectPref(selectionChildHighlightMode =1, query=True)
sel = pm.ls(sl=1, type = 'transform')
obj = sel[0]
shapeName = str(obj.getShape())
clusterName = str(get_skin_cluster(shapeName))
sciezka = sciezka1 + '\\'+ obj.name() +'.json'


#SAVE WEIGHTS
skinFn = get_skinFn(clusterName)
weights, infs, infIds, fixIds = get_weights(skinFn, kompresuj) # kompresuj = True - przycina wagi do 5 miejsc po ,
weight_data = {'weights': weights, 'infs': infs, 'infIds': fixIds}
name = str(pm.selected()[0].name())


for mainBone in main_skeleton:
	if mainBone not in weight_data['infs']:
		print mainBone, 'is missing, skipping this bone'
		continue
		
	mainBoneID = weight_data['infs'].index(mainBone)
	children = get_hierarchy(mainBone)
	print mainBone, mainBoneID, children
	
	if children != []:
		#print mainBone, mainBoneID
		childrenID = [weight_data['infs'].index(c) for c in children]
		print children, childrenID
		
		#dla każdego werteksa dodaje wartości wag childrenID do wagi mainBoneID, później zeruje i usuwam childrenID 
		for vtxID,vtxWeights in weights.items():
			for childID in childrenID:
				if childID in vtxWeights.keys():
					#print ""
					#print 'original', vtxID, vtxWeights
					break
					
				
			for childID in childrenID:
				if childID in vtxWeights.keys():
					if mainBoneID not in vtxWeights.keys():	vtxWeights[mainBoneID]=0.0000 #add main bone to weights if its missing for specific vertex
						
					vtxWeights[mainBoneID]+=vtxWeights[childID]
					del vtxWeights[childID]
					#print 'changed ', vtxID, vtxWeights					
			weights[vtxID] = vtxWeights
					

#Load Weights
set_weights(clusterName, infs, weights, False)
print 'Done'
