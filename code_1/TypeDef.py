import abc
from datetime import timedelta
import struct
from GlobalVar import getLogIndex, getIgnoreSameMsgcnt, getResource, getLogger
from enum import Enum
import math
try:
    from qgis.core import *
    from qgis.gui import *
    from qgis.PyQt import QtGui
    from PyQt5.QtCore import QDateTime
    from PyQt5.QtGui import QColor
except:
    pass

class Structure:
    pass

# AD2緊急停止で使う車種コード
# Vehicle Parameterメッセージとして、ADAS->MAPECUに送っている。
# Action Flag選択時の車種番号コードは、ADASの内部で管理し、MAPECUに送らないため、ログ上では分からない。
# そのため、この車種区別から、Action Flag選択位置は、読み替えて変換する必要がある。（Recommended Lane Messageでの処理を参照）
VehicleCodeTable = {0x00:'PZ1A/LZ1FE', 0x01:'J32V/J42U', 0x02:'P61QR', 0x03:'P33A/P42SV', 0x04:'P42QR', 0x05:'PZ1D'}

class EtherID(Enum):
    AllMessageTimeLog    =    0x0000FFFF
    SubscribeMessage    =    0xFFFF8100
    ServiceID    =    0xFFFE8100
    HttpMessage    =    0xEEEEEEEE
    ExternalLonLatMessage = 0xDDDD0000
    #Ether Frame
    TimeStampMessage    =    0x00000000
    ErrorMessage    =    0x00000001
    SendVINData    =    0x00000002
    USBupdateinfo    =    0x00000013
    specificADmode    =    0x00000014
    VehicleParameterMessage    =    0x00000015
    SensorRedundancyStatus    =    0x000000fe
    PerformanceMessage    =    0x000000ff
    ProfileControlMessage    =    0x00000106
    PathControlMessage    =    0x00000107
    PositionMessage    =    0x00000108
    IntersectionMessage    =    0x00000109
    ProfileMessage    =    0x0000010a
    GlobalDataMessage    =    0x0000010b
    GlobalSDMapDataMessage    =    0x0000010c
    RecommendLaneMessage_JP =    0x00000110
    RecommendLaneMessage_US =    0x00000158
    IVIDataStatus    =    0x00000120
    MapLinkageStatus    =    0x00000121
    RequestlostMessage    =    0x00000151
    RequestInitialMessage    =    0x00000152
    ReconstructorLaneList    =    0x00000153
    ADPositionMessage    =    0x00000154
    IVIPositionMessage    =    0x00000155
    ADASISGlobalDataMessage    =    0x00000157
    CarPositionMessage    =    0x00000300
    SensorDataMessage    =    0x00000500
    GNSSDataMessage    =    0x00000501
    SensorCalibrationMessage    =    0x00000502
    CAMLaneInfrastructureInfo    =    0x00000601
    TransferToEyeQforRSD    =    0x00000608
    TransferFromEyeQforRSD    =    0x00000609
    TTPResponseMsg    =    0x00000620
    TTPErrorAleartMsg    =    0x00000625
    TTPMapManifestRequestMsg    =    0x00000626
    TTPTileRequestMsg    =    0x00000627
    TTPTileDropMsg    =    0x00000628
    TTPEyeQErrorAlertsMsg    =    0x00000629
    TTPResponseMsg_US    =    0x0000062A
    TTPErrorAleartMsg_US    =    0x0000062B
    TTPMapManifestRequestMsg_US    =    0x0000062C
    TTPTileRequestMsg_US    =    0x0000062D
    TTPTileDropMsg_US    =    0x0000062E
    TTPEyeQErrorAlertsMsg_US    =    0x0000062F
    VehicleInfo    =    0x00000700
    SendADstatus    =    0x00000801
    AligmentRequest    =    0x00000901
    AligmentResponse    =    0x00000902
    ADASISv2POSITION    =    0x00001080
    ADASISv2SEGMENT    =    0x00001081
    ADASISv2STUB    =    0x00001082
    ADASISv2PROFILESHORT    =    0x00001083
    ADASISv2PROFILELONGforAD2    =    0x00001084
    ADASISv2METADATA    =    0x00001085
    Road_Data_4_ADAS    =    0x00001090
    RouteInfo    =    0x00001091
    DataForEyeQ    =    0x006d8001
    CAMInfrastructureList = 0x00678001
    DebugEther = 0x00438003
    #CAN Frame
    CAN_ADASISv2POSITION = 0xCAF0054C
    CAN_ADASISv2SEGMENT  = 0xCAF0036D
    CAN_ADASISv2STUB     = 0xCAF00370
    CAN_ADASISv2PROFILESHORT = 0xCAF0025E
    CAN_ADASISv2PROFILELONGforAD2 = 0xCAF0036A
    CAN_LATLON_POS = 0xCAF003CD
    CAN_ADASISv2METADATA = 0xCAF006A1
    CAN_Road_Data_4_ADAS = 0xCAF0052D
    CAN_NAVI_STATUS_ADAS = 0xCAF003C1
    CAN_FRCAMERA_A2 = 0xCAF00517
    CAN_ADAS_ModeDisplay = 0xCAF00601
    CAN_VDC_A116_WheelPulse = 0xCAFFD226
    CAN_ADAS_GlobalTimeStamp = 0xCAF00562
    CAN_VDC_A117SC_Sensor = 0xCAFFD1AB
    CAN_IVI_A5_SatelliteGPSNumber = 0xCAF003C7
    CAN_IVI_A105_GPSPosition = 0xCAF00615

