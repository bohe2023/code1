import dpkt,socket
from dpkt.compat import compat_ord
import traceback
import os
import pandas
from MessageType import DrawMode, analyzeMessage, initMessage, isSegmentableMessage, isAnalyzePositionErrorMessage, setLayerStyle, ProfileMessage, SendADstatus, ExternalLonLatinfo
from TypeDef import EtherID, getEtherIdDic, degrees2meters, etherIdDic, VehicleCodeTable
from PCAPLoader import TCPStream, getTcpPackets, getUdpPackets, getCANFramePacket, initPCAPLoader
from GlobalVar import getLogger, setEthernetSpecVer, getRecommandLaneViewerClear, setRecommandLaneViewerClear, setSrcMAC, setVehicleType, setADASISanalyze, getADASISanalyze, setDebugEtherAnalyze, setREDRanalyze, getDebugEtherAnalyze, getREDRanalyze
from ExcelFileCtrl import MyWorkSheet
from datetime import datetime, timedelta
try:
    from qgis.core import *
    from qgis.gui import *
    from qgis.PyQt import QtGui
    from qgis.utils import iface
    from PyQt5.QtCore import QDateTime
except:
    pass
from BLF_Eethernet import BLFEtherReader
from ACSCanReader import ACSCanReader
from time import sleep
from ControlPanel import *
from LayerManager import *
import subprocess

class Structure:
    pass

###################################################################################################
##                            Task Define [Start]                                                ##
###################################################################################################
class QgisADASISdrawTask(QgsTask):
    def __init__(self, controlPanel):
        super().__init__('QgisADASISdrawTask', QgsTask.CanCancel)
        self.controlPanel = controlPanel
        self.cpuLoadStr = "M-CPU : ---%"
        self.ErrorStr = "Code(R):------, Code(nR):----, DTC:----"
        self.factoryMode = False
        self.cpuLoadLevel = 0
        self.showMessageStr = ''
        self.layerRegisterReq1 = []
        self.layerRegisterReq2 = []
        self.layerRegisterBuf = self.layerRegisterReq2
        self.resetDrawGroup()
        self.latestCarPositionMessage = None
        self.latestGNSSPositionMessage = None
        self.latestIVIPositionMessage = None
        self.latestADASISPositionMessage = None
        self.latestADPositionMessage = None
        self.latestVehicleTypeValue = 0xFFFF
        self.cancelReq = False
        
        if (getDebugEtherAnalyze() == False): etherIdDic[EtherID.DebugEther.value]['implementQGIS'] = -1
        if (getREDRanalyze() == False): etherIdDic[EtherID.SendADstatus.value]['implementQGIS'] = -1
    
    def resetDrawGroup(self):
        self.logStartTime = None
        self.logEndTime = None
        self.oldMessageDic = {}
        self.oldMessageTime = {}
    
    def getLayerRegisterBufDataCount(self):
        return len(self.layerRegisterBuf)
        
    def getLayerRegisterBuf(self):
        if len(self.layerRegisterBuf) == 0:
            return []
        if self.layerRegisterBuf == self.layerRegisterReq2:
            self.layerRegisterReq1.clear()
            self.layerRegisterBuf = self.layerRegisterReq1
            return self.layerRegisterReq2
        else:
            self.layerRegisterReq2.clear()
            self.layerRegisterBuf = self.layerRegisterReq2
            return self.layerRegisterReq1
            
    def run(self):
        return True
    
    def cancel(self):
        super().cancel()
        self.cancelReq = True
            
    def drawLayerProcess(self, packets, fileName, logTime, readIndex):
        logger = getLogger()
        viewerClear = getRecommandLaneViewerClear()
        for packet in packets:
            try:
                messageID = packet.header.ID
                if (getEtherIdDic(messageID) != None) and (len(self.filter_messageID) == 0 or (messageID in self.filter_messageID)):
                    if self.controlPanel.realTimeViewMode == True and 'implementQGISinRealTimeMode' in getEtherIdDic(messageID):
                        drawFrameRate = getEtherIdDic(messageID)['implementQGISinRealTimeMode']
                    elif 'implementQGIS' in getEtherIdDic(messageID):
                        drawFrameRate = getEtherIdDic(messageID)['implementQGIS']
                    else:
                        continue
                    if drawFrameRate < 0:
                        continue
                    
                    # controlPanelで、realTimeViewMode = True時は、drawWithLoadは常にTrue
                    if self.controlPanel.drawWithLoad == False:
                        #全体一揆描画モード時は、Widget専用表示の物は無視
                        if messageID == EtherID.specificADmode.value:
                            continue
                        #推奨レーンのクリアの場合は、全体一揆描画モード時は、無視
                        if viewerClear == True:
                            if messageID == EtherID.RecommendLaneMessage_JP.value or messageID == EtherID.RecommendLaneMessage_US.value:
                                continue

                    if messageID in self.oldMessageDic:
                        oldMessage = self.oldMessageDic[messageID]
                    else:
                        oldMessage = None

