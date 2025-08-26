'''
Created on 2024/02/22

@author: Jeong
'''
from GlobalVar import getResource, setResource, getLogger
from GlobalVar import setEthernetSpecVer, setSrcMAC, setVehicleType, setADASISanalyze, getADASISanalyze, setRecommandLaneViewerClear, setRecommendedLaneShowTarget
from multiprocessing import Process, Manager, Queue
from openGL_window import OpenGLWindow
import dpkt,socket
from dpkt.compat import compat_ord
import traceback
from MessageType import analyzeMessage, createLayer, initMessage, isSegmentableMessage, DrawMode, ProfileMessage, SendADstatus, RecommendLaneMessage, GNSSDataMessage, ADPositionMessage, CarPositionMessage, ADASISv2SEGMENT
from TypeDef import EtherID, getEtherIdDic, VehicleCodeTable
from PCAPLoader import TCPStream, getTcpPackets, getUdpPackets, getCANFramePacket, initPCAPLoader
from datetime import datetime, timedelta
from Logger import loadLogger
from BLF_Eethernet import BLFEtherReader
from time import sleep
from ACSCanReader import ACSCanReader
from LayerManagerForViewer import LayerManager, Feature, FeatureType
import tkinter
from tkinter import messagebox
import math
import sys
from enum import Enum, auto

class ADASISdrawTask():
    def __init__(self):
        self.logStartTime = None
        self.logEndTime = None
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
        self.currentMessageList = []
        self.currentMessageList_temporary = {}
        self.oldTick = 0

        # for shared data (low speed. so, just only use sharing data between multiProcess)
        self.params = {}
        self.interProcConn = Queue()
        self.conn = Queue()
        manager = Manager()
        self.control = manager.dict()
        self.control['showMessageStr'] = ''
        self.control['processCancel'] = False
#         self.control['layerRegisterReq'] = False
#         self.control['layerRegisterRes'] = False
        
        sys.setrecursionlimit(10000)
#         sys.setrecursionlimit(1024*1024*1024) #1GB
#         threading.stack_size(64*1024*1024)

    def start(self):
        logger = getLogger()
        try:
            self.params['interProcConn'] = self.interProcConn
            self.params['conn'] = self.conn
            
            process_featureAnalyz = Process(target=self.analyzeFeatureProcess, name='featureAnalyzer', args=[getResource(), self.control, self.params])
            if process_featureAnalyz != None: process_featureAnalyz.start()
            process_read = Process(target=self.run, name='reader', args=[getResource(), self.control, self.params])
            if process_read != None: process_read.start()
            
            return [process_featureAnalyz, process_read]
            
        except Exception as e:
            logger.errLog("<Process Start Error> Error:{}".format(e))
            logger.errLog(traceback.format_exc())
            return []
        
    def isCanceled(self):
        return self.control['processCancel']
    
    def finish(self):
        while (self.isCanceled() == False):
            sleep(1)
        while not self.interProcConn.empty():
            (self.interProcConn.get())
        while not self.conn.empty():
            (self.conn.get())
        
    def getLayerRegisterBuf(self):
        try:
            result = self.conn.get(False, 0)
            return result
        except Exception:
            #print('Receive Queue Error : {}'.format(e))
            return []

    def readDataProcess(self, packets, logTime, readIndex): 
        logger = getLogger()
        for packet in packets:
            try:
                messageID = packet.header.ID                
                if (getEtherIdDic(messageID) != None) and (len(self.filter_messageID) == 0 or (messageID in self.filter_messageID)):
                    if 'implementOpenGLdraw' in getEtherIdDic(messageID):
                        drawFrameRate = getEtherIdDic(messageID)['implementOpenGLdraw']
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
                        self.currentMessageList.append([messageID, logTime, packet.dat])
                    except Exception as e:
