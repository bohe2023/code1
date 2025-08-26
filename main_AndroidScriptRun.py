'''
Created on 2024/06/03

@author: AD2Gen2-19
'''
from Logger import initLogger, closeLogger
from GlobalVar import setResource, getResource, setLocal, addProcessMessageList, setRecommandLaneViewerClear, setRecommendedLaneShowTarget
setResource({})
setLocal('US') # for opengl window
from Process_AndroidScriptRun import readLogFile, getFeatureList
from threading import Thread
from datetime import datetime
import time
import os
from TypeDef import EtherID

#-----------------------------------------------#
#----   Main for test                       ----#
#-----------------------------------------------#
def readLog(resource):
    setResource(resource)
    readLogFile("sample/visionAR/2024-09-18-18-09-17-PZ1A_JPN2_AD2_V001_01ALL_20220701_115258_017.pcap", 50)
    print("Read Thread Terminated")
    
def receivePacket(resource):
    setResource(resource)
    while True:
        ret = getFeatureList()
        if (ret == None): break
        if len(ret) > 0:
            for reqItem in ret:
                messageID = reqItem[0]
                layerType = reqItem[1]
                features = reqItem[2]
                
                if messageID == EtherID.TimeStampMessage.value:
                    print(' ')
                    logTime = str(features[0].getAttributes())
                    print("logTime = {}".format(logTime))
                
                if messageID == EtherID.RecommendLaneMessage_JP.value:
                    print(' ')
                    print('[messageID={}, layerType={}] features count {}'.format(messageID, layerType, len(features)))
                    for feature in features:
                        print('feature.type={}, attribute={}, geometryList={}'.format(feature.type, feature.attribute, feature.geometryList))
#                         for geometry in feature.geometryList:
#                             print([(point.lon, point.lat, point.z) for point in geometry.pointList])

        time.sleep(0.1)
    print("Receive Thread Terminated")
        
if __name__ == '__main__':
    try:
        os.mkdir('logData')
    except FileExistsError:
        pass
    dateStr = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    os.mkdir('logData/{0}'.format(dateStr))
    initLogger('logData/{0}/log_{0}.txt'.format(dateStr), True)
    
    addProcessMessageList(0x00000501) # GNSS message. for GPS time adjust, it need.
    addProcessMessageList(0x00000110) # RecommendLaneMessage_JP, RecommendLaned
    addProcessMessageList(0x0000010a) # profile message
    addProcessMessageList(0x00000154)
    addProcessMessageList(0x00678001)
    setRecommandLaneViewerClear(False)
    setRecommendedLaneShowTarget('IVI')
    
    p1 = Thread(target=readLog, name='fileReader', args=[getResource()])
    p1.start()
            
    p2 = Thread(target=receivePacket, name='packetReceive', args=[getResource()])
    p2.start()
    
    p1.join()
    p2.join()
        
    closeLogger()
    print("Completed")
            
    
