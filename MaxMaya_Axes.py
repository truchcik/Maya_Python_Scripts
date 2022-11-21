# Toggles between Max (MetaHuman) and Maya axes
# Updates viewports

import pymel.core as pm

maya_set = {'log':'\nChange viewports settings to default (Maya)\n',
            'axis':'z', 'trans':[50,-400,900], 'rots':[90,0,0]}
max_set  = {'log':'\nChange viewports settings to MetaHuman (3dMax)\n',
            'axis':'y', 'trans':[50,-400,900], 'rots':[0,0,0]}

def setViewports(settings):
    print (settings['log'])
    pm.Env().setUpAxis(settings['axis'])
    pm.select('persp')
    cam.setTranslation(settings['trans'], space ='world')
    cam.setRotation(settings['rots'], space ='world')

if pm.Env().getUpAxis()=='y': setViewports(maya_set)
else: setViewports(max_set)