#                         print('Append Error({}) : {}'.format(messageID, e))
                        pass
                        
            except Exception as e:
                logger.errLog("logIndex:{0}, Error:{1}".format(readIndex, e))
                logger.errLog(traceback.format_exc())
                
        if len(self.currentMessageList) > 0:
            try:
                self.interProcConn.put(self.currentMessageList.copy(), False, 0)
                self.currentMessageList.clear()
            except Exception as e:
                #print('Send Queue Error : {}'.format(e))
                pass
                
    def analyzeFeatureProcess(self, resource, control, params):
        sys.setrecursionlimit(10000)
        
        setResource(resource)
        self.control = control #変数共有のため
        self.interProcConn = params['interProcConn']
        self.conn = params['conn']
        self.ethernetSpecVer = params['ethernetSpecVer']
        
        logger = loadLogger() # only when subProcess started. log setup.
        initPCAPLoader(False)
        initMessage()
        setEthernetSpecVer(self.ethernetSpecVer)
        
        dummyLayerManager = LayerManager()
        
        while (True):
            if self.isCanceled():
                break
            
            # receive Data
            try:
                receiveDataList = self.interProcConn.get(False, 0)
            except Exception:
                #print('Receive Queue Error')
                receiveDataList = []
                
            if len(receiveDataList) == 0:
                continue
            
            #print('receive data : {}'.format(len(receiveDataList)))
            
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
                    if message == None:
                        continue
                    
                    ############ old更新 ############
                    self.oldMessageDic[messageID] = message
                    self.oldMessageTime[messageID] = logTime
                    if logTime.second != self.oldTick:
                        feature = Feature(FeatureType.COMMAND)
                        feature.setAttributes(logTime)
                        self.currentMessageList.append([EtherID.TimeStampMessage.value, 0, [feature]])
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
                            self.currentMessageList.append([messageID, 0, [feature]])
                        continue
                    
                    if messageID == EtherID.specificADmode.value:
                        if self.latestPerTestAD2TestMode != message.perTestAD2TestMode:
                            self.latestPerTestAD2TestMode = message.perTestAD2TestMode
                            feature = Feature(FeatureType.COMMAND)
                            feature.setAttributes(message.perTestAD2TestMode)
                            self.currentMessageList.append([messageID, 0, [feature]])
                        continue
                    
                    if messageID == EtherID.HttpMessage.value:
                        feature = Feature(FeatureType.COMMAND)
                        feature.setAttributes(message.cmd + ' ' + message.addr)
                        self.currentMessageList.append([messageID, 0, [feature]])
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
                                            currentLaneInfo = (laneID, laneLinkInfo['maxSpeed'], laneLinkInfo['roadTypeStr'], laneLinkInfo['laneTypeStr'], sum(laneLinkGeoInfo['width']) / len(laneLinkGeoInfo['width']))
                                            if self.latestCurrentLaneInfo != currentLaneInfo:
                                                self.latestCurrentLaneInfo = currentLaneInfo
                                                feature = Feature(FeatureType.COMMAND)
                                                feature.setAttributes(currentLaneInfo)
                                                self.currentMessageList.append([messageID, 0, [feature]])
                        continue
                                                   
                    layerGroup = dummyLayerManager.getLayer(messageID)
                    if layerGroup == None:
                        layerGroup = message.createLayer(getEtherIdDic(messageID)['name'], dummyLayerManager, DrawMode.OpenGL_RealTimeDraw)
                        if layerGroup != None:
                            dummyLayerManager.addLayer(messageID, layerGroup)
                   
                    if layerGroup != None:
                        message.drawQGIS(layerGroup, DrawMode.OpenGL_RealTimeDraw)
                        
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
                                            self.currentMessageList.append([messageID, layerType, self.currentMessageList_temporary[messageID][layerType]]) # layerListItem[1] is layer type ID
                                    self.currentMessageList_temporary.clear()
                        else:
                            for layerListItem in layerGroup:
                                if len(layerListItem[0].getFeatures()) > 0:
                                    self.currentMessageList.append([messageID, layerListItem[1], layerListItem[0].getFeatures().copy()]) # layerListItem[1] is layer type ID
                                    layerListItem[0].clearFeatures()

                except:
                    logger.errLog(traceback.format_exc())
                    
            if len(self.currentMessageList) > 0:
                try:
                    self.conn.put(self.currentMessageList.copy(), False, 0)
                    self.currentMessageList.clear()
                except Exception:
                    #print('Send Queue Error : {}'.format(e))
                    pass
                
        self.finish()
        logger.logPrint('terminate process')
        logger.flush()
        return True
        
class ADASISdrawTask_LogFileDraw(ADASISdrawTask):
    def __init__(self, ethernetSpecVer, targetFiles,  startPoint, endPoint, filter_srcMAC, filter_messageID, CAN_chanel_filter, someipmode):
        super().__init__()
        self.targetFiles = targetFiles
        fileFullName = targetFiles[0]
        self.fileName = fileFullName[fileFullName.rfind('/')+1:fileFullName.rfind('.')]
        
        self.params['ethernetSpecVer'] = ethernetSpecVer
        self.params['targetFiles'] = targetFiles
        self.params['filter_srcMAC'] = filter_srcMAC
        self.params['startPoint'] = startPoint
        self.params['endPoint'] = endPoint
        self.params['filter_messageID'] = filter_messageID
        self.params['CAN_chanel_filter'] = CAN_chanel_filter
        self.params['someipmode'] = someipmode
        
    def run(self, resource, control, params):
        sys.setrecursionlimit(10000)
