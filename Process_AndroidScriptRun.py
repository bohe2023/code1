'''
Created on 2024/02/22

@author: Jeong
'''
from GlobalVar import getLogger, setEthernetSpecVer, setVehicleType, setADASISanalyze, getADASISanalyze, getProcessMessageList
import dpkt,socket
from dpkt.compat import compat_ord
import traceback
from MessageType import analyzeMessage, initMessage, isSegmentableMessage, DrawMode, ProfileMessage
from TypeDef import EtherID, getEtherIdDic
from PCAPLoader import TCPStream, getTcpPackets, getUdpPackets, getCANFramePacket, initPCAPLoader
from datetime import datetime, timedelta
from BLF_Eethernet import BLFEtherReader
from time import sleep
from ACSCanReader import ACSCanReader
from LayerManagerForViewer import LayerManager, Feature, FeatureType

TOOL_VERSION = "1.04"

class ADASISdrawTask():    
    def __init__(self):
        self.oldMessageDic = {}
        self.oldMessageTime = {}    
        self.latestCarPositionMessage = None
        self.latestGNSSPositionMessage = None
        self.latestIVIPositionMessage = None
        self.latestADASISPositionMessage = None
        self.latestADPositionMessage = None
        self.latestVehicleTypeValue = 0xFFFF
        self.latestPerTestAD2TestMode = 0
        self.latestCurrentLaneInfo = None
        self.currentMessageList_temporary = {}
        self.dummyLayerManager = LayerManager()
        self.logger = getLogger()
        self.logger.logPrintWithConsol('<Ver ' + TOOL_VERSION + '>')
        self.terminateFlag = False
        self.closed = False
        self.oldTick = 0
        self.processMessageList = getProcessMessageList()
        
        self.featureListIndex = 1
        self.featureListBuf1 = []
        self.featureListBuf2 = []
        
    def getFeatureList(self):
        if self.featureListIndex == 1:
            ret = self.featureListBuf2.copy()
            self.featureListBuf2.clear()
            self.featureListIndex = 2
        else:
            ret = self.featureListBuf1.copy()
            self.featureListBuf1.clear()
            self.featureListIndex = 1
        return ret
    
    def getFeatureCount(self):
        return len(self.featureListBuf1) + len(self.featureListBuf2)
    
    def terminate(self):
        self.terminateFlag = True
        
    def isClosed(self):
        return self.closed
    
    def readDataProcess(self, packets, logTime, readIndex):        
        currentMessageList = []
        for packet in packets:
            try:
                messageID = packet.header.ID             
                
#                 if messageID in [EtherID.HttpMessage.value, EtherID.SendADstatus.value]:
#                     continue
                   
                if (getEtherIdDic(messageID) != None):
                    if messageID in self.processMessageList:
                        drawFrameRate = self.processMessageList[messageID]
                    else:
                        continue
                    if drawFrameRate < 0:
                        continue
    
                    if (messageID in self.oldMessageTime) and (drawFrameRate > 0):
                        spanTime_ms = (logTime - self.oldMessageTime[messageID]).total_seconds() * 1000
                        if spanTime_ms >= 0 and spanTime_ms < drawFrameRate:
                            continue
    
                    ############ old更新 ############
                    self.oldMessageTime[messageID] = logTime
                    
                    ############ 描画Queueに保存 ############
                    try:
                        currentMessageList.append((messageID, logTime, packet.dat))
                    except Exception as e:
    #                         print('Append Error({}) : {}'.format(messageID, e))
                        pass
                        
            except Exception as e:
                self.logger.errLog("logIndex:{0}, Error:{1}".format(readIndex, e))
                self.logger.errLog(traceback.format_exc())
                
        if len(currentMessageList) > 0:
#             self.logger.logPrintWithConsol("Start analyzeFeatureProcess for {0} packets, logTime = {1}".format(len(currentMessageList), logTime))
            return self.analyzeFeatureProcess(currentMessageList)
        else:
            return []
                    
    def analyzeFeatureProcess(self, receiveDataList):
        currentMessageList = []
        
        for receiveData in receiveDataList:
            try:
                messageID = receiveData[0]
                logTime = receiveData[1]
                messageDat = receiveData[2]
                
                ############ Message解析 ############
                if messageID in self.oldMessageDic:
                    oldMessage = self.oldMessageDic[messageID]
                else:
                    oldMessage = None
                message = analyzeMessage(0, logTime, messageID, messageDat, oldMessage)
