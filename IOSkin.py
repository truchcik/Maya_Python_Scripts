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
    if '.' in sciezka.split('\\')[-1]: sciezka = '\\'.join(sciezka.split('\\')[:-1])
    if not os.path.isdir(sciezka): os.makedirs(sciezka)
    
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

        print ('\t!', plik, '\tnie istnieje, szukam podobnych...')      
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
    if prnt: print ('\tSaving weights to','\n\t', path)
    pliczek = json.dumps(comp_dict, indent=4)
    f=open(path,"w")
    f.write(pliczek)
    f.close()
    

def open_json (path):
    if not os.path.exists(path):
        print ('\t!!! nie znalazłem pliku z wagami, pomijam mesh')
        return
    print ('\tOtwieram wagi z', '\t\t', path, '\n')
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
        print ('\tLoading weights from attibutes')
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
    
    missing_bones   = []
    ok_infs         = []
    for k, inf in enumerate (infs):
        try:
            pm.select(inf)
            ok_infs.append(inf)
        except:
            missing_bones.append(k)
    print ('Brakuje ',len(missing_bones),'kości:', [val for k,val in enumerate(infs) if k in missing_bones])
    print ('Naprawiam skining...')
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
                
    # Podmieniam stare indexy kości na nowe (na podstawie mapowania ind_dic)
    for k in weights.keys():                
        for kk in weights[k].keys():
            weights[k][ind_dic[int(kk)]] = weights[k].pop(kk)
            
    del ind_dic, missing_bones, infs    
    return {'infs': ok_infs, 'infIds':infIds, 'weights':weights}
                
                
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


def set_weights(obj, infs, weights, no_skin):
    
    def zero_weights(clusterName, infs):
        #zeroes weights in clusterName 
        for inf in infs: cmds.setAttr(str(inf)+'.liw')
        skinNorm = cmds.getAttr('%s.normalizeWeights' % clusterName)
        if skinNorm != 0: cmds.setAttr('%s.normalizeWeights' % clusterName, 0)
        cmds.skinPercent(clusterName, shapeName, nrm=False, prw=100)
        if skinNorm != 0:
            cmds.setAttr('%s.normalizeWeights' % clusterName, skinNorm)
        return clusterName
                            
    shapeName = str(obj.getShape())
    clusterName = str(get_skin_cluster(shapeName))
    zero_weights(clusterName, infs)

    for vertId, weightData in weights.items():
        wlAttr = '%s.weightList[%s]' % (clusterName, vertId)
        #print ('vertId =', vertId)
        for infId, infValue in weightData.items():          
            try:
                #print ('    infIds[infId] =', infIds[infId], joints[int(infIds[infId])],'   infValue =', infValue)         
                if no_skin: wAttr = '.weights[%s]' % infId
                else: wAttr = '.weights[%s]' % infIds[infId]
                #print ('       ', wlAttr, wAttr, infValue)
                cmds.setAttr(wlAttr + wAttr, infValue)
            except: pass

def del_SkinAttr(obj):
    print ('Kasuje attrybuty:',)
    for  a in pm.listAttr(obj):
        try:            
            if a == 'SavedSkin':
                att=obj.attr(a)
                print (a,)
                att.unlock()
                pm.deleteAttr(att)
            if a == 'SkinAttr':
                att=obj.attr(a)
                print (a,)
                pm.deleteAttr(att)
        except Exception as e: print (e)

def saveSkin(obj, sciezka):
    shapeName = str(obj.getShape())
    clusterName = str(get_skin_cluster(shapeName))
    sciezka_copy = sciezka + '\\' + '_copy_' + str(i) + '.json'
    sciezka = sciezka + '\\'+ obj.name().split('|')[-1] +'.json'
    
    try: skinFn = get_skinFn(clusterName)
    except:
        print ('\tNie znalazłem skina. Pomijam.')
        return
    
    #SAVE WEIGHTS
    weights, infs, infIds, fixIds = get_weights(skinFn, kompresuj) # kompresuj = True - przycina wagi do 5 miejsc po ,
    weight_data = {'weights': weights, 'infs': infs, 'infIds': fixIds}
    name = str(pm.selected()[0].name().split('|')[-1])      
    
    if zapisz_jsona:
        try:
            save_json(weight_data , sciezka) #Zapisywanie wag do pliku JSON
            save_json(weight_data , sciezka_copy)
        except Exception as e:
            print ('Błąd przy zapisywaniu jsona', e)
            
    att = data_2_attr(obj, 'SkinAttr', weight_data)
    show_skin_attr(obj, 'SavedSkin')
    att_size = str(round(sys.getsizeof(pm.getAttr(att))/1048576.0, 4))+ 'MB'
    print ('\t', obj.attr('SkinAttr').name() ,'\tsaved. Size =',att_size)