#         sys.setrecursionlimit(1024*1024*1024) #1GB
#         threading.stack_size(64*1024*1024)
        
        setResource(resource)
        self.control = control #変数共有のため
        self.interProcConn = params['interProcConn']
        self.targetFiles = params['targetFiles']
        self.filter_srcMAC = params['filter_srcMAC']
        self.showFilterStartPoint = params['startPoint']
        self.showFilterEndPoint = params['endPoint']
        self.filter_messageID = params['filter_messageID']
        self.CAN_chanel_filter = params['CAN_chanel_filter']
        self.someipmode = params['someipmode']
        playSpeed = 10.0
        
        logger = loadLogger() # only when subProcess started. log setup.
        setSrcMAC(','.join(self.filter_srcMAC))

        startReadIndex = 0
        readIndex = 0
        baseTimeTs_gps = None
        startPoint_adjust = None
        endPoint_adjust = None
        gpsTimeExist = False
        oldTimeTs = 0
        try:
            for logFile in self.targetFiles:
                fileFullName = logFile
                self.fileName = fileFullName[fileFullName.rfind('/')+1:fileFullName.rfind('.')]
                expName = fileFullName[fileFullName.rfind('.')+1:]
                self.control['showMessageStr'] = 'Now on file load... (File: ' + self.fileName + ')'
                logger.logPrintWithConsol('Draw File : {0}'.format(self.fileName))
                if expName.lower() == "pcapng":
                    reader = dpkt.pcapng.Reader(open(fileFullName,'rb'))
                elif expName.lower() == "pcap":
                    reader = dpkt.pcap.Reader(open(fileFullName,'rb'))
                elif expName.lower() == "blf":
                    reader = BLFEtherReader(open(fileFullName,'rb'), True, getADASISanalyze())
                elif expName.lower() == "asc":
                    reader = ACSCanReader(open(fileFullName))
                else:
                    logger.logPrintWithConsol('Unknown file format')
                    return False
                
                startReadIndex = readIndex
                criterionTime = None
                oldTime = None
                tcpstream = {}
                logTime = None
                
                try:
                    for ts, buf in reader:
                        readIndex += 1
                        if readIndex & 0xFFF == 0xFFF:
                            if self.isCanceled():
                                break
    
                        if oldTimeTs != 0 and (ts < oldTimeTs-10 or ts > oldTimeTs+10): #10秒以上飛んだtsが来た場合
                            baseTimeTs_gps = None
                            criterionTime = None #ログを飛ばす分、時間描画基準点をリセットする。
                            logger.logPrintWithConsol("Log timestamp jump detected (timestamp:{}) (logIndex:{})".format(
                                str(datetime.fromtimestamp(ts if baseTimeTs_gps == None else ts + baseTimeTs_gps)),
                                readIndex))
                        oldTimeTs = ts
                        if baseTimeTs_gps != None:
                            ts = ts + baseTimeTs_gps
    
                        #indexによる描画区間制御
                        if self.showFilterStartPoint != None and type(self.showFilterStartPoint) == type(readIndex):
                            if readIndex < self.showFilterStartPoint:
                                criterionTime = None #ログを飛ばす分、時間描画基準点をリセットする。
                                if readIndex & 0xFFF == 0xFFF:
                                    logTime = datetime.fromtimestamp(ts)
                                    self.control['showMessageStr'] = "Now on search start point..." + " , logTime = [ " + str(logTime) + " ] , logIndex = ( " + str(readIndex) + " )"
                                continue
                        if self.showFilterEndPoint != None and type(self.showFilterEndPoint) == type(readIndex):
                            if readIndex > self.showFilterEndPoint:
                                break
                        
                        logTime = datetime.fromtimestamp(ts)
                        #時間による描画区間制御 (GNSS時間取得前はできない)
                        if baseTimeTs_gps != None:
                            if self.showFilterStartPoint != None and type(self.showFilterStartPoint) == type(logTime):
                                if logTime < self.showFilterStartPoint:
                                    criterionTime = None #ログを飛ばす分、時間描画基準点をリセットする。
                                    if readIndex & 0xFFF == 0xFFF:
                                        self.control['showMessageStr'] = "Now on search start point..." + " , logTime = [ " + str(logTime) + " ] , logIndex = ( " + str(readIndex) + " )"
                                    continue
                            if self.showFilterEndPoint != None and type(self.showFilterEndPoint) == type(logTime):
                                if logTime > self.showFilterEndPoint:
                                    break
                                         
                        # *********** 時間の流れ制御 ********** #
                        currentTime = datetime.now()
                        if criterionTime == None:
                            logger.logPrintWithConsol("Draw Start Point : " + str(logTime) + " (index = " + str(readIndex) + ")")
                            criterionTime = logTime
                        else:
                            criterionTime += (currentTime - oldTime) * playSpeed
                        oldTime = currentTime
                        
                        while (criterionTime < logTime):
                            if self.isCanceled():
                                break
                            sleep(0.1)
                            currentTime = datetime.now()
                            criterionTime += (currentTime - oldTime) * playSpeed
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
                                (packets, _) = getUdpPackets(L4_layer.data, self.someipmode)
                    
                            else:
                                if not(toInfo in tcpstream):
                                    tcpstream[toInfo] = TCPStream()
                                
                                if tcpstream[toInfo].recv(L4_layer, ts) == 0:
                                    continue
                    
                                # separate and remains into tcpDataBuf
                                (packets, remains) = getTcpPackets(tcpstream[toInfo].get(), self.someipmode)
                                tcpstream[toInfo].setRemains(remains)
                
                        # ログ時間範囲
                        if gpsTimeExist == False:
                            if self.logStartTime == None or self.logStartTime > logTime:
                                self.logStartTime = logTime
                            if self.logEndTime == None or self.logEndTime < logTime:
                                self.logEndTime = logTime
                        else:
                            if baseTimeTs_gps != None:
                                # baseTimeTs_gps を基準にしたログ時間範囲も取っておく
                                if startPoint_adjust == None or startPoint_adjust > logTime:
                                    startPoint_adjust = logTime
                                if endPoint_adjust == None or endPoint_adjust < logTime:
                                    endPoint_adjust = logTime
                                self.logStartTime = startPoint_adjust
                                self.logEndTime = endPoint_adjust
                        
                        if baseTimeTs_gps == None:
                            for packet in packets:
                                messageID = packet.header.ID
                                if messageID == EtherID.GNSSDataMessage.value:
                                    message = analyzeMessage(readIndex, datetime.fromtimestamp(ts), messageID, packet.dat)
                                    if message != None and message.year != 0xFFFF:
                                        firstGNSStime = datetime(message.year, message.month, message.day, message.hour, message.min, message.sec)
                                        baseTimeTs_gps = datetime.timestamp(firstGNSStime) - ts
                                        logger.logPrintWithConsol("Log time adjust from GNSS time {0}".format(firstGNSStime))
                                        gpsTimeExist = True
                                        if criterionTime != None:
                                            criterionTime += timedelta(seconds=baseTimeTs_gps)
                                            logger.logPrintWithConsol("Draw Start Point : " + str(criterionTime) + " (index = " + str(readIndex) + ")")
    
                        self.readDataProcess(packets, logTime, readIndex)
                
                except Exception as e:
                    logger.errLog("<Process Error> FilelogIndex:{0}, Error:{1}".format(readIndex-startReadIndex, e))
                    logger.errLog(traceback.format_exc())
                    logger.logPrintWithConsol('  (logfile error detected. But ignore and read next log file.)')
                    
                if logTime != None:
                    logger.logPrintWithConsol("Draw End Point   : " + str(logTime) + " (index = " + str(readIndex) + ")")
                else:
                    logger.logPrintWithConsol("Draw End Point   : -- (index = " + str(readIndex) + ")")
                logger.flush()
                #memory management
                del reader
                
                if self.isCanceled():
                    break
            
            logger.logPrintWithConsol('All read complete. StartLogTime={}, EndLogTime={}'.format(str(self.logStartTime), str(self.logEndTime)))  
                    
        except:
            logger.errLog(traceback.format_exc())
                
        self.finish()
        logger.logPrint('terminate process')
        logger.flush()
        return True
    
    def cancel(self, processList):
        self.control['processCancel'] = True
        for proc in processList:
            if (proc != None):
                proc.join(3)

