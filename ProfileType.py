from TypeDef import ProfileType
from typing import List
try:
    from ExcelFileCtrl import rowGroupingPrint
except:
    pass
from dataclasses import dataclass
from datetime import datetime
from GlobalVar import getEthernetSpecVer

profileIdDic = {
    0x1000:{'name':'レーンリンク情報',      'class':'PROFILETYPE_MPU_ZGM_LANE_LINK_INFO'},
    0x1001:{'name':'区画線情報',        'class':'PROFILETYPE_MPU_ZGM_LANE_DIVISION_LINE'},
    0x1002:{'name':'線形状情報',        'class':'PROFILETYPE_MPU_LINE_GEOMETRY'},
    0x1003:{'name':'破線ペイント情報',     'class':'DotLinePaintInfoProfile'},
    0x1004:{'name':'信号機情報',        'class':'PROFILETYPE_MPU_ZGM_TRAFFIC_LIGHT'},
    0x1005:{'name':'道路標示',          'class':'PROFILETYPE_MPU_ZGM_TRAFFIC_PAINT'},
    0x1006:{'name':'標識情報',          'class':'PROFILETYPE_MPU_ZGM_SIGN_INFO'},
    0x1007:{'name':'停止線',            'class':'PROFILETYPE_MPU_ZGM_STOP_LINE'},
    0x1008:{'name':'曲率情報',          'class':'PROFILETYPE_MPU_ZGM_CURVATURE'},
    0x1009:{'name':'勾配情報',          'class':'PROFILETYPE_MPU_ZGM_SLOPE'},
    0x100A:{'name':'路肩幅員',          'class':'PROFILETYPE_MPU_ZGM_SHOULDER_WIDTH'},
    0x100B:{'name':'LanesGeometry',    'class':'LanesGeometryProfile'},
    0x100C:{'name':'TRANSFER_STS',     'class':'PROFILE_MPU_MAP_DATA_TRANSFER_STS'},
    0x100D:{'name':'BASE_POINT',       'class':'PROFILE_MPU_MAP_DATA_BASE_POINT'},
    0x100E:{'name':'不足データチェック用リスト情報', 'class':'PROFILE_MPU_MAP_ID_LIST'},
    0x1011:{'name':'IVI Stub Info',    'class':'IVIStubInfoProfile'},
    
    0x2000:{'name':'自車位置情報',       'class':'AbsoluteVehiclePositionProfile'},
    
    0x3000:{'name':'レーンリンク情報(US)',  'class':'PROFILETYPE_MPU_US_LANE_LINK_INFO'},
    0x3001:{'name':'Lane Line情報(US)', 'class':'PROFILETYPE_MPU_US_LANE_LINE'},
    0x3002:{'name':'Lane Line形状情報(US)','class':'PROFILETYPE_MPU_US_LANE_LINE_GEOMETRY'},
    0x3003:{'name':'Road Edge情報(US)',  'class':'PROFILETYPE_MPU_US_ROAD_EDGE'},
    0x3004:{'name':'Road Edge形状情報(US)','class':'PROFILETYPE_MPU_US_ROAD_EDGE_GEOMETRY'},
    0x3005:{'name':'信号機情報(US)',     'class':'PROFILETYPE_MPU_US_REGULATORY_TRRAFIC_DEVICE'},
    0x3006:{'name':'道路標示(US)',      'class':'PROFILETYPE_MPU_US_PAVEMENT_MARKING'},
    0x3007:{'name':'標識情報(US)',      'class':'PROFILETYPE_MPU_US_SIGN'},
    0x3008:{'name':'曲率情報(US)',      'class':'PROFILETYPE_MPU_US_CURVATURE'},
    0x3009:{'name':'勾配情報(US)',      'class':'PROFILETYPE_MPU_US_SLOPE'},
    0x300A:{'name':'レーン幅員(US)',      'class':'PROFILETYPE_MPU_US_LANE_WIDTH'},
    0x300B:{'name':'LanesGeometry(US)','class':'LanesGeometryProfile_US'},
    0x300C:{'name':'TRANSFER_STS(US)', 'class':'PROFILE_MPU_MAP_DATA_TRANSFER_STS'},
    0x300D:{'name':'BASE_POINT(US)',   'class':'PROFILE_MPU_MAP_DATA_BASE_POINT'},
    0x300E:{'name':'不足データチェック用リスト情報(US)', 'class':'PROFILE_MPU_MAP_ID_LIST'},
    0x300F:{'name':'IVI Stub Info(US)','class':'IVIStubInfoProfile'}}

#-----------------------------------------------#
#----   Functions                           ----#
#-----------------------------------------------#
def analyzeProfile(profileType, data, refMessage):
    if profileType in profileIdDic:
        try:
            result = globals()[profileIdDic[profileType]['class']](data, refMessage) 
            return result
        except Exception:
            return UnknownProfile(data, refMessage)
    else:
        return UnknownProfile(data, refMessage)

