'''
Created on 2021/07/17

@author: N200797
'''
import os
import re
from datetime import datetime, timedelta
from LayerManager import *
from GlobalVar import getSrcMAC, setRecommendedLaneShowTarget
try:
    from qgis.core import *
    from qgis.gui import *
    from qgis.PyQt import QtGui
    from PyQt5.QtWidgets import QDialog, QFileDialog, QPushButton, QLabel, QApplication, QTextEdit, QSlider, QCheckBox, QComboBox, QMessageBox
except:
    pass

class ControlPanel(QDialog):
    def reset(self, realTimeViewMode):
        self.realTimeViewMode = realTimeViewMode
        self.stopRequest = False
        self.pauseRequest = False
        self.newLayerRequest = False
        self.playSpeed = 1.0
        self.drawWithLoad = True
        self.trackingScale = 1000
        self.tracking = False
        self.setWindowTitle("Control Panel [Scale : {0}m]".format(self.trackingScale*2))
        self.currentGroupName = None
        
        self.trackingBtn.setText("Tracking")
        self.trackingBtn.setStyleSheet('QPushButton {color: green;}')
        
        self.pauseBtn.setText("Pause")
        self.pauseBtn.setStyleSheet('QPushButton {color: black;}')
        
        for btn in self.speedBtnList:
            btn.setStyleSheet('QPushButton {color: black;}')
        self.speed2Btn.setStyleSheet('QPushButton {color: red;}')
        
        self.HandsOffProhibitReason.setText('---')
        self.ND2code.setText('---')
        self.CancelCode.setText('---')
        
        self.recommendedLaneShowTarget.setCurrentIndex(0)
            
        if self.realTimeViewMode == True:
            self.HandsOffProhibitReasonLabel.setVisible(True)
            self.HandsOffProhibitReason.setVisible(True)
            self.ND2codeLabel.setVisible(True)
            self.ND2code.setVisible(True)
            self.CancelCodeLabel.setVisible(True)
            self.CancelCode.setVisible(True)
            self.pauseBtn.setVisible(False)
            for btn in self.speedBtnList:
                btn.setVisible(False)
            self.filterCheck.setVisible(False)
            self.filterRangePrev10.setVisible(False)
            self.filterRangePrev.setVisible(False)
            self.totalRangeLabel.setVisible(False)
            self.filterRangeLabel.setVisible(False)
            self.filterRangeNext.setVisible(False)
            self.filterRangeNext10.setVisible(False)
            self.filterRange.setVisible(False)
            self.secLabel.setVisible(False)
            self.filterSlider.setVisible(False)
            self.recommendedLaneShowTarget.setVisible(True)
            self.recommendedLaneShowLabel.setVisible(True)
            
        else:
            self.HandsOffProhibitReasonLabel.setVisible(False)
            self.HandsOffProhibitReason.setVisible(False)
            self.ND2codeLabel.setVisible(False)
            self.ND2code.setVisible(False)
            self.CancelCodeLabel.setVisible(False)
            self.CancelCode.setVisible(False)
            self.pauseBtn.setVisible(True)
            for btn in self.speedBtnList:
                btn.setVisible(True)
            self.filterCheck.setVisible(True)
            self.filterRangePrev10.setVisible(True)
            self.filterRangePrev.setVisible(True)
            self.totalRangeLabel.setVisible(True)
            self.filterRangeLabel.setVisible(True)
            self.filterRangeNext.setVisible(True)
            self.filterRangeNext10.setVisible(True)
            self.filterRange.setVisible(True)
            self.secLabel.setVisible(True)
            self.filterSlider.setVisible(True)
            self.recommendedLaneShowTarget.setVisible(False)
            self.recommendedLaneShowLabel.setVisible(False)
            self.speed5Click()
            
        self.newLayerBtn.setVisible(True)
        self.zoomInBtn.setVisible(True)
        self.trackingBtn.setVisible(True)
        self.zoomOutBtn.setVisible(True)
        
    def __init__(self, layerManager, realTimeViewMode):
        super(ControlPanel, self).__init__(None)
        self.layerManager = layerManager
        self.logDataStartTime = {}
        self.logDataEndTime = {}
        self.filterStartTime = {}
        self.filterEndTime = {}
        self.filterOnOff = {}
        self.setFixedSize(530, 340)
        
        self.pauseBtn = QPushButton("Pause", self)
        self.pauseBtn.setStyleSheet('QPushButton {color: black;}')
        self.pauseBtn.move(50, 20)
        self.pauseBtn.resize(130, 50)
        self.pauseBtn.clicked.connect(self.pauseClick)
        
        self.newLayerBtn = QPushButton("New Layer", self)
        self.newLayerBtn.setStyleSheet('QPushButton {color: black;}')
        self.newLayerBtn.move(200, 20)
        self.newLayerBtn.resize(130, 50)
        self.newLayerBtn.clicked.connect(self.newLayerClick)
        
        self.stopBtn = QPushButton("Stop", self)
        self.stopBtn.setStyleSheet('QPushButton {color: black;}')
        self.stopBtn.move(350, 20)
        self.stopBtn.resize(130, 50)
        self.stopBtn.clicked.connect(self.stopClick)
        
        self.HandsOffProhibitReasonLabel = QLabel('HandsOff Prohibit Reason : ', self)
        self.HandsOffProhibitReasonLabel.setFont(QtGui.QFont('Arial', 10))
        self.HandsOffProhibitReasonLabel.move(50, 75)
        self.HandsOffProhibitReasonLabel.resize(300, 20)
        self.HandsOffProhibitReason = QLabel('---', self)
        self.HandsOffProhibitReason.setFont(QtGui.QFont('Arial', 10))
        self.HandsOffProhibitReason.move(220, 75)
        self.HandsOffProhibitReason.resize(300, 20)
        
        self.ND2codeLabel = QLabel('ND2 Code : ', self)
        self.ND2codeLabel.setFont(QtGui.QFont('Arial', 10))
        self.ND2codeLabel.move(140, 95)
        self.ND2codeLabel.resize(300, 20)
        self.ND2code = QLabel('---', self)
        self.ND2code.setFont(QtGui.QFont('Arial', 10))
        self.ND2code.move(220, 95)
        self.ND2code.resize(300, 20)
        
        self.CancelCodeLabel = QLabel('Cancel Code : ', self)
        self.CancelCodeLabel.setFont(QtGui.QFont('Arial', 10))
        self.CancelCodeLabel.move(125, 115)
        self.CancelCodeLabel.resize(300, 20)
        self.CancelCode = QLabel('---', self)
        self.CancelCode.setFont(QtGui.QFont('Arial', 10))
        self.CancelCode.move(220, 115)
        self.CancelCode.resize(300, 20)
        
        self.speed1Btn = QPushButton("x0.5", self)
        self.speed1Btn.setStyleSheet('QPushButton {color: black;}')
        self.speed1Btn.move(50, 90)
        self.speed1Btn.resize(70, 30)
        self.speed1Btn.clicked.connect(self.speed1Click)
        
        self.speed2Btn = QPushButton("x1.0", self)
        self.speed2Btn.setStyleSheet('QPushButton {color: red;}')
        self.speed2Btn.move(140, 90)
        self.speed2Btn.resize(70, 30)
        self.speed2Btn.clicked.connect(self.speed2Click)
        
        self.speed3Btn = QPushButton("x2.0", self)
        self.speed3Btn.setStyleSheet('QPushButton {color: black;}')
        self.speed3Btn.move(230, 90)
        self.speed3Btn.resize(70, 30)
        self.speed3Btn.clicked.connect(self.speed3Click)
        
        self.speed4Btn = QPushButton("x3.0", self)
        self.speed4Btn.setStyleSheet('QPushButton {color: black;}')
        self.speed4Btn.move(320, 90)
        self.speed4Btn.resize(70, 30)
        self.speed4Btn.clicked.connect(self.speed4Click)
        
        self.speed5Btn = QPushButton("Max", self)
        self.speed5Btn.setStyleSheet('QPushButton {color: black;}')
        self.speed5Btn.move(410, 90)
        self.speed5Btn.resize(70, 30)
        self.speed5Btn.clicked.connect(self.speed5Click)
        
        self.speedBtnList = [self.speed1Btn, self.speed2Btn, self.speed3Btn, self.speed4Btn, self.speed5Btn]
        
        self.zoomInBtn = QPushButton("Zoom In", self)
        self.zoomInBtn.setStyleSheet('QPushButton {color: black;}')
        self.zoomInBtn.move(50, 140)
        self.zoomInBtn.resize(130, 50)
        self.zoomInBtn.clicked.connect(self.zoomInClick)
        
        self.trackingBtn = QPushButton("Tracking", self)
        self.trackingBtn.setStyleSheet('QPushButton {color: green;}')
        self.trackingBtn.move(200, 140)
        self.trackingBtn.resize(130, 50)
        self.trackingBtn.clicked.connect(self.trackingClick)
        
        self.zoomOutBtn = QPushButton("Zoom Out", self)
        self.zoomOutBtn.setStyleSheet('QPushButton {color: black;}')
        self.zoomOutBtn.move(350, 140)
        self.zoomOutBtn.resize(130, 50)
        self.zoomOutBtn.clicked.connect(self.zoomOutClick)
        
        self.recommendedLaneShowLabel = QLabel('RecommendedLane Show Target : ', self)
        self.recommendedLaneShowLabel.setFont(QtGui.QFont('Arial', 10))
        self.recommendedLaneShowLabel.move(50, 270)
        self.recommendedLaneShowLabel.resize(200, 20)
        
        self.recommendedLaneShowTarget = QComboBox(self)
        self.recommendedLaneShowTarget.move(260, 270)
        self.recommendedLaneShowTarget.resize(100, 20)
        self.recommendedLaneShowTarget.addItems(['All', 'IVI' , 'MPU' , 'AD'])
        self.recommendedLaneShowTarget.currentTextChanged.connect(self.recommendedLaneShowTargetClick)
        
        self.filterCheck = QCheckBox('Enable Time Filter Draw', self)
        self.filterCheck.move(50, 230)
        self.filterCheck.resize(480, 30)
        self.filterCheck.stateChanged.connect(self.filterCheckClick)
        
        self.shpSaveBtn = QPushButton("All shp save", self)
        self.shpSaveBtn.setStyleSheet('QPushButton {color: black;}')
        self.shpSaveBtn.move(220, 200)
        self.shpSaveBtn.resize(125, 20)
        self.shpSaveBtn.clicked.connect(self.shpSaveAllClick)
        
        self.shpSaveBtn = QPushButton("shp save", self)
        self.shpSaveBtn.setStyleSheet('QPushButton {color: black;}')
        self.shpSaveBtn.move(355, 200)
        self.shpSaveBtn.resize(125, 20)
        self.shpSaveBtn.clicked.connect(self.shpSaveClick)
        
        self.groupList = QComboBox(self)
        self.groupList.move(220, 230)
        self.groupList.resize(260, 20)
        self.groupList.currentTextChanged.connect(self.groupListClick)
        
        self.filterRangePrev10 = QPushButton("<<", self)
        self.filterRangePrev10.setStyleSheet('QPushButton {color: black;}')
        self.filterRangePrev10.move(50, 260)
        self.filterRangePrev10.resize(30, 30)
        self.filterRangePrev10.clicked.connect(self.filterRangePrev10Click)
        
        self.filterRangePrev = QPushButton("<", self)
        self.filterRangePrev.setStyleSheet('QPushButton {color: black;}')
        self.filterRangePrev.move(90, 260)
        self.filterRangePrev.resize(30, 30)
        self.filterRangePrev.clicked.connect(self.filterRangePrevClick)
        
        self.totalRangeLabel = QLabel('Total time range : --:--:-- ~ --:--:--', self)
        self.totalRangeLabel.setFont(QtGui.QFont('Arial', 10))
        self.totalRangeLabel.move(130, 255)
        self.totalRangeLabel.resize(240, 20)
        self.filterRangeLabel = QLabel('Filter time range : --:--:-- ~ --:--:--', self)
        self.filterRangeLabel.setFont(QtGui.QFont('Arial', 10))
        self.filterRangeLabel.move(130, 270)
        self.filterRangeLabel.resize(240, 20)
        
        self.filterRangeNext = QPushButton(">", self)
        self.filterRangeNext.setStyleSheet('QPushButton {color: black;}')
        self.filterRangeNext.move(370, 260)
        self.filterRangeNext.resize(30, 30)
        self.filterRangeNext.clicked.connect(self.filterRangeNextClick)
        
        self.filterRangeNext10 = QPushButton(">>", self)
        self.filterRangeNext10.setStyleSheet('QPushButton {color: black;}')
        self.filterRangeNext10.move(410, 260)
        self.filterRangeNext10.resize(30, 30)
        self.filterRangeNext10.clicked.connect(self.filterRangeNext10Click)
        
        self.filterRange = QTextEdit('10', self)
        self.filterRange.move(450, 260)
        self.filterRange.resize(30, 30)
        
        self.secLabel = QLabel('sec', self)
        self.secLabel.setFont(QtGui.QFont('Arial', 10))
        self.secLabel.move(490, 260)
        self.secLabel.resize(20, 30)
        
        self.filterSlider = QSlider(1, self)
        self.filterSlider.move(50, 300)
        self.filterSlider.resize(430, 20)
        self.filterSlider.setMinimum(0)
        self.filterSlider.setMaximum(0)
        self.filterSlider.sliderReleased.connect(self.filterSliderReleased)
        self.filterSlider.valueChanged.connect(self.filterSliderValueChanged)
        
        self.reset(realTimeViewMode)
        
    def updateDataRangeInfo(self):
        groupName = self.groupList.currentText()
        if self.logDataStartTime[groupName] != None:
            self.totalRangeLabel.setText('Total time range : {0} ~ {1}'.format(self.logDataStartTime[groupName].strftime("%H:%M:%S"), self.logDataEndTime[groupName].strftime("%H:%M:%S")))
            self.filterSlider.setMaximum((self.logDataEndTime[groupName] - self.logDataStartTime[groupName]).total_seconds())
        else:
            self.totalRangeLabel.setText('Total time range : --:--:-- ~ --:--:--')
        if self.filterStartTime[groupName] != None:
            self.filterRangeLabel.setText('Filter time range : {0} ~ {1}'.format(self.filterStartTime[groupName].strftime("%H:%M:%S"), self.filterEndTime[groupName].strftime("%H:%M:%S")))
        else:
            self.filterRangeLabel.setText('Filter time range : --:--:-- ~ --:--:--')
            
    def setDataRange(self, startTime, endTime):
        if startTime == None or endTime == None:
            return
        self.logDataStartTime[self.currentGroupName] = startTime - timedelta(seconds=10)
        self.logDataEndTime[self.currentGroupName] = endTime + timedelta(seconds=10)
        self.updateDataRangeInfo()
    
    def shpSaveClick(self):
        groupName = self.groupList.currentText()
        if self.filterOnOff[groupName] == True:
            if QMessageBox.Cancel == QMessageBox.question(None, "Confirm", "Filter is enabled. Do you want only save filtered part ?", QMessageBox.Ok, QMessageBox.Cancel):
                return
            
        matchObj = re.search('^\([0-9\-]+\)', groupName)
        if matchObj:
            saveName =  groupName[matchObj.end():]
        else:
            saveName =  groupName
        saveName = '(shp)' + saveName.replace('.', '_')
        savePath = QFileDialog.getSaveFileName(caption='Choose log files', directory = saveName)[0] # because result include filter tuple
        if len(savePath) == 0:
            return
        
        try:
            os.mkdir(savePath)
        except:
            pass
        self.layerManager.shpSave(groupName, savePath)
        
    def shpSaveAllClick(self):
        savePath = QFileDialog.getSaveFileName(caption='Choose log files', directory = 'ShpSave')[0] # because result include filter tuple
        if len(savePath) == 0:
            return
        
        try:
            os.mkdir(savePath)
        except:
            pass
        
        for groupName in [self.groupList.itemText(i) for i in range(self.groupList.count())]:
            saveName =  groupName
            saveName = '(shp)' + saveName.replace('.', '_')
            subSavePath = savePath + '/' + saveName
            try:
                os.mkdir(subSavePath)
            except:
                pass
            self.layerManager.shpSave(groupName, subSavePath)
        print('All save completed.')
        
    def recommendedLaneShowTargetClick(self):
        setRecommendedLaneShowTarget(self.recommendedLaneShowTarget.currentText())
    
    def filterCheckClick(self):
        groupName = self.groupList.currentText()
        if self.filterCheck.checkState() == False:
            self.layerManager.clearFilter(groupName)
            self.filterOnOff[groupName] = False
        else:
            if self.filterStartTime == None:
                self.filterSliderValueChanged()
            self.layerManager.setFilter(groupName, self.filterStartTime[groupName], self.filterEndTime[groupName])
            self.filterOnOff[groupName] = True
        
    def filterSliderValueChanged(self):
        groupName = self.groupList.currentText()
        if self.logDataStartTime[groupName] == None or self.logDataEndTime[groupName] == None:
            return
        if len(self.filterRange.toPlainText()) == 0:
            filterRange = 0
        else:
            filterRange = int(self.filterRange.toPlainText())
        value = self.filterSlider.value()
        self.filterStartTime[groupName] = self.logDataStartTime[groupName] + timedelta(seconds=value)
        self.filterEndTime[groupName] = self.filterStartTime[groupName] + timedelta(seconds=filterRange)
        self.updateDataRangeInfo()
        self.filterCheckClick()
        
    def filterSliderReleased(self):
        self.filterSliderValueChanged()
        
    def filterRangePrev10Click(self):
        value = self.filterSlider.value()
        if value > 10:
            value -= 10
        else:
            value = 0
        self.filterSlider.setValue(value)
        
    def filterRangePrevClick(self):
        value = self.filterSlider.value()
        if value > 1:
            value -= 1
        else:
            value = 0
        self.filterSlider.setValue(value)
        
    def filterRangeNext10Click(self):
        value = self.filterSlider.value()
        value += 10
        self.filterSlider.setValue(value)
        
    def filterRangeNextClick(self):
        value = self.filterSlider.value()
        value += 1
        self.filterSlider.setValue(value)
            
    def zoomInClick(self):
        if self.trackingScale > 1000:
            self.trackingScale -= 1000
        elif self.trackingScale >= 600:
            self.trackingScale -= 200
        elif self.trackingScale >= 200:
            self.trackingScale -= 100
        else:
            self.trackingScale = 100
        self.setWindowTitle("Control Panel [Scale : {0}m]".format(self.trackingScale*2))
    
    def zoomOutClick(self):
        if self.trackingScale < 400:
            self.trackingScale += 100
        elif self.trackingScale < 1000:
            self.trackingScale += 200
        else:
            self.trackingScale += 1000
        self.setWindowTitle("Control Panel [Scale : {0}m]".format(self.trackingScale*2))
        
    def trackingClick(self):
        if self.drawWithLoad == False:
            return
        
        if self.tracking == True:
            self.tracking = False
            self.trackingBtn.setText("Tracking")
            self.trackingBtn.setStyleSheet('QPushButton {color: green;}')
        else:
            self.tracking = True
            self.trackingBtn.setText("Tracking stop")
            self.trackingBtn.setStyleSheet('QPushButton {color: black;}')

    def stopClick(self):
        self.stopRequest = True
                
    def pauseClick(self):
        if self.pauseRequest == True:
            self.pauseRequest = False
            self.pauseBtn.setText("Pause")
            self.pauseBtn.setStyleSheet('QPushButton {color: black;}')
        else:
            self.pauseRequest = True
            self.pauseBtn.setText("Play")
            self.pauseBtn.setStyleSheet('QPushButton {color: blue;}')
    
    def newLayerClick(self):
        self.newLayerRequest = True
    
    def speed1Click(self):
        self.drawWithLoad = True
        self.playSpeed = 0.5
        for btn in self.speedBtnList:
            btn.setStyleSheet('QPushButton {color: black;}')
        self.speed1Btn.setStyleSheet('QPushButton {color: red;}')
        
    def speed2Click(self):
        self.drawWithLoad = True
        self.playSpeed = 1.0
        for btn in self.speedBtnList:
            btn.setStyleSheet('QPushButton {color: black;}')
        self.speed2Btn.setStyleSheet('QPushButton {color: red;}')
        
    def speed3Click(self):
        self.drawWithLoad = True
        self.playSpeed = 2.0
        for btn in self.speedBtnList:
            btn.setStyleSheet('QPushButton {color: black;}')
        self.speed3Btn.setStyleSheet('QPushButton {color: red;}')
        
    def speed4Click(self):
        self.drawWithLoad = True
        self.playSpeed = 3.0
        for btn in self.speedBtnList:
            btn.setStyleSheet('QPushButton {color: black;}')
        self.speed4Btn.setStyleSheet('QPushButton {color: red;}')
        
    def speed5Click(self):
        self.drawWithLoad = False
        print('Now read log data... please wait until finish. If you want cancel, select other speed.')
        for btn in self.speedBtnList:
            btn.setStyleSheet('QPushButton {color: black;}')
        self.speed5Btn.setStyleSheet('QPushButton {color: red;}')
        
    def closePanel(self):
        self.pauseBtn.setVisible(False)
        self.newLayerBtn.setVisible(False)
        for btn in self.speedBtnList:
            btn.setVisible(False)
        self.zoomInBtn.setVisible(False)
        self.trackingBtn.setVisible(False)
        self.zoomOutBtn.setVisible(False)
        self.HandsOffProhibitReasonLabel.setVisible(False)
        self.HandsOffProhibitReason.setVisible(False)
        self.ND2codeLabel.setVisible(False)
        self.ND2code.setVisible(False)
        self.CancelCodeLabel.setVisible(False)
        self.CancelCode.setVisible(False)
    
    def closeEvent(self, _):
        pass
        
    def addLayerGroup(self, name):
        self.currentGroupName = name
        self.filterOnOff[name] = False
        self.logDataStartTime[name] = None
        self.logDataEndTime[name] = None
        self.filterStartTime[name] = None
        self.filterEndTime[name] = None
        self.groupList.addItems([name])
        self.groupList.setCurrentIndex(self.groupList.count()-1)
        
    def groupListClick(self, _):
        groupName = self.groupList.currentText()
        self.filterCheck.setChecked(self.filterOnOff[groupName])
        self.updateDataRangeInfo()
        if self.filterStartTime[groupName] != None:
            self.filterSlider.setValue((self.filterStartTime[groupName] - self.logDataStartTime[groupName]).total_seconds())
        else:
            self.filterSlider.setValue(0)
            