class ADASISdrawTask_RealTimeDraw(ADASISdrawTask):
    def __init__(self, ethernetSpecVer, interfaceName, filter_srcMAC, filter_messageID, someipmode, saveCapturePackets, captureFileName):
        super().__init__()
        self.fileName = str(datetime.now())
        self.readIndex = 0
        self.lastPacketReceivedTime = None
        self.restart = False
        self.outputPCAPfile = None
        
        self.filter_srcMAC = filter_srcMAC
        self.interfaceName = interfaceName
        self.params['ethernetSpecVer'] = ethernetSpecVer
        self.params['filter_srcMAC'] = filter_srcMAC
        self.params['filter_messageID'] = filter_messageID
        self.params['interfaceName'] = interfaceName
        self.params['someipmode'] = someipmode
        self.params['saveCapturePackets'] = saveCapturePackets
        self.params['captureFileName'] = captureFileName
        
    def pkt_callback(self, pkt):
        from scapy import all as scapy
        self.readIndex += 1
        currentTime = datetime.now()
        if self.lastPacketReceivedTime == None:
            self.lastPacketReceivedTime = currentTime
        elif (currentTime - self.lastPacketReceivedTime).total_seconds() >= 3:
            #3秒以上、間隔を開けてパケットを受信したケース。
            #途中で通信が途切れていた可能性あり。キャプチャを再起動(再起動しないとなぜか一部のパケットを受信できない場合があった)
            #現在の時刻は以下で保存、再起動は3秒以内で終わるはずなので、無限再起動はしない。
            self.restart = True
        self.lastPacketReceivedTime = currentTime
        
        try:
            if self.saveCapturePackets: 
                ts = currentTime.timestamp()
                if self.outputPCAPfile == None:
                    logger = getLogger()
                    try:
                        self.outputPCAPfile = dpkt.pcap.Writer(open(self.captureFileName, 'wb'))
                        logger.logPrint('make ethernet capture file : {}'.format(self.captureFileName))
                    except Exception as e:
                        self.saveCapturePackets = False
                        self.outputPCAPfile = None
                        logger.errLog('Cannot save ethernet capture file : {}'.format(e))
                        
                if self.outputPCAPfile == None:
                    self.outputPCAPfile.writepkt(pkt, ts)
            
            data = pkt[scapy.Raw].load
            (packets, _) = getUdpPackets(data, self.someipmode, onlyReadFirstMessage = True)
            if len(packets) > 0:
                self.fileName = str(currentTime)
                self.readDataProcess(packets, currentTime, self.readIndex)
                if self.logStartTime == None:
                    self.logStartTime = currentTime
                self.logEndTime = currentTime
        except:
            pass     
    
    def run(self, resource, control, params):
        sys.setrecursionlimit(10000)
        from scapy import all as scapy
#         sys.setrecursionlimit(1024*1024*1024) #1GB
#         threading.stack_size(64*1024*1024)
        
        setResource(resource)
        self.control = control #変数共有のため
        self.interProcConn = params['interProcConn']
        self.interfaceName = params['interfaceName']
        self.filter_srcMAC = params['filter_srcMAC']
        self.filter_messageID = self.params['filter_messageID']
        self.someipmode = params['someipmode']
        self.saveCapturePackets = self.params['saveCapturePackets']
        self.captureFileName = self.params['captureFileName']
        
        logger = loadLogger() # only when subProcess started. log setup.
        setSrcMAC(','.join(self.filter_srcMAC))
        
        while (True):
            filterRule = '(udp or tcp)'
            if len(self.filter_srcMAC) > 0:
                filterRule += ' and ('
                for i in range(len(self.filter_srcMAC)):
                    if i > 0:
                        filterRule += ' or '
                    filterRule += 'ether src ' + self.filter_srcMAC[i]
                filterRule += ')'
            logger.logPrintWithConsol('start sniff [{0}] : {1}'.format(self.interfaceName,filterRule))
            logger.flush()
            
            try:
                scapy.sniff(iface=self.interfaceName, prn=self.pkt_callback, filter=filterRule, store=0, stop_filter=lambda p: (self.isCanceled() or self.restart == True))
            except Exception as e:
                self.control['showMessageStr'] = 'CaptureError'
                logger.errLog('Cannot start ethernet capture : {}'.format(e.args[0].decode("UTF-8")))
                root = tkinter.Tk() # make hide tkinter window for message box.
                root.withdraw()
                messagebox.showerror(title='Error', message='<Cannot start ethernet capture>\n{}'.format(e.args[0].decode("UTF-8")))
                root.quit()
                root.destroy()
        
            if self.restart == True:
                logger.logPrintWithConsol('retry...')
                self.restart = False
            else:
                if (self.saveCapturePackets) and (self.outputPCAPfile != None):
                    self.outputPCAPfile.close()
                    logger.logPrint('close ethernet capture file')
                self.finish()
                logger.logPrint('terminate process')
                logger.flush()
                return True
            
    def cancel(self, processList):
        self.control['processCancel'] = True
        
        if self.control['showMessageStr'] != 'CaptureError':
            from scapy import all as scapy
            try:
                # realTime Viewモードの場合は、終了時、任意のパケットが一つキャプチャー必要
                if len(self.filter_srcMAC) > 0:
                    scapy.sendp(scapy.Ether(src=self.filter_srcMAC[0],dst='00:00:00:00:00:00')/scapy.IP()/scapy.UDP(), iface=self.interfaceName, verbose=False)
                else:
                    scapy.sendp(scapy.Ether(src='AA:BB:CC:DD:00:06',dst='00:00:00:00:00:00')/scapy.IP()/scapy.UDP(), iface=self.interfaceName, verbose=False)
            except:
                pass
        
        for proc in processList:
            if (proc != None):
                proc.join(3)

