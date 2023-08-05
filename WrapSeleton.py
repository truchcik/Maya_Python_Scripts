#Wrap skeleton
# select bones, source mesh and target mesh 
# 1 create mesh fitting bones
# 2 deforms mesh by delta between two cage meshes
# 3 fits bones to deformed mesh vtx positions

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.api.OpenMaya as api
import pymel.core as pm


def getListPos(lista):
    #det list of positions of objects in a list
    locPos = [pm.xform(loc, q=1, ws=1, t=1) for loc in lista]
    return locPos
    

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
                    if logme: print ('\tVertex{}:, {}'.format(n+k, vertices[n+k]))
                meshFn.addPolygon(faceArray, True, 0.001)
        return meshFn
    
    locPos = getListPos(bones)
    vertices = [om.MPoint(locP[0], locP[1], locP[2]) for locP in locPos]
    meshFn = makeTriMesh(vertices, logme=True)
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


bones = [x for x in pm.ls(sl=1)[:-2]]
oSrc=  pm.ls(sl=1)[-2]
oTrg = pm.ls(sl=1)[-1]

oMesh = makeSkelMesh(bones) #Make mesh with vtx fitting bones positions
defByDelta(oMesh, oSrc, oTrg)   #Deforms mesh by delta between to cages
moveBones2Vertices(bones, oMesh) #Fits skel positions to deformed mesh
pm.select(bones)