#                 self.logger.logPrintWithConsol("analyzeMessage end, messageID = {0}, logTime = {1}".format(messageID, logTime))
                if message == None:
                    continue
                
                ############ old更新 ############
                self.oldMessageDic[messageID] = message
                self.oldMessageTime[messageID] = logTime
                if logTime.second != self.oldTick:
#                     self.logger.logPrintWithConsol('analyze log point : {0}'.format(logTime))
                    feature = Feature(FeatureType.COMMAND)
                    feature.setAttributes(logTime)
                    currentMessageList.append((EtherID.TimeStampMessage.value, 0, (feature,)))
                    self.oldTick = logTime.second
                
                ############ 関連CarPosition設定 ############
                if messageID == EtherID.CarPositionMessage.value:
                    self.latestCarPositionMessage = message
                elif messageID == EtherID.GNSSDataMessage.value:
                    self.latestGNSSPositionMessage = message
                elif messageID == EtherID.ADPositionMessage.value:
                    self.latestADPositionMessage = message
                elif messageID == EtherID.RouteInfo.value or messageID == EtherID.CAN_LATLON_POS.value:
                    self.latestIVIPositionMessage = message
                elif messageID == EtherID.ADASISv2POSITION.value or messageID == EtherID.CAN_ADASISv2POSITION.value:
                    self.latestADASISPositionMessage = message
                message.setRelatedCarPositionMessage(self.latestCarPositionMessage, self.latestGNSSPositionMessage, self.latestADPositionMessage, self.latestIVIPositionMessage, self.latestADASISPositionMessage)
                                        
                ############ メッセージ別特殊処理 ############
                if messageID == EtherID.VehicleParameterMessage.value:
                    if self.latestVehicleTypeValue != message.vehicleCode:
                        self.latestVehicleTypeValue = message.vehicleCode
                        setVehicleType(message.vehicleCode)
                        feature = Feature(FeatureType.COMMAND)
                        feature.setAttributes(message.vehicleCodeStr)
                        currentMessageList.append((messageID, 0, (feature,)))
                    continue
                
                if messageID == EtherID.specificADmode.value:
                    if self.latestPerTestAD2TestMode != message.perTestAD2TestMode:
                        self.latestPerTestAD2TestMode = message.perTestAD2TestMode
                        feature = Feature(FeatureType.COMMAND)
                        feature.setAttributes(message.perTestAD2TestMode)
                        currentMessageList.append((messageID, 0, (feature,)))
                    continue
                
                if messageID == EtherID.HttpMessage.value:
                    feature = Feature(FeatureType.COMMAND)
                    feature.setAttributes(message.cmd + ' ' + message.addr)
                    currentMessageList.append((messageID, 0, (feature,)))
                    continue
                
                if messageID == EtherID.PositionMessage.value:
                    if len(message.dataArray) > 0:
                        currentPathID = message.dataArray[0].pathID
                        currentOffset = message.dataArray[0].offset
                        if currentPathID in ProfileMessage.pathIDinfoDic:
                            for (offset, endOffset, laneID) in ProfileMessage.pathIDinfoDic[currentPathID]:
                                if currentOffset >= offset and currentOffset < endOffset:
                                    if laneID in ProfileMessage.laneLinkInfoDic and laneID in ProfileMessage.laneLinkGeometryDic:
                                        laneLinkInfo = ProfileMessage.laneLinkInfoDic[laneID]
                                        laneLinkGeoInfo = ProfileMessage.laneLinkGeometryDic[laneID]
                                        currentLaneInfo = [laneID, laneLinkInfo['maxSpeed'], laneLinkInfo['roadTypeStr'], laneLinkInfo['laneTypeStr'], sum(laneLinkGeoInfo['width']) / len(laneLinkGeoInfo['width'])]
                                        if self.latestCurrentLaneInfo != currentLaneInfo:
                                            self.latestCurrentLaneInfo = currentLaneInfo
                                            feature = Feature(FeatureType.COMMAND)
                                            feature.setAttributes(currentLaneInfo)
                                            currentMessageList.append((messageID, 0, (feature,)))
                    continue
                                               
                layerGroup = self.dummyLayerManager.getLayer(messageID)
                if layerGroup == None:
                    layerGroup = message.createLayer(getEtherIdDic(messageID)['name'], self.dummyLayerManager, DrawMode.OpenGL_RealTimeDraw)
                    if layerGroup != None:
                        self.dummyLayerManager.addLayer(messageID, layerGroup)
               
                if layerGroup != None:
