# -*- coding: utf-8 -*-
import struct
import collections
import dpkt
from GlobalVar import getLogger, getProcessMessageList
from TypeDef import someipIdDic 

IPdic = {
'192.168.11.1':'A-IVI',
'192.168.12.1':'A-IVI',
'192.168.15.1':'A-IVI',
'192.168.16.1':'A-IVI',
'192.168.17.1':'A-IVI',
'192.168.10.1':'A-IVI',
'192.168.40.1':'A-IVI',
'192.168.60.1':'A-IVI',
'192.168.61.1':'A-IVI',
'192.168.254.1':'A-IVI',
'192.168.11.2':'Meter',
'192.168.12.2':'Meter',
'192.168.16.2':'Meter',
'192.168.10.2':'Meter',
'192.168.40.2':'Meter',
'192.168.60.2':'Meter',
'192.168.11.3':'A-IVC',
'192.168.12.3':'A-IVC',
'192.168.14.3':'A-IVC',
'192.168.17.3':'A-IVC',
'192.168.61.3':'A-IVC',
'192.168.254.3':'A-IVC',
'192.168.11.4':'CGW',
'192.168.11.4':'CGW',
'192.168.12.4':'CGW',
'192.168.15.4':'CGW',
'192.168.18.4':'CGW',
'192.168.50.6':'ADAS_ECU',
'192.168.60.6':'ADAS_ECU',
'192.168.50.7':'FRONTCAM',
'192.168.50.8':'RADAR',
'192.168.11.9':'HUD',
'192.168.12.9':'HUD',
'192.168.16.9':'HUD',
'192.168.11.10':'DTOOL',
'192.168.11.10':'DTOOL',
'192.168.50.11':'AVM',
'192.168.11.12':'HDMAP',
'192.168.12.12':'HDMAP',
'192.168.18.12':'HDMAP',
'192.168.19.12':'HDMAP',
'192.168.50.12':'HDMAP',
'192.168.14.14':'HDMAP_External',
'192.168.19.14':'HDMAP_External',
'192.168.40.19':'OMC',
'192.168.60.19':'OMC',
'192.168.50.20':'ADAS_ECU_2',
'192.168.50.23':'FRONTCAM_2',
'237.50.0.1':'ADAS1+2+AVM+FRONTCAM_2+HDMAP',
'237.50.25.1':'FRONTCAM_2+HDMAP',
'237.50.54.1':'ADAS1+2',
'237.50.52.1':'ADAS1+2',
'237.50.83.1':'ADAS1+2',
'237.50.69.1':'ADAS1+2',
'237.50.98.1':'ADAS1+2+AVM',
'237.50.100.1':'ADAS1+2+AVM',
'237.50.8.1':'ADAS1+2',
'237.50.9.1':'ADAS1+2',
'237.50.10.1':'ADAS1+2',
'237.50.11.1':'ADAS1+2',
'237.50.12.1':'ADAS1+2',
'237.50.42.1':'ADAS1+2',
'237.50.43.1':'ADAS1+2',
'237.50.103.1':'ADAS1+2+AVM',
'237.50.99.1':'ADAS1+2+AVM',
'237.50.104.1':'ADAS1+2+AVM',
'237.50.23.1':'ADAS1+2',
'237.50.57.1':'ADAS1+2',
'237.61.0.1':'IVC+IVI',
'237.60.0.1':'IVI+Meter'
}

HEADER_FIELDS = [
    # field_name, byte
    ('length',    4),
    ('timestamp', 6),
    ('seq',       2),
    ('ID',        4),
    ('msgcnt',    4),
]

MAXIMUM_VALID_LENGTH = 2000
MINIMUM_VALID_LENGTH = 16
HEADERSIZE = 20
SOMEIP_HEADERSIZE = 16
HEADER_FIELDNAMES = [t[0] for t in HEADER_FIELDS]
Header = collections.namedtuple('Header', HEADER_FIELDNAMES)
Packet = collections.namedtuple('Packet', ['header', 'dat'])

# 分析のための情報
SomeipListup = {}
SomeipMessageIDmatchListup = {}
analyzeSomeIPheader = False
someipFilter = set()