#                     if messageID == EtherID.CAN_ADASISv2PROFILELONGforAD2.value or messageID == EtherID.ADASISv2PROFILELONGforAD2.value:
#                         # profile longの緯度経度情報をより早く反映するために、特別にログ時刻を１秒早める。
#                         logTime -= timedelta(seconds=2)

                    if isSegmentableMessage(messageID):
                        #分割メッセージの場合は、描画しなくても、全てのメッセージをParseする必要がある。
                        message = analyzeMessage(readIndex, logTime, messageID, packet.dat, oldMessage)
                        if (messageID in self.oldMessageTime) and (drawFrameRate > 0):
                            spanTime_ms = (logTime - self.oldMessageTime[messageID]).total_seconds() * 1000
                            if spanTime_ms >= 0 and spanTime_ms < drawFrameRate:
                                continue
                    else:
                        #一般メッセージは、描画する時のみParseする。
                        if (messageID in self.oldMessageTime) and (drawFrameRate > 0):
                            spanTime_ms = (logTime - self.oldMessageTime[messageID]).total_seconds() * 1000
                            if spanTime_ms >= 0 and spanTime_ms < drawFrameRate:
                                continue
                        message = analyzeMessage(readIndex, logTime, messageID, packet.dat, oldMessage)
                        
                    if message == None:
                        continue
                    
                    ############ old更新 ############
                    self.oldMessageDic[messageID] = message
                    self.oldMessageTime[messageID] = logTime
                    
                    ############ メッセージ別特殊処理 ############
                    if messageID == EtherID.VehicleParameterMessage.value:
                        if self.latestVehicleTypeValue != message.vehicleCode:
                            logger.logPrintWithConsol('VehicleCode detected = {}'.format(message.vehicleCodeStr))
                            self.latestVehicleTypeValue = message.vehicleCode
                            setVehicleType(message.vehicleCode)
                        continue
                    
                    if messageID == EtherID.SendADstatus.value: #-- SendADstatusは、描画bufに登録もするし、ここで別処理もする    
                        if self.controlPanel.realTimeViewMode == True:
                            self.controlPanel.HandsOffProhibitReason.setText(SendADstatus.Hands_off_prohibit_symbolDic.get(message.The_reason_that_Hands_off_is_prohibited, ('-','-'))[1])
                            self.controlPanel.ND2code.setText(SendADstatus.ND2_code_symbolDic.get(message.ND2_code, ('-','-'))[1])
                            self.controlPanel.CancelCode.setText(SendADstatus.Cancel_code_symbolDic.get(message.Cancel_code, ('-','-'))[1])
                    
                    if messageID == EtherID.PerformanceMessage.value:
                        self.cpuLoadStr = "M-CPU : {0:03d}%".format(message.cpuUsage_MCPU)
                        if message.cpuUsage_MCPU >= 95:
                            self.cpuLoadLevel = 2
                        elif message.cpuUsage_MCPU >= 80:
                            self.cpuLoadLevel = 1
                        else:
                            self.cpuLoadLevel = 0
                        if self.controlPanel.realTimeViewMode == True:
                            #リアルタイムモードじは、描画しないので、飛ばす。
                            continue
                    
                    if messageID == EtherID.specificADmode.value:
                        if message.perTestAD2TestMode == 0:
                            self.factoryMode = False
                        else:
                            self.factoryMode = True
                        continue #-- 描画不要なwidget専用メッセージ。描画しなくてよいので、飛ばす。
                    
                    if messageID == EtherID.ErrorMessage.value:
                        self.ErrorStr = 'Code(R) : 0x{0:04X}, Code(nR) : 0x{1:02X}, DTC : 0x{2:02X}'.format(message.recoverErrorCode, message.nonRecoverErrorCode, message.dtcCode)
                        if self.controlPanel.realTimeViewMode == True:
                            #リアルタイムモードじは、描画しないので、飛ばす。
                            continue
                        
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
                    
                    ############ 描画Queueに保存 ############
                    self.layerRegisterBuf.append([messageID, message])
                        
            except Exception as e:
                logger.errLog("logIndex:{0}, Error:{1}".format(readIndex, e))
                logger.errLog(traceback.format_exc())
        
        if self.controlPanel.drawWithLoad == True:  
            self.showMessageStr = self.cpuLoadStr + " , " + self.ErrorStr + " , logTime = [ " + str(logTime) + " ] , logIndex = ( " + str(readIndex) + " )"
            if self.factoryMode == True:
                self.showMessageStr += " [工場モードON]"
            else:
                self.showMessageStr += " [工場モードOFF]"
            if fileName != None:
                self.showMessageStr += " (File: " + fileName + ")"

    
