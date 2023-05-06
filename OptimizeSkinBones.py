#OptimizeBones
#for selected mesh:
#Removes all deformers except 'main_skeleton' list from skinning  
#Moves removed bone's skin weights to their parents/grandparents from 'main_skeleton' list

import pymel.core as pm


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
		children = [x for x in children if x in weight_data['infs']] #zbieram tylko te dzieci które są w wagach
		if children:
				for c in children: allChildren.append(c)
				for child in children:hierarchyTree(child, allChildren)   
	
	allChildren = []
	hierarchyTree(str(mainBone), allChildren)
	return allChildren	



main_skeleton  = ['Hips','Spine','Spine1','Spine2','Spine3','Neck','Neck1','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase','LeftInHandThumb','LeftHandThumb1','LeftHandThumb2','LeftInHandIndex','LeftHandIndex1','LeftHandIndex2','LeftHandIndex3','LeftInHandMiddle','LeftHandMiddle1','LeftHandMiddle2','LeftHandMiddle3','LeftInHandRing','LeftHandRing1','LeftHandRing2','LeftHandRing3','LeftInHandPinky','LeftHandPinky1','LeftHandPinky2','LeftHandPinky3','RightInHandThumb','RightHandThumb1','RightHandThumb2','RightInHandIndex','RightHandIndex1','RightHandIndex2','RightHandIndex3','RightInHandMiddle','RightHandMiddle1','RightHandMiddle2','RightHandMiddle3','RightInHandRing','RightHandRing1','RightHandRing2','RightHandRing3','RightInHandPinky','RightHandPinky1','RightHandPinky2','RightHandPinky3']


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
	mainBoneID = weight_data['infs'].index(mainBone)
	children = get_hierarchy(mainBone)
	if children != []:
		print mainBone, mainBoneID
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
