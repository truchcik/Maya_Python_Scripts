#Saves or loads skin to 'SkinAttr' attribute
#Sets visible attribute 'SavedSkin' to show artist that skin is saved on mesh
# G:\nauka\Scripts_Python\Scripts_Python_Maya\PyMel\_FAST_SKIN_WRK\OpenMayaSkin_Fast.py


import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import json, sys, time, os.path, string

def check_folder(sciezka):
	try:
		if not os.path.isdir(sciezka):
			os.mkdir(sciezka)
	except: pass

def check_usr():
	import os
	dev_user = ['dominik.milecki']
	for us in dev_user:
		if us in os.environ['user']: return True
	return False
	
def unlock(obj):
	try:
		for att in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
			if obj.attr(att).isLocked: obj.attr(att).unlock()
	except: pass
	
def find_json (path): #ignoruje cyferki na koncu, pasted__, bodytype ( w tej kolejnosci)
	body_types = ['_ma_', '_maf', '_wa_','_waf_', '_mb_', '_mba_', '_wba_', '_mf_', '_mc_']
	plik = path.split('\\')[-1].replace('.json','')
	folder = path.replace(plik+'.json', '')
	if os.path.exists(path):return path
	else: 

		print '\t!', plik, '\tnie istnieje, szukam podobnych...'			
		for bt in body_types:
			if bt in plik:
				body_types_1 = list(body_types)
				body_types_1.insert(0, bt)
				for bt_swap in body_types_1:
					for pref in ['','pasted__']:
						for plik_1 in [plik, plik.rstrip(string.digits)]:
							szukam = plik_1.replace(pref,'').replace(bt, bt_swap)
							for x in os.listdir(folder):
								if szukam in x:
									path = folder+x
									m=pm.confirmDialog( title= obj.name(), message='Cannot find original skin file "'+obj.name()+'.json"', button=['Use '+x, 'Skip'],defaultButton='Skip')
									if m == 'Skip':
										del m
										return ''
									return path
		return ''
		
			
def save_json (comp_dict, path, prnt = True):
	if prnt: print 'Saving weights to','\n\t', path
	pliczek = json.dumps(comp_dict)
	f=open(path,"w")
	f.write(pliczek)
	f.close()
	

def open_json (path):
	if not os.path.exists(path):
		print '\t!!! nie znalazłem pliku z wagami, pomijam mesh'
		return
	print '\tOtwieram wagi z', '\tt', path.split('\\')[-1], '\n'
	js = open(path)
	mySel=json.load(js) #dictionary
	js.close()
	return mySel
	

def data_2_attr(obj, att_name, dane):
	dane_str = json.dumps(dane) #zamienia dane na string
	if pm.attributeQuery( att_name, node=obj, exists=1):
		attribute_node = obj.attr(att_name)
		pm.deleteAttr(attribute_node)	
	pm.addAttr(obj, ln=att_name, dataType='string', hidden = False)
	attribute_node = obj.attr(att_name)	
	pm.setAttr(attribute_node, dane_str)
	return attribute_node
	

def attr_2_data (obj, att_name):
	if pm.attributeQuery( att_name, node=obj, exists=1):
		att_node = obj.attr(att_name)
		weight_str = pm.getAttr(att_node)
		weight_data = json.loads(weight_str)
		return weight_data
	else:
		return None
		
def show_skin_attr(obj, att_name):
	if pm.attributeQuery( att_name, node=obj, exists=1):
		if obj.attr(att_name).isLocked: obj.attr(att_name).unlock()
		pm.deleteAttr(obj.name()+'.'+att_name)
	pm.addAttr(obj, ln=att_name, at='bool')
	att_node = obj.attr(att_name)
	pm.setAttr(att_node, 1)
	pm.setAttr(att_node,  channelBox = True, keyable = False,  lock = 1)

