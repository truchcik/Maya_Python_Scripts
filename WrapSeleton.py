#Wrap skeleton
# select bones, source mesh and target mesh 
# 1 create mesh fitting bones
# 2 deforms mesh by delta between two cage meshes
# 3 fits bones to deformed mesh vtx positions

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.api.OpenMaya as api
import pymel.core as pm


def setSelection():
    #Expand seclection to be compatible with rest of the script
    #a) 1 bone selected: children of bone hierarchy necessary to adjust skeleton
    #b) 3 objs slelected: does a) and adds delta meshes to end of selection
    
    def listHierarchy(obj):
        #select bone hierarchy except of:
        #children of '_GRP' objects
        #bojs with Constraint1 in name
        def hierarchyTree(parent, lista):
            if parent[-4:]== '_GRP': return lista
            pLoc = pm.xform(parent, q=1, ws=1, t=1)
            children = pm.listRelatives(parent, c=True, type='transform')
            children = [str(x.name() ) for x in children]
            
            if children:
                for child in children:
                    #remove unwanted children
                    if child[-11:] == 'Constraint1': continue
                    pLoc = pm.xform(child, q=1, ws=1, t=1)
                    #if cLoc == pLoc:continue                
                    lista.append(child)
                    hierarchyTree(child, lista)
                                                  
        lista = [str(obj)]
        hierarchyTree(str(obj), lista)
        return lista    

    if len(pm.selected()) == 1:
        print ('1 obj selected. Skeleton only')
        oObj = pm.selected()[0]
        pm.select(listHierarchy(oObj))
    elif len(pm.selected()) ==3:
        oObj = pm.selected()[0]
        oSrc = pm.selected()[-2]
        oTrg = pm.selected()[-1]
        pm.select(listHierarchy(oObj), oSrc, oTrg)
        print ('3 objs selected. Full service')
    else: print('Pleas select pivot, or pivot and  two delta meshes')


def getListPos(lista):
    #det list of positions of objects in a list
    locPos = [pm.xform(loc, q=1, ws=1, t=1) for loc in lista]
    return locPos
    

def expandListN(lista, n):
    print ('List len = {}, %= {}'.format(len(lista), len(lista)%n))
    #print 'Reszta:', len(lista)%n
    if len(lista)%n != 0:
        for k in range(n - len(lista)%n):
            lista.append(lista[k])
    print ('Expanded list len = {}, %= {}'.format(len(lista), len(lista)%n))
    print ()
    return lista
    

def makeSkelMesh(bones):
    #Create mesh with vertices fitting locations of list of objects    
    
    def makeTriMesh(vertices, logme=False):
        #create mesh from om.MPoint position list 
        meshFn = om.MFnMesh()    
        faceArray = om.MPointArray()
        faceArray.setLength(3)
        
        for k in range(len(vertices)-1):
            if k+2<len(vertices):
                if logme: print ('Triangle {}, verices {}-{}'.format(k,k,k+2))
                for n in range(3):
                    faceArray.set(vertices[n+k],n)
                    if logme: print ('\tVertex{}:, {}'.format(n+k, [vertices[n+k][x] for x in range(3)]))
                meshFn.addPolygon(faceArray, True, 0.001)
        return meshFn

    def makeSplitMesh(veritces, logme=False):
        meshFn = om.MFnMesh()
        faceArray = om.MPointArray()
        faceArray.setLength(3)  
        
        for v in range(len(veritces)/3):
            if logme: print ('Triangle{}'.format(v))
            for k in range(3):     
                faceArray.set(vertices[v*3+k],k)        
                if logme: print ('\tVertex {}, pos {}'.format(v*3+k,[veritces[v*3+k][x] for x in range(3)]))
            meshFn.addPolygon(faceArray, False)
        return meshFn  
    
    locPos = getListPos(bones)
    vertices = [om.MPoint(locP[0], locP[1], locP[2]) for locP in locPos]
    vertices = expandListN(vertices, 3)
    #meshFn = makeTriMesh(vertices, logme=True)
    meshFn = makeSplitMesh(vertices, logme=False) #choosen to build uconnected triangles to avoid merge issues
    meshPm = pm.PyNode(meshFn.fullPathName()).listRelatives(parent = 1)[0]
    meshPm.rename('Skeleton_Mesh')
    return meshPm
  
    
def defByDelta(oMesh, oSrc, oTrg):
    #deforms oMesh by delta between oSrc and oTrg using Wrap deformer
    
    def setBlendshape(oSrc, oTrg):
        pm.select(oTrg)
        pm.select(oSrc, add=1)
        skelBlend = pm.blendShape(automatic = 1, n= 'skelBlend', en = 1)    
        return skelBlend
    
    def setWrap(meshPm, oSrc):
        pm.select(meshPm)
        pm.select(oSrc, add=1)
        cmds.CreateWrap()      
    
    morph =  setBlendshape(oSrc, oTrg)
    setWrap(oMesh, oSrc)
    pm.blendShape( morph, edit=True, w=[(0, 1)])


def moveBones2Vertices(bones, oMesh):
  
    def get_positions(obj):
        #get list of vertices positions
    	posa = []
    	mobj = api.MGlobal.getSelectionListByName(obj.name()).getDagPath(0)	#Open Maya mesh handle	
    	base_node_mfn = api.MFnMesh(mobj) #Open Maya shape handle
    	base_face_inds = base_node_mfn.getVertices() #[indexy vertexów w trójkątach, indexy vertexow]
    	positions = base_node_mfn.getPoints()
    	for i in range(len(positions)):
    		posa.append([positions[i][0], positions[i][1], positions[i][2]])		
    	return posa	    
    
    posa = get_positions(oMesh)    
    for k, b in enumerate(bones): pm.move(posa[k][0], posa[k][1], posa[k][2], b, absolute=True)

setSelection()

action  = 'skelOnly' # if only hierachy is selected, script ends after building mesh
if len(pm.ls(sl=1))>2:
    oSrc=  pm.ls(sl=1)[-2]
    oTrg = pm.ls(sl=1)[-1]
    try:
        if pm.listRelatives(oTrg, children=True)[0].nodeType() == 'mesh':
            if pm.listRelatives(oSrc, children=True)[0].nodeType() == 'mesh':
                bones = [x for x in pm.ls(sl=1)[:-2]]
                action = 'fullService'                
        else:
            bones = [x for x in pm.ls(sl=1)]
            del oSrc
            del oTrg
    except: bones = [x for x in pm.ls(sl=1)]
        
oMesh = makeSkelMesh(bones) #Make mesh with vtx fitting bones position

if action == 'fullService':
    defByDelta(oMesh, oSrc, oTrg)   #Deforms mesh by delta between to cages
    moveBones2Vertices(bones, oMesh) #Fits skel positions to deformed mesh
    
pm.select(bones)