#-----------------------------------------------#
#----   PROFILETYPE_MPU_ZGM_LANE_LINK_INFO  ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_LANE_LINK_INFO(ProfileType):
    SDLinkageString = {0x0000:'有効', 0x8000:'無効'}
    
    @dataclass
    class ADAS2property:
        startLinkFlag: int
        laneClassCode: int
        linkClass: int
        linkPropertyOptionFlag: int
        linkAddtionalPropertyFlag: int
        
    class LaneInfo:
        laneID: int #64
        leftLaneID: int #64
        rightLaneID: int #64
        lanePropFlag: int #32
        lanePropOptionFlag: int #32
        distance: int #32
        laneNWclass: int #16
        lanePropClass: int #16
        laneNumber: int #16
        maxSpeed: int #16
        width: int #16
        versionCheckStatus: int #8
        versionInfo: int #8
        middleGuideClass: int #16
        precisionFlag: int #16
        maintainStartDay: int #32
        maintainStartTime: int #16
        functionLimitationFlag1: int #32
        functionLimitationFlag2: int #32
        functionLimitationFlag3: int #32
        maintainClass: int #32
        routeChangeStatus: int #32
        SDLinkage: int #16
        adas2propertyCount: int
        adas2propertyArray: List[int]
        signInfoIDcount: int #32
        signInfoID: List[int] #64
        roadMarkingIDcount: int #32
        roadMarkingID: List[int] #64
        markerIDcount: int #32
        markerID: List[int] #64
        stopLineIDcount: int #32
        stopLineID: List[int] #64
        objectIDcount: int #32
        objectID: List[int] #64
        objectPositionClass: List[int] #16
        frontLaneIDcount: int #32
        frontLaneID: List[int] #64
        backLaneIDcount: int #32
        backLaneID: List[int] #64
        
        def printValue(self, sheet, row, col, _level = 1):
            printList = [
                sheet.cellFormats('blue'), '   *レーンID: ', str(self.laneID) + "\n",
                sheet.cellFormats('blue'), '   *左側車線のレーンID: ', str(self.leftLaneID) + "\n",
                sheet.cellFormats('blue'), '   *右側車線のレーンID: ', str(self.rightLaneID) + "\n",
                sheet.cellFormats('blue'), '   *レーン付加属性フラグ: ', str(self.lanePropFlag) + "\n",
                sheet.cellFormats('blue'), '   *レーン属性オプションフラグ : ', str(self.lanePropOptionFlag) + "\n",
                sheet.cellFormats('blue'), '   *距離[cm]: ', str(self.distance) + "\n",
                sheet.cellFormats('blue'), '   *レーンNW種別: ', str(self.laneNWclass) + "\n",
                sheet.cellFormats('blue'), '   *車線属性種別 : ', str(self.lanePropClass) + "\n",
                sheet.cellFormats('blue'), '   *レーン番号: ' , str(self.laneNumber) + "\n",
                sheet.cellFormats('blue'), '   *最高速度情報[kmh]: ', str(self.maxSpeed) + "\n",
                sheet.cellFormats('blue'), '   *幅員情報[cm]: ', str(self.width) + "\n",
                sheet.cellFormats('blue'), '   *鮮度情報チェック状態: ', str(self.versionCheckStatus) + "\n",
                sheet.cellFormats('blue'), '   *鮮度情報: ', str(self.versionInfo) + "\n",
                sheet.cellFormats('blue'), '   *中央分離帯種別: ', str(self.middleGuideClass) + "\n",
                sheet.cellFormats('blue'), '   *精度管理フラグ: ', str(self.precisionFlag) + "\n",
                sheet.cellFormats('blue'), '   *工事開始日: ', str(self.maintainStartDay) + "\n",
                sheet.cellFormats('blue'), '   *工事開始時間: ', str(self.maintainStartTime) + "\n",
                sheet.cellFormats('blue'), '   *工事種別: ', str(self.maintainClass) + "\n",
                sheet.cellFormats('blue'), '   *機能制限フラグ３: ', str(self.functionLimitationFlag3) + "\n",
                sheet.cellFormats('blue'), '   *機能制限フラグ２: ', str(self.functionLimitationFlag2) + "\n",
                sheet.cellFormats('blue'), '   *機能制限フラグ１: ', str(self.functionLimitationFlag1) + "\n",
                sheet.cellFormats('blue'), '   *経路変換状態: ', str(self.routeChangeStatus) + "\n",
                sheet.cellFormats('blue'), '   *SDLinkage有無: ', PROFILETYPE_MPU_ZGM_LANE_LINK_INFO.SDLinkageString.get(self.SDLinkage, '[error]') + "\n"]
            
            printList += [sheet.cellFormats('blue'), '   *ADAS2.0属性数: ', str(self.adas2propertyCount) + "\n"]
            for i in range(self.adas2propertyCount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 始点リンクフラグ: ', hex(self.adas2propertyArray[i].startLinkFlag) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 道路種別コード: ', hex(self.adas2propertyArray[i].laneClassCode) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') リンク種別: ', str(self.adas2propertyArray[i].linkClass) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') リンク属性オプションフラグ: ', hex(self.adas2propertyArray[i].linkPropertyOptionFlag) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') リンク付加属性フラグ: ', hex(self.adas2propertyArray[i].linkAddtionalPropertyFlag) + "\n"]

            printList += [sheet.cellFormats('blue'), '   *信号機情報ID数: ', str(self.signInfoIDcount) + "\n"]
            for i in range(self.signInfoIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 信号機情報ID: ', (hex(self.signInfoID[i])) + "\n"]
            
            printList += [sheet.cellFormats('blue'), '   *道路標示情報ID数: ', str(self.roadMarkingIDcount) + "\n"]
            for i in range(self.roadMarkingIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 道路標示情報ID: ', (hex(self.roadMarkingID[i])) + "\n"]
                
            printList += [sheet.cellFormats('blue'), '   *標識情報ID数: ', str(self.markerIDcount) + "\n"]
            for i in range(self.markerIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 標識情報ID: ', (hex(self.markerID[i])) + "\n"]

            printList += [sheet.cellFormats('blue'), '   *停止線情報ID数: ', str(self.stopLineIDcount) + "\n"]
            for i in range(self.stopLineIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 停止線情報ID: ', (hex(self.stopLineID[i])) + "\n"]

            printList += [sheet.cellFormats('blue'), '   *ライン型地物ID数: ', str(self.objectIDcount) + "\n"]
            for i in range(self.objectIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') ライン型地物ID: ', (hex(self.objectID[i])) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 位置種別: ', str(self.objectPositionClass[i]) + "\n"]
                
            printList += [sheet.cellFormats('blue'), '   *前方レーンID数: ', str(self.frontLaneIDcount) + "\n"]
            for i in range(self.frontLaneIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 前方レーンID: ', str(self.frontLaneID[i]) + "\n"]
            
            printList += [sheet.cellFormats('blue'), '   *後方レーンID数: ', str(self.backLaneIDcount) + "\n"]
            for i in range(self.backLaneIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 後方レーンID: ', str(self.backLaneID[i]) + "\n"]

            printList += [sheet.cellFormats('wrap')]
            sheet.write_rich_string(row, col, *printList)
            sheet.write(row, col+1, "...")
#             for i in range(0,len(printList),3):
#                 sheet.write_rich_string(row, col+i/3, *(printList[i:i+3]))
#             sheet.set_row(row, 13.5*6)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        ethernetSpecVersion = getEthernetSpecVer()
        
        self.laneInfoArrayCount = readFunc(int,32)
        self.laneInfoArray = []
        for _ in range(self.laneInfoArrayCount):
            laneInfo = self.LaneInfo()
            laneInfo.laneID = readFunc(int,64)
            laneInfo.leftLaneID = readFunc(int,64)
            laneInfo.rightLaneID = readFunc(int,64)
            laneInfo.lanePropFlag = readFunc(int,32)
            laneInfo.lanePropOptionFlag = readFunc(int,32)
            laneInfo.distance = readFunc(int,32)
            laneInfo.laneNWclass = readFunc(int,16,True)
            laneInfo.lanePropClass = readFunc(int,16,True)
            laneInfo.laneNumber = readFunc(int,16,True)
            laneInfo.maxSpeed = readFunc(int,16)
            laneInfo.width = readFunc(int,16,True)
            laneInfo.versionCheckStatus = readFunc(int,8)
            laneInfo.versionInfo = readFunc(int,8)
            laneInfo.middleGuideClass = readFunc(int,16)
            laneInfo.precisionFlag = readFunc(int,16)
            laneInfo.maintainStartDay = readFunc(int,32)
            laneInfo.maintainStartTime = readFunc(int,16)
            readFunc(int,16) #reserved
            
            if ethernetSpecVersion >= datetime(2020, 3, 31):
                laneInfo.maintainClass = readFunc(int,32)
                laneInfo.functionLimitationFlag3 = readFunc(int,32)
                laneInfo.functionLimitationFlag2 = readFunc(int,32)
                laneInfo.functionLimitationFlag1 = readFunc(int,32)
            else:
                laneInfo.maintainClass = readFunc(int,32)
                laneInfo.functionLimitationFlag3 = 0xFFFFFFFF
                laneInfo.functionLimitationFlag2 = 0xFFFFFFFF
                laneInfo.functionLimitationFlag1 = 0xFFFFFFFF
                
            laneInfo.routeChangeStatus = readFunc(int,32)
            
            if ethernetSpecVersion >= datetime(2020, 4, 14):
                laneInfo.SDLinkage = readFunc(int,16)
            else:
                laneInfo.SDLinkage = 0x8000
                
            if ethernetSpecVersion >= datetime(2020, 3, 19):
                laneInfo.adas2propertyCount = readFunc(int,32)
                laneInfo.adas2propertyArray = []
                for _ in range(laneInfo.adas2propertyCount):
                    laneInfo.adas2propertyArray.append(self.ADAS2property(
                        startLinkFlag = readFunc(int,8),
                        laneClassCode = readFunc(int,16),
                        linkClass = readFunc(int,16),
                        linkPropertyOptionFlag = readFunc(int,32),
                        linkAddtionalPropertyFlag = readFunc(int,32)))
            else:
                laneInfo.adas2propertyCount = 0
                laneInfo.adas2propertyArray = []
                
            laneInfo.signInfoIDcount = readFunc(int,32)
            laneInfo.signInfoID = []
            for _ in range(laneInfo.signInfoIDcount):
                laneInfo.signInfoID.append(readFunc(int,64,True))
            laneInfo.roadMarkingIDcount = readFunc(int,32)
            laneInfo.roadMarkingID = []
            for _ in range(laneInfo.roadMarkingIDcount):
                laneInfo.roadMarkingID.append(readFunc(int,64,True))
            laneInfo.markerIDcount = readFunc(int,32)
            laneInfo.markerID = []
            for _ in range(laneInfo.markerIDcount):
                laneInfo.markerID.append(readFunc(int,64,True))
            laneInfo.stopLineIDcount = readFunc(int,32)
            laneInfo.stopLineID = []
            for _ in range(laneInfo.stopLineIDcount):
                laneInfo.stopLineID.append(readFunc(int,64,True))
            laneInfo.objectIDcount = readFunc(int,32)
            laneInfo.objectID = []
            laneInfo.objectPositionClass = []
            for _ in range(laneInfo.objectIDcount):
                laneInfo.objectID.append(readFunc(int,64,True))
                laneInfo.objectPositionClass.append(readFunc(int,16))
                readFunc(int,16) #reserved
            laneInfo.frontLaneIDcount = readFunc(int,32)
            laneInfo.frontLaneID = []
            for _ in range(laneInfo.frontLaneIDcount):
                laneInfo.frontLaneID.append(readFunc(int,64))
            laneInfo.backLaneIDcount = readFunc(int,32)
            laneInfo.backLaneID = []
            for _ in range(laneInfo.backLaneIDcount):
                laneInfo.backLaneID.append(readFunc(int,64))
            self.laneInfoArray.append(laneInfo)

    def printHeader(self, _sheet, row, col, _level = 1):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level = 1):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *レーン情報数: ', str(self.laneInfoArrayCount))
        row += 1
        
        groupResult = []
        for i in range(self.laneInfoArrayCount):
            [row, _, result] = rowGroupingPrint(
                'レーン情報(' + str(i+1) + ')', 
                None, 
                self.laneInfoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_LANE_LINK_INFO     ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_LANE_LINK_INFO(ProfileType):
    SDLinkageString = {0x0000:'有効', 0x8000:'無効'}
    RouteChangeStatusString = { 0:'変換成功',
                                1:'変換不可（対応する地図が無い）',
                                2:'変換不可（変換候補の評価値が低い）',
                                3:'変換不可（隣のLRPまでの距離が離れすぎている）',
                                4:'変換不可（隣のLRPに接続できるレーンが無い）',
                                5:'変換不可（IVI経路情報異常）',
                                6:'変換不可（その他）'}
    RoadTypeString = {  0: '(0) Controlled Access Divided',
                        1: '(1) Non-Controlled Access Divided',
                        2: '(2) Interchange',
                        3: '(3) Ramp',
                        4: '(4) Controlled Access Non-Divided',
                        5: '(5) Non-Controlled Access Non-Divided',
                        6: '(6) Local Divided',
                        7: '(7) Local Non-Divided'}
    LaneTypeString = {  1: '(1) Normal Driving Lane',
                        2: '(2) HOV Lane',
                        4: '(4) Bidirectional Lane',
                        8: '(8) Bus/Taxi Lane',
                        16: '(16) Toll Booth Lane',
                        32: '(32) Convertible To Shoulder ',
                        64: '(64) Turn Only Lane',
                        128: '(128) Other'}
    laneAddRemoveTypeString = { 0: '(0)None',
                                1: '(1)Ending Lane',
                                2: '(2)Merging Lane',
                                3: '(3)Added Lane',
                                4: '(4)Diverging Lane'}
    
    @dataclass
    class ADAS2property:
        OSMID: int #64
        laneClassCode: int #8
        subLinkClassCode: int #8
        infoFlag: int #8
        
    class LaneInfo:
        laneID: int #64
        leftLaneID: int #64
        rightLaneID: int #64
        roadType: int #16
        roadTypeStr: str
        laneAddRemoveType: int #16
        acceleratingLane: int #8
        deceleratingLane: int #8
        laneType: int #16
        laneTypeStr: str
        crossingType: int #8
        leftChangeAllowed: int #8
        rightChangeAllowed: int #8
        distance: int #16
        laneNumber: int #16
        numberOfLanes: int #16
        maxSpeed: int #16
        mapFunctionalAuthority: int #32
        functionalAuthority3: int #32
        functionalAuthority2: int #32
        functionalAuthority1: int #32
        versionCheckStatus: int #8
        versionInfo: int #8
        routeChangeStatus: int #32
        SDLinkage: int #16
        adas2propertyCount: int
        adas2propertyArray: List[int]
        signInfoIDcount: int #32
        signInfoID: List[int] #64
        roadMarkingIDcount: int #32
        roadMarkingID: List[int] #64
        markerIDcount: int #32
        markerID: List[int] #64
        laneLineIDcount: int #32
        laneLineID: List[int] #64
        laneLinePosClass: List[int] #16
        loadEdgeIDcount: int #32
        loadEdgeID: List[int] #64
        loadEdgePosClass: List[int] #16
        frontLaneIDcount: int #32
        frontLaneID: List[int] #64
        backLaneIDcount: int #32
        backLaneID: List[int] #64
        
        def printValue(self, sheet, row, col, _level = 1):
            printList = [
                sheet.cellFormats('blue'), '   *レーンID: ', str(self.laneID) + "\n",
                sheet.cellFormats('blue'), '   *左側車線のレーンID: ', str(self.leftLaneID) + "\n",
                sheet.cellFormats('blue'), '   *右側車線のレーンID: ', str(self.rightLaneID) + "\n",
                sheet.cellFormats('blue'), '   *Road Type: ', str(self.roadTypeStr) + "\n",    
                sheet.cellFormats('blue'), '   *Lane_Add_Remove_Type: ', str(self.laneAddRemoveType) + "\n",    
                sheet.cellFormats('blue'), '   *Accelerating Lane: ', str(self.acceleratingLane) + "\n",    
                sheet.cellFormats('blue'), '   *Decelerating Lane: ', str(self.deceleratingLane) + "\n",    
                sheet.cellFormats('blue'), '   *Lane Type: ', str(self.laneTypeStr) + "\n",    
                sheet.cellFormats('blue'), '   *Crossing Type (only tunnel): ', str(self.crossingType) + "\n",    
                sheet.cellFormats('blue'), '   *Left Change Allowed: ', str(self.leftChangeAllowed) + "\n",    
                sheet.cellFormats('blue'), '   *Right Change Allowed: ', str(self.rightChangeAllowed) + "\n",    
                sheet.cellFormats('blue'), '   *距離[m]: ', str(self.distance) + "\n",
                sheet.cellFormats('blue'), '   *レーン番号: ' , str(self.laneNumber) + "\n",
                sheet.cellFormats('blue'), '   *レーン総数: ' , str(self.numberOfLanes) + "\n",
                sheet.cellFormats('blue'), '   *最高速度情報[kmh]: ', str(self.maxSpeed) + "\n",
                sheet.cellFormats('blue'), '   *MAP Functional Authority: ', str(self.mapFunctionalAuthority) + "\n",    
                sheet.cellFormats('blue'), '   *Functional Authority 3: ', str(self.functionalAuthority3) + "\n",    
                sheet.cellFormats('blue'), '   *Functional Authority 2: ', str(self.functionalAuthority2) + "\n",    
                sheet.cellFormats('blue'), '   *Functional Authority 1: ', str(self.functionalAuthority1) + "\n",    
                sheet.cellFormats('blue'), '   *鮮度情報チェック状態: ', str(self.versionCheckStatus) + "\n",
                sheet.cellFormats('blue'), '   *鮮度情報: ', str(self.versionInfo) + "\n",
                sheet.cellFormats('blue'), '   *経路変換状態: ', PROFILETYPE_MPU_US_LANE_LINK_INFO.RouteChangeStatusString.get(self.routeChangeStatus, '[error]') + "\n",
                sheet.cellFormats('blue'), '   *SDLinkage有無: ', PROFILETYPE_MPU_US_LANE_LINK_INFO.SDLinkageString.get(self.SDLinkage, '[error]') + "\n"]
            
            printList += [sheet.cellFormats('blue'), '   *ADAS2.0属性数: ', str(self.adas2propertyCount) + "\n"]
            for i in range(self.adas2propertyCount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') OSMID: ', str(self.adas2propertyArray[i].OSMID) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 道路種別: ', str(self.adas2propertyArray[i].laneClassCode) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') サブリンク種別: ', str(self.adas2propertyArray[i].subLinkClassCode) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 橋・トンネル属性: ', bin(self.adas2propertyArray[i].infoFlag) + "\n"]

            printList += [sheet.cellFormats('blue'), '   *信号機情報ID数: ', str(self.signInfoIDcount) + "\n"]
            for i in range(self.signInfoIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 信号機情報ID: ', (hex(self.signInfoID[i])) + "\n"]
            
            printList += [sheet.cellFormats('blue'), '   *道路標示情報ID数: ', str(self.roadMarkingIDcount) + "\n"]
            for i in range(self.roadMarkingIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 道路標示情報ID: ', (hex(self.roadMarkingID[i])) + "\n"]
                
            printList += [sheet.cellFormats('blue'), '   *標識情報ID数: ', str(self.markerIDcount) + "\n"]
            for i in range(self.markerIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 標識情報ID: ', (hex(self.markerID[i])) + "\n"]

            printList += [sheet.cellFormats('blue'), '   *Lane Line ID数: ', str(self.laneLineIDcount) + "\n"]
            for i in range(self.laneLineIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') Lane Line ID: ', (hex(self.laneLineID[i])) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 位置種別: ', (str(self.laneLinePosClass[i])) + "\n"]

            printList += [sheet.cellFormats('blue'), '   *Road Edge ID数: ', str(self.loadEdgeIDcount) + "\n"]
            for i in range(self.loadEdgeIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') Road Edge ID: ', (hex(self.loadEdgeID[i])) + "\n"]
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 位置種別: ', (str(self.loadEdgePosClass[i])) + "\n"]
                
            printList += [sheet.cellFormats('blue'), '   *前方レーンID数: ', str(self.frontLaneIDcount) + "\n"]
            for i in range(self.frontLaneIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 前方レーンID: ', str(self.frontLaneID[i]) + "\n"]
            
            printList += [sheet.cellFormats('blue'), '   *後方レーンID数: ', str(self.backLaneIDcount) + "\n"]
            for i in range(self.backLaneIDcount):
                printList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 後方レーンID: ', str(self.backLaneID[i]) + "\n"]

            printList += [sheet.cellFormats('wrap')]
            sheet.write_rich_string(row, col, *printList)
            sheet.write(row, col+1, "...")
#             for i in range(0,len(printList),3):
#                 sheet.write_rich_string(row, col+i/3, *(printList[i:i+3]))
#             sheet.set_row(row, 13.5*6)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        ethernetSpecVersion = getEthernetSpecVer()
        
        self.laneInfoArrayCount = readFunc(int,32)
        self.laneInfoArray = []
        for _ in range(self.laneInfoArrayCount):
            laneInfo = self.LaneInfo()
            laneInfo.laneID = readFunc(int,64)
            laneInfo.leftLaneID = readFunc(int,64)
            laneInfo.rightLaneID = readFunc(int,64)
            
            laneInfo.roadType = readFunc(int,16)
            laneInfo.roadTypeStr = PROFILETYPE_MPU_US_LANE_LINK_INFO.RoadTypeString.get(laneInfo.roadType, 'Unknown')
            laneInfo.laneAddRemoveType = readFunc(int,16)    
            laneInfo.acceleratingLane = readFunc(int,8)    
            laneInfo.deceleratingLane = readFunc(int,8)    
            laneInfo.laneType = readFunc(int,16)
            laneInfo.laneTypeStr = ''
            for bitIndex in range(0,8):
                bitValue = laneInfo.laneType & (0x1 << bitIndex)
                if bitValue != 0:
                    if laneInfo.laneTypeStr != '': laneInfo.laneTypeStr += ', '
                    laneInfo.laneTypeStr += PROFILETYPE_MPU_US_LANE_LINK_INFO.LaneTypeString[bitValue]
            laneInfo.crossingType = readFunc(int,8)  
            laneInfo.leftChangeAllowed = readFunc(int,8)    
            laneInfo.rightChangeAllowed = readFunc(int,8)    

            laneInfo.distance = readFunc(int,16)
            laneInfo.laneNumber = readFunc(int,16)
            laneInfo.numberOfLanes = readFunc(int,16)
            laneInfo.maxSpeed = readFunc(int,16)
            laneInfo.mapFunctionalAuthority = readFunc(int,32)    
            laneInfo.functionalAuthority3 = readFunc(int,32)    
            laneInfo.functionalAuthority2 = readFunc(int,32)    
            laneInfo.functionalAuthority1 = readFunc(int,32)
            laneInfo.versionCheckStatus = readFunc(int,8)
            laneInfo.versionInfo = readFunc(int,8)
            laneInfo.routeChangeStatus = readFunc(int,32)
            
            if ethernetSpecVersion >= datetime(2021, 4, 21):
                laneInfo.SDLinkage = readFunc(int,16)
                laneInfo.adas2propertyCount = readFunc(int,32)
            else:
                laneInfo.SDLinkage = 0
                laneInfo.adas2propertyCount = 0
            
            laneInfo.adas2propertyArray = []
            for _ in range(laneInfo.adas2propertyCount):
                laneInfo.adas2propertyArray.append(self.ADAS2property(
                    OSMID = readFunc(int,64),
                    laneClassCode = readFunc(int,8),
                    subLinkClassCode = readFunc(int,8),
                    infoFlag = readFunc(int,8)))

            laneInfo.signInfoIDcount = readFunc(int,32)
            laneInfo.signInfoID = []
            for _ in range(laneInfo.signInfoIDcount):
                laneInfo.signInfoID.append(readFunc(int,64))
            laneInfo.roadMarkingIDcount = readFunc(int,32)
            laneInfo.roadMarkingID = []
            for _ in range(laneInfo.roadMarkingIDcount):
                laneInfo.roadMarkingID.append(readFunc(int,64))
            laneInfo.markerIDcount = readFunc(int,32)
            laneInfo.markerID = []
            for _ in range(laneInfo.markerIDcount):
                laneInfo.markerID.append(readFunc(int,64))
            laneInfo.laneLineIDcount = readFunc(int,32)
            laneInfo.laneLineID = []
            laneInfo.laneLinePosClass = []
            for _ in range(laneInfo.laneLineIDcount):
                laneInfo.laneLineID.append(readFunc(int,64))
                laneInfo.laneLinePosClass.append(readFunc(int,16))
            laneInfo.loadEdgeIDcount = readFunc(int,32)
            laneInfo.loadEdgeID = []
            laneInfo.loadEdgePosClass = []
            for _ in range(laneInfo.loadEdgeIDcount):
                laneInfo.loadEdgeID.append(readFunc(int,64))
                laneInfo.loadEdgePosClass.append(readFunc(int,16))
                
            laneInfo.frontLaneIDcount = readFunc(int,32)
            laneInfo.frontLaneID = []
            for _ in range(laneInfo.frontLaneIDcount):
                laneInfo.frontLaneID.append(readFunc(int,64))
            laneInfo.backLaneIDcount = readFunc(int,32)
            laneInfo.backLaneID = []
            for _ in range(laneInfo.backLaneIDcount):
                laneInfo.backLaneID.append(readFunc(int,64))
            
            self.laneInfoArray.append(laneInfo)

    def printHeader(self, _sheet, row, col, _level = 1):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level = 1):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *レーン情報数: ', str(self.laneInfoArrayCount))
        row += 1
        
        groupResult = []
        for i in range(self.laneInfoArrayCount):
            [row, _, result] = rowGroupingPrint(
                'レーン情報(' + str(i+1) + ')', 
                None, 
                self.laneInfoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_ZGM_LANE_DIVISION_LINE----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_LANE_DIVISION_LINE(ProfileType):
    LaneLineTypeDic = { 0:    '(0)線無し',
                        1:    '(1)単線-白実線',
                        2:    '(2)単線-白破線(細)',
                        3:    '(3)単線-白破線(太)',
                        4:    '(4)黄実線',
                        11:    '(11)二重線(同種)-白実線',
                        22:    '(22)二重線(同種)-白破線(細)',
                        44:    '(44)二重線(同種)-黄実線',
                        12:    '(12)二重線(別種)-白実線×白破線(細)',
                        21:    '(21)二重線(別種)-白破線(細)×白実線',
                        14:    '(14)二重線(別種)-白実線×黄実線',
                        41:    '(41)二重線(別種)-黄実線×白実線',
                        24:    '(24)二重線(別種)-白破線(細)×黄実線',
                        42:    '(42)二重線(別種)-黄実線×白破線(細)',
                        414:    '(414)三重線-黄実線×白実線×黄実線',
                        424:    '(424)三重線-黄実線×白破線(細)×黄実線',
                        4114:    '(4114)四重線-黄実線×白実線×白実線×黄実線'
}
    
    @dataclass
    class SplitData:
        ID: int
        parentID: int
        objectAccuracyInfo: int
        objectID: int
        classify: int
        propertyFlag: int
        startLineWidth: int
        endLineWidth: int
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *対象の区画線ID: ', str(hex(self.ID)) + "\n",
            sheet.cellFormats('blue'), '   *対象の区画線の親区画線のID: ', str(hex(self.parentID)) + "\n",
            sheet.cellFormats('blue'), '   *MMS測位誤差[mm]: ', str(self.objectAccuracyInfo & 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *レーザー測位誤差[mm]: ', str((self.objectAccuracyInfo & 0xFFFFFFFF00000000) >> 32) + "\n",
            sheet.cellFormats('blue'), '   *道路構成地物ID: ', str(hex(self.objectID)) + "\n",
            sheet.cellFormats('blue'), '   *区画線種別: ', str(self.classify) + "\n",
            sheet.cellFormats('blue'), '   *区画線付加属性フラグ: ', str(self.propertyFlag) + "\n",
            sheet.cellFormats('blue'), '   *始点側線幅[cm]: ', str(self.startLineWidth) + "\n",
            sheet.cellFormats('blue'), '   *終点側線幅[cm]: ', str(self.endLineWidth), sheet.cellFormats('wrap')])
            sheet.write(row, col+1, "...")
#             sheet.set_row(row, 13.5*6)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.splitCount = readFunc(int,32)
        self.splitDataArray = []
        for _ in range(self.splitCount):
            splitData = self.SplitData(
                ID = readFunc(int,64,True),
                parentID = readFunc(int,64,True),
                objectAccuracyInfo = readFunc(int,64,True),
                objectID = readFunc(int,32),
                classify = readFunc(int,16,True),
                propertyFlag = readFunc(int,16),
                startLineWidth = readFunc(int,16,True),
                endLineWidth = readFunc(int,16,True))
            self.splitDataArray.append(splitData)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *区画線数: ', str(self.splitCount))
        row += 1
        
        groupResult = []
        for i in range(self.splitCount):
            [row, _, result] = rowGroupingPrint(
                '区画線情報(' + str(i+1) + ')', 
                None, 
                self.splitDataArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_LANE_LINE          ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_LANE_LINE(ProfileType):
    LaneLineTypeDic = { 0: '(0)Virtual',
                        1: '(1)Single Solid Paint Line',
                        2: '(2)Single Dashed Paint Line',
                        3: '(3)Double Paint Line, Left Solid, Right Solid',
                        4: '(4)Double Paint Line, Left Dashed, Right Solid',
                        5: '(5)Double Paint Line, Left Solid, Right Dashed',
                        6: '(6)Double Paint Line, Left Dashed, Right Dashed',
                        7: '(7)Triple Paint Line All Solid',
                        8: '(8)Other'}
    
    @dataclass
    class LaneLineInfo:
        targetLaneLineID: int
        laneLineType: int    
        laneLineColor: int    
        laneLineWidth: int    
        reflectiveMarkings: int    
        pavementStripingPresent: int    

        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *対象のLane Line ID: ', str(self.targetLaneLineID) + "\n",    
            sheet.cellFormats('blue'), '   *Lane Line Type: ', str(self.laneLineType) + "\n",    
            sheet.cellFormats('blue'), '   *Lane Line Color: ', str(self.laneLineColor) + "\n",    
            sheet.cellFormats('blue'), '   *Lane Line Width: ', str(self.laneLineWidth) + "\n",    
            sheet.cellFormats('blue'), '   *Reflective Markings: ', str(self.reflectiveMarkings) + "\n",    
            sheet.cellFormats('blue'), '   *Pavement Striping Present: ', str(self.pavementStripingPresent), sheet.cellFormats('wrap')])
            sheet.write(row, col+1, "...")
#             sheet.set_row(row, 13.5*6)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.laneLineInfoCount = readFunc(int,32)
        self.laneLineInfoArray = []
        for _ in range(self.laneLineInfoCount):
            data = self.LaneLineInfo(
                targetLaneLineID = readFunc(int,64),
                laneLineType = readFunc(int,16),  
                laneLineColor = readFunc(int,16),
                laneLineWidth = readFunc(int,16),    
                reflectiveMarkings = readFunc(int,8), 
                pavementStripingPresent = readFunc(int,16))
            self.laneLineInfoArray.append(data)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *Lane Line情報: ', str(self.laneLineInfoCount))
        row += 1
        
        groupResult = []
        for i in range(self.laneLineInfoCount):
            [row, _, result] = rowGroupingPrint(
                'Lane Line情報(' + str(i+1) + ')', 
                None, 
                self.laneLineInfoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   PROFILETYPE_MPU_LINE_GEOMETRY       ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_LINE_GEOMETRY(ProfileType):
    
    @dataclass
    class GeometryPointData:
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *高さ[m]: ', str(self.height / 100.0), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class GeometryObjectData:
        laneLineID: int #64
        propertyFlag: int #32
        type: int #8
        geometryPointCount: int #16
        geometryPointArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *ライン型地物ID: ', str(hex(self.laneLineID)) + "\n",
                sheet.cellFormats('blue'), '   *3D地物属性オプションフラグ: ', str(self.propertyFlag) + "\n",
                sheet.cellFormats('blue'), '   *Type: ', str(self.type) + "\n",
                sheet.cellFormats('blue'), '   *形状要素点数: ', str(self.geometryPointCount), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            row += 1
            
            groupResult = []
            for i in range(self.geometryPointCount):
                [row, _, result] = rowGroupingPrint(
                    '形状要素点(' + str(i+1) + ')', 
                    None, 
                    self.geometryPointArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.geometyObjectCount = readFunc(int,32)
        self.geometyObjectArray = []
        for _ in range(self.geometyObjectCount):
            geometyObject = self.GeometryObjectData()
            geometyObject.laneLineID = readFunc(int,64,True)
            geometyObject.propertyFlag = readFunc(int,32)
            readFunc(int,8) #reserved
            geometyObject.type = readFunc(int,8)
            geometyObject.geometryPointCount = readFunc(int,16)
            geometyObject.geometryPointArray = []
            for _ in range(geometyObject.geometryPointCount):
                pointData = self.GeometryPointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True))
                geometyObject.geometryPointArray.append(pointData)
            self.geometyObjectArray.append(geometyObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *線形状情報数: ', str(self.geometyObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.geometyObjectCount):
            [row, _, result] = rowGroupingPrint(
                '線形状情報(' + str(i+1) + ')', 
                None, 
                self.geometyObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_LANE_LINE_GEOMETRY ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_LANE_LINE_GEOMETRY(ProfileType):
    
    @dataclass
    class GeometryPointData:
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *高さ[m]: ', str(self.height / 1000.0), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class GeometryObjectData:
        laneLineID: int #64
        geometryPointCount: int #16
        geometryPointArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *Lane Line ID: ', hex(self.laneLineID) + "\n",
                sheet.cellFormats('blue'), '   *形状要素点数: ', str(self.geometryPointCount), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            row += 1
            
            groupResult = []
            for i in range(self.geometryPointCount):
                [row, _, result] = rowGroupingPrint(
                    '形状要素点(' + str(i+1) + ')', 
                    None, 
                    self.geometryPointArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.geometyObjectCount = readFunc(int,32)
        self.geometyObjectArray = []
        for _ in range(self.geometyObjectCount):
            geometyObject = self.GeometryObjectData()
            geometyObject.laneLineID = readFunc(int,64)
            geometyObject.geometryPointCount = readFunc(int,16)
            geometyObject.geometryPointArray = []
            for _ in range(geometyObject.geometryPointCount):
                pointData = self.GeometryPointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True))
                geometyObject.geometryPointArray.append(pointData)
            self.geometyObjectArray.append(geometyObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *Lane Line形状情報数: ', str(self.geometyObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.geometyObjectCount):
            [row, _, result] = rowGroupingPrint(
                'Lane Line形状情報(' + str(i+1) + ')', 
                None, 
                self.geometyObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#----   DotLinePaintInfoProfile             ----#
#-----------------------------------------------#
class DotLinePaintInfoProfile(ProfileType):
    
    class GeometryObjectData:
        objectID: int #64
        infoCount: int #32
        objectIndex: List[int] #16
        dotPaintInfo: List[int] #8
        
        def printValue(self, sheet, row, col, _level):
            strList = []
            strList += [sheet.cellFormats('blue'), '   *ライン型地物ID: ', str(hex(self.objectID)) + "\n"]
            strList += [sheet.cellFormats('blue'), '   *破線ペイント情報数: ', str(self.infoCount) + "\n"]
            for i in range(self.infoCount):
                strList += [sheet.cellFormats('blue'), '   *破線ペイント情報[' + str(self.objectIndex[i]) + ']: ', str(self.dotPaintInfo[i]) + "\n"]
            strList += [sheet.cellFormats('wrap')]
            sheet.write_rich_string(row, col, *strList)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.geometyObjectCount = readFunc(int,32)
        self.geometyObjectArray = []
        for _ in range(self.geometyObjectCount):
            geometyObject = self.GeometryObjectData()
            geometyObject.objectID = readFunc(int,64,True)
            geometyObject.infoCount = readFunc(int,32)
            geometyObject.objectIndex = []
            geometyObject.dotPaintInfo = []
            for _ in range(geometyObject.infoCount):
                geometyObject.objectIndex.append(readFunc(int,16))
                geometyObject.dotPaintInfo.append(readFunc(int,8))
                readFunc(int,8) #reserved
            self.geometyObjectArray.append(geometyObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *破線ペイント情報数: ', str(self.geometyObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.geometyObjectCount):
            [row, _, result] = rowGroupingPrint(
                '破線ペイント情報(' + str(i+1) + ')', 
                None, 
                self.geometyObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   PROFILETYPE_MPU_US_ROAD_EDGE        ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_ROAD_EDGE(ProfileType):
    
    class ObjectData:
        targetRoadEdgeID: int #64
        
        def printValue(self, sheet, row, col, _level):
            strList = []
            strList += [sheet.cellFormats('blue'), '   *対象のRoad Edge ID: ', str(self.targetRoadEdgeID) + "\n"]
            strList += [sheet.cellFormats('wrap')]
            sheet.write_rich_string(row, col, *strList)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.objectCount = readFunc(int,32)
        self.objectArray = []
        for _ in range(self.objectCount):
            objectData = self.ObjectData()
            objectData.targetRoadEdgeID = readFunc(int,64)
            readFunc(int,32) #reserved
            self.objectArray.append(objectData)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *Road Edge情報数: ', str(self.objectCount))
        row += 1
        
        groupResult = []
        for i in range(self.objectCount):
            [row, _, result] = rowGroupingPrint(
                'Road Edge情報(' + str(i+1) + ')', 
                None, 
                self.objectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#---- PROFILETYPE_MPU_ZGM_TRAFFIC_LIGHT     ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_TRAFFIC_LIGHT(ProfileType):
    
    @dataclass
    class Info:
        ID: int #64
        accuracyInfo: int #64
        classifyInfo: int #32
        point1Latitude: int #32
        point1Longitude: int #32
        point1Height: int #32
        point2Latitude: int #32
        point2Longitude: int #32
        point2Height: int #32
        height: int #16
        depth: int #16
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *信号機ID: ', str(hex(self.ID)) + "\n",
            sheet.cellFormats('blue'), '   *MMS測位誤差[mm]: ', str(self.accuracyInfo & 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *レーザー測位誤差[mm]: ', str((self.accuracyInfo & 0xFFFFFFFF00000000) >> 32) + "\n",
            sheet.cellFormats('blue'), '   *信号機種別: ', str(self.classifyInfo) + "\n",
            sheet.cellFormats('blue'), '   *座業1_緯度[deg]: ', str(self.point1Latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業1_軽度[deg]: ', str(self.point1Longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業1_楕円体高[cm]: ', str(self.point1Height) + "\n",
            sheet.cellFormats('blue'), '   *座業2_緯度[deg]: ', str(self.point2Latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業2_軽度[deg]: ', str(self.point2Longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業2_楕円体高[cm]: ', str(self.point2Height) + "\n",
            sheet.cellFormats('blue'), '   *高さ(地物の縦幅)[cm]: ', str(self.height) + "\n",
            sheet.cellFormats('blue'), '   *奥行き[cm]: ', str(self.depth), sheet.cellFormats('wrap')])
            sheet.write(row, col+1, "...")
#             sheet.set_row(row, 13.5*6)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.signCount = readFunc(int,32)
        self.signDataArray = []
        for _ in range(self.signCount):
            signData = self.Info(
                ID = readFunc(int,64,True),
                accuracyInfo = readFunc(int,64,True),
                classifyInfo = readFunc(int,32),
                point1Latitude = readFunc(int,32,True),
                point1Longitude = readFunc(int,32,True),
                point1Height = readFunc(int,32,True),
                point2Latitude = readFunc(int,32,True),
                point2Longitude = readFunc(int,32,True),
                point2Height = readFunc(int,32,True),
                height = readFunc(int,16),
                depth = readFunc(int,16))
            self.signDataArray.append(signData)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *信号機情報数: ', str(self.signCount))
        row += 1
        
        groupResult = []
        for i in range(self.signCount):
            [row, _, result] = rowGroupingPrint(
                '信号機情報(' + str(i+1) + ')', 
                None, 
                self.signDataArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_ROAD_EDGE_GEOMETRY ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_ROAD_EDGE_GEOMETRY(ProfileType):
    
    @dataclass
    class GeometryPointData:
        latitude: int #32
        longitude: int #32
        height: int #32
    
    @dataclass
    class PropertyData:
        roadEdgeType: int #16
        
    @dataclass
    class WidthData:
        leftWidth: int #16
        rightWidth: int #16
        
    class ObjectData:
        roadEdgeID: int #64
        geometryPointCount: int #16
        geometryPointArray: List[int]
        propertyArray: List[int]
        widthArray: List[int]
        
        def printValue(self, sheet, row, col, _level):
            strList = []
            
            strList += [sheet.cellFormats('blue'), '   *Road Edge ID: ', str(self.roadEdgeID) + "\n"]
            strList += [sheet.cellFormats('blue'), '   *形状要素点数: ', str(self.geometryPointCount) + "\n"]
            for i in range(self.geometryPointCount):
                strList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 緯度[deg]: ', str(self.geometryPointArray[i].latitude * 360.0 / 0xFFFFFFFF) + "\n"]
                strList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 軽度[deg]: ', str(self.geometryPointArray[i].longitude * 360.0 / 0xFFFFFFFF) + "\n"]
                strList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 高さ[m]: ', str(self.geometryPointArray[i].height * 0.001) + "\n"]
                strList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') Road Edge Type: ', str(self.propertyArray[i].roadEdgeType) + "\n"]
                strList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 左側路肩幅員値[m]: ', str(self.widthArray[i].leftWidth * 0.01) + "\n"]
                strList += [sheet.cellFormats('blue'), '   *(' + str(i+1) + ') 右側路肩幅員値[m]: ', str(self.widthArray[i].rightWidth * 0.01) + "\n"]          

            strList += [sheet.cellFormats('wrap')]
            sheet.write_rich_string(row, col, *strList)
            sheet.write(row, col+1, "...")
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.objectCount = readFunc(int,32)
        self.objectArray = []
        for _ in range(self.objectCount):
            objectData = self.ObjectData()
            objectData.roadEdgeID = readFunc(int,64)
            objectData.geometryPointCount = readFunc(int,16)
            
#             objectData.geometryPointArray = []
#             for _ in range(objectData.geometryPointCount):
#                 objectData.geometryPointArray.append(self.GeometryPointData(
#                     latitude = readFunc(int,32,True),
#                     longitude = readFunc(int,32,True),
#                     height = readFunc(int,32,True)))
#             objectData.propertyArray = []
#             for _ in range(objectData.geometryPointCount):
#                 objectData.propertyArray.append(self.PropertyData(
#                     roadEdgeType = readFunc(int,16)))
#             objectData.widthArray = []
#             for _ in range(objectData.geometryPointCount):
#                 objectData.widthArray.append(self.WidthData(
#                     leftWidth = readFunc(int,16),
#                     rightWidth = readFunc(int,16)))

            objectData.geometryPointArray = []
            objectData.propertyArray = []
            objectData.widthArray = []
            for _ in range(objectData.geometryPointCount):
                objectData.geometryPointArray.append(self.GeometryPointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True)))
                objectData.propertyArray.append(self.PropertyData(
                    roadEdgeType = readFunc(int,16)))
                objectData.widthArray.append(self.WidthData(
                    leftWidth = readFunc(int,16),
                    rightWidth = readFunc(int,16)))

            self.objectArray.append(objectData)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *Road Edge形状情報の配列数: ', str(self.objectCount))
        row += 1
        
        groupResult = []
        for i in range(self.objectCount):
            [row, _, result] = rowGroupingPrint(
                'Road Edge形状情報(' + str(i+1) + ')', 
                None, 
                self.objectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#---- PROFILETYPE_MPU_ZGM_TRAFFIC_PAINT     ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_TRAFFIC_PAINT(ProfileType):
    
    @dataclass
    class PointData:
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *楕円体高[cm]: ', str(self.height), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class Info:
        ID: int #64
        classify: int #32
        accuracyInfo: int #64
        pointCount: int #32
        pointArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *道路標示ID: ', str(hex(self.ID)) + "\n",
                sheet.cellFormats('blue'), '   *交通ペイント種別: ', str(self.classify) + "\n",
                sheet.cellFormats('blue'), '   *MMS測位誤差[mm]: ', str(self.accuracyInfo & 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *レーザー測位誤差[mm]: ', str((self.accuracyInfo & 0xFFFFFFFF00000000) >> 32) + "\n",
                sheet.cellFormats('blue'), '   *座標点数: ', str(self.pointCount), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            row += 1
            
            groupResult = []
            for i in range(self.pointCount):
                [row, _, result] = rowGroupingPrint(
                    '座標点(' + str(i+1) + ')', 
                    None, 
                    self.pointArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.dataCount = readFunc(int,32)
        self.dataArray = []
        for _ in range(self.dataCount):
            data = self.Info()
            data.ID = readFunc(int,64,True)
            data.classify = readFunc(int,32)
            data.accuracyInfo = readFunc(int,64,True)
            data.pointCount = readFunc(int,32)
            data.pointArray = []
            for _ in range(data.pointCount):
                pointData = self.PointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True))
                data.pointArray.append(pointData)
            self.dataArray.append(data)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *道路標示物情報数: ', str(self.dataCount))
        row += 1
        
        groupResult = []
        for i in range(self.dataCount):
            [row, _, result] = rowGroupingPrint(
                '道路標示物情報(' + str(i+1) + ')', 
                None, 
                self.dataArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_REGULATORY_TRRAFIC_DEVICE ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_REGULATORY_TRRAFIC_DEVICE(ProfileType):
        
    class SignalObjectData:
        laneID: int #64
        signalObjectID: int #64
        regulatoryTrafficDevicesType: int #16
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *レーンID: ', str(self.laneID) + "\n",
                sheet.cellFormats('blue'), '   *信号機ID: ', str(self.signalObjectID) + "\n",
                sheet.cellFormats('blue'), '   *Regulatory Traffic Devices Type: ', str(self.regulatoryTrafficDevicesType) + "\n",
                sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *楕円体高[m]: ', str(self.height * 0.001), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.signalObjectCount = readFunc(int,32)
        self.signalObjectArray = []
        for _ in range(self.signalObjectCount):
            signalObject = self.SignalObjectData()
            signalObject.laneID = readFunc(int,64)
            signalObject.signalObjectID = readFunc(int,64)
            signalObject.regulatoryTrafficDevicesType = readFunc(int,16)
            signalObject.latitude = readFunc(int,32,True)
            signalObject.longitude = readFunc(int,32,True)
            signalObject.height = readFunc(int,32,True)
            self.signalObjectArray.append(signalObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *信号機情報の配列数: ', str(self.signalObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.signalObjectCount):
            [row, _, result] = rowGroupingPrint(
                '信号機情報(' + str(i+1) + ')', 
                None, 
                self.signalObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_PAVEMENT_MARKING   ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_PAVEMENT_MARKING(ProfileType):
        
    class MakerObjectData:
        laneID: int #64
        makerID: int #64
        markingType: int #16
        latitude: int #32
        longitude: int #32
        height: int #32
        length: int #16
        width: int #16
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *レーンID: ', str(self.laneID) + "\n",
                sheet.cellFormats('blue'), '   *道路標示ID: ', str(self.makerID) + "\n",
                sheet.cellFormats('blue'), '   *Marking Type: ', str(self.markingType) + "\n",
                sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *楕円体高[m]: ', str(self.height * 0.001) + "\n",
                sheet.cellFormats('blue'), '   *length[m]: ', str(self.length * 0.01) + "\n",
                sheet.cellFormats('blue'), '   *width[m]: ', str(self.width * 0.01), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.makerObjectCount = readFunc(int,32)
        self.makerObjectArray = []
        for _ in range(self.makerObjectCount):
            makerObject = self.MakerObjectData()
            makerObject.laneID = readFunc(int,64)
            makerObject.makerID = readFunc(int,64)
            makerObject.markingType = readFunc(int,16)
            makerObject.latitude = readFunc(int,32,True)
            makerObject.longitude = readFunc(int,32,True)
            makerObject.height = readFunc(int,32,True)
            makerObject.length = readFunc(int,16)
            makerObject.width = readFunc(int,16)
            self.makerObjectArray.append(makerObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *道路標示物情報の配列数: ', str(self.makerObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.makerObjectCount):
            [row, _, result] = rowGroupingPrint(
                '道路標示物情報(' + str(i+1) + ')', 
                None, 
                self.makerObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_US_SIGN               ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_SIGN(ProfileType):
        
    class MakerObjectData:
        makerID: int #64
        shape: int #16
        type: int #16
        is_digital: int #8
        latitude: int #32
        longitude: int #32
        eclipseHeight: int #32
        signFaceAzimuth: int #16 
        signFaceElevation: int #16    
        height: int #16
        width: int #16
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *標識情報ID: ', str(self.makerID) + "\n",
                sheet.cellFormats('blue'), '   *shape: ', str(self.shape) + "\n",
                sheet.cellFormats('blue'), '   *type: ', str(self.type) + "\n",
                sheet.cellFormats('blue'), '   *is_digital: ', str(self.is_digital) + "\n",
                sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *楕円体高[m]: ', str(self.eclipseHeight * 0.001) + "\n",
                sheet.cellFormats('blue'), '   *Sign Face Azimuth[deg]: ', str(self.signFaceAzimuth * 0.1) + "\n",
                sheet.cellFormats('blue'), '   *Sign Face Elevation[deg]: ', str(self.signFaceElevation * 0.1) + "\n",
                sheet.cellFormats('blue'), '   *height[m]: ', str(self.height * 0.01) + "\n",
                sheet.cellFormats('blue'), '   *width[m]: ', str(self.width * 0.01), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.makerObjectCount = readFunc(int,32)
        self.makerObjectArray = []
        for _ in range(self.makerObjectCount):
            makerObject = self.MakerObjectData()
            makerObject.makerID = readFunc(int,64)
            makerObject.shape = readFunc(int,16)
            makerObject.type = readFunc(int,16)
            makerObject.is_digital = readFunc(int,8)
            makerObject.latitude = readFunc(int,32,True)
            makerObject.longitude = readFunc(int,32,True)
            makerObject.eclipseHeight = readFunc(int,32,True)
            makerObject.signFaceAzimuth = readFunc(int,16)
            makerObject.signFaceElevation = readFunc(int,16,True)
            makerObject.height = readFunc(int,16)
            makerObject.width = readFunc(int,16)
            self.makerObjectArray.append(makerObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *標識情報の配列数: ', str(self.makerObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.makerObjectCount):
            [row, _, result] = rowGroupingPrint(
                '標識情報(' + str(i+1) + ')', 
                None, 
                self.makerObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#---- PROFILETYPE_MPU_ZGM_SIGN_INFO         ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_SIGN_INFO(ProfileType):
    ClassifyInfoDic = {
        0xC5000000:'初期値(未調査)　※未使用',
        0xC5010000:'初期値(未調査)',
        0xC5010100:'地名・施設・道路名・路線番号に関する表記',
        0xC5010200:'SA・PA・道の駅・駐車場に関する表記',
        0xC5010300:'歩行者向け案内表記　※未使用',
        0xC5010400:'料金徴収所',
        0xC5010500:'非常電話',
        0xC5010600:'待避所',
        0xC5010700:'非常駐車帯',
        0xC5010800:'車線区分の変化による車線増減の終始を示す標識',
        0xC5010900:'総重量限度緩和指定道路',
        0xC5010A00:'高さ限度緩和指定道路',
        0xC5010B00:'まわり道（Ａ）',
        0xC5010C00:'まわり道（Ｂ）',
        0xC5010D00:'歩行者向け案内標識',
        0xC501FF00:'不明　※未使用',
        0xC5020000:'初期値(未調査)',
        0xC5020100:'+形道路交差点あり',
        0xC5020200:'ト形道路交差点あり',
        0xC5020300:'T形道路交差点あり',
        0xC5020400:'Y形道路交差点あり',
        0xC5020500:'ロータリーあり',
        0xC5020600:'右（または左）方屈曲あり',
        0xC5020700:'右（または左）方屈折あり',
        0xC5020800:'右（または左）方背向屈曲あり',
        0xC5020900:'右（または左）方背向屈折あり',
        0xC5020A00:'右（または左）つづら折りあり',
        0xC5020B00:'踏切あり',
        0xC5020C00:'学校、幼稚園、保育所等あり',
        0xC5020D00:'信号機あり',
        0xC5020E00:'すべりやすい',
        0xC5020F00:'落石のおそれあり',
        0xC5021000:'路面凹凸あり',
        0xC5021100:'合流交通あり',
        0xC5021200:'車線数減少',
        0xC5021300:'幅員減少',
        0xC5021400:'二方向交通',
        0xC5021500:'上り急勾配あり',
        0xC5021600:'下り急勾配あり',
        0xC5021700:'横風注意',
        0xC5021800:'動物が飛び出すおそれあり',
        0xC5021900:'その他の危険',
        0xC502FF00:'不明　※未使用',
        0xC5030000:'初期値(未調査)',
        0xC5030100:'通行止め',
        0xC5030200:'車両通行止め',
        0xC5030300:'車両進入禁止',
        0xC5030400:'二輪の自動車以外の自動車通行止め',
        0xC5030500:'大型貨物自動車等通行止め （特定の）最大積載量以上の貨物自動車等通行止め',
        0xC5030600:'大型乗用自動車等通行止め',
        0xC5030700:'二輪の自動車・原動機付自転車通行止め',
        0xC5030800:'自転車以外の軽車両通行止め',
        0xC5030900:'自転車通行止め',
        0xC5030A00:'車両(組合せ)通行止め',
        0xC5030B00:'大型自動二輪車及び普通自動二輪車二人乗り通行禁止',
        0xC5030C00:'指定方向外進行禁止',
        0xC5030D00:'車両横断禁止',
        0xC5030E00:'転回禁止',
        0xC5030F00:'追越のための右側部分はみ出し通行禁止　追越し禁止',
        0xC5031000:'駐停車禁止',
        0xC5031100:'駐車禁止 駐車余地',
        0xC5031200:'時間制限駐車区間',
        0xC5031300:'危険物積載車両通行止め',
        0xC5031400:'重量制限',
        0xC5031500:'高さ制限',
        0xC5031600:'最大幅',
        0xC5031700:'最高速度／特定の種類の車両の最高速度',
        0xC5031800:'最低速度',
        0xC5031900:'自動車専用',
        0xC5031A00:'自転車専用',
        0xC5031B00:'自転車及び歩行者専用',
        0xC5031C00:'歩行者専用',
        0xC5031D00:'一方通行',
        0xC5031E00:'自転車一方通行',
        0xC5031F00:'車両通行区分',
        0xC5032000:'特定の種類の車両の通行区分',
        0xC5032100:'牽引自動車の高速自動車国道通行区分',
        0xC5032200:'専用通行帯',
        0xC5032300:'普通自転車専用通行帯',
        0xC5032400:'路線バス等優先通行帯',
        0xC5032500:'牽引自動車の自動車専用道路第一通行帯通行指定区間',
        0xC5032600:'進行方向別通行区分',
        0xC5032700:'原動機つき自転車の右折方法(2段階)',
        0xC5032800:'原動機つき自転車の右折方法(小回り)',
        0xC5032900:'平行駐車',
        0xC5032A00:'直角駐車',
        0xC5032B00:'斜め駐車',
        0xC5032C00:'警笛鳴らせ 警笛区間',
        0xC5032D00:'徐行 前方優先道路',
        0xC5032E00:'一時停止',
        0xC5032F00:'歩行者通行止め',
        0xC5033000:'歩行者横断禁止',
        0xC503FF00:'不明　※未使用',
        0xC5040000:'初期値(未調査)',
        0xC5040100:'並進可',
        0xC5040200:'軌道敷内通行可',
        0xC5040300:'駐車可　※未使用',
        0xC5040400:'停車可',
        0xC5040500:'優先道路',
        0xC5040600:'中央線',
        0xC5040700:'停止線',
        0xC5040800:'横断歩道',
        0xC5040900:'自転車横断帯',
        0xC5040A00:'横断歩道・自転車横断帯',
        0xC5040B00:'安全地帯',
        0xC5040C00:'規制予告',
        0xC504FF00:'不明　※未使用',
        0xC5050000:'初期値(未調査)　※未使用',
        0xC5050100:'ETCレーン標示',
        0xC5050200:'一般／ETC区分',
        0xC5050300:'車線区分',
        0xC5050400:'左折可標示',
        0xC5050500:'ここから走行車線',
        0xC5FF0000:'初期値(未調査)　※未使用'}
    
    @dataclass
    class SignInfo:
        ID: int #64
        accuracyInfo: int #64
        classifyInfo: int #32
        propertyFlag: int #8
        addtionalPropertyFlag: int #16
        reserved1: int #8
        point1Latitude: int #32
        point1Longitude: int #32
        point1Height: int #32
        point2Latitude: int #32
        point2Longitude: int #32
        point2Height: int #32
        height: int #16
        heightFromGround: int #16
        maximumVelocity: int #32
        subClassify: int #16
        reserved2: int #16
        
        def printValue(self, sheet, row, col, _level):       
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *標識情報ID: ', str(hex(self.ID)) + "\n",
            sheet.cellFormats('blue'), '   *MMS測位誤差[mm]: ', str(self.accuracyInfo & 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *レーザー測位誤差[mm]: ', str((self.accuracyInfo & 0xFFFFFFFF00000000) >> 32) + "\n",
            sheet.cellFormats('blue'), '   *標識情報種別: ', str(hex(self.classifyInfo)) + "\n",
            sheet.cellFormats('blue'), '   *標識付加属性フラグ: ', str(self.propertyFlag) + "\n",
            sheet.cellFormats('blue'), '   *3D地物付加属性フラグ: ', str(hex(self.addtionalPropertyFlag)) + "\n",
            sheet.cellFormats('blue'), '   *座業1_緯度[deg]: ', str(self.point1Latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業1_軽度[deg]: ', str(self.point1Longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業1_楕円体高[cm]: ', str(self.point1Height) + "\n",
            sheet.cellFormats('blue'), '   *座業2_緯度[deg]: ', str(self.point2Latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業2_軽度[deg]: ', str(self.point2Longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *座業2_楕円体高[cm]: ', str(self.point2Height) + "\n",
            sheet.cellFormats('blue'), '   *高さ(地物の縦幅)[cm]: ', str(self.height) + "\n",
            sheet.cellFormats('blue'), '   *地上高さ[cm]: ', str(self.heightFromGround) + "\n",
            sheet.cellFormats('blue'), '   *最高速度値[km/h]: ', str(self.maximumVelocity) + "\n",
            sheet.cellFormats('blue'), '   *補助標識分類: ', str(self.subClassify), sheet.cellFormats('wrap')])
            sheet.write(row, col+1, "...")
#             sheet.set_row(row, 13.5*6)
            return [row+1, col, []]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.signCount = readFunc(int,32)
        self.signDataArray = []
        for _ in range(self.signCount):
            signData = self.SignInfo(
                ID = readFunc(int,64,True),
                accuracyInfo = readFunc(int,64,True),
                classifyInfo = readFunc(int,32),
                propertyFlag = readFunc(int,8),
                addtionalPropertyFlag = readFunc(int,16),
                reserved1 = readFunc(int,8),
                point1Latitude = readFunc(int,32,True),
                point1Longitude = readFunc(int,32,True),
                point1Height = readFunc(int,32,True),
                point2Latitude = readFunc(int,32,True),
                point2Longitude = readFunc(int,32,True),
                point2Height = readFunc(int,32,True),
                height = readFunc(int,16,True),
                heightFromGround = readFunc(int,16,True),
                maximumVelocity = readFunc(int,32),
                subClassify = readFunc(int,16),
                reserved2 = readFunc(int,16))
            self.signDataArray.append(signData)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *標識情報数: ', str(self.signCount))
        row += 1
        
        groupResult = []
        for i in range(self.signCount):
            [row, _, result] = rowGroupingPrint(
                '標識情報(' + str(i+1) + ')', 
                None, 
                self.signDataArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#---- PROFILETYPE_MPU_ZGM_STOP_LINE         ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_STOP_LINE(ProfileType):
    
    @dataclass
    class PointData:
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *楕円体高[cm]: ', str(self.height), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class Info:
        ID: int #64
        accuracyInfo: int #64
        pointCount: int #32
        pointArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *停止線ID: ', str(hex(self.ID)) + "\n",
                sheet.cellFormats('blue'), '   *MMS測位誤差[mm]: ', str(self.accuracyInfo & 0xFFFFFFFF) + "\n",
                sheet.cellFormats('blue'), '   *レーザー測位誤差[mm]: ', str((self.accuracyInfo & 0xFFFFFFFF00000000) >> 32) + "\n",
                sheet.cellFormats('blue'), '   *座標点数: ', str(self.pointCount), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            row += 1
            
            groupResult = []
            for i in range(self.pointCount):
                [row, _, result] = rowGroupingPrint(
                    '座標点(' + str(i+1) + ')', 
                    None, 
                    self.pointArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.dataCount = readFunc(int,32)
        self.dataArray = []
        for _ in range(self.dataCount):
            data = self.Info()
            data.ID = readFunc(int,64,True)
            data.accuracyInfo = readFunc(int,64,True)
            data.pointCount = readFunc(int,32)
            data.pointArray = []
            for _ in range(data.pointCount):
                pointData = self.PointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True))
                data.pointArray.append(pointData)
            self.dataArray.append(data)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *停止線情報数: ', str(self.dataCount))
        row += 1
        
        groupResult = []
        for i in range(self.dataCount):
            [row, _, result] = rowGroupingPrint(
                '道路標示物情報(' + str(i+1) + ')', 
                None, 
                self.dataArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#----   PROFILETYPE_MPU_ZGM_CURVATURE       ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_CURVATURE(ProfileType):
    
    @dataclass
    class Curvature:
        index: int #16
        degree: int #16
        curvature: int #32
        accuracyInfo: int #16
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *形状インデックス: ', str(self.index) + "\n",
            sheet.cellFormats('blue'), '   *方位角[deg]: ', str(self.degree * 0.1) + "\n",
            sheet.cellFormats('blue'), '   *曲率値[rad/m]: ', str(self.curvature / 100000000.0) + "\n",
            sheet.cellFormats('blue'), '   *精度情報: ', str(self.accuracyInfo), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    class Lane:
        laneID: int #64
        dataCount: int #32
        dataArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_column(row, col, [
                'ID: ' + str(self.laneID),
                '地点曲率データ数: ' + str(self.dataCount)])
            row += 2
            
            groupResult = []
            for i in range(self.dataCount):
                [row, _, result] = rowGroupingPrint(
                    '曲率(' + str(i+1) + ')', 
                    None, 
                    self.dataArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.infoCount = readFunc(int,32)
        self.infoArray = []
        for _ in range(self.infoCount):
            info = self.Lane()
            info.laneID = readFunc(int,64)
            info.dataCount = readFunc(int,32)
            info.dataArray = []
            for _ in range(info.dataCount):
                data = self.Curvature(
                    index = readFunc(int,16,True),
                    degree = readFunc(int,16,True),
                    curvature = readFunc(int,32,True),
                    accuracyInfo = readFunc(int,16))
                readFunc(int,16) #reserved
                info.dataArray.append(data)
            self.infoArray.append(info)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *曲率情報のレーン数: ', str(self.infoCount))
        row += 1
        
        groupResult = []
        for i in range(self.infoCount):
            [row, _, result] = rowGroupingPrint(
                'レーンごとの曲率情報(' + str(i+1) + ')', 
                None, 
                self.infoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   PROFILETYPE_MPU_US_CURVATURE        ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_CURVATURE(ProfileType):
    
    @dataclass
    class Curvature:
        index: int #16
        degree: int #16
        curvature: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *形状インデックス: ', str(self.index) + "\n",
            sheet.cellFormats('blue'), '   *方位角[deg]: ', str(self.degree * 0.01) + "\n",
            sheet.cellFormats('blue'), '   *曲率値[1/m]: ', str(self.curvature / 10000), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    class Lane:
        laneID: int #64
        dataCount: int #32
        dataArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_column(row, col, [
                'ID: ' + str(self.laneID),
                '地点曲率データ数: ' + str(self.dataCount)])
            row += 2
            
            groupResult = []
            for i in range(self.dataCount):
                [row, _, result] = rowGroupingPrint(
                    '曲率(' + str(i+1) + ')', 
                    None, 
                    self.dataArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.infoCount = readFunc(int,32)
        self.infoArray = []
        for _ in range(self.infoCount):
            info = self.Lane()
            info.laneID = readFunc(int,64)
            info.dataCount = readFunc(int,32)
            info.dataArray = []
            for _ in range(info.dataCount):
                data = self.Curvature(
                    index = readFunc(int,16),
                    degree = readFunc(int,16),
                    curvature = readFunc(int,16,True))
                info.dataArray.append(data)
            self.infoArray.append(info)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *曲率情報のレーン数: ', str(self.infoCount))
        row += 1
        
        groupResult = []
        for i in range(self.infoCount):
            [row, _, result] = rowGroupingPrint(
                'レーンごとの曲率情報(' + str(i+1) + ')', 
                None, 
                self.infoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#----   PROFILETYPE_MPU_ZGM_SLOPE           ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_SLOPE(ProfileType):
    
    @dataclass
    class Slope:
        index: int #16
        alongSlope: int #16
        crossSlope: int #16
        accuracyInfo: int #16

        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *形状インデックス: ', str(self.index) + "\n",
            sheet.cellFormats('blue'), '   *縦断勾配値[%]: ', str(self.alongSlope * 0.01) + "\n",
            sheet.cellFormats('blue'), '   *横断勾配値[%]: ', str(self.crossSlope * 0.01) + "\n",
            sheet.cellFormats('blue'), '   *精度情報: ', str(self.accuracyInfo), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    class Lane:
        laneID: int #64
        dataCount: int #32
        dataArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_column(row, col, [
                'ID: ' + str(self.laneID),
                '地点勾配データ数: ' + str(self.dataCount)])
            row += 2
            
            groupResult = []
            for i in range(self.dataCount):
                [row, _, result] = rowGroupingPrint(
                    '勾配(' + str(i+1) + ')', 
                    None, 
                    self.dataArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.infoCount = readFunc(int,32)
        self.infoArray = []
        for _ in range(self.infoCount):
            info = self.Lane()
            info.laneID = readFunc(int,64)
            info.dataCount = readFunc(int,32)
            info.dataArray = []
            for _ in range(info.dataCount):
                data = self.Slope(
                    index = readFunc(int,16,True),
                    alongSlope = readFunc(int,16,True),
                    crossSlope = readFunc(int,16,True),
                    accuracyInfo = readFunc(int,16))
                info.dataArray.append(data)
            self.infoArray.append(info)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *勾配情報のレーン数: ', str(self.infoCount))
        row += 1
        
        groupResult = []
        for i in range(self.infoCount):
            [row, _, result] = rowGroupingPrint(
                'レーンごとの勾配情報(' + str(i+1) + ')', 
                None, 
                self.infoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   PROFILETYPE_MPU_US_SLOPE            ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_SLOPE(ProfileType):
    
    @dataclass
    class Slope:
        index: int #16
        alongSlope: int #16
        crossSlope: int #16

        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *形状インデックス: ', str(self.index) + "\n",
            sheet.cellFormats('blue'), '   *縦断勾配値[deg]: ', str(self.alongSlope * 0.01) + "\n",
            sheet.cellFormats('blue'), '   *横断勾配値[deg]: ', str(self.crossSlope * 0.01), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*4)
            return [row+1, col, []]
        
    class Lane:
        laneID: int #64
        dataCount: int #32
        dataArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_column(row, col, [
                'ID: ' + str(self.laneID),
                '地点勾配データ数: ' + str(self.dataCount)])
            row += 2
            
            groupResult = []
            for i in range(self.dataCount):
                [row, _, result] = rowGroupingPrint(
                    '勾配(' + str(i+1) + ')', 
                    None, 
                    self.dataArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.infoCount = readFunc(int,32)
        self.infoArray = []
        for _ in range(self.infoCount):
            info = self.Lane()
            info.laneID = readFunc(int,64)
            info.dataCount = readFunc(int,32)
            info.dataArray = []
            for _ in range(info.dataCount):
                data = self.Slope(
                    index = readFunc(int,16),
                    alongSlope = readFunc(int,16,True),
                    crossSlope = readFunc(int,16,True))
                info.dataArray.append(data)
            self.infoArray.append(info)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *勾配情報のレーン数: ', str(self.infoCount))
        row += 1
        
        groupResult = []
        for i in range(self.infoCount):
            [row, _, result] = rowGroupingPrint(
                'レーンごとの勾配情報(' + str(i+1) + ')', 
                None, 
                self.infoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#----   PROFILETYPE_MPU_ZGM_SHOULDER_WIDTH  ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_ZGM_SHOULDER_WIDTH(ProfileType):
    
    @dataclass
    class Shoulder:
        index: int #16
        leftSideWidth: int #16
        rightSideWidth: int #16

        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *形状要素インデックス: ', str(self.index) + "\n",
            sheet.cellFormats('blue'), '   *左側路肩幅員値[cm]: ', str(self.leftSideWidth) + "\n",
            sheet.cellFormats('blue'), '   *右側路肩幅員値[cm]: ', str(self.rightSideWidth), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class Lane:
        laneID: int #64
        dataCount: int #32
        dataArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_column(row, col, [
                'ID: ' + str(self.laneID),
                '路肩幅員値数: ' + str(self.dataCount)])
            row += 2
            
            groupResult = []
            for i in range(self.dataCount):
                [row, _, result] = rowGroupingPrint(
                    '路肩幅員値(' + str(i+1) + ')', 
                    None, 
                    self.dataArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.infoCount = readFunc(int,32)
        self.infoArray = []
        for _ in range(self.infoCount):
            info = self.Lane()
            info.laneID = readFunc(int,64)
            info.dataCount = readFunc(int,32)
            info.dataArray = []
            for _ in range(info.dataCount):
                data = self.Shoulder(
                    index = readFunc(int,16,True),
                    leftSideWidth = readFunc(int,16,True),
                    rightSideWidth = readFunc(int,16,True))
                readFunc(int,16) #reserved
                info.dataArray.append(data)
            self.infoArray.append(info)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *路肩幅員情報数: ', str(self.infoCount))
        row += 1
        
        groupResult = []
        for i in range(self.infoCount):
            [row, _, result] = rowGroupingPrint(
                'レーンごとの路肩幅員情報(' + str(i+1) + ')', 
                None, 
                self.infoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   PROFILETYPE_MPU_US_LANE_WIDTH       ----#
#-----------------------------------------------#
class PROFILETYPE_MPU_US_LANE_WIDTH(ProfileType):
    
    @dataclass
    class LaneWidth:
        index: int #16
        width: int #16

        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *形状要素インデックス: ', str(self.index) + "\n",
            sheet.cellFormats('blue'), '   *幅員値[m]: ', str(self.width * 0.01), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class Lane:
        laneID: int #64
        dataCount: int #32
        dataArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_column(row, col, [
                'ID: ' + str(self.laneID),
                'レーン幅員値の配列数: ' + str(self.dataCount)])
            row += 2
            
            groupResult = []
            for i in range(self.dataCount):
                [row, _, result] = rowGroupingPrint(
                    'レーン幅員値(' + str(i+1) + ')', 
                    None, 
                    self.dataArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.infoCount = readFunc(int,32)
        self.infoArray = []
        for _ in range(self.infoCount):
            info = self.Lane()
            info.laneID = readFunc(int,64)
            info.dataCount = readFunc(int,32)
            info.dataArray = []
            for _ in range(info.dataCount):
                data = self.LaneWidth(
                    index = readFunc(int,16),
                    width = readFunc(int,16))
                info.dataArray.append(data)
            self.infoArray.append(info)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *幅員情報の配列数: ', str(self.infoCount))
        row += 1
        
        groupResult = []
        for i in range(self.infoCount):
            [row, _, result] = rowGroupingPrint(
                'レーンごとの幅員情報(' + str(i+1) + ')', 
                None, 
                self.infoArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]
    
#-----------------------------------------------#
#----   LanesGeometryProfile                ----#
#-----------------------------------------------#
class LanesGeometryProfile(ProfileType):
    
    @dataclass
    class GeometryPointData:
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *高さ[cm]: ', str(self.height), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class GeometryObjectData:
        laneID: int #64
        type: int #8
        geometryPointCount: int #16
        geometryPointArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *Lane ID: ', str(self.laneID) + "\n",
                sheet.cellFormats('blue'), '   *Type: ', str(self.type) + "\n",
                sheet.cellFormats('blue'), '   *形状要素点数: ', str(self.geometryPointCount), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            row += 1
            
            groupResult = []
            for i in range(self.geometryPointCount):
                [row, _, result] = rowGroupingPrint(
                    '形状要素点(' + str(i+1) + ')', 
                    None, 
                    self.geometryPointArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.geometyObjectCount = readFunc(int,32)
        self.geometyObjectArray = []
        for _ in range(self.geometyObjectCount):
            geometyObject = self.GeometryObjectData()
            geometyObject.laneID = readFunc(int,64,True)
            geometyObject.type = readFunc(int,8)
            readFunc(int,8) #reserved
            geometyObject.geometryPointCount = readFunc(int,16)
            geometyObject.geometryPointArray = []
            for _ in range(geometyObject.geometryPointCount):
                pointData = self.GeometryPointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True))
                geometyObject.geometryPointArray.append(pointData)
            self.geometyObjectArray.append(geometyObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *レーン形状情報数: ', str(self.geometyObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.geometyObjectCount):
            [row, _, result] = rowGroupingPrint(
                'レーン形状情報(' + str(i+1) + ')', 
                None, 
                self.geometyObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   LanesGeometryProfile(US)            ----#
#-----------------------------------------------#
class LanesGeometryProfile_US(ProfileType):
    
    @dataclass
    class GeometryPointData:
        latitude: int #32
        longitude: int #32
        height: int #32
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *軽度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *高さ[m]: ', str(self.height / 1000), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    @dataclass
    class GeometryTypeData:
        crossingType: int #16
        RegulatoryTrafficDevice: int #16
        
        def printValue(self, sheet, row, col, _level):
            sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *crossing type: ', str(self.crossingType) + "\n",
            sheet.cellFormats('blue'), '   *RegulatoryTrafficDevice: ', str(self.RegulatoryTrafficDevice), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            return [row+1, col, []]
        
    class GeometryObjectData:
        laneID: int #64
        geometryPointCount: int #16
        geometryPointArray: List[int]
        geometryTypeArray: List[int]
        
        def printValue(self, sheet, row, col, level):
            sheet.write_rich_string(row, col, *[
                sheet.cellFormats('blue'), '   *Lane ID: ', str(self.laneID) + "\n",
                sheet.cellFormats('blue'), '   *形状要素点数: ', str(self.geometryPointCount), sheet.cellFormats('wrap')])
#             sheet.set_row(row, 13.5*3)
            row += 1
            
            groupResult = []
            for i in range(self.geometryPointCount):
                [row, _, result] = rowGroupingPrint(
                    '形状要素点(' + str(i+1) + ')', 
                    None, 
                    self.geometryPointArray[i].printValue, 
                    sheet, 
                    row, 
                    col, 
                    level)
                groupResult += result
         
            return [row, col, groupResult]
        
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.geometyObjectCount = readFunc(int,32)
        self.geometyObjectArray = []
        for _ in range(self.geometyObjectCount):
            geometyObject = self.GeometryObjectData()
            geometyObject.laneID = readFunc(int,64)
            geometyObject.geometryPointCount = readFunc(int,16)
            
#             geometyObject.geometryPointArray = []
#             for _ in range(geometyObject.geometryPointCount):
#                 pointData = self.GeometryPointData(
#                     latitude = readFunc(int,32,True),
#                     longitude = readFunc(int,32,True),
#                     height = readFunc(int,32,True))
#                 geometyObject.geometryPointArray.append(pointData)
#             geometyObject.geometryTypeArray = []
#             for _ in range(geometyObject.geometryPointCount):
#                 typeData = self.GeometryTypeData(
#                     crossingType = readFunc(int,16),
#                     RegulatoryTrafficDevice = readFunc(int,16))
#                 geometyObject.geometryTypeArray.append(typeData)

            geometyObject.geometryPointArray = []
            geometyObject.geometryTypeArray = []
            for _ in range(geometyObject.geometryPointCount):
                pointData = self.GeometryPointData(
                    latitude = readFunc(int,32,True),
                    longitude = readFunc(int,32,True),
                    height = readFunc(int,32,True))
                geometyObject.geometryPointArray.append(pointData)
                typeData = self.GeometryTypeData(
                    crossingType = readFunc(int,16),
                    RegulatoryTrafficDevice = readFunc(int,16))
                geometyObject.geometryTypeArray.append(typeData)
                
            self.geometyObjectArray.append(geometyObject)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, level):
        sheet.write_rich_string(row, col, sheet.cellFormats('blue'), '   *レーン形状情報数: ', str(self.geometyObjectCount))
        row += 1
        
        groupResult = []
        for i in range(self.geometyObjectCount):
            [row, _, result] = rowGroupingPrint(
                'レーン形状情報(' + str(i+1) + ')', 
                None, 
                self.geometyObjectArray[i].printValue, 
                sheet, 
                row, 
                col, 
                level)
            groupResult += result
     
        return [row, col, groupResult]

#-----------------------------------------------#
#----   PROFILE_MPU_MAP_ID_LIST             ----#
#-----------------------------------------------#
class PROFILE_MPU_MAP_ID_LIST(ProfileType):
    classifyDic = {0x00:'無効値', 0x01:'周辺情報　(MPU経路)', 0x02:'周辺情報  (ADECU経路)', 0x03:'周辺情報（SDMAP/MPU経路）', 0x04:'周辺情報（SDMAP/ADECU経路）'}
    
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.laneListID = readFunc(int,16)
        self.classify = readFunc(int,8)
        readFunc(int,8) #reserved
        self.numberOfArray = readFunc(int,32)
        self.laneIDArray = []
        for _ in range(self.numberOfArray):
            self.laneIDArray.append(readFunc(int,64))
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, _level):
        sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *レーンリストID: ', str(self.laneListID) + "\n",
            sheet.cellFormats('blue'), '   *情報種別: ', self.classifyDic.get(self.classify, '[error]') + "\n",
            sheet.cellFormats('blue'), '   *レーンID数: ', str(self.numberOfArray), sheet.cellFormats('wrap')])
#         sheet.set_row(row, 13.5*3)
        row += 1
        
        if self.numberOfArray > 0:
            strList = []
            for i in range(self.numberOfArray):
                strList += [sheet.cellFormats('blue'), '   *レーンID(' + str(i+1) + '): ', str(self.laneIDArray[i]) + "\n"]
            strList += [sheet.cellFormats('wrap')]
            sheet.write_rich_string(row, col, *strList)
#             if self.numberOfArray > 6:
#                 sheet.set_row(row, 13.5*6)
#             else:
#                 sheet.set_row(row, 13.5*self.numberOfArray)
            row += 1
     
        return [row, col, []]

#-----------------------------------------------#
#----   AbsoluteVehiclePositionProfile      ----#
#-----------------------------------------------#
class AbsoluteVehiclePositionProfile(ProfileType):
    classifyDic = {0x00:'MPU', 0x01:'AD'}
    
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.classify = readFunc(int,32)
        self.latitude = readFunc(int,32,True)
        self.longitude = readFunc(int,32,True)
        self.altitude = readFunc(int,32,True)
        self.timestamp = readFunc(int,64)
        self.heading = readFunc(float,32,True)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, _level):
        sheet.write_rich_string(row, col+0, *[sheet.cellFormats('blue'), '   *情報種別: ', self.classifyDic.get(self.classify, '[error]'), sheet.cellFormats('wrap')])
        sheet.write_rich_string(row, col+1, *[sheet.cellFormats('blue'), '   *latitude[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF), sheet.cellFormats('wrap')])
        sheet.write_rich_string(row, col+2, *[sheet.cellFormats('blue'), '   *longitude[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF), sheet.cellFormats('wrap')])
        sheet.write_rich_string(row, col+3, *[sheet.cellFormats('blue'), '   *altitude[cm]: ', str(self.altitude), sheet.cellFormats('wrap')])
        sheet.write_rich_string(row, col+4, *[sheet.cellFormats('blue'), '   *Timestamp[ms]: ', str(self.timestamp), sheet.cellFormats('wrap')])
        sheet.write_rich_string(row, col+5, *[sheet.cellFormats('blue'), '   *Heading[deg]: ', str(self.heading), sheet.cellFormats('wrap')])
#         sheet.write(row, col+1, "...")
#         sheet.set_row(row, 13.5*6)
        row += 1
        
        return [row, col, []]
    
#-----------------------------------------------#
#----   IVIStubInfoProfile                  ----#
#-----------------------------------------------#
class IVIStubInfoProfile(ProfileType):
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.pathID = readFunc(int,32)
        self.offset = readFunc(int,32)
        self.mappingFlag = readFunc(bool,32)
        self.classify = readFunc(int,32)
        self.laneLinkID = readFunc(int,64)
        self.latitude = readFunc(int,32,True)
        self.longitude = readFunc(int,32,True)
        self.height = readFunc(int,32,True)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, _level):
        sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *IVI Stub位置(PathID): ', str(hex(self.pathID)) + "\n",
            sheet.cellFormats('blue'), '   *IVI Stub位置(Offset[m]): ', str(self.offset) + "\n",
            sheet.cellFormats('blue'), '   *分合流マッピングフラグ: ', str(self.mappingFlag) + "\n",
            sheet.cellFormats('blue'), '   *分合流種別: ', str(hex(self.classify)) + "\n",
            sheet.cellFormats('blue'), '   *レーンリンクID: ', str(self.laneLinkID) + "\n",
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *経度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *楕円体高度[cm]: ', str(self.height), sheet.cellFormats('wrap')])
        sheet.write(row, col+1, "...")
#         sheet.set_row(row, 13.5*6)
        row += 1
        
        return [row, col, []]
    
    
#-----------------------------------------------#
#----   PROFILE_MPU_MAP_DATA_TRANSFER_STS   ----#
#-----------------------------------------------#
class PROFILE_MPU_MAP_DATA_TRANSFER_STS(ProfileType):
    classifyDic = {0x00:'無効値', 0x01:'周辺情報　(MPU経路)', 0x02:'周辺情報  (ADECU経路)', 0x03:'経路情報（IVI経路）', 0x04:'経路情報（MPU経路）', 0x05:'経路情報（ADECU経路）', 0x06:'周辺情報（SDMAP:MPU経路)', 0x07:'周辺情報（SDMAP:ADECU経路)'}
    startEndflagDic = {0x00:'無効値', 0x01:'データ送信開始', 0x02:'データ送信完了'}
    initFlagDic = {0x00:'初期化を実施しない', 0x01:'初期化を実施する'}
    outputClassifyDic = {
        0x01:{0x00:'通常出力', 0x01:'全出力', 0x02:'差分出力(再送)'}, #データ送信開始の場合
        0x02:{0x00:'未完了', 0x01:'完了'}} #データ送信完了の場合
    
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.pareID = readFunc(int,32)
        self.classify = readFunc(int,8)
        self.startEndflag = readFunc(int,8)
        self.initFlag = readFunc(int,8)
        self.outputClassify = readFunc(int,8)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, _level):
        sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *開始終了ペアＩＤ: ', str(self.pareID) + "\n",
            sheet.cellFormats('blue'), '   *情報種別: ', self.classifyDic.get(self.classify, '[error]') + "\n",
            sheet.cellFormats('blue'), '   *開始終了フラグ: ', self.startEndflagDic.get(self.startEndflag, '[error]') + "\n",
            sheet.cellFormats('blue'), '   *初期化フラグ: ', self.initFlagDic.get(self.initFlag, '[error]') + "\n",
            sheet.cellFormats('blue'), '   *出力種別: ', self.outputClassifyDic.get(self.startEndflag, '[error]').get(self.outputClassify, '[error]'), sheet.cellFormats('wrap')])
#         sheet.write(row, col+1, "...")
#         sheet.set_row(row, 13.5*5)
        row += 1
        return [row, col, []]
    
#-----------------------------------------------#
#----   PROFILE_MPU_MAP_DATA_BASE_POINT     ----#
#-----------------------------------------------#
class PROFILE_MPU_MAP_DATA_BASE_POINT(ProfileType):
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        readFunc = self.data.readValue
        self.latitude = readFunc(int,32,True)
        self.longitude = readFunc(int,32,True)
        self.eclipseHeight = readFunc(int,32,True)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, sheet, row, col, _level):
        sheet.write_rich_string(row, col, *[
            sheet.cellFormats('blue'), '   *緯度[deg]: ', str(self.latitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *経度[deg]: ', str(self.longitude * 360.0 / 0xFFFFFFFF) + "\n",
            sheet.cellFormats('blue'), '   *楕円体高[cm]: ', str(self.eclipseHeight), sheet.cellFormats('wrap')])
#         sheet.set_row(row, 13.5*3)
        return [row+1, col, []]
    
#-----------------------------------------------#
#----   UnknownProfile                      ----#
#-----------------------------------------------#
class UnknownProfile(ProfileType):
    def __init__(self, data, refMessage):
        super().__init__(data, refMessage)
        
    def printHeader(self, _sheet, row, col, _level):
        return [row, col, []]
    
    def printValue(self, _sheet, row, col, _level):
        return [row+1, col, []]