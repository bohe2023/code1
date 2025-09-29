'''
Created on 2023/12/28

@author: AD2Gen2-19
'''
from GlobalVar import setResource, setProgramDir, setLocal, getProgramDir
setResource({})
setLocal('US') # for opengl window
from multiprocessing import freeze_support
from os import getcwd
from Logger import initLogger, LogLevel
from Process_openGLViewer import drawLogFile, realTimeView, drawLayer, drawPositionPuck
from openGL_window import OpenGLWindow
from LayerManagerForViewer import LayerManager
from EthernetDeviceSelectBox import showEthernetDeviceSelectBox
from datetime import datetime
import os
import subprocess
TOOL_VERSION = '1.02'

#-----------------------------------------------#
#----   Main                                ----#
#-----------------------------------------------#
if __name__ == '__main__':
    freeze_support() # for multiprocess with pyinstaller
    setProgramDir(getcwd())

    defaultSelectedDevice = ''
    defaultSavePCAPlog = False
    try:
        configFile = open('config.txt', 'r')
        for readLine in configFile.readlines():
            readData = readLine.split("\n")[0].split(",")
            if readData[0] == 'EthernetDevice': defaultSelectedDevice = readData[1]
            elif readData[0] == 'saveCapturePackets': defaultSavePCAPlog = int(readData[1])
        configFile.close()
    except:
        pass
        
    (mirroringDevice, selectedLogfile, savePCAPlog) = showEthernetDeviceSelectBox(defaultSelectedDevice, defaultSavePCAPlog)
    if mirroringDevice != '' or selectedLogfile != None:
        try:
            os.mkdir("logData")
        except FileExistsError:
            pass
        dateStr = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        os.mkdir('logData/{0}'.format(dateStr))
        logger = initLogger('logData/{0}/log_{0}.txt'.format(dateStr), True, LogLevel.INFO)
        logger.logPrintWithConsol('<Ver ' + TOOL_VERSION + '>')

        if mirroringDevice != '':
            task = realTimeView(
                interfaceName = mirroringDevice,
                saveCapturePackets = savePCAPlog,
                captureFileName = 'logData/{0}/{0}_ethCapture.pcap'.format(dateStr)
                )
            procList = task.start()
        elif selectedLogfile != None:
            task = drawLogFile(
                targetFiles = selectedLogfile)
            procList = task.start()
            
        configFile = open('config.txt', 'w')
        if mirroringDevice != '':
            configFile.write('EthernetDevice,{}\n'.format(mirroringDevice))
        else:
            configFile.write('EthernetDevice,{}\n'.format(defaultSelectedDevice))
        configFile.write('saveCapturePackets,{}\n'.format(int(savePCAPlog)))
        configFile.close()
    
        drawGLwindow = OpenGLWindow('Realtime Viewer v{}'.format(TOOL_VERSION), 
                                    prepareDataFunction = drawLayer,
                                    additionalDrawFunction = drawPositionPuck,
                                    drawTask = task,
                                    layerManager = LayerManager())
        drawGLwindow.mainLoop()
        
        #after close window
        task.cancel(procList)

        logger.logPrintWithConsol('All process terminated.')
        logger.close()
        subprocess.run('explorer {}\\logData\\{}'.format(getProgramDir(), dateStr))
    

    