def LoadPasteSkin(obj, sciezka, wybor):
    shapeName = str(obj.getShape())
    clusterName = str(get_skin_cluster(shapeName))
    sciezka_copy = sciezka + '\\' + '_copy_' + str(i) + '.json'
            
    mtrx = obj.getTransformation()
    unlock(obj)
    try: obj.setTransformation([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
    except: print ('Reset transforms failed. Do it manualy and restuart script')    
    
    no_skin = False
    name            = str(obj.name().split('|')[-1] )
    
    if wybor == 'Paste Skin': #delete skin attribute, load skin from _copy_n.jsons, save skin attr
        weight_data = open_json(sciezka_copy)
    else:
        weight_data= attr_2_data(obj, 'SkinAttr')
        if not weight_data:
            sciezka = sciezka + '\\' + obj.name() + '.json' 
            weight_data = open_json(sciezka)
                  
    if not weight_data:     
        print ('\t! Brakuje skin_attr, paste i load failed. Try to load envs from file searching similar names...')
        sciezka = sciezka + '\\' + obj.name() + '.json'                             
        sciezka = find_json(sciezka)
        weight_data = open_json(sciezka)
        
        if weight_data == None:
            sciezka = find_json(sciezka)
            weight_data = open_json(sciezka)
    
    weight_data     = tweak_data(weight_data) #wywalam u'
    weights, infs, infIds = weight_data["weights"], weight_data["infs"], weight_data["infIds"]      
    pm.refresh()
    pm.select(cl=1)
    
    #Selecting all deformers to  see if they are here. If not, try to skip them    
    try: pm.select(infs)
    except:
        print ('\tSome deforemers from JSON file are missing, change weights to skin them...')
        weight_data  = fix_skinning(weight_data)
        weights, infs, infIds = weight_data["weights"], weight_data["infs"], weight_data["infIds"]
        pm.select(infs)
        
    #Deleting skin cluster, to make new one
    try: 
        pm.delete(clusterName)
        clusterName = 'None'
    except: print ('\t\tDeleting skin cluster failed')

    if clusterName == 'None':
        try:
            clusterName = pm.skinCluster(infs, obj.getShape(),  name=obj.name().replace(":", "_").replace("|", "") + "_SKN",toSelectedBones = True)
            clusterName = str(get_skin_cluster(shapeName))
            no_skin = True
        except:
            print ('\t!Blad przy wczytowyaniu skina!\n\t', obj)
            
    print ('\tApplying weights to skin cluster')
    set_weights(obj, infs, weights, no_skin)
    unlock(obj)
    try: obj.setTransformation(mtrx)
    except: pass
    return
            
    
#weights    {vert index:{influence id : weight}, vert index 2 {}, ...}
#infs       tablica kosci
#infIds     dict mapuje id istniejącego deformera mesha w id deformera z binda {index w meshu(str) : index w meshu podczas binda (int), ...}
#weights    dict [vert index(int) : {deformer index(int) : weight(float), ...}

sciezka =       r'Z:\p4\WX\wx.assets\characters\_tech\Char_Scripts_Data\XENVS\fast_skin'
inf_mode =      'long_names'    #Zapisuje deformery tylko jako nazwy np 'Hips'.'long_names' jako hierarchie np 'Skeleton|Root|Hips'
kompresuj =     False           #Pełna precyzja wag. True przycina je do 5 miejsc po przecinku
zapisz_jsona =  True            #Zapisz dodatkowo skin do plików json.
sel_child_highlight = pm.selectPref(selectionChildHighlightMode =1, query=True)
obj = None

wybor =pm.confirmDialog( title='SkinTool', message='Choose', button=['Save/Copy Skin', 'Load Skin', 'Paste Skin', 'Delete SkinAttr','CANCEL'],defaultButton='CANCEL')
check_folder(sciezka) #make sure yoou have skin folder

t0 = time.time()
pm.selectPref(selectionChildHighlightMode=1) #umożliwia nadawanie skina meshom ułożonym w hierarchii
sel = [x for x in pm.ls(sl=1, type = 'transform')]
        
        
for i,obj in enumerate(sel):
    weight_data = None
    if pm.listRelatives(obj, children=True)[0].nodeType() != 'mesh':
        print ('\n! {} is not a mesh, skipping'.format(obj))
        continue
    
    print ('Working on', obj, 'mesh')
    
    if wybor == 'Delete SkinAttr': del_SkinAttr(obj)
    elif wybor == 'Save/Copy Skin': saveSkin(obj, sciezka)    
    elif wybor == 'Load Skin' or wybor == 'Paste Skin':
        LoadPasteSkin(obj, sciezka, wybor)
    
pm.select(sel)
pm.selectPref(selectionChildHighlightMode = sel_child_highlight) #przywraca oryginalne ustawienie selekcji dzieci
print ('\n', '***  Gotowe,  czas = ', time.time()-t0, 's.  ***')
