'''
Created on 2021/07/12

@author: N200797
'''
import sys
sys.dont_write_bytecode = True
import ADASIS_LogViewer
from QgisADASIS_Process import *
import importlib
try:
    importlib.reload(ADASIS_LogViewer.ADASIS_LogViewer_Param)
    del param
except:
    pass
from ADASIS_LogViewer.ADASIS_LogViewer_Param import *
from MessageType import initNewLayer
from ControlPanel import *
from LayerManager import *
from datetime import datetime
from Logger import initLogger, LogLevel
from GlobalVar import setResource
TOOL_VERSION = '2.92'

#######################################################################################
##                            Code （修正禁止）                                                                                                 ##
#######################################################################################
    
print('----------------------------------------------------------------------')
print('                              Setting                                 ')
print('----------------------------------------------------------------------')
param = getParam()
try:
    mode = param.mode
except:
    mode = 1
if mode == 1:
    print('Log View Mode')
elif mode == 2:
    print('Realtime View Mode')
elif mode == 3:
    print('GNSS Analyze Mode')
else:
    print('Unknown Mode')

try:
    simpleDrawMode = param.simpleDrawMode
except:
    simpleDrawMode = None
if simpleDrawMode == None:
    if mode == 1 or mode == 3:
        simpleDrawMode = False
    else:
        simpleDrawMode = True
print('simpleDrawMode = ' + str(simpleDrawMode))

if mode == 1:
    try:
        logFile = param.logFile
    except:
        logFile = None
    if logFile != None:
        print('logFile = ' + logFile)
            
    try:
        startPoint = param.startPoint
    except:
        startPoint = None
    if startPoint != None:
        print('startPoint = ' + str(startPoint))
        
    try:
        endPoint = param.endPoint
    except:
        endPoint = None
    if endPoint != None:
        print('endPoint = ' + str(endPoint))
        
    try:
        recommendLaneLayerRedraw = param.recommendLaneLayerRedraw
    except:
        recommendLaneLayerRedraw = None
    if recommendLaneLayerRedraw == None:
        if simpleDrawMode == True:
            recommendLaneLayerRedraw = True
        else:
            recommendLaneLayerRedraw = False
    if recommendLaneLayerRedraw == True:
        print('Clear recommendLaneLayer every draw')
        
    try:
        ADASISanalyze = param.ADASISanalyze
    except:
        ADASISanalyze = False
        
    try:
        DebugEtherAnalyze = param.DebugEtherAnalyze
    except:
        DebugEtherAnalyze = False
        
    try:
        REDRanalyze = param.REDRanalyze
    except:
        REDRanalyze = True
    
elif mode == 2:
    try:
        interfaceName = param.interfaceName
    except:
        interfaceName = 'イーサネット'
    print('interfaceName = ' + interfaceName)

elif mode == 3:
    try:
        useDefaultRef = param.useDefaultRef
    except:
        useDefaultRef = 'LaneProjection'

try:
    someipmode = param.someipmode
except:
    someipmode = True
print('someipmode = ' + str(someipmode))

try:
    vehicle = param.vehicle
except:
    vehicle = 'PZ1A'
        
try:
    filter_srcMAC = param.filter_srcMAC
except:
    filter_srcMAC = None
if filter_srcMAC != None:
    print('filter_srcMAC = ' + str(filter_srcMAC))

try:
    filter_messageID = param.MessageID_filter
except:
    filter_messageID = None
if filter_messageID != None:
    print('filter_messageID = ' + str([hex(x) for x in filter_messageID]))

try:
    CAN_chanel_filter = param.CAN_chanel_filter
except:
    CAN_chanel_filter = None
if CAN_chanel_filter != None:
    print('CAN_chanel_filter = ' + str(CAN_chanel_filter))

try:
    ethernetSpecVer = param.ethernetSpecVer
except:
    ethernetSpecVer = None
if ethernetSpecVer != None:
    print('ethernetSpecVer = ' + str(ethernetSpecVer))
    
try:
    HDMAP_Geojson = param.HDMAP_Geojson
except:
    HDMAP_Geojson = None
if HDMAP_Geojson != None:
    print('HDMAP_Geojson = ' + HDMAP_Geojson)
    
try:
    HDMAP_Geojson_old = param.HDMAP_Geojson_old
except:
    HDMAP_Geojson_old = None
if HDMAP_Geojson_old != None:
    print('HDMAP_Geojson_old = ' + HDMAP_Geojson_old)

try:
    laneIDconvert = param.laneIDconvert
except:
    laneIDconvert = False
if laneIDconvert == True:
    print('laneIDconvert On')
    
try:
    debugMode = param.debugMode
except:
    debugMode = False
if debugMode == True:
    print(' !! Debug Mode ON !!')
    
drawTask = None
resource = {}
setResource(resource) #変数共有のため
    
#simpleDrawMode = True #Test for realtime view using log
try:
    index = index
    controlPanel.reset(simpleDrawMode)
except:
    index = 0
    layerManager = LayerManager()
    controlPanel = ControlPanel(layerManager, simpleDrawMode)
    