class QgisADASISdrawTask_LogFileDrawForGnssAnalyze(QgisADASISdrawTask):
    def __init__(self, targetFiles,  controlPanel, someipmode, targetRefFile = None):
        super().__init__(controlPanel)
        self.targetFiles = targetFiles
        self.fileName = 'GnssAnalyze(' + str(datetime.now()) + ')'
        self.someipmode = someipmode
        self.targetRefFile = targetRefFile
        
    def makeWorkSheet(self, basePath, name):
        worksheetInfo = Structure()
        worksheetInfo.worksheet = MyWorkSheet()
        worksheetInfo.worksheet.initAsOnlyCSVmode(basePath + name)
        worksheetInfo.currentRow = 0
        worksheetInfo.currentCol = 0
        return worksheetInfo
    
    def run(self):
        logger = getLogger()
        allPacketList = []
        workSheetList = {}
        externalLonLatCount = 0
        baseTimeTs_gps = None
        startPoint_adjust = None
        endPoint_adjust = None
        gpsTimeExist = False
        oldTimeTs = 0
        latestRefPositionMessage = None
        
        
        if self.targetRefFile == None:
            RefFileMessageID = EtherID.CarPositionMessage.value
            logger.logPrintWithConsol('GNSS Analyze Ref is [MAPECU Lane Projection Position]')
        else:
            if self.targetRefFile == 'LaneProjection':
                RefFileMessageID = EtherID.CarPositionMessage.value
                logger.logPrintWithConsol('GNSS Analyze Ref is [MAPECU Lane Projection Position]')
            elif self.targetRefFile == 'ADPosition':
                RefFileMessageID = EtherID.ADPositionMessage.value
                logger.logPrintWithConsol('GNSS Analyze Ref is [AD Position]')
            elif self.targetRefFile == 'MAPECUGNSS':
                RefFileMessageID = EtherID.GNSSDataMessage.value
                logger.logPrintWithConsol('GNSS Analyze Ref is [MAPECU GNSS Position]')
            else:
                RefFileMessageID = EtherID.ExternalLonLatMessage.value
                logger.logPrintWithConsol('GNSS Analyze Ref is [{}]'.format(self.targetRefFile))
                if not(self.targetRefFile in self.targetFiles):
                    self.targetFiles.append(self.targetRefFile)
        
        try:
            basePath = os.path.dirname(self.targetFiles[0]) + '/'
            workSheetList[EtherID.GNSSDataMessage.value] = self.makeWorkSheet(basePath, 'GnssPositionError(' + getEtherIdDic(EtherID.GNSSDataMessage.value)['name'] + ')')
            workSheetList[EtherID.CarPositionMessage.value] = self.makeWorkSheet(basePath, 'CarPositionError(' + getEtherIdDic(EtherID.CarPositionMessage.value)['name'] + ')')
            workSheetList[EtherID.ADPositionMessage.value] = self.makeWorkSheet(basePath, 'ADPositionError(' + getEtherIdDic(EtherID.ADPositionMessage.value)['name'] + ')')

            for logFile in self.targetFiles:
                fileFullName = logFile
                self.fileName = fileFullName[fileFullName.rfind('/')+1:fileFullName.rfind('.')]
                expName = fileFullName[fileFullName.rfind('.')+1:]
                self.showMessageStr = 'Now on file load... (File: ' + self.fileName + ')'
                logger.logPrintWithConsol('Read File : {0}'.format(self.fileName))
                if expName.lower() == "pcapng":
                    reader = dpkt.pcapng.Reader(open(fileFullName,'rb'))
                elif expName.lower() == "pcap":
                    reader = dpkt.pcap.Reader(open(fileFullName,'rb'))
                elif expName.lower() == "blf":
                    reader = BLFEtherReader(open(fileFullName,'rb'), True, False)
                elif expName.lower() == "csv":
                    reader = open(fileFullName, 'r')
                else:
                    logger.logPrintWithConsol('Unknown file format')
                    return False
                
                readIndex = 0
                tcpstream = {}
                
                try:
                    if expName.lower() == "csv":
                        if self.targetRefFile == fileFullName:
                            RefFileMessageID = EtherID.ExternalLonLatMessage.value + externalLonLatCount
                        else:
                            workSheetList[EtherID.ExternalLonLatMessage.value + externalLonLatCount] = self.makeWorkSheet(basePath, 'LatLngError(' + self.fileName + ')')
                        timeOffsetSec = 0
                        oldMessage = None
                        
                        lines = reader.readlines()
                        try:
                            #offset , header
                            data = lines[0].rstrip().split(',')
                            timeOffsetSec = float(data[1])
                            readIndex += 2
                        except Exception as e:
                            logger.errLog('line:{}, err:{}'.format(readIndex, e))
                
                        # [time, lon, lat]
                        for line in lines[2:]:
                            readIndex += 1
                            try:
                                data = line.rstrip().split(',')
                                if '/' in data[0]:
                                    if '.' in data[0]:
                                        logTime = datetime.strptime(data[0], '%Y/%m/%d %H:%M:%S.%f')
                                    else:
                                        logTime = datetime.strptime(data[0], '%Y/%m/%d %H:%M:%S')
                                elif '-' in data[0]:
                                    if '.' in data[0]:
                                        logTime = datetime.strptime(data[0], '%Y-%m-%d %H:%M:%S.%f')
                                    else:
                                        logTime = datetime.strptime(data[0], '%Y-%m-%d %H:%M:%S')
                                else:
                                    logTime = datetime.fromtimestamp(float(data[0]))
                                if timeOffsetSec != 0:
                                    logTime += timedelta(seconds=timeOffsetSec)
                                lon = float(data[1])
                                lat = float(data[2])
                            except Exception as e:
                                logger.errLog('line:{}, err:{}'.format(readIndex, e))
                                continue
                            
                            message = ExternalLonLatinfo(0, logTime, EtherID.ExternalLonLatMessage.value + externalLonLatCount, self.fileName)
                            if message == None:
                                continue
                            message.oldMessage = oldMessage
                            if oldMessage != None:
                                oldMessage.nextMessage = message
                            message.parse(lon, lat, oldMessage)
                            oldMessage = message
                            
                            allPacketList.append(message)
                        externalLonLatCount += 1
                        
                    else:
                        for ts, buf in reader:
                            if self.cancelReq == True or self.isCanceled():
                                break
                            readIndex += 1
                            
                            if ts < oldTimeTs-10 or ts > oldTimeTs+10: #10秒以上飛んだtsが来た場合
                                baseTimeTs_gps = None
                            oldTimeTs = ts
                            if baseTimeTs_gps != None:
                                ts = ts + baseTimeTs_gps
    
                            self.showMessageStr = "Now read all log datas..."
    
                            if buf[0:4] == b'\xFF\x0C\xAF\x00': #CANフレーム。（独自の識別子をBLF_Ethernetコード上でつけた）
                                continue
                                
                            else: #Etherフレーム    
                                L2_layer = dpkt.ethernet.Ethernet(buf)
                                if type(L2_layer.data) != dpkt.ip.IP:
                                    continue
                                
                                #srcMAC = ':'.join('%02x' % compat_ord(b) for b in L2_layer.src).upper()
                                dstMAC = ':'.join('%02x' % compat_ord(b) for b in L2_layer.dst).upper()
    
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
                                                
                            logTime = datetime.fromtimestamp(ts)
                            
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
                            
                            for packet in packets:
                                messageID = packet.header.ID
                                if messageID in [EtherID.GNSSDataMessage.value, EtherID.CarPositionMessage.value, EtherID.ADPositionMessage.value]:
                                    #描画対象全て。（Error解析するかどうかは、さらに、そのメッセージがAnalyzePositionErrorを引き継いでいるかによる。）
                                    if messageID in self.oldMessageDic:
                                        oldMessage = self.oldMessageDic[messageID]
                                    else:
                                        oldMessage = None
                                        
                                    message = analyzeMessage(0, logTime, messageID, packet.dat, oldMessage)
                                    if message == None:
                                        continue
                                        
                                    self.oldMessageDic[messageID] = message
                                    allPacketList.append(message)
                        
                        #memory management
                        del reader
                
                except Exception as e:
                    logger.errLog("<Process Error> File:{}, logIndex:{}, Error:{}".format(fileFullName, readIndex, e))
                    logger.errLog(traceback.format_exc())
                    logger.logPrintWithConsol('  (logfile error detected. But ignore and read next log file.)')
                    
                logger.flush()
                
                if self.cancelReq == True or self.isCanceled():
                    break
            
            logger.logPrintWithConsol('All read complete. StartLogTime={}, EndLogTime={}'.format(str(self.logStartTime), str(self.logEndTime)))   
            allPacketList = sorted(allPacketList, key=lambda x: x.commonHeader.logTime)
            
            if self.logStartTime == None:
                logTimeUpdate = True
            else:
                logTimeUpdate = False
            
            totalPacketCount = len(allPacketList)
            currentPacketIndex = 0
            progressCurrentPacket = 0
            logger.logPrintWithConsol('Now on packet analyze... (all read packet count = {})'.format(totalPacketCount))
            for message in allPacketList:
                currentPacketIndex += 1
                if progressCurrentPacket != int(currentPacketIndex * 100 / totalPacketCount / 10):
                    progressCurrentPacket = int(currentPacketIndex * 100 / totalPacketCount / 10)
                    logger.logPrintWithConsol('Now on packet analyze... ({}%) [logTime={}])'.format(progressCurrentPacket * 10, message.commonHeader.logTime))
                    logger.flush()
                    
                if self.cancelReq == True or self.isCanceled():
                    break
                
                messageID = message.commonHeader.messageID
                
                if logTimeUpdate == True:
                    if self.logStartTime == None:
                        self.logStartTime = message.commonHeader.logTime
                    self.logEndTime = message.commonHeader.logTime

                ############ 関連CarPosition設定 ############
                if messageID == RefFileMessageID:
                    latestRefPositionMessage = message
                
                ############ 誤差解析および出力 ############
                if isAnalyzePositionErrorMessage(messageID) and messageID != RefFileMessageID:
                    message.analyzePositionError(latestRefPositionMessage)
                    messageSheet = workSheetList[messageID]
                    if messageSheet != None:
                        if messageSheet.currentRow == 0:
                            messageSheet.worksheet.write_row(messageSheet.currentRow, 0, ['Log Time', 'Target Lon', 'Target Lat', 'Ref Lon', 'Ref Lat', 'Err Distance[m]'])
                            messageSheet.currentRow += 1
                        if message.positionError.distance >= 0:
                            messageSheet.worksheet.write_row(messageSheet.currentRow, 0, 
                                                             [str(message.commonHeader.logTime)]
                                                              + message.positionError.target
                                                              + message.positionError.foot
                                                              + [message.positionError.distance])
                            messageSheet.currentRow += 1
                
                ############ 描画Queueに保存 ############
                self.layerRegisterBuf.append([messageID, message])
        except:
            logger.errLog(traceback.format_exc())
                
        if self.cancelReq == True or self.isCanceled():
            return True
        else:
            self.showMessageStr = "All read complete."
            subprocess.run('explorer {}'.format(basePath.replace('/','\\')))
            return True

