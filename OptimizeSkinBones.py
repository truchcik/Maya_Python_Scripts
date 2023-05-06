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
main_skeleton  = ['Hips','Spine','Spine1','Spine2','Spine3','Neck','Neck1','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase','LeftInHandThumb','LeftHandThumb1','LeftHandThumb2','LeftInHandIndex','LeftHandIndex1','LeftHandIndex2','LeftHandIndex3','LeftInHandMiddle','LeftHandMiddle1','LeftHandMiddle2','LeftHandMiddle3','LeftInHandRing','LeftHandRing1','LeftHandRing2','LeftHandRing3','LeftInHandPinky','LeftHandPinky1','LeftHandPinky2','LeftHandPinky3','RightInHandThumb','RightHandThumb1','RightHandThumb2','RightInHandIndex','RightHandIndex1','RightHandIndex2','RightHandIndex3','RightInHandMiddle','RightHandMiddle1','RightHandMiddle2','RightHandMiddle3','RightInHandRing','RightHandRing1','RightHandRing2','RightHandRing3','RightInHandPinky','RightHandPinky1','RightHandPinky2','RightHandPinky3']


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
