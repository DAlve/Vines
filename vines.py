'''
Created on 4/04/2016

@author: dalve
'''

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.OpenMayaFX as omfx
import maya.mel as mel
import random
import time
import math



root_grp = '|vines_grp'
particle_grp = '%s|particles_grp' % root_grp
dynamics_grp = '%s|dynamics_grp' % root_grp
outCurve_grp = '%s|outCurves_grp' % root_grp
ctrlCurves_grp = '%s|ctrlCurves_grp' % root_grp
outGeo_grp = '%s|outGeo_grp' % root_grp 


def _setup_grps(root_grp, grps = [], additional = None):
    """
    Sets up the group structure that we want in our scene
    """
    
    # once we have our selection stuff done we want to create some groups
    # to help keep everything tidy
    if not cmds.ls(root_grp):
        cmds.group(name=root_grp, empty=True)
    
    children = cmds.listRelatives(root_grp, children=True, typ='transform')
    
    for i in grps:
    
        grp_name = i.split('|')[-1]
        
        if not children or not grp_name in children:
            cmds.group(name=grp_name, empty=True)
            
            cmds.parent(grp_name, root_grp)
    
    
    if additional:
        for masterGrp in additional:
            
            addGrps = additional[masterGrp]
            
            children = cmds.listRelatives(masterGrp, children=True, type='transform')
            
            for grp in addGrps:
                if not children or not grp in children:
                    cmds.group(name=grp, empty=True)
                    cmds.parent(grp, masterGrp)
       
        
def create_particle(numParticles = 5):
    
    print 'Creating paticles'
    
    # before we start set the time back to the first frame
    tMin = int(cmds.playbackOptions(q=True, minTime=True))
    cmds.currentTime(tMin, e=True)
    
    
    # get our current selection
    selList = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(selList)
    
    # make sure that something is selected!
    if selList.length() == 0:
        print 'Nothing is selected. Please select something to emit from!'
        return
    
    
    mFnMesh = om.MFnMesh()
    mFnDepend = om.MFnDependencyNode()
    
    # create our itereator and start looping
    # (mostly should only be one item but putting this in just in case) 
    iterSel = om.MItSelectionList(selList)
    
    # once the selections are all done we can setup our grouping structure to 
    # keep everything clean (hopefully)
    _setup_grps(root_grp,
                grps=[particle_grp, dynamics_grp])
    
    
    print 'finished creating groups'
    
    items = []
    
    while not iterSel.isDone():
        
        # setup some arrays we want to fill
        partPos = om.MPointArray()
        
        # get the dagpath and mobject for our currrent item
        dagPath = om.MDagPath()
        mObj = om.MObject()
        
        iterSel.getDagPath(dagPath)
        iterSel.getDependNode(mObj)
        
        # make sure our object is compatible with mFnMesh
        if not dagPath.hasFn(om.MFn.kMesh):
            print '%s is not valid with MFnMesh!' % dagPath.fullPathName()
            iterSel.next()
            continue
        
        mFnMesh.setObject(dagPath)
        mFnDepend.setObject(mObj)
        
        # start a search for particle system or create one if we can't
        # find a connected particle system
        npObj = None
        
        if mFnDepend.hasAttribute('particles'):
            print 'Found attribute'
            
            particlesPlug = mFnDepend.findPlug('particles')
            
            connectedParticles = particlesPlug.numConnectedElements()
            
            # if no connections create a particle system
            if connectedParticles == 0:
                print 'No particles found. Creating some!'
                npObj = _create_part(mFnDepend)
            
            # if we get one connection, make sure it's not empty
            # if it's not get the particle system connected or if
            # it is then create a new particle system
            elif  connectedParticles > 1:
                print '### Error: Currently not dealing with more than one particle conncected to an object!'
                iterSel.next()
                continue
                
                
            else:
                print 'Found a connection!!!'
                # as we only have one connection we can just get the first connected
                # plug
                particlePlug = particlesPlug.connectionByPhysicalIndex(0)
                
                # get all the plugs connect to our plug as a desitination
                mPlugArray = om.MPlugArray()
                particlePlug.connectedTo(mPlugArray, True, False)
                
                # if we have more than one plug connected then something is wrong!
                if mPlugArray.length() > 1:
                    print 'Oh noes! More than one object connected!'
                    iterSel.next()
                    continue
                
                # get the plug connected to our particle plug and retrieve the mObject
                # it is coming from
                connectedPlug = mPlugArray[0]
                npObj = connectedPlug.node()
                    
        else:
            npObj = _create_part(mFnDepend)
            
        # make sure we have an MObject item
        if not isinstance(npObj, om.MObject):
            print '###Error: Could not find or create a nParticle system!!!'
            iterSel.next()
            continue
        
        # create a function set for our particle system
        npDagPath = om.MDagPath.getAPathTo(npObj)
        npPart = omfx.MFnParticleSystem(npDagPath)
        
        # make sure that particle system is empty
        if not npPart.count() == 0:
            #npPart.setCount(0)
            mDoubleArray = om.MDoubleArray()
            for i in range(npPart.count()):
                mDoubleArray.append(0.0)
            
            npPart.setPerParticleAttribute('lifespanPP', mDoubleArray)
            
            mTime = om.MTime(tMin+1)
            npPart.evaluateDynamics(mTime, False)
            npPart.saveInitialState()
            
            cmds.currentTime(tMin, e=True)
            
        # setup the particle positions we want
        for i in range(numParticles):
            
            print '#-------------------------------#'
            print '### %s' % i
            point = _get_rand_point(dagPath)
            partPos.append(point)
        
        
        npPart.emit(partPos)
        
        # save the initial state of particles
        npPart.saveInitialState()
        
        # if we get this far then we want to add the item to our list
        # so that when we are done we can create a clean selection
        items.append(dagPath.fullPathName())
        
        iterSel.next()
    
    # select all the successful objects to finish
    # this allows the user ease of acces to re-seed their particles
    cmds.select(items)
        
