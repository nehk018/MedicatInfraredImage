import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import sitkUtils
import SimpleITK as sitk
from qt import QWidget, QLabel, QPushButton, QCheckBox, QRadioButton, QSpinBox, QTimer, QButtonGroup, QGroupBox
from qt import QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QSizePolicy, QDialog, QSize, QPoint

#
# IrBaseUlcerDetection
#

class IrBaseUlcerDetection(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "IR-Base Ulcer Detection" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["Jorge Quintero (IAC-IACTEC)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# IrBaseUlcerDetectionWidget
#

class IrBaseUlcerDetectionWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  crosshairNode = 0
  global seedRightFiducialsNodeSelector

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Instantiate and connect widgets ...

    #clear scene
    # slicer.mrmlScene.Clear(0) 

    #Define Widgets layout
    lm = slicer.app.layoutManager()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutThreeOverThreeView)
    lm.sliceWidget('Red').setSliceOrientation('Axial')
    lm.sliceWidget('Red+').setSliceOrientation('Axial')
    lm.sliceWidget('Yellow').setSliceOrientation('Axial')
    lm.sliceWidget('Yellow+').setSliceOrientation('Axial')
    lm.sliceWidget('Green').setSliceOrientation('Axial')
    lm.sliceWidget('Green+').setSliceOrientation('Axial')

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # input volume selector
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene( slicer.mrmlScene )
    self.inputSelector.setToolTip( "Pick the input to the algorithm." )
    #parametersFormLayout.addRow("Input Volume: ", self.inputSelector)  Por ahora no lo mostramos.


    #
    # output volume selector
    #
    self.outputSelector = slicer.qMRMLNodeComboBox()
    self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSelector.selectNodeUponCreation = True
    self.outputSelector.addEnabled = True
    self.outputSelector.removeEnabled = True
    self.outputSelector.noneEnabled = True
    self.outputSelector.showHidden = False
    self.outputSelector.showChildNodeTypes = False
    self.outputSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSelector.setToolTip( "Pick the output to the algorithm." )
    parametersFormLayout.addRow("Volume: ", self.outputSelector)

    #
    # Take Working Image Button
    #
    self.takeImageButton = qt.QPushButton("Take working image")
    self.takeImageButton.toolTip = "Take working image"
    self.takeImageButton.enabled = True
    parametersFormLayout.addRow(self.takeImageButton)

    #
    # Processing selector
    #
    self.processingSelector = qt.QComboBox()
    self.processingSelector.addItem("original")
    self.processingSelector.addItem("image smoothing")
    self.processingSelector.addItem("image segmentation")
    self.processingSelector.addItem("image segmentation + no holes")
    self.processingSelector.addItem("contouring")
    parametersFormLayout.addRow("Processing: ", self.processingSelector)

    #
    #  SpinBoxes : numerical inputs
    #
    self.segmentationGroupBox=qt.QGroupBox("Segmentation Data")
    self.segmentationVBoxLayout = qt.QVBoxLayout()
    
    self.tempGroupBox=qt.QGroupBox("Temperature")
    self.tempHBoxLayout = qt.QHBoxLayout()
    
    self.qlabelMin = QLabel('Min:')
    self.doubleMinTemp = ctk.ctkSliderWidget()
    self.doubleMinTemp.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    self.doubleMinTemp.setDecimals(2)
    self.doubleMinTemp.setValue(27.0)
    self.tempHBoxLayout.addWidget(self.qlabelMin)
    self.tempHBoxLayout.addWidget(self.doubleMinTemp)

    self.labelMax = qt.QLabel("Max:  ")
    self.doubleMaxTemp = ctk.ctkSliderWidget()
    self.doubleMaxTemp.setValue(35.0)
    self.tempHBoxLayout.addWidget(self.labelMax)
    self.tempHBoxLayout.addWidget(self.doubleMaxTemp)

    self.tempGroupBox.setLayout(self.tempHBoxLayout)
    self.segmentationVBoxLayout.addWidget(self.tempGroupBox)

     #
    # Button to get foot seed
    #
    self.seedBoxesGroup=qt.QGroupBox("Seed")

    frameControlHBox = qt.QVBoxLayout()   

    self.seedCoords = {}

    # Seed Left selector
    self.seedLeftFiducialsNodeSelector = slicer.qSlicerSimpleMarkupsWidget()
    self.seedLeftFiducialsNodeSelector.objectName = 'seedLeftFiducialsNodeSelector'
    self.seedLeftFiducialsNodeSelector.toolTip = "Select a fiducial to use as the origin of the left segments."
    self.seedLeftFiducialsNodeSelector.setNodeBaseName("Left")
    self.seedLeftFiducialsNodeSelector.defaultNodeColor = qt.QColor(0,255,0)
    self.seedLeftFiducialsNodeSelector.tableWidget().hide()
    self.seedLeftFiducialsNodeSelector.markupsSelectorComboBox().noneEnabled = False
    self.seedLeftFiducialsNodeSelector.markupsPlaceWidget().placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup    
    self.seedLeftFiducialsNodeSelector.markupsPlaceWidget().buttonsVisible = False
    self.seedLeftFiducialsNodeSelector.markupsPlaceWidget().placeButton().show()
    self.seedLeftFiducialsNodeSelector.setMRMLScene(slicer.mrmlScene)

    self.seedFiducialsBox = qt.QHBoxLayout()
    self.seedLabelWidget = qt.QLabel("Choose left seed node:")
    self.seedFiducialsBox.addWidget(self.seedLabelWidget)
    self.seedFiducialsBox.addWidget(self.seedLeftFiducialsNodeSelector)
    self.leftFiducial=qt.QGroupBox("Left: ")
    self.leftFiducial.setLayout(self.seedFiducialsBox)

    # Seed Right selector
    self.seedRightFiducialsNodeSelector = slicer.qSlicerSimpleMarkupsWidget()
    self.seedRightFiducialsNodeSelector.objectName = 'seedRightFiducialsNodeSelector'
    self.seedRightFiducialsNodeSelector.toolTip = "Select a fiducial to use as the origin of the left segments."
    self.seedRightFiducialsNodeSelector.setNodeBaseName("Right")
    self.seedRightFiducialsNodeSelector.defaultNodeColor = qt.QColor(0,255,0)
    self.seedRightFiducialsNodeSelector.tableWidget().hide()
    self.seedRightFiducialsNodeSelector.markupsSelectorComboBox().noneEnabled = False
    self.seedRightFiducialsNodeSelector.markupsPlaceWidget().placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup    
    self.seedRightFiducialsNodeSelector.markupsPlaceWidget().buttonsVisible = False
    self.seedRightFiducialsNodeSelector.markupsPlaceWidget().placeButton().show()
    self.seedRightFiducialsNodeSelector.setMRMLScene(slicer.mrmlScene)
    seedRightFiducialsNodeSelector = self.seedRightFiducialsNodeSelector
    
    self.seedRightFiducialsBox = qt.QHBoxLayout()
    self.seedRightLabelWidget = qt.QLabel("Choose right seed node:")
    self.seedRightFiducialsBox.addWidget(self.seedRightLabelWidget)
    self.seedRightFiducialsBox.addWidget(self.seedRightFiducialsNodeSelector)
    self.rightFiducial=qt.QGroupBox("Right: ")
    self.rightFiducial.setLayout(self.seedRightFiducialsBox)
 
    frameControlHBox.addWidget(self.leftFiducial)
    frameControlHBox.addWidget(self.rightFiducial)

    self.seedBoxesGroup.setLayout(frameControlHBox)
    self.segmentationVBoxLayout.addWidget(self.seedBoxesGroup)

    # #Set Group
    self.segmentationGroupBox.setLayout(self.segmentationVBoxLayout)
    
    parametersFormLayout.addRow(self.segmentationGroupBox)

    #
    # Processing Button
    #
    self.extractButton = qt.QPushButton("Apply Segmentation")
    self.extractButton.toolTip = "Run the algorithm."
    # self.extractButton.enabled = False
    parametersFormLayout.addRow(self.extractButton)

    # connections
    self.extractButton.connect('clicked(bool)', self.onExtractButton)
    self.takeImageButton.connect('clicked(bool)', self.onTakeImageButton)
    self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectWorkingImage)
    self.processingSelector.connect('currentIndexChanged(QString)', self.onProcessing)
    
    # self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', self.seedFiducialsNodeSelector, 'setMRMLScene(vtkMRMLScene*)')

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def onExtractButton(self):
    logic = IrBaseUlcerDetectionLogic()
    # Other access method
    # arr = [0,0,0]
    # self.seedRightFiducialsNodeSelector.currentNode().GetMarkupPoint(self.seedRightFiducialsNodeSelector.currentNode().GetNumberOfMarkups()-1,0,arr)

    leftCoordinatesRAS = [0, 0, 0]
    leftPoint = self.seedLeftFiducialsNodeSelector.currentNode()
    leftPoint.GetNthFiducialPosition(0,leftCoordinatesRAS)

    rightCoordinatesRAS = [0, 0, 0]
    rightPoint = self.seedRightFiducialsNodeSelector.currentNode()
    rightPoint.GetNthFiducialPosition(0,rightCoordinatesRAS)


    # rightImage = logic.processVolume(self.outputSelector,self.processingSelector, self.doubleMinTemp.value, self.doubleMaxTemp.value, rightCoordinatesRAS)
    logic.runSegmentation(self.outputSelector, self.processingSelector, self.doubleMinTemp.value, self.doubleMaxTemp.value, rightCoordinatesRAS, leftCoordinatesRAS)
 
  def onTakeImageButton(self):
    logic = IrBaseUlcerDetectionLogic()
    self.outputSelector.setCurrentNode(logic.runTakeImage(self.inputSelector.currentNode()))

  def onSelectWorkingImage(self):
    self.extractButton.enabled = self.outputSelector.currentNode()
    
    # display image in Yellow Slice viwer
    lm = slicer.app.layoutManager()
    yellow = lm.sliceWidget('Yellow')
    yellow.setSliceOrientation('Axial')
    yellow.fitSliceToBackground()
    yellowLogic = yellow.sliceLogic()
    yellowLogic.GetSliceCompositeNode().SetBackgroundVolumeID(self.outputSelector.currentNode().GetID())

  def onProcessing(self):
    logic = IrBaseUlcerDetectionLogic()
    logic.runProcessing(self.outputSelector, self.processingSelector, self.doubleMinTemp.value, self.doubleMaxTemp.value)


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# IrBaseUlcerDetectionLogic
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class IrBaseUlcerDetectionLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def runTakeImage(self, inputVolume):
    #clone volume
    volumesLogic = slicer.modules.volumes.logic()
    workingVolume = volumesLogic.CloneVolume(slicer.mrmlScene, inputVolume, 'workingVolume')
    return workingVolume
  
  def rasToXYZ(self,rasPoint):
    """return x y for a give r a s"""
    sliceNode = self.sliceLogic.GetSliceNode()
    rasToXY = vtk.vtkMatrix4x4()
    rasToXY.DeepCopy(sliceNode.GetXYToRAS())
    rasToXY.Invert()
    xyzw = rasToXY.MultiplyPoint(rasPoint+(1,))
    return xyzw[:3]

  def processVolume(self, workingSelector, processingSelector,tempMin,tempMax, coordinates, name):
    print("processing")
    
    inputImage = sitkUtils.PullVolumeFromSlicer(workingSelector.currentNode())
    volumesLogic = slicer.modules.volumes.logic()
    processedVolume = volumesLogic.CloneVolume(slicer.mrmlScene, workingSelector.currentNode(), name)

    #extract image from volume
    zslice = 0
    size = list(inputImage.GetSize())
    size[2] = 0
    index = [0, 0, zslice]
    Extractor = sitk.ExtractImageFilter()
    Extractor.SetSize(size)
    Extractor.SetIndex(index)

    outputImage=Extractor.Execute(inputImage)

    # step 1)filtering: noise reduction
    imgSmooth =  sitk.CurvatureFlow(image1=outputImage, timeStep=0.125, numberOfIterations=5)

    # step 2) filtering: segmentation
    # aux = self.rasToXYZ(coordinates)
    # coordinates=[197, 140, 190,2]
    lstSeeds = [()]
    lstSeeds[0] = tuple(coordinates[0:2])
    print(lstSeeds)
    print(coordinates)
    labelLeftHand=1
    imgLeftHand = sitk.ConnectedThreshold(image1=imgSmooth, seedList=lstSeeds, lower=tempMin, upper=tempMax, replaceValue=labelLeftHand)

    #step 3) create image to display
    imgSmoothInt = sitk.Cast(sitk.RescaleIntensity(imgSmooth), imgLeftHand.GetPixelID())
    # Use 'LabelOverlay' to overlay 'imgSmooth' and 'imgWhiteMatter'
    outI=sitk.LabelOverlay(imgSmoothInt, imgLeftHand)
    outI2 = sitk.Multiply(imgSmooth,  sitk.Cast ( imgLeftHand, sitk.sitkFloat64 ) )

    return outI2

  def visualizationImages(self, workingSelector, viewerName, img, name):
    volumesLogic = slicer.modules.volumes.logic()
    processedVolume = volumesLogic.CloneVolume(slicer.mrmlScene, workingSelector.currentNode(), name)

    workingSelector.setCurrentNode(processedVolume)
    #processedVolume= workingSelector.currentNode()
    outNode = sitkUtils.PushVolumeToSlicer(img, targetNode=workingSelector.currentNode(), name=None, className='vtkMRMLScalarVolumeNode')

    # step 4) display image in Slice viwer
    lm = slicer.app.layoutManager()
    sliceViewer = lm.sliceWidget(viewerName)
    sliceViewerLogic = sliceViewer.sliceLogic()
    sliceViewerLogic.GetSliceCompositeNode().SetBackgroundVolumeID(workingSelector.currentNode().GetID())
    sliceViewer.setSliceOrientation('Axial')
    view=sliceViewer.sliceView()
    view.forceRender()
    # Set the orientation to axial
    sliceViewerLogic.GetSliceNode().UpdateMatrices()
    sliceViewerLogic.EndSliceNodeInteraction()


  def runSegmentation(self, workingSelector, processingSelector,tempMin,tempMax, rightCoordinatesRAS, leftCoordinatesRAS):
    """
    Run the actual algorithm
    """
    #outputVolume=workingSelector.currentNode()

    rightImage = self.processVolume(workingSelector, processingSelector, tempMin, tempMax, [70,117,1], "RightVolumen")
    # rightImage = self.processVolume(workingSelector, processingSelector, tempMin, tempMax, rightCoordinatesRAS)
    self.visualizationImages(workingSelector, "Yellow+", rightImage, "RightVolumen")

    leftImage = self.processVolume(workingSelector, processingSelector, tempMin, tempMax, [206,41,1], "LeftVolumen")
    # leftImage = self.processVolume(workingSelector, processingSelector, tempMin, tempMax, leftCoordinatesRAS)
    self.visualizationImages(workingSelector, "Red+", leftImage, "LeftVolumen")
  
    print("Images processed")

  def runProcessing(self, workingSelector, processingSelector,tempMin,tempMax):

    # outputVolume=workingSelector.currentNode()
    inputImage = sitkUtils.PullVolumeFromSlicer(workingSelector.currentNode())
    # extract image from volume
    zslice = 0
    size = list(inputImage.GetSize())
    size[2] = 0
    index = [0, 0, zslice]
    Extractor = sitk.ExtractImageFilter()
    Extractor.SetSize(size)
    Extractor.SetIndex(index)
    outputImage = Extractor.Execute(inputImage)

    if processingSelector.currentText == "original" :
      # original
      print("no processing required ")
      return
    elif processingSelector.currentText == "image smoothing" :
      # step 1)filtering: noise reduction
      outI2 = sitk.CurvatureFlow(image1=outputImage, timeStep=0.125, numberOfIterations=5)
    elif processingSelector.currentText == "image segmentation" :
      # step 1)filtering: noise reduction
      imgSmooth = sitk.CurvatureFlow(image1=outputImage, timeStep=0.125, numberOfIterations=5)
      # step 2) filtering: segmentation
      lstSeeds = [(247, 86)]
      labelLeftHand = 1
      imgLeftHand = sitk.ConnectedThreshold(image1=imgSmooth, seedList=lstSeeds, lower=tempMin, upper=tempMax, replaceValue=labelLeftHand)
      # step 3) create image to display
      imgSmoothInt = sitk.Cast(sitk.RescaleIntensity(imgSmooth), imgLeftHand.GetPixelID())
      # Use 'LabelOverlay' to overlay 'imgSmooth' and 'imgWhiteMatter'
      outI2 = sitk.Multiply(imgSmooth, sitk.Cast(imgLeftHand, sitk.sitkFloat64))
    elif processingSelector.currentText== "image segmentation + no holes" :
      # step 1)filtering: noise reduction
      imgSmooth = sitk.CurvatureFlow(image1=outputImage, timeStep=0.125, numberOfIterations=5)
      # step 2) filtering: segmentation
      lstSeeds = [(247, 86)]
      labelLeftHand = 1
      imgLeftHand = sitk.ConnectedThreshold(image1=imgSmooth, seedList=lstSeeds, lower=tempMin, upper=tempMax, replaceValue=labelLeftHand)
      # step 3) create image to display
      imgSmoothInt = sitk.Cast(sitk.RescaleIntensity(imgSmooth), imgLeftHand.GetPixelID())
      # Use 'LabelOverlay' to overlay 'imgSmooth' and 'imgWhiteMatter'
      imgLeftHandNoHoles = sitk.VotingBinaryHoleFilling(image1=imgLeftHand , radius=[2] * 3,  majorityThreshold=1, backgroundValue=0, foregroundValue=labelLeftHand )
      #outI2 = sitk.Multiply(imgSmooth, sitk.Cast(imgLeftHandNoHoles, sitk.sitkFloat64))
      outI2 = imgLeftHandNoHoles
    elif processingSelector.currentText == "contouring":
      # step 1)filtering: noise reduction
      imgSmooth = sitk.CurvatureFlow(image1=outputImage, timeStep=0.125, numberOfIterations=5)
      # step 2) filtering: segmentation
      lstSeeds = [(247, 86)]
      labelLeftHand = 1
      imgLeftHand = sitk.ConnectedThreshold(image1=imgSmooth, seedList=lstSeeds, lower=tempMin, upper=tempMax,
                                            replaceValue=labelLeftHand)
      # step 3) create image to display
      imgSmoothInt = sitk.Cast(sitk.RescaleIntensity(imgSmooth), imgLeftHand.GetPixelID())
      # Use 'LabelOverlay' to overlay 'imgSmooth' and 'imgWhiteMatter'
      imgLeftHandNoHoles = sitk.VotingBinaryHoleFilling(image1=imgLeftHand, radius=[2] * 3, majorityThreshold=1, backgroundValue=0, foregroundValue=labelLeftHand)

      #imageContourning=sitk.Cast(sitk.LabelContour(imgLeftHandNoHoles), sitk.sitkUInt16)
      #outI2 = imageContourning*16383
      imageContourning = (sitk.Cast(sitk.LabelContour(imgLeftHandNoHoles), sitk.sitkFloat64))*16383
      # outI2 = sitk.LabelOverlay(imgSmoothInt, sitk.LabelContour(imgLeftHandNoHoles ))
      outI2 = sitk.LabelOverlay(imgSmoothInt, sitk.Cast(sitk.LabelContour(imgLeftHandNoHoles), imgLeftHand.GetPixelID()))

      #outI2 = sitk.Cast(outI, sitk.sitkFloat64)

    else:
      print("unknown processing")

    # step4) Push image to VTK volume
    # if not processedVolume:
    #  print("output node should exist and be selected before processing is performed")
    volumesLogic = slicer.modules.volumes.logic()
    processedVolume = volumesLogic.CloneVolume(slicer.mrmlScene, workingSelector.currentNode(), 'processedVolume')

    workingSelector.setCurrentNode(processedVolume)
    # processedVolume= workingSelector.currentNode()
    outNode = sitkUtils.PushVolumeToSlicer(outI2, targetNode=workingSelector.currentNode(), name=None, className='vtkMRMLScalarVolumeNode')

    # step 4) display image in green Slice viwer
    lm = slicer.app.layoutManager()
    green = lm.sliceWidget('green')
    greenLogic = green.sliceLogic()
    greenLogic.GetSliceCompositeNode().SetBackgroundVolumeID(workingSelector.currentNode().GetID())
    green.setSliceOrientation('Axial')
    view = green.sliceView()
    view.forceRender()
    # Set the orientation to axial
    greenLogic.GetSliceNode().UpdateMatrices()
    greenLogic.EndSliceNodeInteraction()

    return


  # def hasImageData(self,volumeNode):
  #   """This is an example logic method that
  #   returns true if the passed in volume
  #   node has valid image data
  #   """
  #   if not volumeNode:
  #     logging.debug('hasImageData failed: no volume node')
  #     return False
  #   if volumeNode.GetImageData() is None:
  #     logging.debug('hasImageData failed: no image data in volume node')
  #     return False
  #   return True

  # def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
  #   """Validates if the output is not the same as input
  #   """
  #   if not inputVolumeNode:
  #     logging.debug('isValidInputOutputData failed: no input volume node defined')
  #     return False
  #   if not outputVolumeNode:
  #     logging.debug('isValidInputOutputData failed: no output volume node defined')
  #     return False
  #   if inputVolumeNode.GetID()==outputVolumeNode.GetID():
  #     logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
  #     return False
  #   return True

  # def takeScreenshot(self,name,description,type=-1):
  #   # show the message even if not taking a screen shot
  #   slicer.util.delayDisplay('Take screenshot: '+description+'.\nResult is available in the Annotations module.', 3000)

  #   lm = slicer.app.layoutManager()
  #   # switch on the type to get the requested window
  #   widget = 0
  #   if type == slicer.qMRMLScreenShotDialog.FullLayout:
  #     # full layout
  #     widget = lm.viewport()
  #   elif type == slicer.qMRMLScreenShotDialog.ThreeD:
  #     # just the 3D window
  #     widget = lm.threeDWidget(0).threeDView()
  #   elif type == slicer.qMRMLScreenShotDialog.Red:
  #     # red slice window
  #     widget = lm.sliceWidget("Red")
  #   elif type == slicer.qMRMLScreenShotDialog.green:
  #     # green slice window
  #     widget = lm.sliceWidget("green")
  #   elif type == slicer.qMRMLScreenShotDialog.Green:
  #     # green slice window
  #     widget = lm.sliceWidget("Green")
  #   else:
  #     # default to using the full window
  #     widget = slicer.util.mainWindow()
  #     # reset the type so that the node is set correctly
  #     type = slicer.qMRMLScreenShotDialog.FullLayout

  #   # grab and convert to vtk image data
  #   qimage = ctk.ctkWidgetsUtils.grabWidget(widget)
  #   imageData = vtk.vtkImageData()
  #   slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

  #   annotationLogic = slicer.modules.annotations.logic()
  #   annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

  # def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
  #   """
  #   Run the actual algorithm
  #   """

  #   if not self.isValidInputOutputData(inputVolume, outputVolume):
  #     slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
  #     return False

  #   logging.info('Processing started')

  #   # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
  #   cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(), 'ThresholdValue' : imageThreshold, 'ThresholdType' : 'Above'}
  #   cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

  #   # Capture screenshot
  #   if enableScreenshots:
  #     self.takeScreenshot('IrBaseUlcerDetectionTest-Start','MyScreenshot',-1)

  #   logging.info('Processing completed')

  #   return True

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
#  TESTS
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class IrBaseUlcerDetectionTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_IrBaseUlcerDetection1()

  def test_IrBaseUlcerDetection1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = IrBaseUlcerDetectionLogic()
    # self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
