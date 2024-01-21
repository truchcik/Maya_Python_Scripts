#OptimizeBones
#Removes all deformers except in main_skeleton from skinning  for selected mesh
# set MainSkeleton depending on your needs - this are bones to be preserved
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
	for x in range(infDags.length()):
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
	for vId in range(wlPlug.numElements()):
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
		#print ('vertId =', vertId)
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


sciezka1 = 		r'G:\nauka\Scripts_Python\Scripts_Python_Maya\PyMel\_FAST_SKIN_WRK\data'
inf_mode = 		'short_names'	#Zapisuje deformery tylko jako nazwy np 'Hips'.'long_names' jako hierarchie np 'Skeleton|Root|Hips'
kompresuj = 	False			#Pełna precyzja wag. True przycina je do 5 miejsc po przecinku

small_skel =  ['Hips', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'RightLeg', 'RightFoot', 'RightToeBase', 'LeftHand' , 'RightUpLeg', 'Neck', 'Neck1', 'Head' ]
anim_skel = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'Neck', 'Neck1', 'Head', 'HeadTip', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'LeftHandEnd', 'LeftInHandThumb',
            'LeftHandThumb1', 'LeftHandThumb2', 'LeftHandThumb3', 'LeftInHandIndex', 'LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3', 'LeftHandIndex4', 'LeftInHandMiddle', 'LeftHandMiddle1',
            'LeftHandMiddle2', 'LeftHandMiddle3', 'LeftHandMiddle4', 'LeftInHandRing', 'LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3', 'LeftHandRing4', 'LeftInHandPinky', 'LeftHandPinky1', 'LeftHandPinky2',
            'LeftHandPinky3', 'LeftHandPinky4', 'LeftHandWeapon', 'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand', 'RightHandEnd', 'RightInHandThumb', 'RightHandThumb1', 'RightHandThumb2', 'RightHandThumb3',
            'RightInHandIndex', 'RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3', 'RightHandIndex4', 'RightInHandMiddle', 'RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3', 'RightHandMiddle4', 'RightInHandRing',
            'RightHandRing1', 'RightHandRing2', 'RightHandRing3', 'RightHandRing4', 'RightInHandPinky', 'RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3', 'RightHandPinky4', 'RightHandWeapon', 'LeftUpLeg', 'LeftLeg', 'LeftFoot',
            'LeftHeel', 'LeftToeBase', 'LeftToeTip', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightHeel', 'RightToeBase', 'RightToeTip']