def initPCAPLoader(doSomeIPheaderAnalyze = False):
    global analyzeSomeIPheader
    global someipFilter
    SomeipListup.clear()
    SomeipMessageIDmatchListup.clear()
    analyzeSomeIPheader = doSomeIPheaderAnalyze
    
    someipFilter = set()
    targetMessageIDList = getProcessMessageList()
    for key, value in someipIdDic.items():
        if type(value) == type([]):
            for valueItem in value:
                if valueItem in targetMessageIDList.keys():
                    someipFilter.add(key)
                    break
        else:
            if value in targetMessageIDList.keys():
                someipFilter.add(key)
    
def getSomeipListup():
    return SomeipListup

class TCPStream:
    def __init__(self):
        self._buf = bytearray()
        self._v = []
        self._seqno = None
        self._timestamp = 0
        # 再送待ちタイムアウト閾値 [s]
        # 閾値以上待っても再送されてこなかった場合はログ異常と見做して先に進む
        self._THR_RETRANS_TIMER = 1.
        self.tcpDataBuf = b''

    def reset(self, seqno, timestamp):
        self._buf = bytearray()
        self._v = []
        self._seqno = seqno
        self._timestamp = timestamp

    def addSequenceData(self, buf, seqno):
        if self._seqno is None:
            # handshake がログに残っていなかった場合
            # はじめに見つけた TCP セグメントを先頭とみなす
            self._seqno = seqno
            
        # 車内IFのSome/IP的には、一方的な通知であるため、seq番号再設定時は、必ずSYNCが事前にある。
        # ただ、地図更新のTCP/IPのHTTP通信の場合、相手からSYNCが来た可能性がある。そのため、急に値が変化する可能性がある。
        if abs(seqno - self._seqno) > 1522*100: 
            # MSSサイズの100倍。100パケット以上パケット落ちの可能性は低い。
            #　つまり、これほどのseqの飛びは、再送ではなく、新たなseqの始まりと認識すべき
            self._seqno = seqno
            
        if seqno < self._seqno:
            # 受信済みデータの再送
            buf = buf[self._seqno - seqno:]
            seqno = self._seqno

        bidx = seqno - self._seqno
        eidx = bidx + len(buf)
        if eidx > len(self._buf):
            dummylen = seqno - self._seqno + len(buf) - len(self._buf)
            self._buf = self._buf + bytearray(dummylen)
            self._v = self._v + [False] * dummylen

        self._buf[bidx:eidx] = bytearray(buf)
        self._v[bidx:eidx] = [True] * len(buf)

    def retransTO(self, timestamp):
        if len(self._v) == 0 or self._v[0]:
            self._timestamp = timestamp
            return False
        elif timestamp - self._timestamp < self._THR_RETRANS_TIMER:
            return False
        else:
            idx = 0
            for v in self._v:
                if v:
                    break
                else:
                    idx = idx + 1
            self._buf = self._buf[idx:]
            self._v = self._v[idx:]
            self._seqno = self._seqno + idx
            self._timestamp = timestamp
            return True

    def currentPayload(self):
        idx = 0
        for v in self._v:
            if v:
                idx = idx + 1
            else:
                break
        ret = bytes(self._buf[0:idx])
        self._buf = self._buf[idx:]
        self._v = self._v[idx:]
        self._seqno = self._seqno + idx
        return ret
    
    def recv(self, L4_layer, timestamp):
        if len(L4_layer.data) == 0:
            if L4_layer.flags & dpkt.tcp.TH_SYN:
                self.reset(L4_layer.seq + 1, timestamp)
            return 0

        self.addSequenceData(L4_layer.data, L4_layer.seq)
        if self.retransTO(timestamp):
            self.tcpDataBuf = b''
        
        payload = self.currentPayload()
        self.tcpDataBuf += payload
        return len(payload)

    def get(self):
        return self.tcpDataBuf
    
    def setRemains(self, remains):
        self.tcpDataBuf = remains
        
