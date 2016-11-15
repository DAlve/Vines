'''
Created on 7/04/2016

@author: dalve
'''
import maya.cmds as cmds
import maya.mel as mel
from tank.platform.qt import QtCore, QtGui
import time
import re


root_grp = '|vines_grp'
ctrls_grp = '%s|ctrls_grp' % root_grp
dynamics_grp = '%s|dynamics_grp' % root_grp
dynCurves_grp = '%s|dynCurves_grp' % root_grp
outCurve_grp = '%s|outCurves_grp' % root_grp


class vines(object):
    
    def __init__(self, parent):
        print 'Initializing hanging vines!'
        self.parent = parent
        self.ui = self.parent.ui
        
        
    def create_controls(self):
        """
        Used to create the controls that we want to use for the curve creation
        """
        
        # first setup our groups
        self.parent._setup_grps(root_grp, [ctrls_grp])
        
        # look for any ctrls that may already exists so we can get a version number
        grp_contents = cmds.listRelatives(ctrls_grp, children=True)
        
        versions = []
        # go through the group contents and try and find any items
        # that have a version number
        if grp_contents:
            for i in grp_contents:
                digits = re.findall(r'\d+', i)
                
                # only if we find one set of digits do we add it
                if len(digits) == 1:
                    versions.append(int(digits[0]))
        
        if not versions:
            version = 1
        
        else:
            version = max(versions) + 1
                
        # create a start and end locator
        startLocator = cmds.spaceLocator(name='startLoc')
        endLocator = cmds.spaceLocator(name='endLoc')
        
        # get their long path name to stop any confussion 
        startLocator = cmds.ls(startLocator[0], l=True)[0]
        
        
        endLocator = cmds.ls(endLocator[0], l=True)[0]
        
        for loc in [startLocator, endLocator]:
            cmds.setAttr('%s.sx' % loc, lock=True)
            cmds.setAttr('%s.sy' % loc, lock=True)
            cmds.setAttr('%s.sz' % loc, lock=True)
            
            cmds.setAttr('%s.localScaleX' % loc, 5)
            cmds.setAttr('%s.localScaleY' % loc, 5)
            cmds.setAttr('%s.localScaleZ' % loc, 5)
        
        cmds.select(cl=True)
        
        # create our joints that we will use later
        startJnt = cmds.joint()
        endJnt = cmds.joint()
        
        # parent our joints to the locators
        cmds.parent(startJnt, startLocator)
        cmds.parent(endJnt, endLocator)
        
        # put everything under a curve group that we can name with our version
        # and then put all of that under our ctrls grp
        curve_grp = cmds.group([startLocator, endLocator], name='hangingVine%03d_grp' % version)
        
        cmds.parent(curve_grp, ctrls_grp)
    
    
    
    def create_vine(self):
        """
        Creates a dynamic curve between the start and end locator in the
        curves grp provided
        
        :param curve_grp: group that contains our start and end locator
        :param lockEnds: if true will lock dynamic curve so both ends stay put. if false will only lock start
        """
        
        start_time = time.time()
        
        print 'Creating base vine'
        
        ###################################################################
        ### Get details on the group passed in.
        
        # get values from the ui
        lockEnds = self.ui.lockEnds_cbox.isChecked()
        
        # get our selection list
        sel = cmds.ls(sl=True, l=True)
        
        self.parent._setup_grps(root_grp, [dynamics_grp, dynCurves_grp])
        
        
        # go through our selection list
        for grp in sel:
            
            # look for any shapes under our item. if there are any we assume
            # this isn't a group and bail
            shapes = cmds.listRelatives(grp, children=True, shapes=True)
            
            if shapes:
                print '%s is not a group!' % grp 
                continue
            
            # get the short name for the group
            grpName = cmds.ls(grp)[0]
            
            print grp
            print grpName
            
            # create the curve name
            curve_name = '%s_masterCrv' % grpName.split('_')[0]
            
            # get the contents of the group in two ways. everything below it
            # and just the direct children
            all_grpContents = cmds.listRelatives(grp, ad=True)
            grpContents = cmds.listRelatives(grp, children=True, f=True)
            
            if curve_name in all_grpContents:
                print 'We already have a master curve for %s' % grpName
                continue
            
            
            locators = {'startLoc':None, 'endLoc': None}
        
            # search the curves children for the locators defined in the locators
            # dictionary
            for i in grpContents:
                for loc in locators:
                    if loc in i:
                        
                        if locators[loc]:
                            print 'We have found more than one %s!' % loc
                            return
                        else:
                            if not cmds.objectType(i) == 'transform':
                                print '%s is not a transform!!' % loc 
                                return
                            locators[loc] = i
            
            print locators
            
            # get handles on our found locators and make sure that something
            # was returned
            startLoc = locators['startLoc']
            endLoc = locators['endLoc']
            
            if not startLoc:
                print 'Could not find start locator in grp %s' % grpName
                return
            
            if not endLoc:
                print 'Could no find end locator in grp %s' % grpName
                return
            
            
            # get start and end point (note this will get their local 
            # transform and maybe not their actual world transform        
            startPoint = (cmds.getAttr('%s.translateX' % startLoc),
                          cmds.getAttr('%s.translateY' % startLoc),
                          cmds.getAttr('%s.translateZ' % startLoc))
            
            
            endPoint = (cmds.getAttr('%s.translateX' % endLoc),
                          cmds.getAttr('%s.translateY' % endLoc),
                          cmds.getAttr('%s.translateZ' % endLoc))
            
            
            
            ###################################################################
            ### Create the curve
            
            # create the curve between our start and end points
            curve = cmds.curve(d=True, p=[startPoint, endPoint])
        
        
            # rename our curve based on the group name
            cmds.rename(curve, curve_name)
            curve = curve_name
            
            # rebuild the curve to have 8 spans to work with our dynamics
            cmds.rebuildCurve(curve,
                              ch=False,
                              rpo=True,
                              rt=0,
                              end=1,
                              kr=1,
                              kcp=0,
                              kep=1,
                              kt=0,
                              s=8,
                              tol=0.01)
            
            # parent our curve to the curve grp
            cmds.parent(curve, grp)
            
            
            ###################################################################
            ### Make curve dynamic
            
            # check our scene for any hair systems that already exist
            hairSystem = self._get_hair_system()
            
            # make the curve dynamic
            cmds.select(curve)
            
            if hairSystem:
                # if we aleady have a hair system attach our curve to that 
                # system
                hairSystemTransform = cmds.listRelatives(hairSystem, parent=True, f=True)[0]
                
                cmd = 'assignHairSystem %s' % hairSystem
                mel.eval(cmd)
                
                # this will create a follicle grp (hopefully empty)
                # delete it! (if it's empty)
                follicleGrp = '%sFollicles' % hairSystemTransform.split('|')[-1]
                
                if cmds.objExists(follicleGrp):
                    if not cmds.listRelatives(follicleGrp, children=True):
                        cmds.delete(follicleGrp)
            
            else:
                # check to see if there is a nucleus solver before we create the
                # dynamics
                nucleus = self._get_nucleus()
                
                # if we don't have a hair system call makeCurvesDynamic
                cmd = 'makeCurvesDynamic 2 { "1", "0", "1", "1", "0"}'
                mel.eval(cmd)
                
                # since we didn't have a hari system to start with we want
                # to set up a few basic features
                hairSystem = self._get_hair_system()
                
                if not hairSystem:
                    print 'Weird we could not find the new hairsystem!'
                    return
                
                hairSystemTransform = cmds.listRelatives(hairSystem, parent=True, f=True)[0]
                
                
                
                # setup attrs on the hair system
                attr = '%s.stretchResistance' % hairSystem
                cmds.setAttr(attr, 5)
                
                attr = '%s.drag' % hairSystem
                cmds.setAttr(attr, 1)
                
                attr = '%s.damp' % hairSystem
                cmds.setAttr(attr, 1)
                
                # if we didn't have a solver before we created dynamics
                # we want to create one, set some attributes and then 
                # parent it
                if not nucleus:
                    
                    nucleus = self._get_nucleus()
                    
                    if not nucleus:
                        print '###ERROR: Still cannot find nucleus? Not good....'
                        return
                    
                    spaceScale = self.ui.spaceScale_spinBox.value()
                    
                    attr = '%s.spaceScale' % nucleus
                    print '\n### Attr: %s' % attr 
                    cmds.setAttr(attr, spaceScale)
                    
                    cmds.parent(nucleus, dynamics_grp)
                
                print hairSystemTransform
                print nucleus
                print dynamics_grp
                
                # now clean up the dynamic nodes that we created into grps
                cmds.parent(hairSystemTransform, dynamics_grp)
                
            
            
            # get the follicle from the curve and then set the lock point
            # lock attribute based on variables passed to function (or lack of)
            follicle = cmds.listRelatives(curve, parent=True, f=True)[0]
            follicleShape = cmds.listRelatives(follicle, shapes=True, f=True)[0]
            
            if not cmds.objectType(follicleShape) == 'follicle':
                print 'For some reason we have not got a follicle but a %s instead!' % cmds.objectType(follicleShape) 
                return
            
            attr = '%s.pointLock' % follicleShape
            
            if lockEnds:
                cmds.setAttr(attr, 3)
            else:
                cmds.setAttr(attr, 1)
            
            ###################################################################
            ### Clean up scene from dynamics creation
            
            # look in the new grp created for our output curve
            # if we've cleanup up properly along the way it should be the only
            # item in the grp
            outputCurvesGrp = '%sOutputCurves' % hairSystemTransform.split('|')[-1]
            
            if not cmds.objExists(outputCurvesGrp):
                print "Can't find output curves group!"
                return
            
            outputCurves = cmds.listRelatives(outputCurvesGrp, children=True)
            
            if len(outputCurves) == 0:
                # if we don't find anything delete the grp
                print "Can't find the output curve!"
                cmds.delete(outputCurvesGrp)
            elif len(outputCurves) > 1:
                # if we find more than one item don't do anything as we don't know
                # what we want to take
                print "More than one output curve found don't know what to take!"
            else:
                # if only one item we want to rename this and move it 
                # under our curve grp
                outputCurve = outputCurves[0]
                outputCurve_name = '%s_dynCrv' % grpName.split('_')[0]
                
                if cmds.objExists(outputCurve_name):
                    print "Curve with the name %s alreaady exists!"
                else:
                    # rename our curve and move it before deleting the grp
                    outputCurve = cmds.rename(outputCurve, outputCurve_name)
                    
                    cmds.parent(outputCurve, dynCurves_grp)
                    
                    cmds.delete(outputCurvesGrp)
            
            ###################################################################
            ### Find our joints in the group and bind them to our curve
            bindItems = []
            
            bindItems.append(self._get_joint(startLoc))
            bindItems.append(self._get_joint(endLoc))
            
            # only if we find joints do we want to create a bind
            if bindItems:
                bindItems.append(curve)
                
                cmds.skinCluster(bindItems)
                
            
        stop_time = time.time()
        
        total_time = stop_time - start_time
        print 'Total time: %s' % total_time
    
    
    
    def bake_vine(self):
        
        print 'Baking vine!!!'
        
        sel = cmds.ls(sl=True, l=True)
        
        self.parent._setup_grps(root_grp, [outCurve_grp])
        
        for curve in sel:
            
            curveName = cmds.ls(curve)[0]
            
            if not curveName.split('_')[-1] == 'dynCrv':
                print '###Error: Cannot determin if %s is a dynCrv or not!' % curve
                continue
            
            
            digits = re.findall(r'\d+', curveName)
                
            # only if we find one set of digits do we add it
            if len(digits) == 1:
                version = int(digits[0])
            
            else:
                print 'Could not find version number...'
                print 'Please check name!'
                continue
            
            dupCurve_name = 'hangingVine_outCrv_%03d' % version
            
            # look through our outCurve group for any objects that already named that same as 
            # waht we are going to call this duplicate
            children = cmds.listRelatives(outCurve_grp, children=True)
            if not children == None:
                if dupCurve_name in children:
                
                    # if we find something then ask the user if they want to delete
                    # the old output curve create the new one
                    msg = ('Curve %s already has an output curve.\n'
                            'Would you like to delete it and create a new one?' % curveName)
                    
                    reply = QtGui.QMessageBox.question(self.parent,
                                                       'Delete Output?',
                                                       msg,
                                                       QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                                       QtGui.QMessageBox.No)
                    
    
                    # if they reply yes then delete old curve and continue on
                    # with duplicating our curve                
                    if reply == QtGui.QMessageBox.Yes:
                        print 'Deleting output curve to make new one!'
                        oldOutput_curve = '%s|%s' % (outCurve_grp, dupCurve_name)
                        cmds.delete(oldOutput_curve)
                    
                    # if not then we want to skip and continue onto next selection
                    else:
                        continue
            
            dupCurve = cmds.duplicate(curve, name=dupCurve_name)[0]
            
            cmds.parent(dupCurve, outCurve_grp)
            
        
    
    
    
    #######################################################################
    ### Helper Functions
    
    def _get_hair_system(self):
        
        hairSystems = cmds.ls(type='hairSystem')
            
        if len(hairSystems) == 0:
            hairSystem = None
        elif len(hairSystems) == 1:
            hairSystem = hairSystems[0]
        else:
            hairSystem = None
            
            for i in hairSystems:
                parent = cmds.listRelatives(i, parent=True, l=True)[0]
                if parent == dynamics_grp:
                    if not hairSystem:
                        hairSystem = i
                    
                    else:
                        raise Exception('Found more than one hair system bailing!')
            
            if not hairSystem:
                raise Exception('Found more than one hair system but none are valid, bailing!')
            
            
            
        
        return  hairSystem
    
    def _get_nucleus(self):
        
        print 'Getting nucleus'
        # find our nucleus solver and set some attributes on it
        nucleii = cmds.ls(type='nucleus')
        
        if len(nucleii) == 0:
            print 'Can not find nucleus solver!'
            return
        elif len(nucleii) > 1:
            print 'We have more than one nucleus solver. Oh noes!'
            return
        else:
            nucleus = nucleii[0]
            return nucleus
        
        
    
    
    def _get_joint(self, item):
    
        item_children = cmds.listRelatives(item, children=True, typ='transform', f=True)
        
        jnt = None
        
        if len(item_children) == 0:
            print '%s has no joint!' % item
        elif len(item_children) > 1:
            print '%s has more than one child that is a transform!' % item
        else:
            jnt = item_children[0]
        
        
        return jnt