new_skeleton = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Spine3', 'LeftShoulder', 'LeftArm', 'l_SHL_0_JNT', 'l_deltoid_top_top_out_JNT', 'l_deltoid_top_bot_out_JNT', 'l_deltoid_front_top_out_JNT', 'l_deltoid_front_bot_out_JNT', 'l_deltoid_back_top_out_JNT', 'l_deltoid_back_bot_out_JNT', 'l_triceps_mscl_JNT', 'l_biceps_A_mscl_JNT', 'LeftForeArm', 'l_Wrist_0_JNT', 'l_Wrist_1_JNT', 'l_Wrist_2_JNT', 'l_wrist_A_mscl_JNT', 'l_wrist_B_mscl_JNT', 'l_wrist_C_mscl_JNT', 'LeftHand', 'LeftHandThumb1', 'LeftHandThumb2', 'l_thumb_side_mscl_JNT', 'LeftInHandIndex', 'LeftHandIndex1', 'LeftHandIndex2', 'LeftHandIndex3', 'l_ind_knuckle_B_top_mscl_JNT', 'l_ind_knuckle_top_mscl_JNT', 'l_ind_knuckle_bot_mscl_JNT', 'l_thumb_thumb_A_bot_mscl_JNT', 'l_thumb_thumb_A_top_mscl_JNT', 'LeftInHandMiddle', 'LeftHandMiddle1', 'LeftHandMiddle2', 'LeftHandMiddle3', 'l_mid_knuckle_B_top_mscl_JNT', 'l_mid_knuckle_top_mscl_JNT', 'l_mid_knuckle_bot_mscl_JNT', 'LeftInHandRing', 'LeftHandRing1', 'LeftHandRing2', 'LeftHandRing3', 'l_ring_knuckle_B_top_mscl_JNT', 'l_ring_knuckle_top_mscl_JNT', 'l_ring_knuckle_bot_mscl_JNT', 'LeftInHandPinky', 'LeftHandPinky1', 'LeftHandPinky2', 'LeftHandPinky3', 'l_pinky_knuckle_B_top_mscl_JNT', 'l_pinky_knuckle_top_mscl_JNT', 'l_pinky_knuckle_bot_mscl_JNT', 'l_pinkyBase_A_bot_mscl_JNT', 'l_elbow_bend_A_mscl_JNT', 'l_elbow_bend_B_mscl_JNT', 'l_elbow_back_mscl_JNT', 'l_butterfly_top_out_JNT', 'RightShoulder', 'RightArm', 'r_SHL_0_JNT', 'r_deltoid_top_top_out_JNT', 'r_deltoid_top_bot_out_JNT', 'r_deltoid_front_top_out_JNT', 'r_deltoid_front_bot_out_JNT', 'r_deltoid_back_top_out_JNT', 'r_deltoid_back_bot_out_JNT', 'r_triceps_mscl_JNT', 'r_biceps_A_mscl_JNT', 'RightForeArm', 'r_Wrist_0_JNT', 'r_Wrist_1_JNT', 'r_Wrist_2_JNT', 'r_wrist_A_mscl_JNT', 'r_wrist_B_mscl_JNT', 'r_wrist_C_mscl_JNT', 'RightHand', 'RightHandThumb1', 'RightHandThumb2', 'r_thumb_side_mscl_JNT', 'RightInHandIndex', 'RightHandIndex1', 'RightHandIndex2', 'RightHandIndex3', 'r_ind_knuckle_B_top_mscl_JNT', 'r_ind_knuckle_top_mscl_JNT', 'r_ind_knuckle_bot_mscl_JNT', 'r_thumb_thumb_A_bot_mscl_JNT', 'r_thumb_thumb_A_top_mscl_JNT', 'RightInHandMiddle', 'RightHandMiddle1', 'RightHandMiddle2', 'RightHandMiddle3', 'r_mid_knuckle_B_top_mscl_JNT', 'r_mid_knuckle_top_mscl_JNT', 'r_mid_knuckle_bot_mscl_JNT', 'RightInHandRing', 'RightHandRing1', 'RightHandRing2', 'RightHandRing3', 'r_ring_knuckle_B_top_mscl_JNT', 'r_ring_knuckle_top_mscl_JNT', 'r_ring_knuckle_bot_mscl_JNT', 'RightInHandPinky', 'RightHandPinky1', 'RightHandPinky2', 'RightHandPinky3', 'r_pinky_knuckle_B_top_mscl_JNT', 'r_pinky_knuckle_top_mscl_JNT', 'r_pinky_knuckle_bot_mscl_JNT', 'r_pinkyBase_A_bot_mscl_JNT', 'r_elbow_bend_A_mscl_JNT', 'r_elbow_bend_B_mscl_JNT', 'r_elbow_back_mscl_JNT', 'r_butterfly_top_out_JNT', 'Neck', 'Neck1', 'Head', 'r_latissimusDorsi_mscl_JNT', 'l_latissimusDorsi_mscl_JNT', 'l_chest_front_A_bot_out_JNT', 'l_chest_front_B_top_out_JNT', 'l_chest_front_B_bot_out_JNT', 'l_chest_front_C_top_out_JNT', 'l_chest_front_C_bot_out_JNT', 'l_scapula_A_top_out_JNT', 'l_scapula_A_bot_out_JNT', 'r_chest_front_A_bot_out_JNT', 'r_chest_front_B_top_out_JNT', 'r_chest_front_B_bot_out_JNT', 'r_chest_front_C_top_out_JNT', 'r_chest_front_C_bot_out_JNT', 'r_scapula_A_top_out_JNT', 'r_scapula_A_bot_out_JNT', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'l_calf_0_JNT', 'l_lowLeg_back_B_mscl_JNT', 'l_lowLeg_back_A_mscl_JNT', 'l_knee_mscl_JNT', 'l_thigh_0_JNT', 'l_thigh_1_JNT', 'l_leg_back_B_mscl_JNT', 'l_leg_back_A_mscl_JNT', 'l_leg_groin_mscl_JNT', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase', 'r_calf_0_JNT', 'r_lowLeg_back_A_mscl_JNT', 'r_lowLeg_back_B_mscl_JNT', 'r_knee_mscl_JNT', 'r_thigh_0_JNT', 'r_thigh_1_JNT', 'r_leg_back_B_mscl_JNT', 'r_leg_back_A_mscl_JNT', 'r_leg_groin_mscl_JNT', 'l_leg_buttock_mscl_JNT', 'r_leg_buttock_mscl_JNT']


main_skeleton = anim_skel
sel_child_highlight = pm.selectPref(selectionChildHighlightMode =1, query=True)

for obj in pm.selected():

    try: shapeName = str(obj.getShape())
    except: pass
    clusterName = str(get_skin_cluster(shapeName))
    sciezka = sciezka1 + '\\'+ obj.name() +'.json'
    
    
    #SAVE WEIGHTS
    skinFn = get_skinFn(clusterName)
    weights, infs, infIds, fixIds = get_weights(skinFn, kompresuj) # kompresuj = True - przycina wagi do 5 miejsc po ,
    weight_data = {'weights': weights, 'infs': infs, 'infIds': fixIds}
    name = str(pm.selected()[0].name())
    
    
    for mainBone in main_skeleton:
    	if mainBone not in weight_data['infs']:
    		print (mainBone, 'is missing, skipping this bone')
    		continue
    		
    	mainBoneID = weight_data['infs'].index(mainBone)
    	children = get_hierarchy(mainBone)
    	print (mainBone, mainBoneID, children)
    	
    	if children != []:
    		#print mainBone, mainBoneID
    		childrenID = [weight_data['infs'].index(c) for c in children]
    		print (children, childrenID)
    		
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

print ('Done')