def parseHeader(buf):
    if len(buf) != HEADERSIZE:
        return None

    headerDic = {}
    for name, length in HEADER_FIELDS:
        unpacked = struct.unpack('>' + str(length) + 'B', buf[:length])
        headerDic[name] = int.from_bytes(unpacked, 'big')
        buf = buf[length:]

    return Header(**headerDic)

def getSomeipPayload(buf, index, ts, fromStr, toStr): #return ID,Payload,Remains
    if len(buf) >= SOMEIP_HEADERSIZE:
        unpacked = struct.unpack('>4B', buf[0:4])
        serviceID = int.from_bytes(unpacked, 'big')
        unpacked = struct.unpack('>4B', buf[4:8])
        length = int.from_bytes(unpacked, 'big') + 8 #lengthまでのサイズは含んでないため
        if MAXIMUM_VALID_LENGTH < length or MINIMUM_VALID_LENGTH > length: #残りは無効なデータ。バッファクリア
            return None, None, b''
        if len(buf) < length:
            return None, None, buf
        payload = buf[SOMEIP_HEADERSIZE:length]
        buf = buf[length:]
        
        # someip分析のためのリストアップ
        if analyzeSomeIPheader == True:
            if index == None:
                index = 0
            if ts == None:
                ts = 0
            if fromStr == None:
                fromStr = '-'
            if toStr == None:
                toStr = '-'
            if not(fromStr + ',' + toStr in SomeipListup):
                SomeipListup[fromStr + ',' + toStr] = {}
            if serviceID == 0xffff8100:
                if len(payload) >= 8 and payload[0:4] != b'\x00\x00\x00\x01':
                    unpacked = struct.unpack('>4B', payload[4:8])
                    lengthOfEntriesArray = int.from_bytes(unpacked, 'big')
                    for i in range(8,8+lengthOfEntriesArray,16):
                        if payload[i] == 0x00:
                            serviceName = '[0:Find]'
                        elif payload[i] == 0x01:
                            serviceName = '[1:Offer]'
                        elif payload[i] == 0x06:
                            serviceName = '[6:Subscribe]'
                        elif payload[i] == 0x07:
                            if payload[i+11] == 0x00:
                                serviceName = '[7({}):SubscribeNack]'.format(payload[i+11])
                                logger = getLogger()
                                logger.errLog("logIndex:{0}, from:{1}, to:{2} (SubscribeNack Founded)".format(index, fromStr, toStr))
                            else:
                                serviceName = '[7({}):SubscribeAck]'.format(payload[i+11])
                        else:
                            serviceName = '[{0}]'.format(int(payload[i]))
                        serviceName += hex(int.from_bytes(payload[i+4:i+6], 'big'))
                        if not(serviceName in SomeipListup[fromStr + ',' + toStr]):
                            SomeipListup[fromStr + ',' + toStr][serviceName] = {}
                            SomeipListup[fromStr + ',' + toStr][serviceName]['index'] = index
                            SomeipListup[fromStr + ',' + toStr][serviceName]['ts'] = ts
                            SomeipListup[fromStr + ',' + toStr][serviceName]['from'] = fromStr
                            SomeipListup[fromStr + ',' + toStr][serviceName]['to'] = toStr
                            SomeipListup[fromStr + ',' + toStr][serviceName]['serviceID'] = serviceName
                #加工のCommon Headerを付けて、Subscribeも解析できるようにする            
                payload = struct.pack('>I', len(payload)+20) + b'\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x81\x00\x00\x00\x00\x00' + payload
            else: #通常メッセージ
                serviceName = hex(serviceID)
                if not(serviceName in SomeipListup[fromStr + ',' + toStr]):
                    SomeipListup[fromStr + ',' + toStr][serviceName] = {}
                    SomeipListup[fromStr + ',' + toStr][serviceName]['index'] = index
                    SomeipListup[fromStr + ',' + toStr][serviceName]['ts'] = ts
                    SomeipListup[fromStr + ',' + toStr][serviceName]['from'] = fromStr
                    SomeipListup[fromStr + ',' + toStr][serviceName]['to'] = toStr
                    SomeipListup[fromStr + ',' + toStr][serviceName]['serviceID'] = serviceName
                                    
        return serviceID, payload, buf
    else:
        return None, None, buf

