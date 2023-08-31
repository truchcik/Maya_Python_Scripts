#	IO_Pose
#
#	Imports pose fron JSON 	(if sel='')
#	Eksports pose from JSON	(if sel !='')
#	Ignoring namespace if rmv_namespace == True

import pymel.core as pm


def check_folder(sciezka):
    if '.' in sciezka.split('\\')[-1]: sciezka = '\\'.join(sciezka.split('\\')[:-1])
    if not os.path.isdir(sciezka): os.makedirs(sciezka)
    

def save_json(posed, file_pose):
	print('zapisuje', file_pose)
	import json
	json=json.dumps(posed)
	f=open(file_pose,'w')
	f.write(json)
	f.close()
	

def read_json(file_pose):
	import json
	with open(file_pose) as json_data:
		return json.load(json_data)	  
		
		
def openNamedJason(transforms):
	maska =	 named_folder.replace('\\','/')+'/*.json'
	n= pm.fileDialog( directoryMask=maska )
	#print(str(n))
	pose = read_json(n)
	open_pose(pose, transforms)
	
	
def saveNamedJason(*args):
	maska =	 named_folder.replace('\\','/')+'/'
	n = pm.fileDialog2 ( fileFilter = "*.json", dir = maska, dialogStyle = 2 )
	n=str(n[0])
	#print(n)
	save_pose(n)
	

def save_pose(path):
	global rmv_namespace
	sel, posed = [], []
	for oObj in pm.selected():
		nazwa = oObj
		#czy chcesz wyrzućić namespace z nazwy kości?
		if rmv_namespace == True: nazwa = oObj.split(':')[-1]		
		sel.append(nazwa)
		try:
			pos = [ oObj.getTranslation()[0], oObj.getTranslation()[1], oObj.getTranslation()[2]  ]
			rot = [ oObj.getRotation()[0], oObj.getRotation()[1], oObj.getRotation()[2]	 ]
			scl = [ oObj.getScale()[0], oObj.getScale()[1], oObj.getScale()[2]	]
			#print nazwa,round(rot[0],2),round(rot[1],2),round(rot[2],2)			
			posed.append([str(nazwa),pos,rot,scl])
		except: pass
	save_json(posed, path)			
	
			  
def open_pose(posed, transforms):

	sel=[]	 
	for oObj,pos,rot,scl in posed:
		sel.append(oObj)
		try:
			ob = pm.PyNode(oObj)
			sel.append(ob)
			
			if transforms[0]: #transform
				try:ob.tx.set(pos[0])
				except Exception as e: print (e)
				try:ob.ty.set(pos[1])
				except Exception as e: print (e)
				try:ob.tz.set(pos[2])
				except Exception as e: print (e)
			if transforms[1]:#rotation
				try:ob.rx.set(rot[0])
				except Exception as e: print (e)
				try:ob.ry.set(rot[1])
				except Exception as e: print (e)
				try:ob.rz.set(rot[2])
				except Exception as e: print (e)
			if transforms[2]:#scale
				try:ob.sx.set(scl[0])
				except Exception as e: print (e)
				try:ob.sy.set(scl[1])
				except Exception as e: print (e)
				try:ob.sz.set(scl[2])
				except Exception as e: print (e)
		except Exception as e: print(e)
		

def IOpose(action, posBox, rotBox, sclBox, flWin):
	transforms = [pm.checkBox(posBox, query=True, value=True),
					pm.checkBox(rotBox, query=True, value=True),
					pm.checkBox(sclBox, query=True, value=True)]
	pm.deleteUI(flWin, window=True)

	if action == 'Save': saveNamedJason()
	elif action ==  'Load': openNamedJason(transforms)
	elif action == 'Load from Clipboard':
		posed = read_json(default_file)
		open_pose(posed, transforms)
	elif action == 'Save 2 Clipboard':save_pose(default_file)
	

def choose(action):	
	clip_action = 'Save 2 Clipboard'
	if action == 'Load': clip_action = 'Load from Clipboard'
	flWin = pm.window(title=action + " transfoms", wh=(290,55))
	pm.columnLayout()
	pm.text(label='Choose transfoms') 
	pm.rowColumnLayout(numberOfColumns=3)
	posBox	  = pm.checkBox	   (label='Translation',value = True)
	rotBox		 = pm.checkBox	  (label=' Rotation	 ',value = True)
	sclBox		  = pm.checkBox	   (label=' Scale	  ', value = True)
	pm.button(label=clip_action, w=150, command=lambda x: IOpose(clip_action, posBox, rotBox, sclBox, flWin))
	pm.button(label=action+' JSON', w=150, command=lambda x: IOpose(action, posBox, rotBox, sclBox, flWin))
	pm.showWindow(flWin)


default_file = r'Z:\p4\WX\wx.assets\characters\_tech\Char_Scripts_Data\Poses\pose.json'
named_folder = r'Z:\p4\WX\wx.assets\characters\_tech\Char_Scripts_Data\Poses'
rmv_namespace = True	#wyrzuca namespace z nazwy kości

if pm.selected()==[]: action = 'Load'
else: action = 'Save'

choose(action)