#                     self.logger.logPrintWithConsol("drawQGIS start, messageID = {0}, logTime = {1}".format(messageID, logTime))
                    message.drawQGIS(layerGroup, DrawMode.OpenGL_RealTimeDraw)
#                     self.logger.logPrintWithConsol("drawQGIS end")
                    
                    if messageID >= 0xCAF00000:
                        continue
                    
                    ############ 描画Queueに保存 ############
                    if isSegmentableMessage(messageID): #pipeでの頻繁な送受信はdelayとなるため、分割メッセージは、貯めてから一気に転送する。
                        for layerListItem in layerGroup:
                            if len(layerListItem[0].getFeatures()) > 0:
                                if not messageID in self.currentMessageList_temporary:
                                    self.currentMessageList_temporary[messageID] = {}
                                if not layerListItem[1] in self.currentMessageList_temporary[messageID]:
                                    self.currentMessageList_temporary[messageID][layerListItem[1]] = []
                                self.currentMessageList_temporary[messageID][layerListItem[1]] += layerListItem[0].getFeatures().copy()
                                layerListItem[0].clearFeatures()
                        if message.segmentIndex == message.segmentCount:
                            if len(self.currentMessageList_temporary) > 0:
                                for messageID in self.currentMessageList_temporary.keys():
                                    for layerType in self.currentMessageList_temporary[messageID].keys():
                                        currentMessageList.append((messageID, layerType, tuple(self.currentMessageList_temporary[messageID][layerType]))) # layerListItem[1] is layer type ID
                                self.currentMessageList_temporary.clear()
                    else:
                        for layerListItem in layerGroup:
                            if len(layerListItem[0].getFeatures()) > 0:
                                currentMessageList.append((messageID, layerListItem[1], tuple(layerListItem[0].getFeatures()))) # layerListItem[1] is layer type ID
                                layerListItem[0].clearFeatures()
    
            except:
                self.logger.errLog(traceback.format_exc())
        
#         self.logger.logPrintWithConsol("analyzeFeatureProcess end")
        return currentMessageList

class ADASISdrawTask_LogFileDraw(ADASISdrawTask):
    def __init__(self, ethernetSpecVer, targetFiles, someipmode, playSpeed):
        super().__init__()
        self.someipmode = someipmode
        self.targetFiles = targetFiles
        setEthernetSpecVer(ethernetSpecVer)
        self.playSpeed = playSpeed
        self.filter_srcMAC = []
        self.CAN_chanel_filter = None
        
    def run(self):
        global requestReadSuspend
        self.logger = getLogger() # only when subProcess started. log setup.
        logStartTime = None
        logEndTime = None
        
        startReadIndex = 0
        readIndex = 0
        baseTimeTs_gps = None
        startPoint_adjust = None
        endPoint_adjust = None
        oldTimeTs = 0
        try:
            for logFile in self.targetFiles:
                fileFullName = logFile
                fileName = fileFullName[fileFullName.rfind('/')+1:fileFullName.rfind('.')]
                expName = fileFullName[fileFullName.rfind('.')+1:]
                self.logger.logPrintWithConsol('Read File : {0}'.format(fileName))
                if expName.lower() == "pcapng":
                    reader = dpkt.pcapng.Reader(open(fileFullName,'rb'))
                elif expName.lower() == "pcap":
                    reader = dpkt.pcap.Reader(open(fileFullName,'rb'))
                elif expName.lower() == "blf":
                    reader = BLFEtherReader(open(fileFullName,'rb'), True, getADASISanalyze())
                elif expName.lower() == "asc":
                    reader = ACSCanReader(open(fileFullName))
                else:
                    self.logger.logPrintWithConsol('Unknown file format')
                    return False
                
                startReadIndex = readIndex
                criterionTime = None
                oldTime = None
                tcpstream = {}
                logTime = None
                
                try:
                    for ts, buf in reader:
                        if self.terminateFlag:
                            break
                        readIndex += 1
                        