def getMpuPackets(buf, onlyReadFirstMessage = False, lengthCheck = True):
    ret = []
    while len(buf) >= HEADERSIZE:
        if lengthCheck == True:
            unpacked = struct.unpack('>4B', buf[:4])
            length = int.from_bytes(unpacked, 'big')
            if MAXIMUM_VALID_LENGTH < length: #無効なデータ。バッファクリア
                return ret, b''
            if length < HEADERSIZE or len(buf) < length:
                return ret, buf
            header = parseHeader(buf[:HEADERSIZE])
            packet = Packet(header = header, dat = buf[:length])
            ret.append(packet)
            if onlyReadFirstMessage == True:
                buf = b''
                break
            else:
                buf = buf[length:]
        else:
            header = parseHeader(buf[:HEADERSIZE])
            packet = Packet(header = header, dat = buf)
            ret.append(packet)
            buf = b''
            break
    return ret, buf

def analyzeSomeIPpayload(buf, index, ts, fromStr, toStr, onlyReadFirstMessage, useSomeIPfilter):
    mpus = []
    remains = buf
    while True:
        someipID, someipPayload, remains = getSomeipPayload(remains, index, ts, fromStr, toStr)
        if someipPayload == None:
            break
        if useSomeIPfilter and (not someipID in someipFilter):
            break
        payloadMpus, _ = getMpuPackets(someipPayload, onlyReadFirstMessage, lengthCheck=False)
        for i in range(len(payloadMpus)): #someipヘッダありの場合は、メッセージ内の共通ヘッダのIDではなく、someipのIDから求める（共通ヘッダのIDが正しく出ない場合も解析するため）
            # 注意：lengthCheckすることで、MAPECU絡みのないほかのパケットで、たまたまMessageID位置にあった値で誤解釈しないようにできていたが、
            #　このSomeIPのIDで区別する場合は、（共通ヘッダがAll 0の場合も解釈できるようにするため）、lengthCheckをしないため、MAPECU絡みのパケットでないことを確実に示す必要がある。
            # なので、現在のMessageIDの値関係なく、SomeIPのIDを入れることで、EtherID一覧に存在しないIDは解釈されないようにする。
            # ただし、この場合は、同じSomeIP IDを持つ場合は、正しく分類ができない。（JP/NA仕様違いによるもの）
            # その場合は、どっちの仕様かを事前に確認必要。
            if someipID in someipIdDic: #データ台帳にあるもの
                #リストに存在するsomeipIDの場合。 
                messageID = someipIdDic[someipID]
                if type(messageID) == type([]):
                    lastUsedMessageID = SomeipMessageIDmatchListup.get(someipID, 0)
                    if lastUsedMessageID != 0:
                        messageID = lastUsedMessageID
                    elif payloadMpus[i].header.ID != 0:
                        messageID = payloadMpus[i].header.ID
                        SomeipMessageIDmatchListup[someipID] = messageID
                    else:
                        messageID = messageID[0] #わからない時は、配列の前方のether IDに設定。
            else:
                messageID = someipID
            payloadMpus[i] = payloadMpus[i]._replace(header=payloadMpus[i].header._replace(ID = messageID)) 
        mpus += payloadMpus
        # SomeIP subscribe メッセージまとめのため、一般メッセージが届いた事が分かる疑似メッセージを追加する。これが解析される事で、SubscribeMessageが処理される。
        if someipID != 0xffff8100 and (someipID in someipIdDic): #subscribeのffff8100は、ヘッダ解析時にすでに追加されたため、ここでは、一般メッセージにたいしてのみ処理。
            # httpパケットなど、someipヘッダがない項目は除外。更に、一覧にないSimeipIDは解析対象外であるのと、subcribe headerは、表示しているため、ここでコンテンツやり取り一覧にリストアップする必要はない。
            fakeHeaderBuf = struct.pack('>I', 20+8) + b'\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x81\x00\x00\x00\x00\x00'
            fakeContentsBuf = b'\x00\x00\x00\x01' + struct.pack('>I', someipID)
            mpus += [Packet(header = parseHeader(fakeHeaderBuf), dat = fakeHeaderBuf + fakeContentsBuf)]
                    
        if onlyReadFirstMessage == True:
            break
    
    return mpus, remains