def drawLogFile(targetFiles = None, startPoint = None, endPoint = None, someipmode = True, filter_srcMAC = None, filter_messageID = None, CAN_chanel_filter = None, ethernetSpecVer = None):
    if filter_srcMAC == None:
        filter_srcMAC = []
    if filter_messageID == None:
        filter_messageID = []
    if ethernetSpecVer == None:
        ethernetSpecVer = datetime(9999, 12, 31) #always new specsheet
    if targetFiles == None:
        return None, None
    if type(targetFiles) != type([]):
        targetFiles = [targetFiles]
    
    setADASISanalyze(True)
    setRecommandLaneViewerClear(True)
    setRecommendedLaneShowTarget('IVI')
    drawTask = ADASISdrawTask_LogFileDraw(ethernetSpecVer, targetFiles, startPoint, endPoint, filter_srcMAC, filter_messageID, CAN_chanel_filter, someipmode)
    return drawTask

def realTimeView(interfaceName = None, someipmode = True, filter_srcMAC = None, filter_messageID = None, ethernetSpecVer = None, saveCapturePackets = False, captureFileName = None): 
    if filter_srcMAC == None:
        filter_srcMAC = ["AA:BB:CC:DD:00:06", "AA:BB:CC:DD:10:06", "AA:BB:CC:DD:00:0C", "AA:BB:CC:DD:00:17", "AA:BB:CC:DD:00:03"] #ADAS , ADAS2 , HDMAP , FrCamera2 , IVC
    if filter_messageID == None:
        filter_messageID = []
    if ethernetSpecVer == None:
        ethernetSpecVer = datetime(9999, 12, 31) #always new specsheet
    
    setRecommandLaneViewerClear(True)
    setRecommendedLaneShowTarget('IVI')
    drawTask = ADASISdrawTask_RealTimeDraw(ethernetSpecVer, interfaceName, filter_srcMAC, filter_messageID, someipmode, saveCapturePackets, captureFileName)
    return drawTask

lastPositionInfo = {}
nowOnHDMAP = False
propilotInfo = ''
vehicleCodeStr = ''
logTime = ''
view_lastValidZ = 0
class ViewTextLine(Enum):
    GNSS_Location = auto()
    RDR_license = auto()
    RDR_adstatus = auto()
    RDR_TSR = auto()
    RDR_laneProjection = auto()
    RDR_SDMapInfo = auto()
    RDR_handsoffProhibitReason = auto()
    RDR_cancelCode = auto()
    RDR_nd2Code = auto()
    RDR_mapDTC = auto()
    specificADmode = auto()

def adjustZ(zValue):
    global view_lastValidZ
    if zValue > 2000000: # [m] AD PositionのDRによる高さ変動も考慮し、2000000 [m]以上を無効とする。 (invalid z value = 0x7FFFFFFF mm)
        return view_lastValidZ
    else:
        view_lastValidZ = zValue
        return zValue