#                         self.logger.logPrintWithConsol("Read buf : ts = " + str(ts))
    
                        if ts < oldTimeTs-10 or ts > oldTimeTs+10: #10秒以上飛んだtsが来た場合
                            baseTimeTs_gps = None
                            criterionTime = None
                        oldTimeTs = ts
                        if baseTimeTs_gps != None:
                            logTime = datetime.fromtimestamp(ts + baseTimeTs_gps)
                        else:
                            logTime = datetime.fromtimestamp(ts)
#                         print(logTime)
    
                        # *********** 時間の流れ制御 ********** #
                        currentTime = datetime.now()
                        if criterionTime == None:
                            self.logger.logPrintWithConsol("Read Start Point : " + str(logTime) + " (index = " + str(readIndex) + ")")
                            criterionTime = ts
                        else:
                            criterionTime += (currentTime - oldTime).total_seconds() * self.playSpeed
                        oldTime = currentTime
                        
                        criterionTimeLogPrinted = False
                        while (criterionTime < ts or requestReadSuspend == True):
                            if not criterionTimeLogPrinted:
#                                 self.logger.logPrintWithConsol("Wait {} sec, requestReadSuspend = {}".format(ts - criterionTime, requestReadSuspend))
                                criterionTimeLogPrinted = True
                            sleep(0.001)
                            currentTime = datetime.now()
                            criterionTime += (currentTime - oldTime).total_seconds() * self.playSpeed
                            oldTime = currentTime
                        # ************************************** #
                        
                        if buf[0:4] == b'\xFF\x0C\xAF\x00': #CANフレーム。（独自の識別子をBLF_Ethernetコード上でつけた）
                            packets = getCANFramePacket(buf[4:], self.CAN_chanel_filter)
                            
                        else: #Etherフレーム    
                            L2_layer = dpkt.ethernet.Ethernet(buf)
                            if type(L2_layer.data) != dpkt.ip.IP:
                                continue
                            
                            srcMAC = ':'.join('%02x' % compat_ord(b) for b in L2_layer.src).upper()
                            dstMAC = ':'.join('%02x' % compat_ord(b) for b in L2_layer.dst).upper()
                            
                            if len(self.filter_srcMAC) > 0:
                                if not(srcMAC in self.filter_srcMAC):
                                    continue
                                
                            L3_layer = L2_layer.data
                            if type(L3_layer) != dpkt.ip.IP: #ipv4
                                continue
                    
                            src = socket.inet_ntoa( L3_layer.src )
                            to  = socket.inet_ntoa( L3_layer.dst )
                            
                            if str(src) == "0.0.0.0": #DHCP
                                continue
                                
                            L4_layer = L3_layer.data
                            if (type(L4_layer) != dpkt.tcp.TCP and type(L4_layer) != dpkt.udp.UDP):
                                continue
                            
                            toInfo = "{0}({1}):{2}".format(to,dstMAC,L4_layer.dport)
                            
                            if type(L4_layer) == dpkt.udp.UDP:
                                (packets, _) = getUdpPackets(L4_layer.data, self.someipmode, useSomeIPfilter = True)
                    
                            else:
                                if not(toInfo in tcpstream):
                                    tcpstream[toInfo] = TCPStream()
                                
                                if tcpstream[toInfo].recv(L4_layer, ts) == 0:
                                    continue
                    
                                # separate and remains into tcpDataBuf
                                (packets, remains) = getTcpPackets(tcpstream[toInfo].get(), self.someipmode, useSomeIPfilter = True)
                                tcpstream[toInfo].setRemains(remains)
                
                        # ログ時間範囲
                        if baseTimeTs_gps == None:
                            if logStartTime == None or logStartTime > logTime:
                                logStartTime = logTime
                            if logEndTime == None or logEndTime < logTime:
                                logEndTime = logTime
                        else:
                            # baseTimeTs_gps を基準にしたログ時間範囲も取っておく
                            if startPoint_adjust == None or startPoint_adjust > logTime:
                                startPoint_adjust = logTime
                            if endPoint_adjust == None or endPoint_adjust < logTime:
                                endPoint_adjust = logTime
                            logStartTime = startPoint_adjust
                            logEndTime = endPoint_adjust
                        
                        if (len(packets) > 0):
                            if baseTimeTs_gps == None:
                                for packet in packets:
                                    messageID = packet.header.ID
                                    if messageID == EtherID.GNSSDataMessage.value:
                                        message = analyzeMessage(readIndex, datetime.fromtimestamp(ts), messageID, packet.dat)
                                        if message != None and message.year != 0xFFFF:
                                            firstGNSStime = datetime(message.year, message.month, message.day, message.hour, message.min, message.sec)
                                            baseTimeTs_gps = datetime.timestamp(firstGNSStime) - ts
                                            self.logger.logPrintWithConsol("Log time adjust from GNSS time {0}".format(firstGNSStime))
        