class QgisADASISdrawTask_LogFileDraw(QgisADASISdrawTask):
    def __init__(self, targetFiles,  controlPanel, startPoint, endPoint, filter_srcMAC, filter_messageID, CAN_chanel_filter, someipmode):
        super().__init__(controlPanel)
        self.targetFiles = targetFiles
        fileFullName = targetFiles[0]
        self.fileName = fileFullName[fileFullName.rfind('/')+1:fileFullName.rfind('.')]
        self.showFilterStartPoint = startPoint
        self.showFilterEndPoint = endPoint
        self.filter_srcMAC = filter_srcMAC
        self.filter_messageID = filter_messageID
        self.CAN_chanel_filter = CAN_chanel_filter
        self.someipmode = someipmode
        
    def run(self):
        logger = getLogger()
        startReadIndex = 0
        readIndex = 0
        firstInfoShowed = False
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
                self.showMessageStr = 'Now on file load... (File: ' + self.fileName + ')'
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
                        if self.cancelReq == True or self.isCanceled():
                            break
                        readIndex += 1
    
                        if ts < oldTimeTs-10 or ts > oldTimeTs+10: #10秒以上飛んだtsが来た場合
                            baseTimeTs_gps = None
                        oldTimeTs = ts
                        if baseTimeTs_gps != None:
                            ts = ts + baseTimeTs_gps
    
                        #indexによる描画区間制御
                        if self.showFilterStartPoint != None and type(self.showFilterStartPoint) == type(readIndex):
                            if readIndex < self.showFilterStartPoint:
                                criterionTime = None #ログを飛ばす分、時間描画基準点をリセットする。
                                if readIndex & 0xFFF == 0xFFF:
                                    logTime = datetime.fromtimestamp(ts)
                                    self.showMessageStr = "Now on search start point..." + " , logTime = [ " + str(logTime) + " ] , logIndex = ( " + str(readIndex) + " )"
                                    if self.controlPanel.drawWithLoad == False and (firstInfoShowed == False or readIndex & 0x1FFFFF == 0x1FFFFF):
                                        print(self.showMessageStr)
                                        firstInfoShowed = True
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
                                        self.showMessageStr = "Now on search start point..." + " , logTime = [ " + str(logTime) + " ] , logIndex = ( " + str(readIndex) + " )"
                                        if self.controlPanel.drawWithLoad == False and (firstInfoShowed == False or readIndex & 0x1FFFFF == 0x1FFFFF):
                                            print(self.showMessageStr)
                                            firstInfoShowed = True
                                    continue
                            if self.showFilterEndPoint != None and type(self.showFilterEndPoint) == type(logTime):
                                if logTime > self.showFilterEndPoint:
                                    break
                                         
                        # *********** 時間の流れ制御 ********** #
                        if self.controlPanel.drawWithLoad == True:
                            currentTime = datetime.now()
                            if criterionTime == None:
                                logger.logPrintWithConsol("Draw Start Point : " + str(logTime) + " (index = " + str(readIndex) + ")")
                                criterionTime = logTime
                            else:
                                if self.getLayerRegisterBufDataCount() < 1000:
                                    #描画データが溜まりすぎると、描画一旦停止。
                                    criterionTime += (currentTime - oldTime) * self.controlPanel.playSpeed
                            oldTime = currentTime
                            
                            while (criterionTime < logTime) or (self.controlPanel.pauseRequest == True):
                                if self.cancelReq == True or self.isCanceled():
                                    break
                                sleep(0.1)
                                currentTime = datetime.now()
                                if self.controlPanel.pauseRequest == False:
                                    criterionTime += (currentTime - oldTime) * self.controlPanel.playSpeed
                                oldTime = currentTime
                        else:
                            self.showMessageStr = "Now read all log datas..." + " , logTime = [ " + str(logTime) + " ] , logIndex = ( " + str(readIndex) + " )"
                            if criterionTime == None:
                                logger.logPrintWithConsol("Draw Start Point : " + str(logTime) + " (index = " + str(readIndex) + ")")
                            criterionTime = logTime
                            oldTime = logTime
                            
                            while self.controlPanel.pauseRequest == True:
                                if self.cancelReq == True or self.isCanceled():
                                    break
                                sleep(0.1)
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
    
                        self.drawLayerProcess(packets, self.fileName, logTime, readIndex)
                
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
                
                if self.cancelReq == True or self.isCanceled():
                    break
                    
        except:
            logger.errLog(traceback.format_exc())
                
        logger.logPrintWithConsol('All read complete. StartLogTime={}, EndLogTime={}'.format(str(self.logStartTime), str(self.logEndTime)))        
        
        if self.cancelReq == True or self.isCanceled():
            return True
        else:
            self.showMessageStr = "All read complete."
            return True

class QgisADASISdrawTask_RealTimeDraw(QgisADASISdrawTask):
    def __init__(self, controlPanel, interfaceName, filter_srcMAC, filter_messageID, someipmode):
        super().__init__(controlPanel)
        self.fileName = str(datetime.now())
        self.filter_srcMAC = filter_srcMAC
        self.filter_messageID = filter_messageID
        self.someipmode = someipmode
        self.interfaceName = interfaceName
        self.readIndex = 0
        self.lastPacketReceivedTime = None
        self.restart = False
        self.outputPCAPfile = None
        
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
            ts = currentTime.timestamp()
            if self.outputPCAPfile == None:
                self.outputPCAPfile = dpkt.pcap.Writer(open(QgsProject.instance().readPath('./') + '/' + '{}_ethCapture.pcap'.format(datetime.now().strftime('%Y-%m-%d-%H-%M-%S')), 'wb'))
            self.outputPCAPfile.writepkt(pkt, ts)
            
            data = pkt[scapy.Raw].load
            (packets, _) = getUdpPackets(data, self.someipmode, onlyReadFirstMessage = True)
            if len(packets) > 0:
                self.fileName = str(currentTime)
                self.drawLayerProcess(packets, None, currentTime, self.readIndex)
                if self.logStartTime == None:
                    self.logStartTime = currentTime
                self.logEndTime = currentTime
        except:
            pass     
    
    def run(self):
        from scapy import all as scapy
        logger = getLogger()
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
            
            scapy.sniff(iface=self.interfaceName, prn=self.pkt_callback, filter=filterRule, store=0, stop_filter=lambda p: (self.cancelReq == True or self.isCanceled() or self.restart == True))
            
            #以下のAsyncSnifferは試したが、パケットが受信できない
            # t = AsyncSniffer(iface=self.interfaceName, prn=self.pkt_callback, filter=filterRule, store=0, stop_filter=lambda p: (self.controlPanel.stopRequest == True or self.isCanceled()))
            # while True:
                # sleep(1)
                # if self.controlPanel.stopRequest == True or self.isCanceled():
                    # break
            # t.stop()
            
            if self.restart == True:
                logger.logPrintWithConsol('retry...')
                self.restart = False
            else:
                if self.outputPCAPfile != None:
                    self.outputPCAPfile.close()
                return True
                
    def cancel(self):
        from scapy import all as scapy
        super().cancel()
        self.cancelReq = True
        filter_srcMAC = getSrcMAC()
        if len(filter_srcMAC) > 0:
            scapy.sendp(scapy.Ether(src=filter_srcMAC[0],dst='00:00:00:00:00:00')/scapy.IP()/scapy.UDP(), iface=self.interfaceName, verbose=False)
        else:
            scapy.sendp(scapy.Ether(src='AA:BB:CC:DD:00:06',dst='00:00:00:00:00:00')/scapy.IP()/scapy.UDP(), iface=self.interfaceName, verbose=False)
            