def drawLayer(drawGLwindow, drawTask, layerManager):
    global lastPositionInfo
    global nowOnHDMAP
    global propilotInfo
    global vehicleCodeStr
    global logTime
    
    reqList = drawTask.getLayerRegisterBuf()
    if len(reqList) == 0:
        return

    logger = getLogger()
    for reqItem in reqList:
        try:
            messageID = reqItem[0]
            layerType = reqItem[1]
            features = list(reqItem[2])
                
            ###################################################
            ############ 特別処理 (描画レイヤーがないもの) ############
            ###################################################
            
            if messageID == EtherID.TimeStampMessage.value:
                for feature in features:
                    if feature.type == FeatureType.COMMAND:
                        logTime = str(feature.getAttributes()[0])
                continue # 描画には登録せずにスキップ
            
            if messageID == EtherID.VehicleParameterMessage.value:
                for feature in features:
                    if feature.type == FeatureType.COMMAND:
                        vehicleCode = feature.getAttributes()[0]
                        setVehicleType(vehicleCode)
                        vehicleCodeStr = VehicleCodeTable.get(vehicleCode, 'Unknown')
                        logger.logPrintWithConsol('VehicleCode detected = {}'.format(vehicleCodeStr))
                continue # 描画には登録せずにスキップ
            
            if messageID == EtherID.HttpMessage.value:
                for feature in features:
                    if feature.type == FeatureType.COMMAND:
                        response = feature.getAttributes()[0]
                        drawGLwindow.drawText_bottom(0, 'MAPECU <-> vNext : ' + response, 0.4, OpenGLWindow.Color_DiffuseGray)
                        if '<license_status>' in response: #JP
                            sI = response.find('>', response.find('<license_status>', 0))+1
                            eI = response.find('</license_status>', sI)
                            propilot_license_status = response[sI:eI]
                            sI = response.find('>', response.find('<expire_month>', eI))+1
                            eI = response.find('</expire_month>', sI)
                            propilot_expire_month = response[sI:eI]
                            propilotInfo = 'license_status : {} , expire_date : {}'.format(propilot_license_status, propilot_expire_month)
                        elif '"license_status"' in response: #US
                            sI = response.find(':', response.find('"license_status"', 0))+1
                            eI = response.find(',', sI)
                            propilot_license_status = response[sI:eI]
                            sI = response.find(':', response.find('"expiration_date"', eI))+1
                            eI = response.find('}', sI)
                            propilot_expire_month = response[sI:eI]
                            propilotInfo = 'license_status : {} , expire_date : {}'.format(propilot_license_status, propilot_expire_month)
                        
                continue # 描画には登録せずにスキップ
            
            if messageID == EtherID.specificADmode.value:
                for feature in features:
                    if feature.type == FeatureType.COMMAND:
                        if feature.getAttributes()[0] == 1:
                            drawGLwindow.drawText(ViewTextLine.specificADmode.value, 'Factory Mode <ON>', 0.4, OpenGLWindow.Color_DiffuseSG)
                        else:
                            drawGLwindow.drawText(ViewTextLine.specificADmode.value, '', 0, None)
                continue # 描画には登録せずにスキップ
            
            if messageID == EtherID.PositionMessage.value:
                for feature in features:
                    if feature.type == FeatureType.COMMAND:
                        if nowOnHDMAP == True:
                            attr = feature.getAttributes()[0]
                            drawGLwindow.drawText(ViewTextLine.RDR_laneProjection.value, '[HDMAP] On HDMAP , <SpdLim>: {} km/h , <RoadType>:{} , <LinkType>:{} , <LaneWidth>:{:,.2f} m'.format(
                                attr[1], attr[2], attr[3], attr[4]), 0.4, OpenGLWindow.Color_DiffuseSB)
                        else:
                            drawGLwindow.drawText(ViewTextLine.RDR_laneProjection.value, '[HDMAP] Off HDMAP', 0.4, OpenGLWindow.Color_DiffuseSR)
                continue # 描画には登録せずにスキップ

            ################################
            ############ 描画処理 ############
            ################################
            layer = layerManager.getLayerFromLayerTypeID(layerType)
            if layer == None:
                newLayerGroup = createLayer(messageID, layerManager, DrawMode.OpenGL_RealTimeDraw)
                if newLayerGroup != None:
                    layerManager.addLayer(messageID, newLayerGroup)
                    layer = layerManager.getLayerFromLayerTypeID(layerType)
            if layer == None:
                continue
            
            ############ 位置処理 ############
            if layerType == GNSSDataMessage.LayerType.GNSS_Location.value:
                loc = features[0].geometryList[0].pointList[1]
                if not 'AD' in lastPositionInfo or (datetime.now() - lastPositionInfo['AD'][2]).total_seconds() > 3.0:
                    drawGLwindow.setViewTargetLonLatZ(loc.lon, loc.lat, adjustZ(loc.z))
                if 'GNSS' in lastPositionInfo:
                    lastLoc = lastPositionInfo['GNSS'][0]
                    bearing = math.atan2(loc.lat - lastLoc.lat,
                                         loc.lon - lastLoc.lon)
                    lastPositionInfo['GNSS-old'] = lastPositionInfo['GNSS']
                    lastPositionInfo['GNSS'] = (loc, bearing, datetime.now())
                else:
                    lastPositionInfo['GNSS'] = (loc, 0, datetime.now())
                    lastPositionInfo['GNSS-old'] = lastPositionInfo['GNSS']
                #lastPositionInfo['GNSS'] = (loc, features[0].attribute[layer.indexFromName('bearing')]) #bearing : deg
                drawGLwindow.drawText(ViewTextLine.GNSS_Location.value, 'GNSS Lon/Lat : ({:,.4f} , {:,.4f}) [logTime : {}]'.format(loc.lon, loc.lat, logTime), 0.4, OpenGLWindow.Color_DiffuseSR)
                
            if (layerType == ADPositionMessage.LayerType.ADPosition.value):
                loc = features[0].geometryList[0].pointList[1]
                drawGLwindow.setViewTargetLonLatZ(loc.lon, loc.lat, adjustZ(loc.z))
                if 'AD' in lastPositionInfo:
                    lastLoc = lastPositionInfo['AD'][0]
                    bearing = math.atan2(loc.lat - lastLoc.lat,
                                         loc.lon - lastLoc.lon)
                    lastPositionInfo['AD-old'] = lastPositionInfo['AD']
                    lastPositionInfo['AD'] = (loc, bearing, datetime.now())
                else:
                    lastPositionInfo['AD'] = (loc, 0, datetime.now())
                    lastPositionInfo['AD-old'] = lastPositionInfo['AD']
                
            if (layerType == CarPositionMessage.LayerType.CarPosition_CarPos.value):
                loc = features[0].geometryList[0].pointList[1]
                if 'MPU' in lastPositionInfo:
                    lastLoc = lastPositionInfo['MPU'][0]
                    bearing = math.atan2(loc.lat - lastLoc.lat,
                                         loc.lon - lastLoc.lon)
                    lastPositionInfo['MPU-old'] = lastPositionInfo['MPU']
                    lastPositionInfo['MPU'] = (loc, bearing, datetime.now())
                else:
                    lastPositionInfo['MPU'] = (loc, 0, datetime.now())
                    lastPositionInfo['MPU-old'] = lastPositionInfo['MPU']
                
            if (layerType == CarPositionMessage.LayerType.CarPosition_LaneProj.value):
                loc = features[0].geometryList[0].pointList[1]
                if 'LANE' in lastPositionInfo:
                    lastLoc = lastPositionInfo['LANE'][0]
                    bearing = math.atan2(loc.lat - lastLoc.lat,
                                         loc.lon - lastLoc.lon)
                    lastPositionInfo['LANE-old'] = lastPositionInfo['LANE']
                    lastPositionInfo['LANE'] = (loc, bearing, datetime.now())
                else:
                    lastPositionInfo['LANE'] = (loc, 0, datetime.now())
                    lastPositionInfo['LANE-old'] = lastPositionInfo['LANE']
            
            ############ 描画前処理 ############
            if layerType == ProfileMessage.LayerType.Profile_LaneLine.value:
                targetTypeFieldIndex = layer.indexFromName('lineType')
                for feature in features:
                    if feature.type == FeatureType.COMMAND: continue
                    lineType = feature.attribute[targetTypeFieldIndex]
                    if lineType == '(2)Single Dashed Paint Line' or lineType == '(2)単線-白破線(細)' or lineType == '(3)単線-白破線(太)':
                        feature.type = FeatureType.SingleDashedPaintLine
                    else:
                        feature.type = FeatureType.SingleSolidPaintLine
                        
            if layerType == RecommendLaneMessage.LayerType.RecommendLaned.value:
                targetTypeFieldIndex = layer.indexFromName('order')
                for feature in features[:]:
                    if feature.type == FeatureType.COMMAND: continue
                    order = feature.attribute[targetTypeFieldIndex]
                    if order != 3: #high priority
                        features.remove(feature)
                        
            if layerType == SendADstatus.LayerType.RDR_pos.value:
                License_state = layer.indexFromName('License_state')
                TSR_Last_choice_level_ = layer.indexFromName('TSR_Last_choice_level_')
                TSR_HDMAP_level_ = layer.indexFromName('TSR_HDMAP_level_')
                TSR_Camera_ = layer.indexFromName('TSR_Camera_')
                The_reason_that_Hands_off_is_prohibited = layer.indexFromName('The_reason_that_Hands_off_is_prohibited')
                ND2_code = layer.indexFromName('ND2_code')
                Fault_Status_of_Mapecu = layer.indexFromName('Fault_Status_of_Mapecu')
                Cancel_code = layer.indexFromName('Cancel_code')
                Status_transition_of_ADAS = layer.indexFromName('Status_transition_of_ADAS')
                Lane_projection_state = layer.indexFromName('Lane_projection_state')
                ExpressWayFlag = layer.indexFromName('Expressway_judgment_NAVI_')
                FormOfWay = layer.indexFromName('Current_Form_Of_Way')
                
                for feature in features:
                    license_status_message = ''
                    if feature.attribute[License_state] == 0: # license available
                        if propilotInfo == '':
                            license_status_message = 'Propilot License state : Activated'
                        else:
                            license_status_message = 'Propilot License state : Activated ({})'.format(propilotInfo)
                    else:
                        license_status_message = 'Propilot License state : Deactivated (Unavailable AD2)'
                    if vehicleCodeStr != '':
                        license_status_message += ' [Vehicle Code = {}]'.format(vehicleCodeStr)
                    
                    if feature.attribute[License_state] == 0: # license available
                        drawGLwindow.drawText(ViewTextLine.RDR_license.value, license_status_message, 0.4, OpenGLWindow.Color_DiffuseSB)
                    else:
                        drawGLwindow.drawText(ViewTextLine.RDR_license.value, license_status_message, 0.4, OpenGLWindow.Color_DiffuseR)
                    
                    val = feature.attribute[Status_transition_of_ADAS]
                    if val >= 40 and val <= 45:
                        drawGLwindow.drawText(ViewTextLine.RDR_adstatus.value, 'ADAS Status : ' + SendADstatus.Status_transition_of_ADAS_Dic.get(val, '-') + ' (AD2 Hands off)', 0.4, OpenGLWindow.Color_DiffuseB)
                    elif (val >= 30 and val <= 39) or (val >= 50 and val <= 60):
                        drawGLwindow.drawText(ViewTextLine.RDR_adstatus.value, 'ADAS Status : ' + SendADstatus.Status_transition_of_ADAS_Dic.get(val, '-') + ' (AD1e Hands on)', 0.4, OpenGLWindow.Color_DiffuseG)
                    else:
                        drawGLwindow.drawText(ViewTextLine.RDR_adstatus.value, 'ADAS Status : ' + SendADstatus.Status_transition_of_ADAS_Dic.get(val, '-') + ' (AD off)', 0.4, OpenGLWindow.Color_DiffuseGray)
                                        
                    drawGLwindow.drawText(ViewTextLine.RDR_TSR.value, '[TSR] ADAS Select : {0} , from FrCamera : {1} , from HDMAP : {2}'.format(
                        feature.attribute[TSR_Last_choice_level_], feature.attribute[TSR_Camera_], feature.attribute[TSR_HDMAP_level_])
                        , 0.4, OpenGLWindow.Color_DiffuseSR)
                    
                    textLine = ViewTextLine.RDR_laneProjection.value
                    if feature.attribute[Lane_projection_state] == 0:
                        nowOnHDMAP = False
                        drawGLwindow.drawText(textLine, 
                                              drawGLwindow.getText(textLine).replace('[HDMAP] On HDMAP' if drawGLwindow.getText(textLine) != '' else '', '[HDMAP] Off HDMAP'), 
                                              0.4, OpenGLWindow.Color_DiffuseSR)
                    else:
                        nowOnHDMAP = True 
                        drawGLwindow.drawText(textLine, 
                                              drawGLwindow.getText(textLine).replace('[HDMAP] Off HDMAP' if drawGLwindow.getText(textLine) != '' else '', '[HDMAP] On HDMAP'), 
                                              0.4, OpenGLWindow.Color_DiffuseSB)
                    
                    FormOfWayStr = ADASISv2SEGMENT.FormOfWaySymbolDic.get(feature.attribute[FormOfWay], ('', '-'))[1]
                    if feature.attribute[ExpressWayFlag] == 0:
                        drawGLwindow.drawText(ViewTextLine.RDR_SDMapInfo.value, '[SDMAP] Off Highway, <FoW>:' + FormOfWayStr, 0.4, OpenGLWindow.Color_DiffuseSR)
                    else:
                        drawGLwindow.drawText(ViewTextLine.RDR_SDMapInfo.value, '[SDMAP] On Highway, <FoW>:' + FormOfWayStr, 0.4, OpenGLWindow.Color_DiffuseSB)
                    
                    drawGLwindow.drawText(ViewTextLine.RDR_handsoffProhibitReason.value, 'HandsOff Prohibit Reason : {}'.format(
                        SendADstatus.Hands_off_prohibit_symbolDic.get(feature.attribute[The_reason_that_Hands_off_is_prohibited], ('-','-'))[1]),
                        0.4, OpenGLWindow.Color_DiffuseSR)
                    
                    drawGLwindow.drawText(ViewTextLine.RDR_cancelCode.value, 'Cancel code : {}'.format(
                        SendADstatus.Cancel_code_symbolDic.get(feature.attribute[Cancel_code], ('-','-'))[1]),
                        0.4, OpenGLWindow.Color_DiffuseSR)
                    
                    if feature.attribute[ND2_code] != 0:
                        drawGLwindow.drawText(ViewTextLine.RDR_nd2Code.value, 'ND2 code (ADAS DTC) : {}'.format(
                            SendADstatus.ND2_code_symbolDic.get(feature.attribute[ND2_code], ('-','-'))[1]),
                            0.5, OpenGLWindow.Color_DiffuseR)
                    else:
                        drawGLwindow.drawText(ViewTextLine.RDR_nd2Code.value, '', 0, None)
                                                
                    if feature.attribute[Fault_Status_of_Mapecu] != 0:
                        drawGLwindow.drawText(ViewTextLine.RDR_mapDTC.value, 'MAPECU DTC : {}'.format(
                            SendADstatus.MPUerror_symbolDic.get(feature.attribute[Fault_Status_of_Mapecu], ('-','-'))[1]),
                            0.5, OpenGLWindow.Color_DiffuseR)
                    else:
                        drawGLwindow.drawText(ViewTextLine.RDR_mapDTC.value, '', 0, None)
                        
                    
                continue # 描画には登録せずにスキップ
                
            ############ 描画 ############
            if len(features[0].geometryList) > 0: # geometry情報を持つ直線描画物の場合
                featureLoc = features[0].geometryList[0].pointList[0]
                if featureLoc.lat != 0 or featureLoc.lon != 0: # (0, 0) の位置は無効な位置。描画しない。
                    for featureItem in features:
                        for geometryItem in featureItem.geometryList:
                            for point in geometryItem.pointList:
                                point.z = adjustZ(point.z)
                    layer.addFeatures(features)
            else: #そのほかのレイヤ
                layer.addFeatures(features)

        except Exception as e:
            logger.errLog('{}'.format(e))
            logger.errLog(traceback.format_exc())