'''
def set_goals(self):
    
    sel = cmds.ls(sl=True, l=True)
    
    # make sure we have at least two items 
    if len(sel) < 2:
        print 'Please select a nParticle system followed by the objects to set as goals'
        return
    
    elif len(sel) > 2:
        print 'For inital goal we want one particle system and one object to goal!'
        print 'Try again :)'
        return
    
    print sel
    
    # from the list make sure the first object is a nparticle system, get a handle on this
    # then remove from the list
    if not cmds.objectType(sel[0]) == 'nParticle':
        
        shape = cmds.listRelatives(sel[0])[0]
        
        if not cmds.objectType(shape) == 'nParticle':
            print 'Please select a nParticle system followed by objects to goal to!'
            return
        
        else:
            npSystem = sel.pop(0)
            npShape = shape 
    
    else:
        npShape = sel.pop(0)
        npSystem = cmds.listRelatives(npShape, parent=True, f=True)
        
    obj = sel[0]
        
    
    selList = om.MSelectionList()
    selList.add(npShape)
    
    npDag = om.MDagPath()
    npMObj = om.MObject()
    
    selList.getDependNode(0, npMObj)
    selList.getDagPath(0, npDag)
    
    npNode = om.MFnDependencyNode(npMObj)
    npFnPart = omfx.MFnParticleSystem(npDag)
    
    
    if self._get_goal(npNode):
        print 'Particle system already has goal. For now we are only supporting one goal!'
        return
    
    cmds.goal(npSystem, g=obj, w=1)
    
    
    self.set_initial_state(npNode, npFnPart)
    
    print '#------------------------------#'
    
    runtime_dynExpression = ('.goalV += .verticalSpeedPP;\n'
                             '.goalU += .rotationRatePP;\n\n'
                             'if (.jitterIntervalPP > .jitterStepPP)\n'
                             '{\n'
                             '\t.jitterStepPP ++;\n'
                             '}\n'
                             'else\n' 
                             '{\n'
                             '\t.goalU += .jitterValuePP;\n'
                             '\t$hiRange = rand(0, .jitterRangePP);\n'
                             '\t$loRange = $hiRange * -1;\n'
                             '\t.jitterValuePP = rand($loRange, $hiRange);\n'
                             '\t.jitterStepPP = 0;\n'
                             '}\n\n'
                             'if (.goalU > 1)\n'
                             '{\n'
                             '\t.goalU -= 1;\n'
                             '}\n'
                             'else if(.goalU < 0)\n'
                             '{\n'
                             '\t.goalU += 1;\n'
                             '}')
                            
    cmds.dynExpression(npShape, rbd=True,  string=runtime_dynExpression)
    
    # now we want to make our goal object a passive rigid body so that
    # the particles don't go through it
    cmds.select(obj)
    
    print 'Selection is: %s' % cmds.ls(sl=True)
    
    # make our goal object a passive rigid body so the particles 
    # can collide with it
    cmd = 'makeCollideNCloth'
    rigidShape = mel.eval(cmd)
    
    # rigid shape is not created if it already exists!
    if rigidShape:
        # parent the rigid body to keep things tidy
        nRigid = cmds.listRelatives(rigidShape[0], parent=True, f=True)
        cmds.parent(nRigid, dynamics_grp)
    
    # select our particle system to tidy things up
    cmds.select(npSystem)
    
 
def set_initial_state(self, npNode=None, npFnPart=None):
    """
    Given a particle dependency node calculate the start goalU and and goalV values
    :param npNode: Particle dependency node to get goal data from
    :param npFnPart: particle function set we can get the points from and set data
    """
    
    print 'Setting initial state'
    
    # before we start set the time back to the first frame
    tMin = int(cmds.playbackOptions(q=True, minTime=True))
    cmds.currentTime(tMin, e=True)
    
    # a list of all the base attributes we want to make sure exist!
    attrs = {'goalU': {'longName': 'goalU',
                       'shortName': 'goalU',
                       'initialState':True,  
                       'type':om.MFnNumericData.kDoubleArray,
                       'data': om.MDoubleArray()},
             'goalV': {'longName': 'goalV',
                       'shortName': 'goalV',
                       'initialState':True,
                       'type':om.MFnNumericData.kDoubleArray,
                       'data': om.MDoubleArray()},
             'verticalSpeedPP': {'longName': 'verticalSpeedPP',
                                 'shortName': 'vSpePP',
                                 'initialState':True,
                                 'type':om.MFnNumericData.kDoubleArray,
                                 'data': om.MDoubleArray()},
             'rotationRatePP': {'longName': 'rotationRatePP',
                                  'shortName': 'rotRtPP',
                                  'initialState':True,
                                  'type':om.MFnNumericData.kDoubleArray,
                                  'data': om.MDoubleArray()},
             'jitterIntervalPP': {'longName': 'jitterIntervalPP',
                                  'shortName': 'jtrIntPP',
                                  'initialState':True,
                                  'type':om.MFnNumericData.kDoubleArray,
                                  'data': om.MDoubleArray()},
             'jitterStepPP': {'longName': 'jitterStepPP',
                              'shortName': 'jtrStpPP',
                              'initialState':True,
                              'type':om.MFnNumericData.kDoubleArray,
                              'data': om.MDoubleArray()},
             'jitterRangePP': {'longName': 'jitterRangePP',
                               'shortName': 'jtrRngPP',
                               'initialState': True,
                               'type': om.MFnNumericData.kDoubleArray,
                               'data': om.MDoubleArray()},
             'jitterValuePP': {'longName': 'jitterValuePP',
                               'shortName': 'jtrValPP',
                               'initialState':True,
                               'type':om.MFnNumericData.kDoubleArray,
                               'data': om.MDoubleArray()},
             'isDonePP': {'longName': 'isDonePP',
                               'shortName': 'isDonePP',
                               'initialState':True,
                               'type':om.MFnNumericData.kDoubleArray,
                               'data': om.MDoubleArray()},
             'lifespanPP': {'longName': 'lifespanPP',
                               'shortName': 'lifespanPP',
                               'initialState':True,
                               'type':om.MFnNumericData.kDoubleArray,
                               'data': om.MDoubleArray()}}
    
    goalMeshFn = om.MFnMesh()
    
    # if nothing passed in we assume we are updating intial state
    # so need to setup npNode and npFnPart from selection
    if not npNode:
        sel = cmds.ls(sl=True, l=True)
    
        if len(sel) == 0:
            print 'Please select a nParticle system to update initial state on!'
            return
        
        # from the list make sure the first object is a nparticle system, get a handle on this
        # then remove from the list
        if not cmds.objectType(sel[0]) == 'nParticle':
            
            shape = cmds.listRelatives(sel[0])[0]
            
            if not cmds.objectType(shape) == 'nParticle':
                print 'Please select a nParticle system followed by objects to goal to!'
                return
            
            else:
                npShape = shape 
        
        else:
            npShape = sel.pop(0)
            
        # now we have our particle system we need to get the 
        # dependency node and particle system function set        
        selList = om.MSelectionList()
        selList.add(npShape)
        
        npDag = om.MDagPath()
        npMObj = om.MObject()
        
        selList.getDependNode(0, npMObj)
        selList.getDagPath(0, npDag)
        
        npNode = om.MFnDependencyNode(npMObj)
        npFnPart = omfx.MFnParticleSystem(npDag)
    
    
    if npFnPart == None:
        print '###Error: Please make sure you pass in both a dependency node and function set or neither!'
        return
        
        
    # get the goalGeometry plug. this can tell us what our
    # particle is goaled to
    goalGeo_plug = npNode.findPlug('goalGeometry')

    # get the first item that is connected as a goal (this will be our initial goal)
    goal_plug = goalGeo_plug.elementByPhysicalIndex(0)
    attrName = goal_plug.name()
    
    # get the goal index number (this may not be 0)
    goalIndex = attrName.split('[')[-1].split(']')[0]
    
    # create the goal weight attribute
    attrs['goalWeight%sPP' % goalIndex] = {'longName': 'goalWeight%sPP' % goalIndex,
                                            'shortName': 'goalWeight%sPP' % goalIndex,
                                            'initialState': True, 
                                            'type':om.MFnNumericData.kDoubleArray,
                                            'data': om.MDoubleArray()}
    
    # make sure that all the attributes we need exist
    self._create_attributes(npNode, attrs)
    
    # get all the objects connected to our goal array plug (should only be 1!)
    mPlugArray = om.MPlugArray()
    goal_plug.connectedTo(mPlugArray, True, False)
    
    if mPlugArray.length() > 1:
        print '###Error :More than one object is connected to this goal plug. Weird!'
        return
    
    # get the node that is connected the plug and get a mesh function set
    goal_obj = mPlugArray[0].node()
    goal_dagpath = om.MDagPath().getAPathTo(goal_obj)
    goalMeshFn.setObject(goal_dagpath)
    
    # setup a bunch of arrays we are about to calculate
    partPosArray = om.MVectorArray()
    
    # get a list of all the points in our particle system and iterate through them
    npFnPart.position(partPosArray)
    
    
    
    # get user defined variables
    verticalOffset = self.ui.vertOffset_spinBox.value()
    goalWeight_min = self.ui.goalWMin_spinBox.value()
    goalWeight_max = self.ui.goalWMax_spinBox.value()
    verticleSpeed_min = self.ui.vSpdMin_spinBox.value()
    verticleSpeed_max = self.ui.vSpdMax_spinBox.value()
    rotationSpeed = self.ui.rotSpd_spinBox.value()
    jitterInterval = self.ui.jtrInt_spinBox.value()
    jitterRange = self.ui.jtrRange_spinBox.value()
    
    
    
    # for each particle we want to calculate information on the intial state
    # for all of our pp attributes we want to set
    for i in range(partPosArray.length()):
        
        # get our particle point as a vector
        partPoint = partPosArray[i]
        
        # get the goal uvs closest to our point
        uvArray = [0,0]
        scriptUtil = om.MScriptUtil()
        scriptUtil.createFromList(uvArray, 2)
        uvPoint = scriptUtil.asFloat2Ptr()
        
        goalMeshFn.getUVAtPoint(om.MPoint(partPoint), uvPoint, om.MSpace.kWorld)
            
        uPoint = om.MScriptUtil.getFloat2ArrayItem(uvPoint, 0, 0)
        #vPoint = om.MScriptUtil.getFloat2ArrayItem(uvPoint, 0, 1)
        
        # append to our goalU and goalV array 
        attrs['goalU']['data'].append(uPoint%1)
        attrs['goalV']['data'].append(random.uniform(0, verticalOffset))
        
        goalWeight = random.uniform(goalWeight_min, goalWeight_max)
        
        # give this particle a random goal weight
        attrs['goalWeight%sPP' % goalIndex]['data'].append(goalWeight)
        #goal_weights.append(1)
        
        # set a bunch of attributes used to control motion of particles
        attrs['verticalSpeedPP']['data'].append(random.uniform(verticleSpeed_min, verticleSpeed_max))
        
        adjustedRot = rotationSpeed * (1.1 - goalWeight)
        
        attrs['rotationRatePP']['data'].append(random.uniform(0, adjustedRot))
        attrs['jitterIntervalPP']['data'].append(random.randint(1, jitterInterval))
        attrs['jitterStepPP']['data'].append(0)
        attrs['jitterRangePP']['data'].append(jitterRange)
        attrs['jitterValuePP']['data'].append(random.uniform((-1 * jitterRange), jitterRange))
        
        attrs['isDonePP']['data'].append(0)
        
        attrs['lifespanPP']['data'].append(100000000000000000)
    
    # for each item in our attrs dictionary we want to set the attribute data
    for i in attrs:
        print 'Setting: %s' % i
        if npFnPart.hasAttribute(i):
            npFnPart.setPerParticleAttribute(i, attrs[i]['data'])
    
    
    # save our intial state (NB: if the particle sim has moved on from particle start it 
    # will overwrite their positions. Write a check in at the start of function)
    npFnPart.saveInitialState()       


def part2curve(self):
    """
    Converts a particle system in curves
    
    """
    
    start_time = time.time()
    
    # get the frame range that we want to iterate over
    tMin = int(cmds.playbackOptions(q=True, minTime=True))
    tMax = int(cmds.playbackOptions(q=True, maxTime=True))
    
    tStep = self.ui.interval_spinBox.value()
    
    # set the current time to the first frame we want to evaluate
    cmds.currentTime(tMin, e=True )
    
    # get our selection list
    selList = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(selList)
    
    iterSel = om.MItSelectionList(selList) 
    
    # once we have our selection we want to setup our groups
    self.parent._setup_grps(root_grp,
                           grps=[outCurve_grp])
    
    # setup our our function set for use later
    particleFn = omfx.MFnParticleSystem()
    partNode = om.MFnDependencyNode()
    
    
    # iterate over our selection
    while not iterSel.isDone():
        
        print '\n#------------------------------------#'
        
        # get the dagpath and mObj
        mObj = om.MObject()
        dagPath = om.MDagPath()
        iterSel.getDagPath(dagPath)
        iterSel.getDependNode(mObj)
        
        # make sure our selection is valid with our particle function set
        if not dagPath.hasFn(om.MFn.kParticle):
            print '%s not valid with particle function set' % dagPath.fullPathName()
            iterSel.next()
            continue
        
        # set our function set
        particleFn.setObject(dagPath)
        partNode.setObject(mObj)
        
        # get our goal object and function set
        goal = self._get_goal(dg=dagPath)
        goalDagpath = om.MDagPath().getAPathTo(goal)
        
        if goal.hasFn(om.MFn.kMesh):
            mFnMesh = om.MFnMesh(goalDagpath)
        else:
            print '###Error: Have not dealt with non mesh goals yet!'
            mFnMesh = None
        
        particleData = {}
        
        # go through each frame 
        for frame in xrange(int(tMax)):
            #print frame + 1
            numParticles = particleFn.count()
            
            # if this frame is one that we want to sample...
            if frame in range(tMin, tMax, tStep):
                print '#------------------------------#'
                
                print 'Calculating frame: %s' % frame
                # setup arrays that we need for calculations
                particleIds = om.MIntArray()
                positions = om.MVectorArray()
                lifespanPP = om.MDoubleArray()
                
                particleFn.particleIds(particleIds)
                particleFn.position(positions)
                particleFn.getPerParticleAttribute('lifespanPP', lifespanPP)
                
                for i in range(numParticles):
                    
                    partId = particleIds[i]
                    # print partId
                    if not partId in particleData.keys():
                        particleData[partId] = []
                    
                    position = positions[i]
                    
                    particleData[partId].append((position.x,
                                                 position.y,
                                                 position.z))

                    if mFnMesh:
                        print 'Checking if particle is finished!'
                        
                        uvArray = [0,0]
                        uvScriptUtil = om.MScriptUtil()
                        uvScriptUtil.createFromList(uvArray, 2)
                        uvPoint = uvScriptUtil.asFloat2Ptr()
                        
                        mFnMesh.getUVAtPoint(om.MPoint(position), uvPoint, om.MSpace.kWorld)

                        u = om.MScriptUtil.getFloat2ArrayItem(uvPoint, 0, 0)
                        v = om.MScriptUtil.getFloat2ArrayItem(uvPoint, 0, 1)
                        
                        tolerance = self.ui.tolerance_spinBox.value()
                        
                        print 'UV: %s %s' % (u, v)
                        print (1- tolerance)
                        
                        if v > (1- tolerance):
                            print '\t\t\t\tKilling particle'
                            lifespanPP[i] = 0
                            particleFn.setPerParticleAttribute('lifespanPP', lifespanPP)
            
            
            mTime = om.MTime(frame+1)
            particleFn.evaluateDynamics(mTime, False)
            
        for i in particleData:
            print '%s: %s' % (i, particleData[i])
        
        
        curveNum = 1
        for i in particleData:
            partName = partNode.name()
            
            curve_name = '%s_outCrv_%03d' % (partName.split('_')[0], curveNum)
            outCurve = cmds.curve(p=particleData[i])
            
            final_name = cmds.rename(outCurve, curve_name)
            cmds.parent(final_name, outCurve_grp)
            curveNum += 1
        
        iterSel.next()
    
    
    
    # set the current time to the first frame we want to evaluate
    cmds.currentTime(tMin, e=True )
    
    
    stop_time = time.time()
    
    total_time = stop_time - start_time
    print 'Total time: %s' % total_time
    
    
     




def rebuild(self):
    """
    Rebuilds the selected curves to have the number of cvs defind by user
    """
    
    sel = cmds.ls(sl=True)
    
    spans = self.ui.numCvs_spinBox.value()
    
    for i in sel:
        if cmds.objectType(i) == 'transform':
            
            shapes = cmds.listRelatives(i, children=True, shapes=True)
            
            if len(shapes) == 0:
                print '%s is not a curve!' % i
                continue
            elif len(shapes) > 1:
                print '%s has more than one child shape!' % i
                continue
            else:
                if not cmds.objectType(shapes[0]) == 'nurbsCurve':
                    print '%s is not a curve!' % i
                    continue
                
                transform = cmds.ls(i, l=True)
        
        elif cmds.objectType(i) == 'nurbsCurve':
            transform = cmds.listRelatives(i, parent = True, f=True)
        
        else:
            print '%s is not a curve!' % i
            continue
        
        cmds.rebuildCurve(transform,
                          ch = 0,
                          rpo = 1,
                          rt = 0,
                          end = 1,
                          kr = 0,
                          kcp = 0,
                          kep = 1,
                          kt = 0,
                          s = spans,
                          d = 3,
                          tol = 0.01)
    
    
    print sel
    cmds.select(sel)
            

def curve_offset(self, level='Hi'):
    """
    Takes selected curves and runs a noise modifier on it to create variation
    
    :param level: switches between doing a hi and lo offset
    
    """
    
    kinks = self.ui.numKinks_spinBox.value()
    kinkScale = self.ui.kinkMultiplier_spinBox.value()
    randomOffset = self.ui.kinkOffset_spinBox.value()
    
    
    # get our selection list and create an iter for us ot loop over
    selList = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(selList)
    
    iterSel = om.MItSelectionList(selList)
    
    # set up the mFnNurbs curve that we will use later
    mFnNurbsCurve = om.MFnNurbsCurve()
    
    
    # loop through our selection
    while not iterSel.isDone():
        print 'Applying curve offset!'
        # get the dagpath and mObj
        mObj = om.MObject()
        dagPath = om.MDagPath()
        iterSel.getDagPath(dagPath, mObj)
        
        # make sure we have the shape dag path and not the transform
        dagPath.extendToShape()
        
        # make sure we have an item that can work with the nurbs curve 
        # function set, if we don't then skip to the next item
        if not dagPath.hasFn(om.MFn.kNurbsCurve):
            iterSel.next()
            continue
        
        print dagPath.fullPathName()
        # set our function set
        mFnNurbsCurve.setObject(dagPath)
        
        mPointArray = om.MPointArray()
        mFnNurbsCurve.getCVs(mPointArray, om.MSpace.kWorld)
        
        print mPointArray.length()
        
        # count the number of cvs we have in our curve
        numCvs = mFnNurbsCurve.numCVs()
        
        # get the spacing between cvs that our kinks will appear
        kinkSpacing = int(numCvs / kinks)
        
        # get our kink random min and max values
        randomMax = (abs(kinkScale) * abs(randomOffset))
        randomMin = randomMax * -1
        
        
        if level == 'Hi':
            # for each kink step define a random offset in x, y and z
            # for the first kink make sure that we set it to 0 so our
            # intial point doesn't move
            for kink in range(kinks+1):
                
                # kink         -    The kink number we are up to
                # kinks        -    Total number of kinks we are creating
                # kink spacing -    Number of cv's between kinks
                # kink number  -    The cv number that is the current kink
                
                #cmds.select(cl=True)
                kink_number = kink * kinkSpacing
                
                cvPoint = om.MPoint()
                mFnNurbsCurve.getCV(kink_number, cvPoint, om.MSpace.kWorld)
                
                kink_number = kink * kinkSpacing
                    
                
                if kink == 0 or kink == kinks:
                    continue
                    #kink_offset = om.MVector(0,0,0)
                
                else:
                    kink_offset = om.MVector(random.uniform(randomMin, randomMax),
                                            random.uniform(randomMin, randomMax),
                                            random.uniform(randomMin, randomMax))
                
                newPoint = om.MPoint(om.MVector(cvPoint) + kink_offset)
                
                mFnNurbsCurve.setCV(kink_number, newPoint, om.MSpace.kWorld)
                
                
                
                print '#--------------------------#'
                print kink
                
                print 'Kinks: %s' %  kinks
                print 'Kink spacing: %s' % kinkSpacing
                print 'Kink number: %s' % kink_number
                print 'Offset: %s %s %s' % (kink_offset.x, kink_offset.y, kink_offset.z)
                
                for i in range(kinkSpacing):
                    
                    if i == 0:
                        continue
                    
                    if kink_number == 0:
                        continue
                    
                    # Get hi and lo cv
                    cv_lo = kink_number - i
                    cv_hi = kink_number + i
                    
                    
                    # get the MPoint data for our high and lo cvs
                    loPoint = om.MPoint()
                    hiPoint = om.MPoint()
                    mFnNurbsCurve.getCV(cv_lo, loPoint, om.MSpace.kWorld)
                    mFnNurbsCurve.getCV(cv_hi, hiPoint, om.MSpace.kWorld)
                    
                    
                    # get our spacing index number and find the weight of the hi and lo
                    kink_lo = kinkSpacing - i
                    kink_hi = kinkSpacing + i
                    
                    hi_weight = (1 - (((kink_hi*1.0) / kinkSpacing)-1))
                    lo_weight = ((kink_lo*1.0) / kinkSpacing)
                    
                    # Calcutlate our hi and lo offsets
                    lo_offset = om.MPoint(kink_offset) * lo_weight
                    hi_offset = om.MPoint(kink_offset) * hi_weight
                    
                    # get the new hi and lo points
                    newLoPoint = om.MPoint(om.MVector(loPoint) + om.MVector(lo_offset))
                    newHiPoint = om.MPoint(om.MVector(hiPoint) + om.MVector(hi_offset))
                    
                    mFnNurbsCurve.setCV(cv_lo, newLoPoint, om.MSpace.kWorld)
                    mFnNurbsCurve.setCV(cv_hi, newHiPoint, om.MSpace.kWorld)
        
        elif level == 'Lo':
            
            print 'Doing lo offest'
            print numCvs
            # now do our lo level noise
            for i in range(numCvs):
                print i
                # don't offset first cv
                if i == 0:
                    continue
                
                # get our hi and lo values for the offset
                hiRandomMin = abs(randomOffset) / 2 
                loRandomMin = hiRandomMin * -1 / 2
                
                # create an offset vector
                loRandomOffset = om.MVector(random.uniform(loRandomMin, hiRandomMin),
                                          random.uniform(loRandomMin, hiRandomMin),
                                          random.uniform(loRandomMin, hiRandomMin))
                
                # get the cv world space
                cvPoint = om.MPoint()
                mFnNurbsCurve.getCV(i, cvPoint, om.MSpace.kWorld)
                
                # add our offset vector to you point
                newPoint = om.MPoint(om.MVector(cvPoint) + loRandomOffset)
                
                try:
                    # set the newposition
                    mFnNurbsCurve.setCV(i, newPoint, om.MSpace.kWorld)
                except Exception:
                    pass
        
        else:
            print '###Error: Invalid level!'
    
    
        mFnNurbsCurve.updateCurve()
        iterSel.next()


def create_vine(self):


    mSelection = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(mSelection)

    selIter = om.MItSelectionList(mSelection)

    mFnNurbsCurve = om.MFnNurbsCurve()
    mFnDependNode = om.MFnDependencyNode()

    self.parent._setup_grps(root_grp, [ctrlCurves_grp])
    
    ctrlPoints = self.ui.numCtrls_spinBox.value()
    
    self.parent._setup_grps(root_grp, [outGeo_grp])
    
    item = 1
    
    while not selIter.isDone():

        mObj = om.MObject()
        mDagPath = om.MDagPath()

        selIter.getDagPath(mDagPath)
        selIter.getDependNode(mObj)



        if not mDagPath.hasFn(om.MFn.kNurbsCurve):
            print '### Error: Please select a nurbs curve and try again!'
            return

        mFnNurbsCurve.setObject(mDagPath)
        mFnDependNode.setObject(mObj)

        curveName = mFnDependNode.name()
        print curveName
        
        print 'Creating groups'
        
        curveGrp = '%s_ctrlGrp' % curveName
        
        self.parent._setup_grps(root_grp, additional={ctrlCurves_grp:[curveGrp]})
        
        
        curves = []
        
        length = mFnNurbsCurve.length(0.00001)
        print length
        
        spacing = length / (ctrlPoints-1)

        for i in range(ctrlPoints):
            print '#-------------------------------------#'
            position = (spacing * i)
            param = mFnNurbsCurve.findParamFromLength(position)
            
            mPoint = om.MPoint()
            
            mFnNurbsCurve.getPointAtParam(param, mPoint, om.MSpace.kWorld)
            #normal = mFnNurbsCurve.normal(param, om.MSpace.kWorld)
            tangent = mFnNurbsCurve.tangent(param, om.MSpace.kWorld)

            #normalVec = om.MVector(normal).normal()
            aimVec = om.MVector(tangent).normal()
            #tangentVec = (aimVec ^ normalVec).normal()
            
            print 'Getting rotation'
            rotation = self._get_rotation(aimVec)
            
            curve = cmds.circle(nr=[1, 0, 0])
            print curve
            
            
            ctrlCurveName = '%s_ctrlCrv%03d' % (curveName, i+1)
            print ctrlCurveName
            
            ctrlCurveName = cmds.rename(curve[0], ctrlCurveName) 
            
            curveDagpath = om.MDagPath()
            mSel = om.MSelectionList()
            mSel.add(ctrlCurveName)
            mSel.getDagPath(0, curveDagpath)

            mFnTransform = om.MFnTransform(curveDagpath)
            mFnTransform.setTranslation(om.MVector(mPoint), om.MSpace.kWorld)
            mFnTransform.setRotation(rotation)
            
            cmds.parent(ctrlCurveName, '%s|%s' % (ctrlCurves_grp, curveGrp))
            
            curves.append(cmds.ls(ctrlCurveName, l=True)[0])
            
        print curves
        extrudedVine = cmds.loft(curves,
                                 ch = 1,
                                 u = 1,
                                 c = 0,
                                 ar = 1,
                                 d = 3,
                                 ss = 1,
                                 rn = 0,
                                 po = 1,
                                 rsn = True)
        print extrudedVine
        
        #extrudeShape = cmds.listRelatives(extrudeVine[0])
        
        tessalate = cmds.listConnections(extrudedVine[1], d=True, s=False)[0]
        cmds.setAttr('%s.polygonType'  % tessalate, 1)
        cmds.setAttr('%s.format'  % tessalate, 2)
        cmds.setAttr('%s.uNumber'  % tessalate, 12)
        cmds.setAttr('%s.vNumber'  % tessalate, 64)
        
        geoName = '%s_vineGeo_%03d' % (mFnDependNode.name().split('_')[0], item)
        
        geoName = cmds.rename(extrudedVine[0], geoName)
        
        cmds.parent(geoName, outGeo_grp)
        
        
        item += 1
        selIter.next()


#######################################################################
### Helper Functions
#######################################################################

def _get_goal(self, npNode=None, dg=None):
    """
    Gets the mObjects that are attached to the goalGeometry of an 
    nParticleSystem
    :param npNode: dependency node of object we are look for goals
                    if nothing passed in we will try and get it from the selection
    
    :return: returns the first goal that we find or none if we can't find one
    """    
    
    if not npNode:
        if not dg:
            print '###Error: Either a dependency node or dagPath needs to be passed in to get goal!'
            return
        
        dg.extendToShape()
        mObj = dg.node()
        
        npNode = om.MFnDependencyNode(mObj)
        
        
        
    
    print npNode.name()
    
    # get the goalGeometry plug. this can tell us what our
    # particle is goaled to
    goalGeo_plug = npNode.findPlug('goalGeometry')
    
    # if we don't find the plug return empty
    if not goalGeo_plug:
        print 'Could not find goalGeometry attribute!'
        return
    
    # check the number of connections we have
    connections = goalGeo_plug.numConnectedElements()
    
    # if not connections return empty
    if connections == 0:
        print 'No goals are attached to this node!'
        return
    
    # if we have more than one connection tell user that we are 
    # going to return first goal
    elif connections > 1:
        print 'Found more than one goal. Looking for first goal!'
    
    
    # get the element plug that is connected to something
    goal_plug = goalGeo_plug.elementByPhysicalIndex(0)
    
    # find all plugs that are comming into this plug
    mPlugArray = om.MPlugArray()
    goal_plug.connectedTo(mPlugArray, True, False)
    
    # if we have more than one plug connected through weird error!
    if mPlugArray.length() > 1:
        print '###Error :More than one object is connected to this goal plug. Weird!'
        return
    
    goal_obj = mPlugArray[0].node()
    
    return goal_obj
    
    
    

'''
def _create_part(mFnDepend):
    
    npPart = omfx.MFnParticleSystem()
    npNode = om.MFnDependencyNode()
    
    # create a particle system
    part = cmds.nParticle()
    pList = om.MSelectionList()
    pList.add(part[0])
    pList.add(part[1])
    
    cmds.parent(part[0], particle_grp)
    
    # get the mObject and dagPath
    npObj = om.MObject()
    npDagPath = om.MDagPath()
    
    pList.getDependNode(1, npObj)
    pList.getDagPath(1, npDagPath)
    
    # setup our particle system and depency node function sets
    npPart.setObject(npDagPath)
    npNode.setObject(npObj)
    
    # set a number of attributes we find work well for vines
    isg = npNode.findPlug('ignoreSolverGravity')
    isg.setInt(1)
    
    drag = npNode.findPlug('drag')
    drag.setFloat(0.1)
    
    damp = npNode.findPlug('damp')
    damp.setFloat(0.01)
    
    conserve = npNode.findPlug('conserve')
    conserve.setFloat(0.975)
    
    radius = npNode.findPlug('radius')
    radius.setFloat(1.0)
    
    renderType = npNode.findPlug('particleRenderType')
    renderType.setInt(4)
    
    lifespan = npNode.findPlug('lifespanMode')
    lifespan.setInt(3)
    
    
    # create a msg attribute on our object so we can link the
    # particle system to it
    msgAttr = om.MFnMessageAttribute()
    
    if not mFnDepend.hasAttribute('particles'):
        particleAttr = msgAttr.create('particles', 'part')
        msgAttr.setArray(True)
        mFnDepend.addAttribute(particleAttr)
    
    
    particlePlug = mFnDepend.findPlug('particles')
    intArray = om.MIntArray()
    
    particlePlug.getExistingArrayAttributeIndices(intArray)

    if not intArray:
        index = 0
    else:
        index = max(intArray) + 1

    cmds.connectAttr('%s.message' % npNode.name(), '%s.particles[%s]' % (mFnDepend.name(), index))
    
    
    # set the particle name so we can find it later
    partName = '%s_part' % mFnDepend.name().replace('_', '')
    transformDepend = om.MFnDependencyNode(npDagPath.transform())
    transformDepend.setName(partName, False)
    
    # find our nucleus solver and set some attributes on it
    nucleii = cmds.ls(type='nucleus', l=True )
    
    if len(nucleii) == 0:
        print 'Can not find nucleus solver!'
        return
    elif len(nucleii) > 1:
        print 'We have more than one nucleus solver. Oh noes!'
        return
    else:
        nucleus = nucleii[0]
    

    # if the nucleus is already parented under our dynamics grp
    # then assume that it has already been setup        
    parent = cmds.listRelatives(nucleus, parent=True, f=True)
    if not parent or not parent[0] == dynamics_grp:
        
        #spaceScale = self.ui.spaceScale_spinBox.value()
        
        #attr = '%s.spaceScale' % nucleus
        #cmds.setAttr(attr, spaceScale)
        cmds.parent(nucleus, dynamics_grp)
    
    
    
    return npObj