if mode == 1:
    if logFile == None:
        logFile = QFileDialog.getOpenFileNames(caption='Choose log files', filter='EtherLog(*.pcapng;*.pcap;*.blf);;CanLog(*.asc);;Shp File(*.shp);;R-DR Binary(*.dat);;R-DR Gamma CSV(*.csv)') 
        if len(logFile[0]) == 0:
            print("Canceled.")
    if len(logFile[0]) > 0:
        logFile[0].sort()
        if logFile[1] == 'Shp File(*.shp)':
            index += 1
            groupName = '({0}){1}'.format(index, logFile[0][0].split('/')[-2])
            layerManager.makeLayerGroup(groupName, isShpFile = True)
            controlPanel.addLayerGroup(groupName)
            shpFileLoad(controlPanel, logFile[0])
            drawTask = None
        elif logFile[1] == 'R-DR Binary(*.dat)':
            logger = initLogger(QgsProject.instance().readPath('./') + '/' + 'REDR-Viewer({})_'.format(datetime.now().strftime('%Y-%m-%d-%H-%M-%S')), forMultiProcess = False)
            logger.logPrintWithConsol('<Ver ' + TOOL_VERSION + '>')
            index += 1
            RDRdatFileLoad(index, controlPanel, logFile[0])
            drawTask = None
            logger.close()
        elif logFile[1] == 'R-DR Gamma CSV(*.csv)':
            logger = initLogger(QgsProject.instance().readPath('./') + '/' + 'REDR-Viewer({})_'.format(datetime.now().strftime('%Y-%m-%d-%H-%M-%S')), forMultiProcess = False)
            logger.logPrintWithConsol('<Ver ' + TOOL_VERSION + '>')
            index += 1
            RDRdatFileLoad_fromCSV(index, controlPanel, logFile[0])
            drawTask = None
            logger.close()
        else:
            drawTask = draw(controlPanel, logFile[0], startPoint, endPoint, someipmode, filter_srcMAC, filter_messageID, CAN_chanel_filter, ethernetSpecVer, recommendLaneLayerRedraw, vehicle, ADASISanalyze, DebugEtherAnalyze, REDRanalyze)

elif mode == 2:
    drawTask = realTimeView(controlPanel, interfaceName, someipmode, filter_srcMAC, filter_messageID, ethernetSpecVer, True, vehicle)

elif mode == 3:
    logFile = QFileDialog.getOpenFileNames(caption='Choose log files　(Only analyze targets)', filter='EtherLog+LatLon(*.pcapng;*.pcap;*.blf;*.csv);;') 
    if len(logFile[0]) == 0:
        print("Canceled.")
    if len(logFile[0]) > 0:
        logFile[0].sort()
        targetGnssRefFile = QFileDialog.getOpenFileName(caption='Choose ref files (If not select Default Ref will be ref)', filter='LatLon(*.csv);;')
        if len(targetGnssRefFile[0]) == 0:
            drawTask = drawForGnssAnalyze(controlPanel, logFile[0], someipmode, useDefaultRef)
        else:
            drawTask = drawForGnssAnalyze(controlPanel, logFile[0], someipmode, targetGnssRefFile[0])
            
if drawTask != None:
    print(' ')
    print('----------------------------------------------------------------------')
    print('                          Viewer Started                              ')
    print('----------------------------------------------------------------------')
    
    try:
        controlPanel.show()
        logBasePath = QgsProject.instance().readPath('./') + '/' + '{0}({1}).txt'.format('realTimeViewer' if mode == 2 else 'logViewer', drawTask.fileName.replace(':','-'))
        if debugMode == True:
            logger = initLogger(logBasePath, forMultiProcess = False, logLevel = LogLevel.DEBUG)
        else:
            logger = initLogger(logBasePath, forMultiProcess = False, logLevel = LogLevel.INFO)
        logger.logPrintWithConsol('<Ver ' + TOOL_VERSION + '>')

        index += 1
        groupName = '({0}){1}'.format(index, drawTask.fileName)
        layerManager.makeLayerGroup(groupName)
        controlPanel.addLayerGroup(groupName)
        QgsApplication.taskManager().addTask(drawTask)
        readHDMAP(HDMAP_Geojson, HDMAP_Geojson_old, laneIDconvert)
            
        while True:
            # controlPanel.stopRequest == True は見ないようにする。Task終了前にこのループが終わってしまうため。
            if drawTask.status() == QgsTask.TaskStatus.Complete or drawTask.status() == QgsTask.TaskStatus.Terminated:
                break
            
            if controlPanel.drawWithLoad == True:
                drawLayer(drawTask, layerManager, controlPanel, simpleDrawMode)
                refreshCanvas(drawTask, layerManager, controlPanel)
            else:
                QApplication.processEvents()
                controlPanel.update()
            
            if controlPanel.newLayerRequest == True:
                index += 1
                groupName = '({0}){1}'.format(index, drawTask.fileName)
                layerManager.closeLayer()
                layerManager.makeLayerGroup(groupName)
                controlPanel.addLayerGroup(groupName)
                drawTask.resetDrawGroup()
                initNewLayer()
                controlPanel.newLayerRequest = False
                
            if controlPanel.stopRequest == True:
                drawTask.cancel()

        #残り描画
        drawLayer(drawTask, layerManager, controlPanel, simpleDrawMode)
        refreshCanvas(drawTask, layerManager, controlPanel)
    
    except Exception as e: #drawTaskが終了し、obj削除された場合
        if controlPanel.stopRequest != True:
            logger.errLog("Viewer Error:{0}".format(e))
            logger.errLog(traceback.format_exc())
    
    printRDRSummery(logger.logPrintWithConsol)
    layerManager.closeLayer()    
    controlPanel.closePanel()
    if logger.getErrExist() == True:
        print('\nSome error detected.')
        logger.openErrlogFile()
    logger.logPrintWithConsol('\nAll process complete')
    logger.close()

else:
    controlPanel.show()
    controlPanel.closePanel()
