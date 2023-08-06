#Build mesh from pointcloud

import maya.cmds as cmds
import maya.OpenMaya as om

v0 = om.MPoint(1,0,0)
v1 = om.MPoint(0,1,0)
v2 = om.MPoint(0,0,1)
v3 = om.MPoint(1,0,1)
v4 = om.MPoint(1,2,0)

vertices = [v0,v1,v2,v3,v4]

def expandListN(lista, n):
    print 'Reszta:', len(vertices)%n
    if len(vertices)%n != 0:
        for k in range(n - len(vertices)%n):
            lista.append(lista[k])
    return lista
    

def makeTriMesh(vertices):    
    meshFn = om.MFnMesh()
    faceArray = om.MPointArray()
    faceArray.setLength(3)
    
    for k in range(len(vertices)-1):
        print 'Triangle', k
        for n in range(3):
            faceArray.set(vertices[n+k],n)
            print '\tVertex',n+k, vertices[n+k]
        meshFn.addPolygon(faceArray, True, 0.001)

print (expandListN(vertices,3))
#makeTriMesh(vertices)