def _get_rand_point(dagPath):
    """
    Creates a random point on the given surface
    
    :param dagPath: MDagpath object of surace that we want the point to be created on
    :return: point in world space randomly placed on surface of dagpath object
    """
    
    # create the mesh fucntion set
    mFnMesh = om.MFnMesh(dagPath)
    
    # find out how many polygons we have
    numPolygons = mFnMesh.numPolygons()
    
    # get a random face and put the vertices of that polygon
    # into an array
    randomFace = random.randint(0, numPolygons-1)
    vertexArray = om.MIntArray()
    
    
    # get polygon vertex ids
    mFnMesh.getPolygonVertices(randomFace, vertexArray)
    
    random_point = om.MVector()
    
    weights = []
    
    for i in range(vertexArray.length()):
        # get the point of the vertex
        vertexPoint = om.MPoint()
        mFnMesh.getPoint(vertexArray[i], vertexPoint, om.MSpace.kWorld)
        
        # append a rendom weight
        weight = random.uniform(0, 1)
        weights.append(weight)
        
        # convert point to vector and then mutliply by weight
        # add this to our random point vector
        random_point += om.MVector(vertexPoint)*weight 
        
    # calculate total weight to help get average
    total_weight = sum(weights)    
    
    random_point = om.MPoint(random_point / total_weight)
    
    return random_point
    