def drawPositionPuck(drawGLwindow):
    currentTime = datetime.now()
    for name in ['GNSS', 'MPU', 'AD', 'LANE']:
        if not name in lastPositionInfo:
            continue
        (loc, bearing, ts) = lastPositionInfo[name]
        (loc_old, bearing_old, ts_old) = lastPositionInfo[name + '-old']
        if name == 'GNSS': color = (1.0, 0.0, 0.0)
        elif name == 'MPU': color = (0.78, 0.78, 0.78)
        elif name == 'AD': color = (100/255.0,90/255.0,50/255.0)
        elif name == 'LANE': color = (0.0, 0.0, 1.0)
        
        if ts == ts_old:
            timeRate = 1
        else:
            currentElapsedTime = (currentTime - ts).total_seconds()
            timeRate = currentElapsedTime / ((ts - ts_old).total_seconds())
            if (timeRate > 1): timeRate = 1
        
        lon = loc_old.lon * (1-timeRate) + loc.lon * (timeRate)
        lat = loc_old.lat * (1-timeRate) + loc.lat * (timeRate)
        z = adjustZ(loc_old.z * (1-timeRate) + loc.z * (timeRate))
        th = bearing_old * (1-timeRate) + bearing * (timeRate)
        
        drawGLwindow.drawTriangle(lon, lat, z, th, color)
    