###################################################################################################
##                            Task Define [End]                                                  ##
###################################################################################################

def moveToCanvasArea(canvas, controlPanel, message):
    global lastGNSSDataMessageReceiveTime
    currentTime = datetime.now()
    if message.commonHeader.messageID == EtherID.GNSSDataMessage.value:
        latitude = message.lat_JGDAug * 360.0 / 0xFFFFFFFF
        longitude = message.lon_JGDAug * 360.0 / 0xFFFFFFFF
        if latitude > 179 or longitude > 179:
            latitude = message.lat * 360.0 / 0xFFFFFFFF
            longitude = message.lon * 360.0 / 0xFFFFFFFF
            if latitude > 179 or longitude > 179:
                return
            else:
                lastGNSSDataMessageReceiveTime = currentTime
        else:
            lastGNSSDataMessageReceiveTime = currentTime
    elif (message.commonHeader.messageID == EtherID.CarPositionMessage.value) and ((lastGNSSDataMessageReceiveTime == None) or ((currentTime - lastGNSSDataMessageReceiveTime).total_seconds() >= 1)):
        #GNSSが1秒以上来なかったら、レーン投影位置に画面を移動
        latitude = message.laneProjectionPosition.latitude * 360.0 / 0xFFFFFFFF
        longitude = message.laneProjectionPosition.longitude * 360.0 / 0xFFFFFFFF
        if latitude > 179 or longitude > 179:
            return
    else:
        return

    offset = controlPanel.trackingScale
    pos = degrees2meters(longitude, latitude)
    zoomRectangle = QgsRectangle(pos[1]-offset, pos[0]-offset,pos[1]+offset,pos[0]+offset)
    canvas.setExtent(zoomRectangle)
    
def canvasSetReady():
    global nowOnCanvasRefresh
    nowOnCanvasRefresh = False
    
def refreshCanvas(drawTask, layerManager, controlPanel):
    global widget
    global nowOnCanvasRefresh
    global canvas
    
    QApplication.processEvents()
    controlPanel.update()
    if canvas != None and nowOnCanvasRefresh == False:
        nowOnCanvasRefresh = True
        layerManager.refreshLayer()
        canvas.mapCanvasRefreshed.connect( canvasSetReady )
        canvas.refresh()
        while (nowOnCanvasRefresh == True):
            QApplication.processEvents()
            controlPanel.update()
    try:
        widget.setLevel(drawTask.cpuLoadLevel)
        widget.setText(drawTask.showMessageStr)
    except:
        widget = iface.messageBar().createMessage("CPU負荷", drawTask.showMessageStr)
        iface.messageBar().pushWidget(widget, Qgis.Warning)

def init():
    global lastGNSSDataMessageReceiveTime
    global nowOnCanvasRefresh
    global canvas
    
    canvas = iface.mapCanvas()
    canvas.enableAntiAliasing(False)
    canvas.setCachingEnabled(True);
    canvas.setParallelRenderingEnabled(True);
    #canvas.setMapUpdateInterval(3000);

    initPCAPLoader(False)
    nowOnCanvasRefresh = False
    lastGNSSDataMessageReceiveTime = None
    initMessage()

def drawForGnssAnalyze(controlPanel, targetFiles = None, someipmode = True, targetGnssRefFile = None):
    if targetFiles == None:
        return None, None
    if type(targetFiles) != type([]):
        targetFiles = [targetFiles]
    
    init()
    
    drawTask = QgisADASISdrawTask_LogFileDrawForGnssAnalyze(targetFiles, controlPanel, someipmode, targetGnssRefFile)
    return drawTask    

def draw(controlPanel, targetFiles = None, startPoint = None, endPoint = None, someipmode = True, filter_srcMAC = None, filter_messageID = None, CAN_chanel_filter = None, ethernetSpecVer = None, recommendLaneLayerRedraw = True, vehicle = 'PZ1A', ADASISanalyze = False, DebugEtherAnalyze = False, REDRanalyze = True):
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
        
    vehicleCode = 0
    for key, vehicleCodeStr in VehicleCodeTable.items():
        if vehicle in vehicleCodeStr:
            vehicleCode = key
            break
    print('default Vehicle type = ' + VehicleCodeTable.get(vehicleCode, 'Unknown'))
        
    init()
    setEthernetSpecVer(ethernetSpecVer)
    setRecommandLaneViewerClear(recommendLaneLayerRedraw)
    setSrcMAC(','.join(filter_srcMAC))
    setVehicleType(vehicleCode)
    setADASISanalyze(ADASISanalyze)
    setDebugEtherAnalyze(DebugEtherAnalyze)
    setREDRanalyze(REDRanalyze)
    
    
    
    drawTask = QgisADASISdrawTask_LogFileDraw(targetFiles, controlPanel, startPoint, endPoint, filter_srcMAC, filter_messageID, CAN_chanel_filter, someipmode)
    return drawTask