def tweak_data(weight_data):
	for k, val in enumerate(weight_data['infs']): weight_data['infs'][k]=str(val)
	for k in weight_data['infIds'].keys(): weight_data['infIds'][str(k)] = weight_data['infIds'].pop(k)
	for k in weight_data['weights'].keys():
		for v in weight_data['weights'][k].keys():
			weight_data['weights'][k][str(v)] = weight_data['weights'][k].pop(v)
		weight_data['weights'][str(k)] = weight_data['weights'].pop(k)
	return weight_data


def fix_skinning(weight_data):
	infs = weight_data['infs']
	infIds = weight_data['infIds']
	weights = weight_data['weights']
	
	try: pm.select(infs)
	except: pass # Bone tree doesnt exist as whole, restricting to bones only...'
	
	infs = [x.split('|')[-1] for x in infs ]
	try: pm.select(infs)
	except: pass # Some bones are missing ...'
	
	missing_bones 	= []
	ok_infs 		= []
	for k, inf in enumerate (infs):
		try:
			pm.select(inf)
			ok_infs.append(inf)
		except:
			missing_bones.append(k)
	print 'Brakuje ',len(missing_bones),'kości:', [val for k,val in enumerate(infs) if k in missing_bones]
	print 'Naprawiam skining...'
	pm.refresh()
	# mapuje inf na istniejace kosci {old_ind (z pliku) : new_ind(z istniejących)}'
	ind_dic = {}
	for inf in infs:
		try: ind_dic[infs.index(inf)] = ok_infs.index(inf)
		except: ind_dic[infs.index(inf)] = 0
	
	# podmieniam infIds...'
	infIds={}
	for old, new in ind_dic.items(): infIds[str(new)]=new

	# Usuwam wagowanie vertexów z brakującymi kośćmi
	for k in weights.keys():
		for bone in missing_bones:
			if str(bone) in [kk for kk in weights[k].keys()]:
				del weights[k]
				break
				
	# Podmieniam stare indexy kości na nowe	(na podstawie mapowania ind_dic)
	for k in weights.keys():				
		for kk in weights[k].keys():
			weights[k][ind_dic[int(kk)]] = weights[k].pop(kk)
			
	del ind_dic, missing_bones, infs	
	return {'infs':	ok_infs, 'infIds':infIds, 'weights':weights}
				
				
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
	
#weights	{vert index:{influence id : weight}, vert index 2 {}, ...}
#infs		tablica kosci
#infIds     dict mapuje id istniejącego deformera mesha w id deformera z binda {index w meshu(str) : index w meshu podczas binda (int), ...}
#weights	dict [vert index(int) : {deformer index(int) : weight(float), ...}

sciezka1 = 		r'Z:\r6.assets\characters\wip\skins'
sciezka2 = 		r'M:\XENVS\fast_skin'
inf_mode = 		'long_names'	#Zapisuje deformery tylko jako nazwy np 'Hips'.'long_names' jako hierarchie np 'Skeleton|Root|Hips'
kompresuj = 	False			#Pełna precyzja wag. True przycina je do 5 miejsc po przecinku
zapisz_jsona = 	True			#Zapisz dodatkowo skin do plików json.
sel_child_highlight = pm.selectPref(selectionChildHighlightMode =1, query=True)

wybor =pm.confirmDialog( title='SkinTool', message='Choose', button=['Save SkinAttr / Copy', 'Load SkinAttr', 'Paste', 'Delete SkinAttr','CANCEL'],defaultButton='CANCEL')

#make sure yoou have skin folder
check_folder(sciezka1)

