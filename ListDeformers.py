#List deformers of selected mesh in textScrollList
#You can filter the list by textField
#Change  ignore_case to False if you want size of letters matter in filtering

import math
import re
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm

def show_list(ab):

	def filter_list( filter_field,ab,a_list ):
		global ignore_case
		ab_filtered = []
		filter_str = str(pm.textField(filter_field, query=True, text=True))		
		for x in ab:
			y=str(x)
			if ignore_case:filter_field,y = filter_field.lower(), y.lower()
			if filter_str in y:	ab_filtered.append(x)
	
		print ab, filter_str,ab_filtered
		a_list.removeAll()
		for a in ab_filtered: a_list.append(a)


	def defaultButtonPush(*args):
		selbones = pm.textScrollList(a_list, q=1, selectItem =1)
		pm.select(cl=1)
		for s in selbones:
			print s,
			try:pm.select(s.split(' ')[-1] , add=1)
			except: pass			

	okno = pm.window(height = 600, width = 300 )
	#pm.rowLayout( numberOfColumns=2, columnWidth2=(25,  150), columnAlign=(1, 'right'))
	pm.columnLayout( numberOfChildren=3)
	#pm.paneLayout( configuration='horizontal3' )
	bstart = pm.button( label='Select', height = 25, width = 300, command=defaultButtonPush )
	filter_field = pm.textField(width = 300)
	a_list = pm.textScrollList( numberOfRows=8, allowMultiSelection=True, append=ab,showIndexedItem=2, height = 550, width = 300)
	filter_field.changeCommand( pm.windows.Callback( filter_list, filter_field, ab, a_list), edit=True)
	okno.show()
	

def getDeformers(skinNode):	
	joints = cmds.listConnections("%s.matrix" % skinNode)
	cmds.select(cl=True)
	cmds.select(joints)
	deforemers=[]
	for n in joints:
		deforemers.append(str(n))
	return joints
	
def getSkin(fromObj):
	for node in cmds.listHistory(fromObj):
		if cmds.nodeType(node) == "skinCluster":
			skinNode = node
			break
	return skinNode

ignore_case = True

sel = cmds.ls(sl=True)[0]
defs = getDeformers(getSkin(sel))
print ''
for n in defs: print n
print ''

for k, d in enumerate(defs):
	defs[k] = str(k)+'   '+ str(d) 
defs.insert(0, len(defs))
show_list(defs)	
sel = cmds.select(sel)