'''
def _create_attributes(self, npNode, attrs):
    """
    Given a dependency node will create a number of different attributes
    required
    :param npNode: dependency node that we want to add attributes to
    :param attrs: dictionary containing data needed to add attr
                        -longName
                        -shortName
                        -type
                        -initialState
    """
    
    
    ### NB: Currently only create typed attributes!
    print 'creating new attributes!'
    mFnAttr = om.MFnTypedAttribute()
    
    for attr in attrs:
        # make sure that the attribute doesn't already exist
        if not npNode.hasAttribute(attrs[attr]['longName']):
            # create the attribute and then add it
            customAttr = mFnAttr.create(attrs[attr]['longName'],
                                        attrs[attr]['shortName'],
                                        attrs[attr]['type'])
            npNode.addAttribute(customAttr)
            
            # if the attribute requires an intial state then add that one to
            if attrs[attr]['initialState']:
                custom0Attr = mFnAttr.create('%s0' % attrs[attr]['longName'],
                                              '%s0' % attrs[attr]['shortName'],
                                              attrs[attr]['type'])
                npNode.addAttribute(custom0Attr)



def _get_rotation(self, aimVector, normalVector=None, tangentVector=None, returnType = 'euler'):
    """
    Get the rotation as a vector from the three axis vectors that make up a rotation axis
    
    :param aimVector: forward axis vector
    :param normalVector: up axis vector
    :return: euler rotation vector in degress from the 3 axis passed in
    """
    
    ### Get rotation values
    # defines the axis of the model we want to point where
    eyeAim = om.MVector().xAxis
    eyeUp = om.MVector().yAxis
    
    
    if not aimVector:
        print 'Need at least aim vector to get rotation!'
        return 
    
    aimVector.normal()
    
    if not normalVector:
        if tangentVector:
            tangentVector.normal()
        
        else:
            normalVector = om.MGlobal.upAxis()
            tangentVector = (aimVector ^ normalVector).normal()
        
        normalVector = (tangentVector ^ aimVector).normal()
    
    
    # get rotation from x axis where we want to aim it
    quaternionU = om.MQuaternion(eyeAim, aimVector)
    quaternion = quaternionU
    
    upRotated = eyeUp.rotateBy(quaternion)
    
    # get angle between out up vector and our rotated vector
    angle = math.acos(upRotated*normalVector)
    
    
    # angle = upRotated.angle(normalVector)
    # angle = (2*math.pi) - angle
    
    quaternionV = om.MQuaternion(angle, aimVector)
    
    # make sure it's orientated correctly
    if not normalVector.isEquivalent(upRotated.rotateBy(quaternionV), 1.0e-5):
        angle = (2*math.pi) - angle
        quaternionV = om.MQuaternion(angle, aimVector)
    
    
    
    quaternion *= quaternionV
    
    
    
    # convert to euler angle and break out and convert to degrees
    eulerAngle = quaternion.asEulerRotation()
    
    if returnType == 'euler':
        return eulerAngle
    #global_rotate = om.MEulerRotation(math.radians(-90), 0, 0)
    
    final_rot = eulerAngle
    #particle_rot = om.MEulerRotation()
    x = math.degrees(final_rot.x)
    y = math.degrees(final_rot.y)
    z = math.degrees(final_rot.z)
    
    rotVector = om.MVector(x, y, z)
    
    if returnType == 'rotation':
        return rotVector
    
    
    print 'Not sure how you want this value returned!'
    print '%s not an acceptable type' % returnType

'''  
    
    