#implementQGIS'パラメータについて　（ADASIS_LogViewerによるQGISリアルタイム描画時のみ影響）
#implementQGISがあると、通常描画と、realTime描画において、指定した間隔でメッセージ処理。ただし、実際描画する際に、realTime時は描画処理しないなどは、それぞれの描画関数で判断可能。
#implementQGISは指定するが、realTimeModeで描画しないもので、メッセージ処理もしたくない場合は、-1は明示的にrealtimeModeに指定すれば、はメッセージ処理自体をしない。。
etherIdDic = {
    0x0000FFFF:{'name':'All Message TimeLog',           'period':None,  'class':'TimeStampMessage',         'useMacro':True}, # 全体フレームまとめ用。実際は存在しないフレームタイプ
    0xFFFF8100:{'name':'All Subscribe Message',         'period':None,  'class':'SubscribeMessage'}, # 通信確認用。実際は存在しないフレームタイプ
    0xFFFE8100:{'name':'Service ID',                    'period':None,  'class':'SubscribeMessage'}, # 通信確認用。実際は存在しないフレームタイプ
    0xEEEEEEEE:{'name':'Http Message',                  'period':None,  'class':'HttpMessage',    'implementOpenGLdraw':0},
    0xDDDD0000:{'name':'External LonLat info',          'period':None,  'class':'ExternalLonLatinfo'},
    # External LonLat infoがファイル数によって、0xDDDD0000 + ファイル数の分使うので、0xDDDDとしては他のメッセージは追加しないこと。
    0x00000000:{'name':'Time Stamp Message',            'period':100,   'class':'TimeStampMessage'},
    0x00000001:{'name':'Error Message',                 'period':100,   'class':'ErrorMessage',             'implementQGIS':0},
    0x00000002:{'name':'Send VIN Data',                 'period':500,   'class':'VinDataMessage'},
    0x00000013:{'name':'USB update info',               'period':None,  'class':'USBUpdateInfoMessage'},
    0x00000014:{'name':'specific AD mode',              'period':500,   'class':'SpecificADModeMessage',    'implementQGIS':500,      'implementOpenGLdraw':500},
    0x00000015:{'name':'Vehicle Parameter Message',     'period':500,   'class':'VehicleParameterMessage',  'implementQGIS':10000,    'implementOpenGLdraw':10000},
    0x000000fe:{'name':'Sensor Redundancy Status',      'period':100,   'class':'SensorRedundancyStatusMessage'},
    0x000000ff:{'name':'Performance Message',           'period':100,   'class':'PerformanceMonitorMessage', 'implementQGIS':0, 'implementQGISinRealTimeMode':500},
    0x00000106:{'name':'Profile Control Message',       'period':None,  'class':'ProfileControlMessage'},
    0x00000107:{'name':'Path Control Message',          'period':None,  'class':'PathControlMessage',       'implementQGIS':0, 'implementQGISinRealTimeMode':-1}, #リアルタイム描画では解析不要。分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要
    0x00000108:{'name':'Position Message',              'period':100,   'class':'PositionMessage',          'implementOpenGLdraw':0},
    0x00000109:{'name':'Intersection Message',          'period':None,  'class':'IntersectionMessage'},
    0x0000010a:{'name':'Profile Message',               'period':None,  'class':'ProfileMessage',           'useMultiLine':True, 'useMacro':True, 'implementQGIS':0,    'implementOpenGLdraw':0}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要
    0x0000010b:{'name':'Global Data Message',           'period':None,  'class':'GlobalDataMessage',        'useMultiLine':True, 'useMacro':True, 'implementQGIS':0,    'implementQGISinRealTimeMode':-1}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要
    0x0000010c:{'name':'Global SD Map Data Message',    'period':None,  'class':'TimeStampMessage'}, #国内向け非対応
    0x00000110:{'name':'Recommend Lane Message',        'period':None,  'class':'RecommendLaneMessage_JP',   'useMultiLine':True, 'useMacro':True, 'implementQGIS':0,    'implementOpenGLdraw':0}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要
    0x00000158:{'name':'Recommend Lane Message(US)',    'period':None,  'class':'RecommendLaneMessage_US',   'useMultiLine':True, 'useMacro':True, 'implementQGIS':0,    'implementOpenGLdraw':0}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要
    0x00000120:{'name':'IVI Data Status',               'period':100,   'class':'IVIDataStatus'},
    0x00000121:{'name':'MapLinkage Status',             'period':100,   'class':'MapLinkageStatus'},
    0x00000151:{'name':'Request lost Message',          'period':None,  'class':'RequestLostMessage'},
    0x00000152:{'name':'Request Initial Message',       'period':None,  'class':'RequestInitialMessage'},
    0x00000153:{'name':'Reconstructor LaneList',        'period':None,  'class':'ReconstructorLaneList',    'useMultiLine':True, 'implementQGIS':0, 'implementQGISinRealTimeMode':-1}, #-1は明示的にrealtimeMode時はメッセージ処理自体をしない事を意味。
    0x00000154:{'name':'AD Position Message',           'period':50,    'class':'ADPositionMessage',        'useMacro':True,     'implementQGIS':500, 'implementOpenGLdraw':500},
    0x00000155:{'name':'IVI Position Message',          'period':500,   'class':'IVIPositionMessage',       'useMacro':True,     'implementQGIS':500},
    0x00000157:{'name':'ADASIS GlobalDataMessage',      'period':100,  'class':'ADASIS_GlobalDataMessage', 'useMultiLine':True, 'useMacro':True, 'implementQGIS':0, 'implementQGISinRealTimeMode':-1}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要
    0x00000300:{'name':'CarPosition Message',           'period':20,    'class':'CarPositionMessage',       'useMacro':True,'outputCSV':True,     'implementQGIS':500,   'implementOpenGLdraw':500},
    0x00000500:{'name':'Sensor Data Message',           'period':20,    'class':'SensorDataMessage'},
    0x00000501:{'name':'GNSS Data Message',             'period':200,   'class':'GNSSDataMessage',          'useMacro':True,'outputCSV':True,     'implementQGIS':0,     'implementOpenGLdraw':500},
    0x00000502:{'name':'Sensor Calibration Message',    'period':500,   'class':'SensorCalibrationMessage'},
    0x00000601:{'name':'CAM LaneInfrastructureInfo',    'period':30,    'class':'CAMLaneInfrastructureInfo', 'implementQGIS':500, 'implementQGISinRealTimeMode':-1},
    0x00000608:{'name':'Transfer To EyeQ for RSD',      'period':None,  'class':'TransferToEyeQforRSD'},
    0x00000609:{'name':'Transfer From EyeQ for RSD',    'period':None,  'class':'TransferFromEyeQforRSD'},
    0x00000620:{'name':'TTP Response Msg',              'period':None,  'class':'TTPResponseMessage'},
    0x00000625:{'name':'TTP Error Aleart Msg',          'period':None,  'class':'TTPErrorAleartMessage'},
    0x00000626:{'name':'TTP Map Manifest Request Msg',  'period':None,  'class':'TTPMapManifestRequestMessage'},
    0x00000627:{'name':'TTP Tile Request Msg',          'period':None,  'class':'TTPTileRequestMessage'},
    0x00000628:{'name':'TTP Tile Drop Msg',             'period':None,  'class':'TTPTileDropMessage'},
    0x00000629:{'name':'TTP EyeQ Error Alerts Msg',     'period':None,  'class':'TTPEyeQErrorAlertsMessage'},
    0x0000062A:{'name':'TTP Response Msg(ADAS)',        'period':None,  'class':'TTPResponseMessage'},
    0x0000062B:{'name':'TTP Error Aleart Msg(ADAS)',    'period':None,  'class':'TTPErrorAleartMessage'},
    0x0000062C:{'name':'TTP Map Manifest Request Msg(ADAS)','period':None,'class':'TTPMapManifestRequestMessage'},
    0x0000062D:{'name':'TTP Tile Request Msg(ADAS)',    'period':None,  'class':'TTPTileRequestMessage'},
    0x0000062E:{'name':'TTP Tile Drop Msg(ADAS)',       'period':None,  'class':'TTPTileDropMessage'},
    0x0000062F:{'name':'TTP EyeQ Error Alerts Msg(ADAS)','period':None, 'class':'TTPEyeQErrorAlertsMessage'},
    0x00000700:{'name':'Vehicle Info',                  'period':10,    'class':'VehicleInfo',              'outputCSV':True,       'implementQGIS':100, 'implementQGISinRealTimeMode':500, 'implementOpenGLdraw':100},
    0x00000801:{'name':'send AD status',                'period':200,   'class':'SendADstatus',             'outputCSV':True,       'implementQGIS':0, 'implementQGISinRealTimeMode':500, 'implementOpenGLdraw':0}, # message period is 200ms
    0x00000901:{'name':'Aligment Request',              'period':None,  'class':'AligmentRequest'},
    0x00000902:{'name':'Aligment Response',             'period':None,  'class':'AligmentResponse'},
    0x00001080:{'name':'ADASISv2 POSITION',             'period':500,   'class':'ADASISv2POSITION_ETH',      'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0x00001081:{'name':'ADASISv2 SEGMENT',              'period':50,    'class':'ADASISv2SEGMENT_ETH',       'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0x00001082:{'name':'ADASISv2 STUB',                 'period':50,    'class':'ADASISv2STUB_ETH',          'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0x00001083:{'name':'ADASISv2 PROFILE SHORT',        'period':20,    'class':'ADASISv2PROFILESHORT_ETH',  'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0x00001084:{'name':'ADASISv2 PROFILE LONG for AD2', 'period':50,    'class':'ADASISv2PROFILELONG_ETH',   'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0x00001085:{'name':'ADASISv2 METADATA',             'period':3000,  'class':'ADASISv2METADATA_ETH'},
    0x00001090:{'name':'Road_Data_4_ADAS',              'period':500,   'class':'Road_Data_4_ADAS_ETH',      'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0x00001091:{'name':'LatLon Position of IVI',        'period':250,   'class':'ADASISv2RouteInfo_ETH',     'implementQGIS':0}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要  # message period is 500ms (250ms+250ms)
    0x006d8001:{'name':'(ADAS-FrCamera) DataForEyeQ',   'period':None,  'class':'DataForEyeQ'},
    0x00678001:{'name':'(FrCamera-ADAS) CAM InfrastructureList','period':None,'class':'CAMInfrastructureList','implementQGIS':500, 'implementQGISinRealTimeMode':-1,     'implementOpenGLdraw':500},
    0x00438003:{'name':'(ADAS) DebugEther',             'period':None,  'class':'DebugEther',                 'implementQGIS':200, 'implementQGISinRealTimeMode':-1},
    0xCAF0054C:{'name':'(CAN) ADASISv2 POSITION',             'period':500,   'class':'ADASISv2POSITION_CAN', 'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0xCAF0036D:{'name':'(CAN) ADASISv2 SEGMENT',              'period':50,    'class':'ADASISv2SEGMENT_CAN',  'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0xCAF00370:{'name':'(CAN) ADASISv2 STUB',                 'period':50,    'class':'ADASISv2STUB_CAN',     'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0xCAF0025E:{'name':'(CAN) ADASISv2 PROFILE SHORT',        'period':20,    'class':'ADASISv2PROFILESHORT_CAN','implementQGIS':0,'implementQGISinRealTimeMode':-1},
    0xCAF0036A:{'name':'(CAN) ADASISv2 PROFILE LONG for AD2', 'period':50,    'class':'ADASISv2PROFILELONG_CAN','implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0xCAF006A1:{'name':'(CAN) ADASISv2 METADATA',             'period':3000,  'class':'ADASISv2METADATA_CAN'},
    0xCAF003CD:{'name':'(CAN) LatLon Position of IVI',        'period':250,   'class':'ADASISv2RouteInfo_CAN', 'implementQGIS':0, 'implementQGISinRealTimeMode':-1}, #分割メッセージ毎に、推奨レーン情報を入れる仕様であるため、全部描画必要  # message period is 500ms (250ms+250ms)
    0xCAF0052D:{'name':'(CAN) Road_Data_4_ADAS',              'period':500,   'class':'Road_Data_4_ADAS_CAN',  'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0xCAF003C1:{'name':'(CAN) Navi_Status_ADAS',              'period':100,   'class':'Navi_Status_ADAS',      'implementQGIS':500, 'implementQGISinRealTimeMode':-1},
    0xCAFFD226:{'name':'(CAN) VDC_A116_WheelPulse',           'period':20,    'class':'VDC_A116_WheelPulse'},
    0xCAF00517:{'name':'(CAN) FRCAMERA_A2',                   'period':500,   'class':'CAN_FRCAMERA_A2'},
    0xCAF00559:{'name':'(CAN) ADAS_A125_COP_Data',            'period':500,   'class':'CAN_Message'},
    0xCAF00601:{'name':'(CAN) ADAS_ModeDisplay',              'period':500,   'class':'CAN_ADAS_ModeDisplay',  'implementQGIS':0},
    0xCAF0051E:{'name':'(CAN) ADASISv2 FrCamera',             'period':1000,  'class':'CAN_CARTO_R1',          'useMacro':True, 'implementQGIS':0, 'implementQGISinRealTimeMode':-1},
    0xCAF00562:{'name':'(CAN) ADAS_GlobalTimeStamp',          'period':500,   'class':'CAN_ADAS_GlobalTimeStamp'},
    0xCAFFD1AB:{'name':'(CAN) VDC_A117SC_Sensor',             'period':10,    'class':'CAN_VDC_A117SC_Sensor'},
    0xCAF003C7:{'name':'(CAN) CAN_IVI_A5_SatelliteGPSNumber', 'period':100,   'class':'CAN_IVI_A5_SatelliteGPSNumber',  'implementQGIS':500},
    0xCAF00615:{'name':'(CAN) CAN_IVI_A105_GPSPosition',      'period':500,   'class':'CAN_IVI_A105_GPSPosition',  'implementQGIS':0},
    0xCAFFD3EF:{'name':'(CAN) DMC_A01C_FD',                   'period':100,   'class':'CAN_DMC_A01C_FD'},
    }

someipIdDic = {
    0x00548001:    0x00000000,
    0x00348001:    0x00000001,
    0x00548002:    0x00000002,
    0x00348002:    0x00000013,
    0x00548003:    0x00000014,
    0x00548004:    0x00000015,
    0x00348003:    0x000000ff,
    0x00348004:    0x000000fe,
    0x006B8001:    0x00000106,
    0x006B8002:    0x00000107,
    0x00398003:    0x00000108,
    0x006B8004:    0x00000109,
    0x006B8005:    0x0000010a,
    0x006B8006:    0x0000010b,
    0x006B8007:    0x0000010c,
    0x006B8008:    [0x00000110, 0x00000158],
    0x00398009:    0x00000120,
    0x0039800A:    0x00000121,
    0x00568001:    0x00000151,
    0x00568002:    0x00000152,
    0x00568003:    0x00000153,
    0x00568004:    0x00000154,
    0x00398010:    0x00000155,
    0x00398012:    0x00000157,
    0x00368001:    0x00000300,
    0x00368002:    0x00000500,
    0x00368003:    0x00000501,
    0x00368004:    0x00000502,
    0x006A8001:    0x00000601,
    0x002F8001:    0x00000608,
    0x00658001:    0x00000609,
    0x002E8001:    0x00000620,
    0x002E8002:    0x00000625,
    0x00668001:    0x00000626,
    0x00668002:    0x00000627,
    0x00668003:    0x00000628,
    0x00668004:    0x00000629,
    0x00708001:    0x0000062A,
    0x00708002:    0x0000062B,
    0x006F8001:    0x0000062C,
    0x006F8002:    0x0000062D,
    0x006F8003:    0x0000062E,
    0x006F8004:    0x0000062F,
    0x00188001:    0x00000700,
    0x005E8001:    0x00000801,
    0x00598001:    0x00000901,
    0x003C8001:    0x00000902,
    0x00588001:    0x00001080,
    0x00588002:    0x00001081,
    0x00588003:    0x00001082,
    0x00588005:    0x00001083,
    0x00588004:    0x00001084,
    0x00588006:    0x00001085,
    0x005D8001:    0x00001090,
    0x005D8002:    0x00001091,
    0x006D8001:    0x006d8001,
    0x00678001:    0x00678001,
    0x00438003:    0x00438003}

#-----------------------------------------------#
#----   Common Function                     ----#
#-----------------------------------------------#
def isCANmessageIncluded(targetList):
    for messageID in targetList:
        if (messageID & 0xFFF00000 == 0xCAF00000) and (messageID != EtherID.AllMessageTimeLog):
            return True
    return False

def isEthMessageIncluded(targetList):
    for messageID in targetList:
        if (messageID & 0xFFF00000 != 0xCAF00000) and (messageID != EtherID.AllMessageTimeLog):
            return True
    return False

# 解析において、お互いに関連しあうため、並列処理で解析できず、必ずまとめて受信した順番に解析が必要なものをグループという。並列処理可能なメッセージはFalseとして返す。
groupMessageList = {1: [0xCAF0054C, 0xCAF0036D, 0xCAF00370, 0xCAF0025E, 0xCAF0036A],
                    2: [0x00001080, 0x00001081, 0x00001082, 0x00001083, 0x00001084]}
def isGrouppingMessage(messageID):
    for (groupIndex, groupList) in groupMessageList.items():
        if messageID in groupList:
            return groupIndex
    return False
    
def getGrouppingMessage(groupIndex):
    return groupMessageList.get(groupIndex, [])

def getEtherIdDic(messageID):
    if messageID & 0xFFFF0000 == 0xDDDD0000:
        messageID = 0xDDDD0000
    if messageID in etherIdDic:
        return etherIdDic[messageID]
    else:
        return None

def checkInvalidLonLat(longitude, latitude, oldLongitude = None, oldLatitude = None, allowSamePoint = False):
    if abs(latitude) > 179.99 or abs(longitude) > 179.99 or (abs(latitude) < 0.01 and abs(longitude) < 0.01):
        return False
     
    if oldLongitude != None and oldLatitude != None:
        if abs(oldLatitude) > 179.99 or abs(oldLongitude) > 179.99 or (abs(oldLatitude) < 0.01 and abs(oldLongitude) < 0.01):
            return False
         
        if (allowSamePoint == False and latitude == oldLatitude and longitude == oldLongitude) or (((latitude-oldLatitude) ** 2 + (longitude-oldLongitude) ** 2) > 1):
            return False
        
    return True

def calcLatLonDistance(lat1, lon1, lat2, lon2, mode=True):
        # 緯度経度をラジアンに変換
        radLat1 = lat1*math.pi/180.0 # 緯度１
        radLon1 = lon1*math.pi/180.0 # 経度１
        radLat2 = lat2*math.pi/180.0 # 緯度２
        radLon2 = lon2*math.pi/180.0 # 経度２
    
        # 緯度差
        radLatDiff = radLat1 - radLat2
    
        # 経度差算
        radLonDiff = radLon1 - radLon2
    
        # 平均緯度
        radLatAve = (radLat1 + radLat2) / 2.0
    
        # 測地系による値の違い
        a = 6378137.0 if mode else 6377397.155 # 赤道半径
        b = 6356752.314140356 if mode else 6356078.963 # 極半径
        #e2 = (a*a - b*b) / (a*a);
        e2 = 0.00669438002301188 if mode else 0.00667436061028297 # 第一離心率^2
        #a1e2 = a * (1 - e2);
        a1e2 = 6335439.32708317 if mode else 6334832.10663254 # 赤道上の子午線曲率半径
    
        sinLat = math.sin(radLatAve)
        W2 = 1.0 - e2 * (sinLat*sinLat)
        M = a1e2 / (math.sqrt(W2)*W2) # 子午線曲率半径M
        N = a / math.sqrt(W2); # 卯酉線曲率半径
    
        t1 = M * radLatDiff
        t2 = N * math.cos(radLatAve) * radLonDiff
        dist = math.sqrt((t1*t1) + (t2*t2))
    
        return dist

def degrees2meters(lon, lat):
    x = lon * 20037508.34 / 180;
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180);
    y = y * 20037508.34 / 180;
    return y,x

#-----------------------------------------------#
#----   BinaryData                          ----#
#-----------------------------------------------#
class BinaryData:
    def __init__(self, dataBuf):
        self.seekIndex = 0
        self.seekSubBitIndex = 0
        self.dataBuf = dataBuf
    
    def __del__(self):
        pass
    
    def seek(self):
        return self.seekIndex
    
    def getDataBuf(self):
        return self.dataBuf
    
    def setSeek(self, byteIndex, bitIndex):
        self.seekIndex = byteIndex
        self.seekSubBitIndex = bitIndex
        
    def setSeekFirst(self):
        self.seekIndex = 0
        self.seekSubBitIndex = 0
        
    ####################################################################################################################
    #                 ロジック検証コード (修正時はこのコードで検証)
    ####################################################################################################################
    #     dataBuf = bytearray(100)
    #     data = BinaryData(dataBuf) # ADASIS message is this case
    #     data.writeValue(int, 10, 4621, readFromLSB=False, endian='big')
    #     if dataBuf[0] == 0b10000011 and dataBuf[1] == 0b01000000 and dataBuf[2] == 0b00000000 and dataBuf[3] == 0b00000000: print('ok1')
    #     data.writeValue(int, 10, -20, readFromLSB=False, endian='big')
    #     if dataBuf[0] == 0b10000011 and dataBuf[1] == 0b01111110 and dataBuf[2] == 0b11000000 and dataBuf[3] == 0b00000000: print('ok2')
    #     data.writeValue(int, 10, 13, readFromLSB=False, endian='big')
    #     if dataBuf[0] == 0b10000011 and dataBuf[1] == 0b01111110 and dataBuf[2] == 0b11000000 and dataBuf[3] == 0b00110100: print('ok3')
    #     
    #     data.setSeekFirst()
    #     print(data.readValue(int, 10, sign=False, readFromLSB=False, endian='big')) #525
    #     print(data.readValue(int, 10, sign=True, readFromLSB=False, endian='big')) #-20
    #     print(data.readValue(int, 10, sign=True, readFromLSB=False, endian='big')) #13
    #     print(' ')
    #     
    #     data = BinaryData(dataBuf)
    #     data.writeValue(int, 10, 23420, readFromLSB=True, endian='big') #23420 = 0b 0101 1011 0111 1100
    #     if dataBuf[0] == 0b11011111 and dataBuf[1] == 0b01111100 and dataBuf[2] == 0b11000000 and dataBuf[3] == 0b00110100: print('ok4')
    #     data.writeValue(int, 10, -20, readFromLSB=True, endian='big')
    #     if dataBuf[0] == 0b11011111 and dataBuf[1] == 0b11111000 and dataBuf[2] == 0b11001100 and dataBuf[3] == 0b00110100: print('ok5')
    #     data.writeValue(int, 10, 13, readFromLSB=True, endian='big')
    #     if dataBuf[0] == 0b11011111 and dataBuf[1] == 0b11111000 and dataBuf[2] == 0b00001100 and dataBuf[3] == 0b00001101: print('ok6')
    #     
    #     data.setSeekFirst()
    #     print(data.readValue(int, 10, sign=False, readFromLSB=True, endian='big')) #892
    #     print(data.readValue(int, 10, sign=True, readFromLSB=True, endian='big')) #-20
    #     print(data.readValue(int, 10, sign=True, readFromLSB=True, endian='big')) #13
    #     print(' ')
    #     
    #     data = BinaryData(dataBuf)
    #     data.writeValue(int, 10, 20, readFromLSB=False, endian='little')
    #     if dataBuf[0] == 0b00010100 and dataBuf[1] == 0b00111000 and dataBuf[2] == 0b00001100 and dataBuf[3] == 0b00001101: print('ok7')
    #     data.writeValue(int, 10, -20, readFromLSB=False, endian='little')
    #     if dataBuf[0] == 0b00010100 and dataBuf[1] == 0b00101100 and dataBuf[2] == 0b11111100 and dataBuf[3] == 0b00001101: print('ok8')
    #     data.writeValue(int, 10, 13, readFromLSB=False, endian='little')
    #     if dataBuf[0] == 0b00010100 and dataBuf[1] == 0b00101100 and dataBuf[2] == 0b11111101 and dataBuf[3] == 0b00000001: print('ok9')
    #     
    #     data.setSeekFirst()
    #     print(data.readValue(int, 10, sign=True, readFromLSB=False, endian='little')) # 20
    #     print(data.readValue(int, 10, sign=True, readFromLSB=False, endian='little')) # -20
    #     print(data.readValue(int, 10, sign=True, readFromLSB=False, endian='little')) # 13
    #     print(' ')
    #     
    #     data = BinaryData(dataBuf) # R-DR is this case
    #     data.writeValue(int, 10, 20, readFromLSB=True, endian='little')
    #     if dataBuf[0] == 0b00010100 and dataBuf[1] == 0b00101100 and dataBuf[2] == 0b11111101 and dataBuf[3] == 0b00000001: print('ok10')
    #     data.writeValue(int, 10, -20, readFromLSB=True, endian='little')
    #     if dataBuf[0] == 0b00010100 and dataBuf[1] == 0b10110000 and dataBuf[2] == 0b11111111 and dataBuf[3] == 0b00000001: print('ok11')
    #     data.writeValue(int, 10, 13, readFromLSB=True, endian='little')
    #     if dataBuf[0] == 0b00010100 and dataBuf[1] == 0b10110000 and dataBuf[2] == 0b11011111 and dataBuf[3] == 0b00000000: print('ok12')
    #     
    #     data.writeValue(float, 32, 123.4567, readFromLSB=True, endian='little')
    #     if dataBuf[3] == 0b01000000 and dataBuf[4] == 0b01110101 and dataBuf[5] == 0b10111010 and dataBuf[6] == 0b10111101 and dataBuf[7] == 0b00010000: print('ok13')
    #     data.writeValue(float, 64, 234.5678, readFromLSB=True, endian='little')
    #     data.writeValue(float, 32, 123.4567, readFromLSB=True, endian='big')
    #     data.writeValue(float, 64, 234.5678, readFromLSB=True, endian='big')
    #     
    #     data.setSeekFirst()
    #     print(data.readValue(int, 10, sign=True, readFromLSB=True, endian='little')) # 20
    #     print(data.readValue(int, 10, sign=True, readFromLSB=True, endian='little')) # -20
    #     print(data.readValue(int, 10, sign=True, readFromLSB=True, endian='little')) # 13
    #     print(' ')
    #     print(data.readValue(float, 32, readFromLSB=True, endian='little')) # 123.4567
    #     print(data.readValue(float, 64, readFromLSB=True, endian='little')) # 234.5678
    #     print(data.readValue(float, 32, readFromLSB=True, endian='big')) # 123.4567
    #     print(data.readValue(float, 64, readFromLSB=True, endian='big')) # 234.5678
    #     print(' ')
    #     
    #     data = BinaryData(dataBuf)
    #     data.writeValue(float, 32, 123.4567, readFromLSB=False, endian='little')
    #     data.writeValue(float, 64, 234.5678, readFromLSB=False, endian='little')
    #     data.writeValue(float, 32, 123.4567, readFromLSB=False, endian='big')
    #     data.writeValue(float, 64, 234.5678, readFromLSB=False, endian='big')
    # 
    #     data.setSeekFirst()
    #     print(data.readValue(float, 32, readFromLSB=False, endian='little')) # 123.4567
    #     print(data.readValue(float, 64, readFromLSB=False, endian='little')) # 234.5678
    #     print(data.readValue(float, 32, readFromLSB=False, endian='big')) # 123.4567
    #     print(data.readValue(float, 64, readFromLSB=False, endian='big')) # 234.5678
    ####################################################################################################################

    # readFromLSB について、以下のようにデータを格納する。
    # <Little endian, readFromLSB = True> : R-DRデータがこの形式
    # 7  ->  0 7  ->  0
    # [  ->  LSB]######    # : 以前最後に格納されているデータ
    # ------[MSB  ->  ]    [] : 今回新しく格納したデータ
    # <Little endian, readFromLSB = False>
    # 7  ->  0 7  ->  0
    # ######[  ->  LSB]    # : 以前最後に格納されているデータ
    # [MSB  ->  ]------    [] : 今回新しく格納したデータ
    # <Big endian, readFromLSB = True>
    # 7  ->  0 7  ->  0
    # [MSB  ->  ]######    # : 以前最後に格納されているデータ
    # ------[  ->  LSB]    [] : 今回新しく格納したデータ
    # <Big endian, readFromLSB = False> : ADASISデータがこの形式
    # 7  ->  0 7  ->  0
    # ######[MSB  ->  ]    # : 以前最後に格納されているデータ
    # [  ->  LSB]------    [] : 今回新しく格納したデータ
    
    def writeValue(self, typeC, bitSize, value, readFromLSB=False, endian='big'):
        if bitSize <= 0 or len(self.dataBuf) == 0: #データバッファが空の場合は、他のデバイスの起動前など、共通ヘッダ０埋めの可能性が高いため、無視。
            return
        nextIndex = self.seekIndex + int((self.seekSubBitIndex + bitSize)/8)
        if nextIndex > len(self.dataBuf):
            raise ValueError("Data Index Over. Cannot write.")
        else:
            remainBitSize = bitSize
            if typeC == float and bitSize == 32:
                packData = struct.pack('<f', float(value))
            elif typeC == float and bitSize == 64:
                packData = struct.pack('<d', float(value))
            elif typeC == str:
                packData = value
            elif typeC == bytes:
                packData = value
            elif typeC == int:
                packData = struct.pack('<i', int(value + (0.5 if value > 0 else -0.5)))
            else:
                raise ValueError("Unknown data type")    
            
            writeData = []
            index = 0
            while remainBitSize > 0:
                if remainBitSize > 8:
                    packBitSize = 8
                else:
                    packBitSize = remainBitSize
                if index < len(packData):
                    packByte = packData[index]
                else:
                    packByte = 0
                if endian == 'big':
                    writeData.insert(0, (packByte, packBitSize))
                else:
                    writeData.append((packByte, packBitSize))
                remainBitSize -= 8
                index += 1
            
            index = 0
            while index < len(writeData):
                (packByte, packBitSize) = writeData[index]
                index += 1
                
                if packBitSize > 0:
                    if packBitSize < 8:
                        packByte = packByte & (0xFF >> (8-packBitSize))
                    
                    if (8-self.seekSubBitIndex) < packBitSize:
                        #現在書き込む固まりで、溢れる分は次に書き込むようにする
                        packBitSizeRemain = (packBitSize-(8-self.seekSubBitIndex))
                        if endian == 'big': #上を残して下を持っていく
                            packByteRemain = packByte & (0xFF >> (8-self.seekSubBitIndex))
                            packByte = packByte >> self.seekSubBitIndex
                        else: #下を残して上を持っていく
                            packByteRemain = packByte >> (8-self.seekSubBitIndex)
                            packByte = packByte & (0xFF >> self.seekSubBitIndex)
                        packBitSize = (8-self.seekSubBitIndex)
                        writeData.insert(index, (packByteRemain, packBitSizeRemain))
                    elif ((8-self.seekSubBitIndex) > packBitSize) and (index < len(writeData)):
                        #逆に、現在書き込む固まりが、足りないので、次から持ってくる
                        (nextPackByte, nextPackBitSize) = writeData[index]
                        if nextPackBitSize < 8:
                            nextPackByte = nextPackByte & (0xFF >> (8-nextPackBitSize))
                        shiftOffset = (8-self.seekSubBitIndex) - packBitSize
                        if nextPackBitSize - shiftOffset > 0:
                            if endian == 'big': # 後ろの上から持ってきものを、今の下につける
                                packByte = ((packByte << shiftOffset) & 0xFF) | (nextPackByte >> (nextPackBitSize - shiftOffset))
                                nextPackByte = nextPackByte & (0xFF >> (8-(nextPackBitSize - shiftOffset)))
                            else: # 後ろの下から持ってきものを、今の上につける
                                packByte |= ((nextPackByte & (0xFF >> (8-shiftOffset))) << packBitSize) & 0xFF
                                nextPackByte = nextPackByte >> shiftOffset
                            packBitSize += shiftOffset
                            nextPackBitSize -= shiftOffset
                        else:
                            if endian == 'big': # 後ろを全部、今の下につける
                                packByte = ((packByte << nextPackBitSize) & 0xFF) | nextPackByte
                            else: # 後ろを全部、今の上につける
                                packByte |= (nextPackByte << (8-shiftOffset)) & 0xFF
                            nextPackByte = 0
                            packBitSize += nextPackBitSize
                            nextPackBitSize = 0
                        writeData[index] = (nextPackByte, nextPackBitSize)
                        
                    if readFromLSB == False:
                        self.dataBuf[self.seekIndex] = (self.dataBuf[self.seekIndex] & ((0xFF << (8-self.seekSubBitIndex))) & 0xFF) \
                                                    | ((packByte << (8-self.seekSubBitIndex-packBitSize)) & 0xFF) \
                                                    | (self.dataBuf[self.seekIndex] & (0xFF >> (self.seekSubBitIndex+packBitSize)))
                    else:
                        self.dataBuf[self.seekIndex] = (self.dataBuf[self.seekIndex] & (0xFF >> (8-self.seekSubBitIndex))) \
                                                    | ((packByte << self.seekSubBitIndex) & 0xFF) \
                                                    | (self.dataBuf[self.seekIndex] & ((0xFF << (self.seekSubBitIndex+packBitSize)) & 0xFF))
                    
                    self.seekSubBitIndex += packBitSize
                    if self.seekSubBitIndex >= 8:
                        self.seekSubBitIndex -= 8
                        self.seekIndex += 1
                
    def readValue(self, typeC, bitSize, sign=False, readFromLSB=False, endian='big'):
        if bitSize <= 0 or len(self.dataBuf) == 0: #データバッファが空の場合は、他のデバイスの起動前など、共通ヘッダ０埋めの可能性が高いため、無視。
            if typeC == str: return ''
            else: return 0
        else:
            nextIndex = self.seekIndex + int((self.seekSubBitIndex + bitSize)/8)
        
        if nextIndex > len(self.dataBuf):
            if typeC == str: result = ''
            else: result = 0
            #logPrint("Data Index Over : logIndex:{0}, {1}({2})".format(getLogIndex(), getEtherIdDic(self.commonHeader.messageID)['name'], hex(self.commonHeader.messageID)))
            if nextIndex > len(self.dataBuf) + 100:
                # 仕様変更未反映を考慮し、100byteまでは解析を頑張ってみる
                raise ValueError("Data Index Over. Maybe format changed.")
            self.seekIndex = nextIndex
            
        else:
            try:
                dataBuf = []
                dataBufBitSize = []
                if self.seekSubBitIndex > 0 or bitSize % 8 > 0:
                    remainBitSize = bitSize
                    while remainBitSize > 0:
                        readBitSize = 8 - self.seekSubBitIndex
                        if readBitSize > remainBitSize:
                            readBitSize = remainBitSize
                            
                        if readFromLSB == True:
                            tempByte = (self.dataBuf[self.seekIndex] >> self.seekSubBitIndex) & (0xFF >> (8-readBitSize))
                        else:
                            tempByte = (self.dataBuf[self.seekIndex] >> (8-(self.seekSubBitIndex+readBitSize))) & (0xFF >> (8-readBitSize))
                        self.seekSubBitIndex += readBitSize
                        if self.seekSubBitIndex >= 8:
                            self.seekSubBitIndex -= 8
                            self.seekIndex += 1
                            
                        remainBitSize -= readBitSize
                        dataBuf.append(tempByte)
                        dataBufBitSize.append(readBitSize)
                     
                    if endian == 'big':
                        #右に詰めなおす
                        index = len(dataBuf)-1
                        while index > 0:
                            if dataBufBitSize[index] < 8:
                                shiftOffset = 8 - dataBufBitSize[index]
                                if shiftOffset > dataBufBitSize[index-1]:
                                    shiftOffset = dataBufBitSize[index-1]
                                dataBuf[index] |= (dataBuf[index-1] & (0xFF >> (8-shiftOffset))) << dataBufBitSize[index]
                                dataBuf[index-1] = dataBuf[index-1] >> shiftOffset
                                dataBufBitSize[index] += shiftOffset
                                dataBufBitSize[index-1] -= shiftOffset
                                if dataBufBitSize[index-1] == 0:
                                    del dataBufBitSize[index-1]
                                    del dataBuf[index-1]
                                    index -= 1 #前方のデータを消したため
                                if dataBufBitSize[index] == 8:
                                    index -= 1
                            else:
                                index -= 1
                        if sign == True and (dataBuf[0] & (0x1 << (dataBufBitSize[0]-1))) != 0:
                            dataBuf[0] |= (0xFF << dataBufBitSize[0]) & 0xFF
                    else:
                        #左に詰める 
                        index = 0
                        while index < len(dataBuf)-1:
                            if dataBufBitSize[index] < 8:
                                shiftOffset = 8 - dataBufBitSize[index]
                                if shiftOffset > dataBufBitSize[index+1]:
                                    shiftOffset = dataBufBitSize[index+1]
                                dataBuf[index] |= (dataBuf[index+1] & (0xFF >> (8-shiftOffset))) << dataBufBitSize[index]
                                dataBuf[index+1] = dataBuf[index+1] >> shiftOffset
                                dataBufBitSize[index] += shiftOffset
                                dataBufBitSize[index+1] -= shiftOffset
                                if dataBufBitSize[index+1] == 0:
                                    del dataBufBitSize[index+1]
                                    del dataBuf[index+1]
                                if dataBufBitSize[index] == 8:
                                    index += 1
                            else:
                                index += 1
                        if sign == True and (dataBuf[len(dataBuf)-1] & (0x1 << (dataBufBitSize[len(dataBuf)-1]-1))) != 0:
                            dataBuf[len(dataBuf)-1] |= (0xFF << dataBufBitSize[len(dataBuf)-1]) & 0xFF
                               
                else:
                    dataBuf = self.dataBuf[self.seekIndex:nextIndex]
                    for _ in range(len(dataBuf)):
                        dataBufBitSize.append(8)
                    self.seekIndex = nextIndex
    
                if typeC == float and bitSize == 32:
                    if endian == 'big':
                        result = struct.unpack('>f', bytearray(dataBuf))[0]
                    else:
                        result = struct.unpack('<f', bytearray(dataBuf))[0]
                elif typeC == float and bitSize == 64:
                    if endian == 'big':
                        result = struct.unpack('>d', bytearray(dataBuf))[0]
                    else:
                        result = struct.unpack('<d', bytearray(dataBuf))[0]
                elif typeC == str:
                    result = dataBuf.decode('utf-8')
                elif typeC == bytes:
                    result = bytearray(dataBuf)
                else:
                    result = typeC.from_bytes(dataBuf, byteorder=endian, signed=sign)
                    
            except Exception as e:
                print("(readValue error) seekIndex={}, seekBitIndex={}, type={}, bitSize={}, sign={}, readFromLSB={}, endian={}".format(self.seekIndex, self.seekSubBitIndex, typeC, bitSize, sign, readFromLSB, endian))
                raise e
                
        return result
    
    
#-----------------------------------------------#
#----   Message (Super)                     ----#
#-----------------------------------------------#
class Message(abc.ABC):
    def __init__(self, index, time, definitionID, dataBuf, useCommonHeader = True):
        self.data = BinaryData(dataBuf)
        if (useCommonHeader):
            self.commonHeader = CommonHeader(index, time, definitionID, self.data)
            if len(self.data.dataBuf) > self.commonHeader.length: #可変長メッセージの場合、後ろに無効な4byteがついている。それを取り除くための部分。length=0の時は実行しない。
                self.data.dataBuf = self.data.dataBuf[:self.commonHeader.length]
        else:
            self.commonHeader = DummyCommonHeader(index, time, definitionID, self.data)
        self.defaultReset()
        
    def __del__(self):
        pass
    
    def defaultReset(self):
        self.oldMessage = None
        self.nextMessage = None
        self.messageSizeCheckErrorDone = False
        self.relatedCarPositionMessage = None
        self.relatedGNSSPositionMessage = None
        self.relatedIVIPositionMessage = None
        self.relatedADASISPositionMessage = None
        self.relatedADPositionMessage = None
        
    def getRelatedPositionDefault(self):
        return self.getRelatedPosition([self.relatedADPositionMessage, self.relatedCarPositionMessage, self.relatedGNSSPositionMessage, self.relatedIVIPositionMessage])
        
    def getRelatedPosition(self, messageListByPriority):
        for message in messageListByPriority:
            if message != None:
                [curlon, curlat] = message.getLonLat()
                if checkInvalidLonLat(curlon, curlat) == True:
                    return [curlon, curlat]
        return [180, 180]
    
    def setRelatedCarPositionMessage(self, CarPositionMessage, GNSSPositionMessage, ADPositionMessage, IVIPositionMessage, ADASISPositionMessage):
        if CarPositionMessage != None: 
            if (self.commonHeader.logTime - CarPositionMessage.commonHeader.logTime).total_seconds() < 1: #1秒以内のCarPosメッセージのみ関連メッセージとする
                self.relatedCarPositionMessage = CarPositionMessage
                
        if GNSSPositionMessage != None:
            if (self.commonHeader.logTime - GNSSPositionMessage.commonHeader.logTime).total_seconds() < 1: #1秒以内のGNSSPosメッセージのみ関連メッセージとする
                self.relatedGNSSPositionMessage = GNSSPositionMessage
                
        if ADPositionMessage != None:
            if (self.commonHeader.logTime - ADPositionMessage.commonHeader.logTime).total_seconds() < 1: #1秒以内のGNSSPosメッセージのみ関連メッセージとする
                self.relatedADPositionMessage = ADPositionMessage
                
        if IVIPositionMessage != None:
            self.relatedIVIPositionMessage = IVIPositionMessage
            
        if ADASISPositionMessage != None:
            self.relatedADASISPositionMessage = ADASISPositionMessage
                
    def assertMessageSize(self):
        if self.messageSizeCheckErrorDone == False:
            self.messageSizeCheckErrorDone = True
            if self.commonHeader.length == 0:
                #サイズが0の場合は、相手のデバイスが起動直後のデータなしの状態である可能性があるため、チェックしない。
                pass
            elif self.commonHeader.length != self.data.seek():
                logger = getLogger()
                logger.errLog("[logIndex:{0}] <{1}({2})> Common Header effective data length is incorrect (expected:{3}, value:{4})".format( 
                       self.commonHeader.logIndex, 
                       getEtherIdDic(self.commonHeader.definitionID)['name'], 
                       hex(self.commonHeader.messageID),
                       self.data.seek(),
                       self.commonHeader.length))
        
    @abc.abstractmethod
    def parse(self):
        pass
    
    @abc.abstractmethod
    def printHeader(self, sheet, row, col, level = 1):
        pass
    
    @abc.abstractmethod
    def printValue(self, sheet, row, col, level = 1):
        pass
    
    def drawChart(self, book, sheet, totalRows): 
        pass
    
    @classmethod
    def SetLayerStyle(cls, layerType, layer):
        return None
    
    def createLayer(self, name, iface_obj, realTimeMode):
        return None
    
    def drawQGIS(self, layerList, realTimeMode):
        pass


#-----------------------------------------------#
#----   SegmentableMessage (Super)          ----#
#-----------------------------------------------#
class SegmentableMessage(abc.ABC):
    def __init__(self):
        pass
    
    @classmethod
    def Reset(cls):
        SegmentableMessage._segmentCount = {}
        SegmentableMessage._segmentData = {}
        SegmentableMessage._segmentComplete = {}
        SegmentableMessage._oldKey = {}
        SegmentableMessage._oldKeyIndex = {}
        SegmentableMessage._oldKeyCount = 10 #1以上設定。1の場合は、セグメントメッセージは必ず１固まりが完成してから次のセグメントが来る事を意味。2以上の場合、同時に複数のセグメント合体可能
        
    def mergeSegmentData(self, segmentID, index, count, dataBuf):
        logger = getLogger()
        if count > 0:
            if 0 < index and index <= count:
                messageID = self.commonHeader.messageID 
                if not(messageID in SegmentableMessage._segmentCount):
                    SegmentableMessage._segmentCount[messageID] = {}
                    SegmentableMessage._segmentData[messageID] = {}
                    SegmentableMessage._segmentComplete[messageID] = {}
                    SegmentableMessage._oldKey[messageID] = []
                    SegmentableMessage._oldKeyIndex[messageID] = []
                    for _ in range(SegmentableMessage._oldKeyCount):
                        SegmentableMessage._oldKey[messageID].append(None)
                        SegmentableMessage._oldKeyIndex[messageID].append(0)
                
                if segmentID != None and not(segmentID in SegmentableMessage._oldKey[messageID]):
                    oldKey = SegmentableMessage._oldKey[messageID].pop(0)
                    oldKeyIndex = SegmentableMessage._oldKeyIndex[messageID].pop(0)
                    if (oldKey != None) and (oldKey in SegmentableMessage._segmentCount[messageID]):
                        if SegmentableMessage._segmentComplete[messageID][oldKey] == False:
                            #一部のセグメント未受信
                            logger.errLog("Segment Lacked : logIndex:{0}, {1}({2}), segmendID:{3}".format(oldKeyIndex, getEtherIdDic(messageID)['name'], hex(messageID), oldKey))
                        del SegmentableMessage._segmentCount[messageID][oldKey]
                        del SegmentableMessage._segmentData[messageID][oldKey]
                        del SegmentableMessage._segmentComplete[messageID][oldKey]
                    SegmentableMessage._oldKey[messageID].append(segmentID)
                    SegmentableMessage._oldKeyIndex[messageID].append(getLogIndex())
                
                if not(segmentID in SegmentableMessage._segmentCount[messageID]):
                    #新規セグメント受信
                    SegmentableMessage._segmentCount[messageID][segmentID] = count
                    SegmentableMessage._segmentData[messageID][segmentID] = [None for i in range(count)]
                    SegmentableMessage._segmentComplete[messageID][segmentID] = False
                
                if SegmentableMessage._segmentCount[messageID][segmentID] != count:
                    #セグメントカウント異常
                    logger.errLog("Segment Count Error : logIndex:{0}, {1}({2}), index:{3}/{4}, Wrong segment count before {5}".format(getLogIndex(), getEtherIdDic(messageID)['name'], hex(messageID), index, count, SegmentableMessage._segmentCount[messageID][segmentID]))
                    #エラー表示後、新たなセグメント群を受信開始設定
                    SegmentableMessage._segmentCount[messageID][segmentID] = count
                    SegmentableMessage._segmentData[messageID][segmentID] = [None for i in range(count)]
                    SegmentableMessage._segmentData[messageID][segmentID][index-1] = dataBuf
                    SegmentableMessage._segmentComplete[messageID][segmentID] = False
                    return
                
                SegmentableMessage._segmentData[messageID][segmentID][index-1] = dataBuf

                if SegmentableMessage._segmentComplete[messageID][segmentID] == False:
                    if all([(SegmentableMessage._segmentData[messageID][segmentID][i] != None) for i in range(count)]):
                        # All SegmentData merge complete
                        totalData = bytes(0)
                        for i in range(count):
                            totalData += SegmentableMessage._segmentData[messageID][segmentID][i]
                        self.parseMergedData(BinaryData(totalData))
                        SegmentableMessage._segmentComplete[messageID][segmentID] = True
                        if segmentID == None: #segmentID == Noneの場合、どうせ、過去の固まりが区別できないので、再送メッセージかどうかわからない。
                            #以前の固まりが完成されたと判断したらクリア
                            del SegmentableMessage._segmentCount[messageID][segmentID]
                            del SegmentableMessage._segmentData[messageID][segmentID]
                            del SegmentableMessage._segmentComplete[messageID][segmentID]
        else:
            self.parseMergedData(BinaryData(dataBuf))
            
    @abc.abstractmethod
    def parseMergedData(self, data):
        pass

#-----------------------------------------------#
#----   AnalyzePositionError (Super)        ----#
#-----------------------------------------------#
class AnalyzePositionError(abc.ABC):    
    def __init__(self):
        self.positionError = None
        
    @classmethod
    def Reset(cls):
        AnalyzePositionError.LastRefMessageDic = {}
        
    @abc.abstractmethod
    def getAnalyzePositionErrorLonLat(self): #誤差評価対象となる経度緯度
        return [180, 180]
        
    # 以下の二つの異なる点を基準に、最近棒点を探す。計測時刻がずれている可能性があるため、sequentialRefPointも利用している。
    # sequentialRefPoint : 前回近いと検出した点の、繋がり上次の点。このポイントを基準に、前後10サンプルを確認し、近い点を探す。（繋がり上辿りながら比較する感じ）
    # logTimeBaseRefPoint : 計測時刻情報から、同じ時刻に計測されているRefポイント。このポイントを基準に、前後10サンプルを確認し、近い点を探す。
    def analyzePositionError(self, logTimeBaseRefPoint):
        messageID = self.commonHeader.messageID
        self.positionError = Structure()
        self.positionError.foot = [180, 180]
        self.positionError.target = [180, 180]
        self.positionError.distance = -1
        
        sequentialRefPoint = AnalyzePositionError.LastRefMessageDic.get(messageID, None)
        if sequentialRefPoint == None and logTimeBaseRefPoint == None:
            return
        
        [lon, lat] = self.getAnalyzePositionErrorLonLat()
        if checkInvalidLonLat(lon, lat) == False:
            return

        nearestP1Point = None
        nearestP2Point = None
        nearestDistance = 0.01 # lon,lat表現上0.0１より大きい距離の物とは誤差計算しないように(離れすぎているため、誤差評価をする対象ではない)
        minDistanceAsSequentialRef = 0.01
        maxDistanceAsTimeBaseRef = 0
        selectedItemIndex = 0
        for targetStep in range(2):
            if targetStep == 0:
                if sequentialRefPoint == None:
                    continue
                targetPoint = sequentialRefPoint
            else:
                if logTimeBaseRefPoint == None:
                    continue
                targetPoint = logTimeBaseRefPoint
            for step in range(2):
                #step 0 is search old message, step 1 is search next message
                p1 = targetPoint
                distanceIncreaseCount = 0
                beforeDistance = 0.01
                #for _ in range(500):
                while True:
                    [p1Lon, p1Lat] = p1.getLonLat()
                    if step == 0:
                        p2 = p1.oldMessage
                    else:
                        p2 = p1.nextMessage
                    if p2 == None:
                        break
                    [p2Lon, p2Lat] = p2.getLonLat()
                    if checkInvalidLonLat(p1Lon, p1Lat, p2Lon, p2Lat) == False:
                        p1 = p2
                        continue
                        
                    distance = math.sqrt((p1Lon-lon)*(p1Lon-lon) + (p1Lat-lat)*(p1Lat-lat)) + math.sqrt((p2Lon-lon)*(p2Lon-lon) + (p2Lat-lat)*(p2Lat-lat))
                    if distance < nearestDistance:
                        nearestDistance = distance
                        nearestP1Point = p1
                        nearestP2Point = p2
                        selectedItemIndex = targetStep
                        
                    if targetStep == 0:
                        if distance < minDistanceAsSequentialRef: minDistanceAsSequentialRef = distance
                    else:
                        if distance > maxDistanceAsTimeBaseRef: maxDistanceAsTimeBaseRef = distance
                        
                    if math.fabs(distance - beforeDistance) > 0.0002:
                        if beforeDistance < distance:
                            distanceIncreaseCount += 1
                        else:
                            distanceIncreaseCount = 0
                        beforeDistance = distance
                        if distanceIncreaseCount > 10: #10回連続距離が大きくなっていたら、それ以上見る必要ないと判断
                            break
                    p1 = p2
        
        if nearestP1Point == None or nearestP2Point == None:
            return
        
        [p1Lon, p1Lat] = nearestP1Point.getLonLat()
        [p2Lon, p2Lat] = nearestP2Point.getLonLat()

        dx = p1Lon - p2Lon
        dy = p1Lat - p2Lat
        l = (dx*(lon-p2Lon) + dy*(lat-p2Lat)) / (dx*dx + dy*dy)
        px = p2Lon + dx*l
        py = p2Lat + dy*l
        self.positionError.foot = [px, py]
        self.positionError.target = [lon, lat]
        self.positionError.distance = calcLatLonDistance(lat, lon, py, px)
        
        logger = getLogger()
        logger.debugLog('<analyzePositionError Calc>,' + str([p1Lon, p1Lat, p2Lon, p2Lat, px, py, self.positionError.distance]))
        
        if selectedItemIndex == 0 or sequentialRefPoint == None: #sequentialRefPointから近傍点が見つかった場合。
            AnalyzePositionError.LastRefMessageDic[messageID] = nearestP1Point #sequentialなRefPointを更新する。
        else:
            #logTimeBaseRefPointから近傍点が見つかった場合。すぐにはsequentialなRefPointを更新しない。
            #理由としては、たまたま、ロギング時刻がずれていて、ループ形状のような道路の重なる地点で、行き違いの点が近傍点として選ばれた場合、
            #その点にすぐsequentialなRefPointを更新してしまうと、もう戻れなくなる。
            if maxDistanceAsTimeBaseRef < minDistanceAsSequentialRef:
                #SequentialPointを基準に前後を見た時の一番短い距離が、TimeBaseRefPointを基準に前後を見た時の一番遠い距離よりも大きい場合、これ以上そのSequentialRefにこだわる必要はない。
                AnalyzePositionError.LastRefMessageDic[messageID] = nearestP1Point #sequentialなRefPointを更新する。
            else:
                AnalyzePositionError.LastRefMessageDic[messageID] = sequentialRefPoint

#-----------------------------------------------#
#----   ProfileType                         ----#
#-----------------------------------------------#
class ProfileType(abc.ABC):
    def __init__(self, data, refMessage):
        self.data = data
        self.refMessage = refMessage
        
    @abc.abstractmethod
    def printHeader(self, sheet, row, col, level = 1):
        pass
    
    @abc.abstractmethod
    def printValue(self, sheet, row, col, level = 1):
        pass

#-----------------------------------------------#
#----   CommonHeader                        ----#
#-----------------------------------------------#
class DummyCommonHeader():
    def __init__(self, index, time, definitionID, data):
        self.logIndex = index
        self.logTime = time
        self.definitionID = definitionID
        if data.dataBuf == None:
            self.length = 0
        else:
            self.length = len(data.dataBuf)
        self.messageID = definitionID
        self.messageCount = 0
        self.msgCountDiff = 0
        
        if self.definitionID in CommonHeader.preLogTime:
            self.logTimeDiff = self.logTime - CommonHeader.preLogTime[self.definitionID]
            self.timeStamp = (self.logTime - CommonHeader.firstLogTime[self.definitionID]).total_seconds()
            self.timeStampDiff = self.timeStamp - CommonHeader.preTimeStamp[self.definitionID]
        else:
            self.logTimeDiff = timedelta(0, 0, 0)
            self.timeStamp = 0
            self.timeStampDiff = 0
            CommonHeader.firstLogTime[self.definitionID] = self.logTime # DummyCommonHeaderでは、初logTimeからの経過時間[s]をtimestampにする。
            
        CommonHeader.preLogTime[self.definitionID] = self.logTime
        CommonHeader.preTimeStamp[self.definitionID] = self.timeStamp
    
    def columnCount(self):
        return 10
    
    def printHeader(self, sheet, row, col, _level = 1):
        sheet.write_row(row, col, ['logIndex', 'logTime', 'ΔlogTime[ms]', 'length', 'timeStamp[s]', 'ΔtimeStamp[ms]', 'seq', 'ID', 'msgcnt', 'Δmsgcnt'], sheet.cellFormats('header'))
        return [row, col+10, []]
    
    def printValue(self, sheet, row, col, _level = 1):
        sheet.write_row(row, col, [self.logIndex, self.logTime.strftime('%Y-%m-%d %H:%M:%S.%f')], sheet.cellFormats('default'))
        sheet.write_number(row, col+2, self.logTimeDiff.total_seconds() * 1000)
        sheet.write_row(row, col+3, [self.length], sheet.cellFormats('default'))
        sheet.write_number(row, col+4, self.timeStamp)
        sheet.write_number(row, col+5, self.timeStampDiff * 1000)
        sheet.write_row(row, col+6, [0, hex(self.messageID), 0, 0], sheet.cellFormats('default'))
        return [row, col+10, []]

    def drawChart(self, book, sheet, totalRows):
        pass
    
class CommonHeader():
    # MultiProcessにより処理される場合、process毎に別々のメモリ領域となり、値は共有されない。
    # つまり、メッセ時の個別解析と、全体のTimeLog分析を同時にしても、値（過去値）が上書きされないので、大丈夫
    preLogTime = {}
    preTimeStamp = {}
    preMsgCount = {}
    preIndex = {}
    preSameIndexCnt = {}
    maxSameIndexCnt = {}
    maxSameIndexCnt_index = {}
    maxMsgCountDiff = {}
    maxMsgCountDiff_index = {}
    firstLogTime = {}
    
    def __init__(self, index, time, definitionID, data):
        readFunc = data.readValue
        self.logIndex = index
        self.logTime = time
        self.definitionID = definitionID
        self.length = readFunc(int,32)
        self.timeStamp = readFunc(int,48)
        self.sequenceNumber = readFunc(int,16)
        self.messageID = readFunc(int,32)
        self.messageCount = readFunc(int,32)
        
        if self.definitionID in CommonHeader.preLogTime:
            self.logTimeDiff = self.logTime - CommonHeader.preLogTime[self.definitionID]
            self.timeStampDiff = self.timeStamp - CommonHeader.preTimeStamp[self.definitionID]
            self.msgCountDiff = self.messageCount - CommonHeader.preMsgCount[self.definitionID]
            if getIgnoreSameMsgcnt() == True and self.messageCount > 0 and self.msgCountDiff == 0:
                return
            if self.msgCountDiff > CommonHeader.maxMsgCountDiff[self.definitionID]:
                CommonHeader.maxMsgCountDiff[self.definitionID] = self.msgCountDiff
                CommonHeader.maxMsgCountDiff_index[self.definitionID] = index
            if CommonHeader.preIndex[self.definitionID] == index:
                CommonHeader.preSameIndexCnt[self.definitionID] += 1
                if CommonHeader.preSameIndexCnt[self.definitionID] > CommonHeader.maxSameIndexCnt[self.definitionID]:
                    CommonHeader.maxSameIndexCnt[self.definitionID] = CommonHeader.preSameIndexCnt[self.definitionID]
                    CommonHeader.maxSameIndexCnt_index[self.definitionID] = index
            else:
                CommonHeader.preSameIndexCnt[self.definitionID] = 0
        else:
            self.logTimeDiff = timedelta(0, 0, 0)
            self.timeStampDiff = 0
            if self.messageCount == 0:
                self.msgCountDiff = 0
            else:
                self.msgCountDiff = 1
            CommonHeader.preSameIndexCnt[self.definitionID] = 1
            CommonHeader.maxSameIndexCnt[self.definitionID] = 1
            CommonHeader.maxSameIndexCnt_index[self.definitionID] = 0
            CommonHeader.maxMsgCountDiff[self.definitionID] = 1
            CommonHeader.maxMsgCountDiff_index[self.definitionID] = 0

        CommonHeader.preIndex[self.definitionID] = self.logIndex
        CommonHeader.preLogTime[self.definitionID] = self.logTime
        CommonHeader.preTimeStamp[self.definitionID] = self.timeStamp
        CommonHeader.preMsgCount[self.definitionID] = self.messageCount
    
    def columnCount(self):
        return 10
    
    def printHeader(self, sheet, row, col, _level = 1):
        sheet.write_row(row, col, ['logIndex', 'logTime', 'ΔlogTime[ms]', 'length', 'timeStamp[s]', 'ΔtimeStamp[ms]', 'seq', 'ID', 'msgcnt', 'Δmsgcnt'], sheet.cellFormats('header'))
        return [row, col+10, []]
    
    def printValue(self, sheet, row, col, _level = 1):
        sheet.write_row(row, col, [self.logIndex, self.logTime.strftime('%Y-%m-%d %H:%M:%S.%f')], sheet.cellFormats('default'))
        sheet.write_number(row, col+2, self.logTimeDiff.total_seconds() * 1000)
        if isCANmessageIncluded([self.messageID]):
            sheet.write_row(row, col+3, [self.length-20], sheet.cellFormats('default')) # dummy共通ヘッダは除外した長さ
        else:
            sheet.write_row(row, col+3, [self.length], sheet.cellFormats('default'))
        sheet.write_number(row, col+4, self.timeStamp / 1000000)
        sheet.write_number(row, col+5, self.timeStampDiff / 1000)
        sheet.write_row(row, col+6, [self.sequenceNumber, hex(self.messageID), self.messageCount], sheet.cellFormats('default'))
        sheet.write_number(row, col+9, self.msgCountDiff)
        return [row, col+10, []]

    def drawChart(self, book, sheet, totalRows):
        messagePeriod_ms = getEtherIdDic(self.definitionID)['period']
        
        chart = book.add_chart({'type': 'line'})
        chart.set_title({
            'name': '{0}の通信間隔[ms]'.format(getEtherIdDic(self.definitionID)['name']),
            'name_font': {'size': 16, 'bold': False}})
        chart.add_series({
            'name': '間隔[ms]',
            'values':     "='{0}'!$C$1:$C${1}".format(sheet.name, totalRows)})
        if messagePeriod_ms != None:
            if messagePeriod_ms < 20:
                chart.set_y_axis({'min': 0, 'max': messagePeriod_ms*2})
            else:
                chart.set_y_axis({'min': messagePeriod_ms-20, 'max': messagePeriod_ms+20})
        sheet.insert_chart('C4', chart)
        
        chart = book.add_chart({'type': 'line'})
        chart.set_title({
            'name': '{0}のTimeStamp間隔[ms]'.format(getEtherIdDic(self.definitionID)['name']),
            'name_font': {'size': 16, 'bold': False}})
        chart.add_series({
            'name': '間隔[ms]',
            'values':     "='{0}'!$F$1:$F${1}".format(sheet.name, totalRows)})
        if messagePeriod_ms != None:
            if messagePeriod_ms < 20:
                chart.set_y_axis({'min': 0, 'max': messagePeriod_ms*2})
            else:
                chart.set_y_axis({'min': messagePeriod_ms-20, 'max': messagePeriod_ms+20})
        sheet.insert_chart('J4', chart)
        
        chart = book.add_chart({'type': 'line'})
        chart.set_title({
            'name': '{0}のmsgCnt飛び'.format(getEtherIdDic(self.definitionID)['name']),
            'name_font': {'size': 16, 'bold': False}})
        chart.add_series({
            'name': 'ΔmsgCnt',
            'values':     "='{0}'!$J$1:$J${1}".format(sheet.name, totalRows)})
        chart.set_y_axis({'min': -1, 'max': 10, 'major_unit':1})
        sheet.insert_chart('Q4', chart)
        
        
#-----------------------------------------------#
#----   Template_Default_Message            ----#
#-----------------------------------------------#
class Template_Default_Message(Message, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def GetFieldNameList(cls, self = None):
        return []
                
    def __init__(self, index, time, definitionID, data, useCommonHeader = True):
        super().__init__(index, time, definitionID, data, useCommonHeader)
    
    def parse(self, oldMessage = None):
        readFunc = self.data.readValue
        for attr in self.GetFieldNameList(self):
            if len(attr) < 3: # (fieldName, size, readType, resolution, offset, sign, readFromLSB, endian)
                raise ValueError("FieldNameList Attr error")
            fieldName = attr[0]
            size = attr[1]
            readType = attr[2]
            if len(attr) >= 4: resolution = attr[3]
            else: resolution = 1.0
            if len(attr) >= 5: offset = attr[4]
            else: offset = 0.0
            if len(attr) >= 6: sign = attr[5]
            else: sign = False
            if len(attr) >= 7: readFromLSB = attr[6]
            else: readFromLSB = False
            if len(attr) >= 8: endian = attr[7]
            else: endian='big'
            try:
                if fieldName == '':
                    readFunc(readType,size)
                else:
                    if readType == str or readType == bytes:
                        exec('self.{} = readFunc(readType, {}, sign=False, readFromLSB={}, endian=\'{}\')'.format(fieldName, size, readFromLSB, endian))
                    else:
                        exec('self.{} = readFunc(readType, {}, sign={}, readFromLSB={}, endian=\'{}\') * {} + {}'.format(fieldName, size, sign, readFromLSB, endian, resolution, offset))
            except Exception as e:
                print("(parse error) fieldName={}, size={}, readType={}".format(fieldName, size, readType))
                raise e

#         super().assertMessageSize() #CANメッセージは、色んなBusで同じIDで異なるフレームサイズで流れている可能性があるので、長さチェックはしない。

    def printHeader(self, sheet, row, col, _level = 1):
        [_, col, _] = self.commonHeader.printHeader(sheet, row, col)
        
        strList = []
        for attr in self.GetFieldNameList(self):
            fieldName = attr[0]
            if fieldName != '':
                strList.append(fieldName)
        
        sheet.write_row(row, col, strList, sheet.cellFormats('header'))
        col += len(strList)
        
        sheet.freeze_panes(1, 0)
        sheet.set_row(0, 20)
        sheet.autofilter(0, 0, 0, col-1)
        return [row+1, 0, []]
    
    def printValue(self, sheet, row, col, _level = 1):
        [row, col, _] = self.commonHeader.printValue(sheet, row, col)
        
        valList = []
        for attr in self.GetFieldNameList(self):
            fieldName = attr[0]
            if fieldName != '':
                if type(eval('self.{}'.format(fieldName))) == bytearray:
                    valList.append('0x' + ''.join(format(x,'02X') for x in eval('self.{}'.format(fieldName))))
                else:
                    valList.append(eval('self.{}'.format(fieldName)))

        sheet.write_row(row, col, valList)
        
        return  [row+1, 0, []]
    
    def drawChart(self, book, sheet, totalRows): 
        self.commonHeader.drawChart(book, sheet, totalRows)


#-----------------------------------------------#
#----   Template_Default_Message_WithDraw   ----#
#-----------------------------------------------#
class Template_Default_Message_WithDraw(Template_Default_Message):
    class LayerType(Enum):
        DefaultLine = 190
    
    def __init__(self, index, time, definitionID, data, useCommonHeader = True):
        super().__init__(index, time, definitionID, data, useCommonHeader)
        
    @classmethod
    def SetLayerStyle(cls, layerType, layer):
        if layerType == cls.LayerType.DefaultLine:
            symbollist = layer.renderer().symbols(QgsRenderContext())
            symbol = symbollist[0]
            symbol.setColor(QtGui.QColor.fromRgb(0,0,0))
            symbol.setWidth(0.2)
            layer.beginEditCommand( 'QGIS draw' )
            return [layer, layerType.value]
        else:
            return None
    
    def createLayer(self, name, iface_obj, realTimeMode):
        configStr = 'LineString?crs=epsg:4612&field=Time:DateTime'
        for attr in self.GetFieldNameList(self):
            fieldName = attr[0]
            readType = attr[2]
            if fieldName != '':
                if readType == str or readType == bytes:
                    configStr += '&field={}:string'.format(fieldName)
                elif readType == int:
                    configStr += '&field={}:long'.format(fieldName)
                elif readType == float:
                    configStr += '&field={}:double'.format(fieldName)
                else:
                    configStr += '&field={}:{}'.format(fieldName, readType)
        configStr += '&index=yes'
        newLayer = iface_obj.addVectorLayer(configStr,name,'memory')
        newLayer = self.SetLayerStyle(self.LayerType.DefaultLine, newLayer)
        return [newLayer]
    
    def drawQGIS(self, layerList, realTimeMode):
        layer = None
        for layerListItem in layerList:
            if layerListItem[1] == self.LayerType.DefaultLine.value:
                layer = layerListItem[0]

        old = self.oldMessage
        if old == None:
            return
        
        if layer != None:
            [lon, lat] = self.getRelatedPosition([self.relatedGNSSPositionMessage, self.relatedCarPositionMessage, self.relatedADPositionMessage, self.relatedIVIPositionMessage, self.relatedADASISPositionMessage])
            [oldLon, oldLat] = old.getRelatedPosition([old.relatedGNSSPositionMessage, old.relatedCarPositionMessage, old.relatedADPositionMessage, old.relatedIVIPositionMessage, old.relatedADASISPositionMessage])
            
            if checkInvalidLonLat(lon, lat, oldLon, oldLat) == True:
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPolyline([QgsPoint(oldLon, oldLat), QgsPoint(lon, lat)]))
                attributeList = [QDateTime(self.commonHeader.logTime)]
                for attr in self.GetFieldNameList(self):
                    fieldName = attr[0]
                    if fieldName != '':
                        if type(eval('self.{}'.format(fieldName))) == bytearray:
                            attributeList.append('0x' + ''.join(format(x,'02X') for x in eval('self.{}'.format(fieldName))))
                        else:
                            attributeList.append(eval('self.{}'.format(fieldName)))
                feature.setAttributes(attributeList)
                layer.dataProvider().addFeatures( [feature] )