#                             self.logger.logPrintWithConsol("Read {0} packets, logTime = {1}".format(len(packets), logTime))
                            features = self.readDataProcess(packets, logTime, readIndex)
                            if len(features) > 0:
                                if self.featureListIndex == 1:
                                    self.featureListBuf1 += features
                                else:
                                    self.featureListBuf2 += features
#                                 sleep(0.001) # playtimeを1倍速より大きく設定した場合に、receive threadが実行できないことを防ぐため、一定間隔でsend threadを10msだけsleepさせる。
                
                except Exception as e:
                    self.logger.errLog("<Process Error> FilelogIndex:{0}, Error:{1}".format(readIndex-startReadIndex, e))
                    self.logger.errLog(traceback.format_exc())
                    self.logger.logPrintWithConsol('  (logfile error detected. But ignore and read next log file.)')
                    
                if logTime != None:
                    self.logger.logPrintWithConsol("Read End Point   : " + str(logTime) + " (index = " + str(readIndex) + ")")
                else:
                    self.logger.logPrintWithConsol("Read End Point   : -- (index = " + str(readIndex) + ")")
                self.logger.flush()
                #memory management
                del reader
            
            if self.terminateFlag:
                self.logger.logPrintWithConsol('Read terminated.')
            else:
                self.logger.logPrintWithConsol('All read complete. StartLogTime={}, EndLogTime={}'.format(str(logStartTime), str(logEndTime)))  
                    
        except:
            self.logger.errLog(traceback.format_exc())
        
        self.closed = True
    

reader = None
requestReadSuspend = False

def readSuspend():
    global requestReadSuspend
    requestReadSuspend = True
    
def readResume():
    global requestReadSuspend
    requestReadSuspend = False

def readLogFile(targetFiles = None, playSpeed = 1.0, someipmode = True, ethernetSpecVer = None):    
    global reader
    if ethernetSpecVer == None:
        ethernetSpecVer = datetime(9999, 12, 31) #always new specsheet
    if targetFiles == None:
        return None, None
    elif type(targetFiles) == str:
        targetFiles = [targetFiles]
    else:
        targetFiles = list(targetFiles)
    
    initPCAPLoader(False)
    initMessage()
    setADASISanalyze(False)
    
    reader = ADASISdrawTask_LogFileDraw(ethernetSpecVer, targetFiles, someipmode, playSpeed)
    reader.run()

def getFeatureCount():
    global reader
    if (reader == None): return 0
    else: return reader.getFeatureCount()
        
def getFeatureList():
    global reader
    if (reader == None): return set()
    elif (reader.getFeatureCount() == 0 and reader.isClosed()): return None
    else: return reader.getFeatureList()
        
def terminate():
    global reader
    if (reader == None): return
    reader.terminate()
    while (reader.isClosed() == False):
        sleep(0.1)
    reader = None
    