t0 = time.time()
pm.selectPref(selectionChildHighlightMode=1) #umożliwia nadawanie skina meshom ułożonym w hierarchii
sel = pm.ls(sl=1, type = 'transform')
for i,obj in enumerate(sel):
	print '\n', obj
	
	#DELETE SKIN ATTR
	if wybor == 'Delete SkinAttr':
		print 'Kasuje attrybuty:',
		for  a in pm.listAttr(obj):
			try:			
				if a == 'SavedSkin':
					att=obj.attr(a)
					print a,
					att.unlock()
					pm.deleteAttr(att)
				if a == 'SkinAttr':
					att=obj.attr(a)
					print a,
					pm.deleteAttr(att)
			except Exception as e: print e
		continue
		
		
	shapeName = str(obj.getShape())
	clusterName = str(get_skin_cluster(shapeName))
	sciezka = sciezka1 + '\\'+ obj.name().split('|')[-1] +'.json'
	sciezkadev = sciezka2 + '\\'+ obj.name().split('|')[-1] +'.json'
	
	#Save skin
	if wybor == 'Save SkinAttr / Copy':
		try: skinFn = get_skinFn(clusterName)
		except:
			print '\tNie znalazłem skina. Pomijam.'
			continue
		
		#SAVE WEIGHTS
		weights, infs, infIds, fixIds = get_weights(skinFn, kompresuj) # kompresuj = True - przycina wagi do 5 miejsc po ,
		weight_data = {'weights': weights, 'infs': infs, 'infIds': fixIds}
		name = str(pm.selected()[0].name().split('|')[-1])		
		
		sciezka_copy = sciezka1 + '\_copy_' + str(i) + '.json'
		sciezka2_copy = sciezka2 + '\_copy_' + str(i) + '.json'
		
		if zapisz_jsona:
			try:
				save_json(weight_data , sciezka) #Zapisywanie wag do pliku JSON
				save_json(weight_data , sciezka_copy, False)
				if check_usr():
					save_json(weight_data , sciezkadev)
					save_json(weight_data , sciezka2_copy, False)
			except Exception as e:
				print 'Błąd przy zapisywaniu jsona', e
		att = data_2_attr(obj, 'SkinAttr', weight_data)
		show_skin_attr(obj, 'SavedSkin')
		att_size = str(round(sys.getsizeof(pm.getAttr(att))/1048576.0, 4))+ 'MB'
		print '\t', obj.attr('SkinAttr').name() ,'\tsaved. Size =',att_size	
	
	#Load/paste skin
	elif wybor == 'Load SkinAttr' or wybor == 'Paste':
		mtrx = obj.getTransformation()
		unlock(obj)
		try: obj.setTransformation([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
		except: pass
		
		
		no_skin = False
		name 			= str(obj.name().split('|')[-1] )
		print 'name =', name
		
		weight_data 	= attr_2_data(obj, 'SkinAttr')
		if not weight_data:
			print '\t! Brakuje skin_attr, próbuje wczytać wagi z pliku...'
			if wybor == 'Paste':
				sciezkadev = sciezka2 + '\_copy_' + str(i) + '.json'
				sciezka = sciezka1 + '\_copy_' + str(i) + '.json'
			sciezka = find_json(sciezka)
			weight_data	= open_json(sciezka)
			if weight_data == None:
				sciezka = find_json(sciezkadev)
				weight_data	= open_json(sciezka)
			if weight_data == None: continue
		else: print '\tWczytałem wagi z atrybutu "SkinAttr" na obiekt', obj.name()

		weight_data 	= tweak_data(weight_data) #wywalam u'
		weights, infs, infIds = weight_data["weights"], weight_data["infs"], weight_data["infIds"]		
		pm.refresh()
		pm.select(cl=1)
		try: pm.select(infs)
		except:
			weight_data  = fix_skinning(weight_data)
			weights, infs, infIds = weight_data["weights"], weight_data["infs"], weight_data["infIds"]
			pm.select(infs)

		try: 
			pm.delete(clusterName)
			clusterName = 'None'
		except: pass
	
		if clusterName == 'None':
			try:
				clusterName = pm.skinCluster(infs, obj.getShape(),  name=obj.name().replace(":", "_").replace("|", "") + "_SKN",toSelectedBones = True)
				clusterName = str(get_skin_cluster(shapeName))
				no_skin = True
			except:
				print '\t!Blad przy wczytowyaniu skina!\n\t', obj
				continue
			
		set_weights(clusterName, infs, weights, no_skin)
		unlock(obj)
		try: obj.setTransformation(mtrx)
		except: pass
	
pm.select(sel)
pm.selectPref(selectionChildHighlightMode = sel_child_highlight) #przywraca oryginalne ustawienie selekcji dzieci
print '\n', '***  Gotowe,  czas = ', time.time()-t0, 's.  ***'