def RDRdatFileLoad_fromCSV(GroupIndex, controlPanel, targetFiles, ethernetSpecVer = None):        
    ## Init ##
    logStartTime = None
    logEndTime = None
    oldMessage = None
    counter = 0
    lineIndex = 0
    oldMinute = -1
    oldLogtime = None
    estimateMiliSec = 0
    groupSubIndex = 0
    logger = getLogger()
    ## Init ##
    
    messageID = EtherID.SendADstatus.value
    
    if targetFiles == None or len(targetFiles) == 0:
        return
    
    init()
    setEthernetSpecVer(ethernetSpecVer)
    
    logger.logPrintWithConsol('Now on load {0} files. please wait...'.format(len(targetFiles)))
    makeGroup = True    
    for fileFullName in targetFiles:
        df = pandas.read_csv(fileFullName).sort_values(['MSSG_TM_UTC_DTTM','INDX_IN_MSSG_NMBR','GPS_TMSTMP_DTTM','MLG_NMBR'])
        sortedLineIndexList = list(df.index)
        length = len(sortedLineIndexList)
        alreadyFlag = [False]*length
        oldRecogNumber = 0
        oldRecogNumberTime = None
        oldLineIndex = 0
        index = -1
        startMemoryForFastLoop = 0
        while index+1 < length:
            index += 1
            lineIndex = sortedLineIndexList[index]
            if alreadyFlag[lineIndex] == True:
                continue
            
            #R-DRデータ、ソート処理
            recogNumber = int(df.loc[lineIndex,'INDX_IN_MSSG_NMBR'])
            if oldRecogNumber >= recogNumber and df.loc[lineIndex,'MSSG_TM_UTC_DTTM'] == df.loc[oldLineIndex,'MSSG_TM_UTC_DTTM']:
                #通信環境により、同じindexが並んだ場合
                if startMemoryForFastLoop == 0:
                    startMemoryForFastLoop = index+1
                for newIndex in range(startMemoryForFastLoop,length):
                    newLineIndex = sortedLineIndexList[newIndex]
                    if alreadyFlag[newLineIndex] == True:
                        continue
                    
                    if df.loc[newLineIndex,'MSSG_TM_UTC_DTTM'] > df.loc[lineIndex,'MSSG_TM_UTC_DTTM']:
                        #これ以上、大きいindexはない。最初に戻る必要がある。
                        startMemoryForFastLoop = 0
                        break
                    
                    newRecogNumber = int(df.loc[newLineIndex,'INDX_IN_MSSG_NMBR'])
                    if oldRecogNumber < newRecogNumber:
                        try:
                            newRecogNumberTime = datetime.strptime(df.loc[newLineIndex,'GPS_TMSTMP_DTTM'], '%Y/%m/%d %H:%M:%S.%f')
                        except:
                            try:
                                newRecogNumberTime = datetime.strptime(df.loc[newLineIndex,'GPS_TMSTMP_DTTM'], '%Y/%m/%d %H:%M:%S')
                            except:
                                try:
                                    newRecogNumberTime = datetime.strptime(df.loc[newLineIndex,'GPS_TMSTMP_DTTM'], '%Y-%m-%dT%H:%M:%S.%fZ')
                                except:
                                    newRecogNumberTime = datetime.strptime(df.loc[newLineIndex,'GPS_TMSTMP_DTTM'], '%Y-%m-%dT%H:%M:%SZ')
                        if oldRecogNumberTime != None and abs(newRecogNumberTime - oldRecogNumberTime).total_seconds() >= 120:
                            #２分以上離れた場合は、途切れと判断する。最初に戻る必要がある。
                            startMemoryForFastLoop = 0
                            break
                        
                        lineIndex = newLineIndex
                        startMemoryForFastLoop = newIndex+1
                        index = index - 1 #後で改めて処理するため
                        break
            
            #ライン読み込み処理
            counter += 1
            rowValues = df.loc[lineIndex,:]
            oldRecogNumber = int(df.loc[lineIndex,'INDX_IN_MSSG_NMBR'])
            oldLineIndex = lineIndex
            try:
                oldRecogNumberTime = datetime.strptime(df.loc[lineIndex,'GPS_TMSTMP_DTTM'], '%Y/%m/%d %H:%M:%S.%f')
            except:
                try:
                    oldRecogNumberTime = datetime.strptime(df.loc[lineIndex,'GPS_TMSTMP_DTTM'], '%Y/%m/%d %H:%M:%S')
                except:
                    try:
                        oldRecogNumberTime = datetime.strptime(df.loc[lineIndex,'GPS_TMSTMP_DTTM'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    except:
                        oldRecogNumberTime = datetime.strptime(df.loc[lineIndex,'GPS_TMSTMP_DTTM'], '%Y-%m-%dT%H:%M:%SZ')
            alreadyFlag[lineIndex] = True
            
            try:
                #20byteのダミー共通ヘッダを付ける。
                message = SendADstatus(counter, datetime.now(), EtherID.SendADstatus.value, b'\x00\x00\x00\x9c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
                message.parseWithGammaFrame(rowValues)
                
                if message.GPS_UTC_Timestamp_Year_ == 2048 or message.GPS_UTC_Timestamp_Month_ == 0 or message.GPS_UTC_Timestamp_Hour_ == 31:
                    continue
            
                if oldMinute != message.GPS_UTC_Timestamp_Minute_:
                    oldMinute = message.GPS_UTC_Timestamp_Minute_
                    estimateMiliSec = 0
                else:
                    estimateMiliSec += 200
                    if estimateMiliSec >= 59800:
                        estimateMiliSec = 59800
                message.commonHeader.logTime = datetime(message.GPS_UTC_Timestamp_Year_, message.GPS_UTC_Timestamp_Month_, message.GPS_UTC_Timestamp_Day_,
                                                        message.GPS_UTC_Timestamp_Hour_, message.GPS_UTC_Timestamp_Minute_, int(estimateMiliSec/1000), (estimateMiliSec%1000)*1000)
                if oldLogtime == None: oldLogtime = message.commonHeader.logTime

                if abs(message.commonHeader.logTime - oldLogtime).total_seconds() > 10 * 60:                    
                    #10分以上離れたR-DRデータは、別グループのR-DRと認識し、別のLayer Groupを作成する
                    controlPanel.setDataRange(logStartTime, logEndTime)
                    printRDRSummery(logger.logPrintWithConsol)
                    
                    logger.logPrintWithConsol("\n\n* 10 minute time Interval detected, line Index : " + str(lineIndex))
                    logger.logPrintWithConsol("* Before record time : " + str(oldLogtime))
                    logger.logPrintWithConsol("* Current record time : " + str(message.commonHeader.logTime))
                    
                    makeGroup = True
                    ## Init ##
                    logStartTime = None
                    logEndTime = None
                    oldMessage = None
                    oldMinute = -1
                    estimateMiliSec = 0
                    initMessage()
                    ## Init ##

                message.oldMessage = oldMessage
                if oldMessage != None:
                    oldMessage.nextMessage = message
                
                if makeGroup == True:
                    makeGroup = False
                    groupSubIndex += 1
                    groupName = '({0}-{1}){2}'.format(GroupIndex, groupSubIndex, fileFullName.split('/')[-1])
                    logger.logPrintWithConsol('\n\n R-DR Group <{}>'.format(groupName))
                    logger.logPrintWithConsol('Now loading...\n')
                    controlPanel.layerManager.makeLayerGroup(groupName)
                    controlPanel.addLayerGroup(groupName)

                if logStartTime == None:
                    logStartTime = message.commonHeader.logTime
                logEndTime = message.commonHeader.logTime
    
                layer = controlPanel.layerManager.getLayer(messageID)
                if layer == None:
                    newLayer = message.createLayer(getEtherIdDic(messageID)['name'], iface, detailMode = True, createArrow = True)
                    if newLayer != None:
                        controlPanel.layerManager.addLayer(messageID, newLayer)
                        layer = newLayer
            
                if layer != None:
                    message.drawQGIS(layer)
                
                oldLogtime = message.commonHeader.logTime
                oldMessage = message
            except Exception as e:
                logger.errLog('file:{0}, lineIndex:{1}, {2}'.format(os.path.basename(fileFullName),lineIndex,e))
                logger.errLog(traceback.format_exc())
            
    controlPanel.setDataRange(logStartTime, logEndTime)
    printRDRSummery(logger.logPrintWithConsol)
    logger.logPrintWithConsol('\nAll R-DR file load complete.')
       
def RDRdatFileLoad(GroupIndex, controlPanel, targetFiles, ethernetSpecVer = None):
    ## Init ##
    logStartTime = None
    logEndTime = None
    oldMessage = None
    index = 0
    lineIndex = 0
    oldMinute = -1
    oldLogtime = None
    estimateMiliSec = 0
    groupSubIndex = 0
    logger = getLogger()
    ## Init ##
    
    messageID = EtherID.SendADstatus.value
    
    if targetFiles == None or len(targetFiles) == 0:
        return
    
    init()
    setEthernetSpecVer(ethernetSpecVer)
    
    logger.logPrintWithConsol('Now on load {0} files. please wait...'.format(len(targetFiles)))
    
    makeGroup = True    
    for fileFullName in targetFiles:
        file = open(fileFullName, "rb")
        lineIndex = 0
        while True:
            try:
                data = file.read(136)
            except:
                data = None
            
            if data == None or not data:
                break

            index += 1
            lineIndex += 1
            
            try:
                #20byteのダミー共通ヘッダを付ける。
                message = SendADstatus(index, datetime.now(), EtherID.SendADstatus.value, b'\x00\x00\x00\x9c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + data)
                message.parse()
                
                if message.GPS_UTC_Timestamp_Year_ == 2048 or message.GPS_UTC_Timestamp_Month_ == 0 or message.GPS_UTC_Timestamp_Hour_ == 31:
                    continue
            
                if oldMinute != message.GPS_UTC_Timestamp_Minute_:
                    oldMinute = message.GPS_UTC_Timestamp_Minute_
                    estimateMiliSec = 0
                else:
                    estimateMiliSec += 200
                    if estimateMiliSec >= 59800:
                        estimateMiliSec = 59800
                message.commonHeader.logTime = datetime(message.GPS_UTC_Timestamp_Year_, message.GPS_UTC_Timestamp_Month_, message.GPS_UTC_Timestamp_Day_,
                                                        message.GPS_UTC_Timestamp_Hour_, message.GPS_UTC_Timestamp_Minute_, int(estimateMiliSec/1000), (estimateMiliSec%1000)*1000)
                if oldLogtime == None: oldLogtime = message.commonHeader.logTime

                if abs(message.commonHeader.logTime - oldLogtime).total_seconds() > 10 * 60:
                    #10分以上離れたR-DRデータは、別グループのR-DRと認識し、別のLayer Groupを作成する
                    controlPanel.setDataRange(logStartTime, logEndTime)
                    printRDRSummery(logger.logPrintWithConsol)
                    
                    logger.logPrintWithConsol("\n\n* 10 minute time Interval detected, line Index : " + str(lineIndex))
                    logger.logPrintWithConsol("* Before record time : " + str(oldLogtime))
                    logger.logPrintWithConsol("* Current record time : " + str(message.commonHeader.logTime))
                    
                    makeGroup = True
                    ## Init ##
                    logStartTime = None
                    logEndTime = None
                    oldMessage = None
                    oldMinute = -1
                    estimateMiliSec = 0
                    initMessage()
                    ## Init ##
                
                message.oldMessage = oldMessage
                if oldMessage != None:
                    oldMessage.nextMessage = message
                
                if makeGroup == True:
                    makeGroup = False
                    groupSubIndex += 1
                    groupName = '({0}-{1}){2}'.format(GroupIndex, groupSubIndex, fileFullName.split('/')[-1])
                    logger.logPrintWithConsol('\n\n R-DR Group <{}>'.format(groupName))
                    logger.logPrintWithConsol('Now loading...\n')
                    controlPanel.layerManager.makeLayerGroup(groupName)
                    controlPanel.addLayerGroup(groupName)

                if logStartTime == None:
                    logStartTime = message.commonHeader.logTime
                logEndTime = message.commonHeader.logTime
    
                layer = controlPanel.layerManager.getLayer(messageID)
                if layer == None:
                    newLayer = message.createLayer(getEtherIdDic(messageID)['name'], iface, detailMode = True, createArrow = True)
                    if newLayer != None:
                        controlPanel.layerManager.addLayer(messageID, newLayer)
                        layer = newLayer
            
                if layer != None:
                    message.drawQGIS(layer)
                
                oldMessage = message
                oldLogtime = message.commonHeader.logTime
                
            except Exception as e:
                logger.errLog('file:{0}, lineIndex:{1}, {2}'.format(os.path.basename(fileFullName),lineIndex,e))
                logger.errLog(traceback.format_exc())
            
    controlPanel.setDataRange(logStartTime, logEndTime)
    printRDRSummery(logger.logPrintWithConsol)
    logger.logPrintWithConsol('\nAll R-DR file load complete.')

def printRDRSummery(printF):
    if SendADstatus.Summery_TotalRecordLength > 0: #lengthによる統計は、QGIS draw時のみ算出可能
        fieldName = 'length'
        total = SendADstatus.Summery_TotalRecordLength
    else:    
        fieldName = 'count'
        total = SendADstatus.Summery_TotalRecordCount
    
    if total == 0:
        return
        
    ADStatusSummery = sorted(SendADstatus.Summery_ADStatusGroup.items(), key=lambda item: item[1][fieldName], reverse = True)
    ND2CodeSummery = sorted(SendADstatus.Summery_ND2Code.items(), key=lambda item: item[1][fieldName], reverse = True)
    CancelCodeSummery = sorted(SendADstatus.Summery_CancelCode.items(), key=lambda item: item[1][fieldName], reverse = True)
    HandsOffProhibitSummery = sorted(SendADstatus.Summery_HandOffProhibit.items(), key=lambda item: item[1][fieldName], reverse = True)
    
    printF("")
    printF("<AD Status Summery> order by {}".format(fieldName)) 
    nothing = True
    for key, value in ADStatusSummery:
        if key in SendADstatus.AD_status_symbolDic:
            nothing = False
            printF("{0} : {1:.1f}%".format(SendADstatus.AD_status_symbolDic[key][1], value[fieldName] * 100 / total))
    if nothing == True:
        printF('--')
    
    printF("")
    printF("<AD ND2Code Summery> order by {}".format(fieldName)) 
    nothing = True
    for key, value in ND2CodeSummery:
        if key in SendADstatus.ND2_code_symbolDic:
            nothing = False
            printF("{0} : {1:.1f}%".format(SendADstatus.ND2_code_symbolDic[key][1], value[fieldName] * 100 / total))
    if nothing == True:
        printF('--')
    
    printF("")
    printF("<AD CancelCode Summery> order by {}".format(fieldName))
    nothing = True
    for key, value in CancelCodeSummery:
        if key in SendADstatus.Cancel_code_symbolDic:
            nothing = False
            printF("{0} : {1:.1f}%".format(SendADstatus.Cancel_code_symbolDic[key][1], value[fieldName] * 100 / total))
    if nothing == True:
        printF('--')
        
    printF("")
    printF("<AD HandsOffProhibit Summery> order by {}".format(fieldName))
    nothing = True
    for key, value in HandsOffProhibitSummery:
        if key in SendADstatus.Hands_off_prohibit_symbolDic:
            nothing = False
            printF("{0} : {1:.1f}%".format(SendADstatus.Hands_off_prohibit_symbolDic[key][1], value[fieldName] * 100 / total))
    if nothing == True:
        printF('--')

def shpFileLoad(controlPanel, targetFiles):
    logStartTime = None
    logEndTime = None
    root = QgsProject.instance().layerTreeRoot()
    
    init()
                        
    for fileFullName in targetFiles:
        fileName = fileFullName[fileFullName.rfind('/')+1:fileFullName.rfind('.')]
        loadLayer = iface.addVectorLayer(fileFullName,'','ogr')
        if loadLayer == None:
            print('{0} load fail. already opened ?'.format(fileName))
        else:
            messageID, loadLayerInfo = setLayerStyle(fileFullName, loadLayer)
            if messageID == None:
                print('{0} load fail. Unknown Name'.format(fileName))
                target = root.findLayer(loadLayer.id())
                parent = target.parent()
                parent.removeChildNode(target)
            elif loadLayerInfo == None:
                print('{0} load skip.'.format(fileName))
                target = root.findLayer(loadLayer.id())
                parent = target.parent()
                parent.removeChildNode(target)
            else:
                try:
                    print('{0} now on loading... '.format(fileName))
                    features = loadLayerInfo[0].getFeatures()
                    first = next(features)
                    for feature in features:
                        pass
                    last = feature
                    firstTime = datetime.strptime(first.attributes()[0], '%Y/%m/%d %H:%M:%S.%f')
                    lastTime = datetime.strptime(last.attributes()[0], '%Y/%m/%d %H:%M:%S.%f')
                    if logStartTime == None:
                        logStartTime = firstTime
                    else:
                        if abs(logStartTime - firstTime).total_seconds() > 86400:
                            #１日以上差がある場合は、時間フィルタ適用できない。大きいほうに合わせる。また、blfの場合は、GPS信号がない場合は、1970年の初期値の時間になっている可能性もある。
                            if firstTime > logStartTime: #もっと狭い範囲で表示
                                logStartTime = firstTime
                        elif firstTime < logStartTime:
                            logStartTime = firstTime                                        
                    if logEndTime == None or lastTime > logEndTime:
                        logEndTime = lastTime
                    controlPanel.layerManager.addLayer(messageID, loadLayerInfo)
                    print('Ok.')
                except StopIteration:
                    print('Ok. But no data.')
                    target = root.findLayer(loadLayer.id())
                    parent = target.parent()
                    parent.removeChildNode(target)
                except Exception as e:
                    print('Failed. {0}'.format(e))
                    target = root.findLayer(loadLayer.id())
                    parent = target.parent()
                    parent.removeChildNode(target)
                
    controlPanel.setDataRange(logStartTime, logEndTime)
    print('All Shp file load complete.')
    
def realTimeView(controlPanel, interfaceName = None, someipmode = True, filter_srcMAC = None, filter_messageID = None, ethernetSpecVer = None, recommendLaneLayerRedraw = True, vehicle = 'PZ1A'): 
    if filter_srcMAC == None:
        filter_srcMAC = ["AA:BB:CC:DD:00:06", "AA:BB:CC:DD:10:06", "AA:BB:CC:DD:00:0C"] #ADAS , ADAS2 , HDMAP
    if filter_messageID == None:
        filter_messageID = []
    if ethernetSpecVer == None:
        ethernetSpecVer = datetime(9999, 12, 31) #always new specsheet
        
    vehicleCode = 0
    for key, vehicleCodeStr in VehicleCodeTable.items():
        if vehicle in vehicleCodeStr:
            vehicleCode = key
            break
    print('default Vehicle type = ' + VehicleCodeTable.get(vehicleCode, 'Unknown'))
    
    init()
    setEthernetSpecVer(ethernetSpecVer)
    setRecommandLaneViewerClear(recommendLaneLayerRedraw)
    setSrcMAC(','.join(filter_srcMAC))
    setVehicleType(vehicleCode)

    drawTask = QgisADASISdrawTask_RealTimeDraw(controlPanel, interfaceName, filter_srcMAC, filter_messageID, someipmode)
    return drawTask

def drawLayer(drawTask, layerManager, controlPanel, realTimeMode):
    global canvas
    
    if realTimeMode == True:
        realTimeMode = DrawMode.QGIS_RealTimeDraw
    else:
        realTimeMode = DrawMode.FullDraw
    
    dataCount = drawTask.getLayerRegisterBufDataCount()
    if dataCount == 0:
        return 
    
    controlPanel.setDataRange(drawTask.logStartTime, drawTask.logEndTime)
    
    logger = getLogger()
    logger.debugLog('<get drawLayer List>')
    reqList = drawTask.getLayerRegisterBuf()
#     reqList = sorted(reqList, key=lambda x: x[1].commonHeader.logTime)
    for req in reqList:
        messageID = req[0]
        message = req[1]
        
        try:            
            layer = layerManager.getLayer(messageID)
            if layer == None:
                logger.debugLog('<createLayer>, {}'.format(getEtherIdDic(messageID)['name']))
                newLayer = message.createLayer(getEtherIdDic(messageID)['name'], iface, realTimeMode)
                logger.debugLog('<createLayer>, complete')
                if newLayer != None and newLayer != [None]:
                    layerManager.addLayer(messageID, newLayer)
                    layer = newLayer
        
            if layer != None:
                logger.debugLog('<drawLayer> {} - {}'.format(getEtherIdDic(messageID)['name'], message.commonHeader.logTime))
                message.drawQGIS(layer, realTimeMode)
            
            if dataCount < 1000:
                #描画対象が1000個以下の時のみ、描画後画面更新。（描画データが多すぎると、一旦頻繁な画面更新は停止）
                if controlPanel.tracking == True:
                    moveToCanvasArea(canvas, controlPanel, message)
                QApplication.processEvents()
                
        except Exception as e:
            logger.errLog('{}'.format(e))
            logger.errLog(traceback.format_exc())
        
def readHDMAP(filepath = None, filepath_oldHDMAP = None, laneIDconvert = False):
    ProfileMessage.initHDMAPdic()
    logger = getLogger()
    if filepath != None:
        logger.logPrintWithConsol('Now reading HDMAP... ({0})'.format(filepath))
        ProfileMessage.readHDMAPdic(False, filepath, laneIDconvert)
    
    if filepath_oldHDMAP != None:
        logger.logPrintWithConsol('Now reading Old HDMAP... ({0})'.format(filepath_oldHDMAP))
        ProfileMessage.readHDMAPdic(True, filepath_oldHDMAP, laneIDconvert)
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