def getTcpPackets(tcpDataBuf, someipmode, index = None, ts = None, fromStr = None, toStr = None, onlyReadFirstMessage = False, useSomeIPfilter = False):
    if tcpDataBuf[:8] == b'GET http' or tcpDataBuf[:9] == b'POST http' or tcpDataBuf[:4] == b'HTTP':
        payload = struct.pack('>I', 20+len(tcpDataBuf)) + b'\x00\x00\x00\x00\x00\x00\x00\x00\xee\xee\xee\xee\x00\x00\x00\x00' + tcpDataBuf
        mpus, _ = getMpuPackets(payload, onlyReadFirstMessage, lengthCheck=False)
        remains = b''
        
    elif b'Via: 1.1 HD MAP' in tcpDataBuf:
        if b'<?xml' in tcpDataBuf: index = tcpDataBuf.index(b'<?xml')
        elif b'{' in tcpDataBuf: index = tcpDataBuf.index(b'{')
        else: index = -1
        if index >= 0:
            payload = struct.pack('>I', 20+len(tcpDataBuf[index:])) + b'\x00\x00\x00\x00\x00\x00\x00\x00\xee\xee\xee\xee\x00\x00\x00\x00' + tcpDataBuf[index:]
            mpus, _ = getMpuPackets(payload, onlyReadFirstMessage, lengthCheck=False)
            remains = b''
        else:
            mpus = []
            remains = b''
                
    elif someipmode: #無効なSomeIPヘッダの場合は残りバッファクリア
        mpus, remains = analyzeSomeIPpayload(tcpDataBuf, index, ts, fromStr, toStr, onlyReadFirstMessage, useSomeIPfilter)  
            
    else: #無効な共通ヘッダの場合は残りバッファクリア
        mpus, remains = getMpuPackets(tcpDataBuf, onlyReadFirstMessage, lengthCheck=True)
        
    return (mpus, remains)

def getUdpPackets(udpDataBuf, someipmode, index = None, ts = None, fromStr = None, toStr = None, onlyReadFirstMessage = False, useSomeIPfilter = False):
    if someipmode:
        mpus, _ = analyzeSomeIPpayload(udpDataBuf, index, ts, fromStr, toStr, onlyReadFirstMessage, useSomeIPfilter)  

    else:
        mpus, _ = getMpuPackets(udpDataBuf, onlyReadFirstMessage, lengthCheck=True)
    
    #UDPは残りバッファ引き継がない。
    return (mpus, b'')

def getCANFramePacket(dataBuf, CAN_chanel_filter = None):
        mChannel = (dataBuf[0]<<8) + dataBuf[1]
        if CAN_chanel_filter != None and not(mChannel in CAN_chanel_filter):
            return []
        mLength = (dataBuf[2]<<8) + dataBuf[3]
        mID = (dataBuf[4]<<24) + (dataBuf[5]<<16) + (dataBuf[6]<<8) + dataBuf[7]
        mTS = dataBuf[8:16]
        
        if mID > 0xFFF: #長いIDの物は扱わない
            return []
        if mLength <= 8:
            #疑似common headerをつける。Ether ID と重複しないように、CAN IDの前に、CAFを付ける。
            headerBuf = struct.pack('>I', 20+mLength) + mTS[2:] + struct.pack('>H', mChannel) + struct.pack('>I', 0xCAF00000 + mID) + b'\x00\x00\x00\x00'
        elif mLength > 8:
            headerBuf = struct.pack('>I', 20+mLength) + mTS[2:] + struct.pack('>H', mChannel) + struct.pack('>I', 0xCAFFD000 + mID) + b'\x00\x00\x00\x00'
        header = parseHeader(headerBuf)
        packet = Packet(header = header, dat = headerBuf + dataBuf[16:])
            
        return [packet]
