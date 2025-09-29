'''
Created on 2023/01/10

@author: N200797
'''   
import math
import sys

class ADASISinfoManager:
    def __init__(self):
        self.reset()
        
    def reset(self):            
        self.pathInfoDic = {} #各PathIndex,offset毎に、profile longから受信した緯度経度を格納
        self.predictPathInfoDic = {} #各PathIndex,offset毎に、推定緯度経度を格納
        self.stubInfoDic = {} #PathIndex別に、各Stubのoffset位置とturn angleを格納。offsetは、adjustされたoffset
        
        self.usedPathIndexList = []
        self.receivedPLcount = {}
        self.positionLoopCnt = {}
        self.lastpositionOffset = {}
        self.PLcount_oldPLtype = 0
        self.PLcount_oldpathIndex = 0
        self.PLcount_oldoffset = 0
        
    def cyclicReceiveComplete(self, cycleStartPathIndex):
        usedMainPath = []
        for index in range(len(self.usedPathIndexList)):
            if self.usedPathIndexList[index] == cycleStartPathIndex:
                usedMainPath = self.usedPathIndexList[index:]
                break
                    
        for index in self.pathInfoDic.keys():
            if not index in usedMainPath:
                self.pathInfoDic[index] = {}
                # stubInfoDicおよびpredictPathInfoDicは、Stubメッセージ受信でのstubツリー構成時、適宜クリアされるため、ここでクリア不要。
        for index in self.positionLoopCnt.keys():
            if not index in usedMainPath:
                self.positionLoopCnt[index] = 0
                self.lastpositionOffset[index] = 0
                
        self.receivedPLcount = {}
        self.usedPathIndexList = []
    
    def setCurrentPosition(self, pathIndex, offset):
        if not pathIndex in self.positionLoopCnt:
            self.positionLoopCnt[pathIndex] = 0
            self.lastpositionOffset[pathIndex] = offset
        elif offset < self.lastpositionOffset[pathIndex] and self.lastpositionOffset[pathIndex] - offset > 7000: #現在地が、前方に煤に、offsetを一周した場合
            self.positionLoopCnt[pathIndex] += 1
        elif offset > self.lastpositionOffset[pathIndex] and offset - self.lastpositionOffset[pathIndex] > 7000: #現在地が、後方にジャンプし、offsetを一周した場合
            self.positionLoopCnt[pathIndex] -= 1
        self.lastpositionOffset[pathIndex] = offset
    
    # offset will cyclic 0 ～ 8190. and trailing length is 500～600m
    # so, if offset less current position offset - 1000, then it is forward.
    def adjustOffset(self, pathIndex, offset):
        if pathIndex in self.positionLoopCnt:
            if self.lastpositionOffset[pathIndex] >= 1000 and (offset < (self.lastpositionOffset[pathIndex] - 1000)):
                return (self.positionLoopCnt[pathIndex]+1) * 8191 + offset
            elif self.lastpositionOffset[pathIndex] < 1000 and (offset >= (self.lastpositionOffset[pathIndex] + 8191 - 1000)):
                return (self.positionLoopCnt[pathIndex]-1) * 8191 + offset
            else:
                return self.positionLoopCnt[pathIndex] * 8191 + offset
        else:
            return offset
    
    def setReceivedPLcount(self, PLtype, pathIndex, offset):
        if self.PLcount_oldPLtype == PLtype and self.PLcount_oldpathIndex == pathIndex and self.PLcount_oldoffset == offset:
            return #まったく全体と同じPLが来た場合は、サイクリック完了チェック行わない
        self.PLcount_oldPLtype = PLtype
        self.PLcount_oldpathIndex = pathIndex
        self.PLcount_oldoffset = offset
        
        if not PLtype in self.receivedPLcount:
            self.receivedPLcount[PLtype] = {}
        if not pathIndex in self.receivedPLcount[PLtype]:
            self.receivedPLcount[PLtype][pathIndex] = {}
        if not offset in self.receivedPLcount[PLtype][pathIndex]:
            self.receivedPLcount[PLtype][pathIndex][offset] = 0
        else:
            self.receivedPLcount[PLtype][pathIndex][offset] += 1
            if self.receivedPLcount[PLtype][pathIndex][offset] >= 1:
                self.cyclicReceiveComplete(pathIndex)
                self.receivedPLcount[PLtype] = {}
                self.receivedPLcount[PLtype][pathIndex] = {}
                self.receivedPLcount[PLtype][pathIndex][offset] = 0
    
    def addLonLatInfo(self, pathIndex, offset, value, isLongitude):
        if not pathIndex in self.pathInfoDic:
            self.pathInfoDic[pathIndex] = {}
            self.predictPathInfoDic[pathIndex] = {}
        if not pathIndex in self.usedPathIndexList:
            self.usedPathIndexList.append(pathIndex)
        else:
            self.usedPathIndexList.remove(pathIndex)
            self.usedPathIndexList.append(pathIndex)
            
        offset = self.adjustOffset(pathIndex, offset)
        if not offset in self.pathInfoDic[pathIndex]:
            if isLongitude == True: self.pathInfoDic[pathIndex][offset] = [value, 180.0] #lon, lat
            else: self.pathInfoDic[pathIndex][offset] = [180.0, value] #lon, lat
        else:
            if isLongitude == True and self.pathInfoDic[pathIndex][offset][0] != value:
                if type(self.pathInfoDic[pathIndex][offset]) == tuple:
                    self.pathInfoDic[pathIndex][offset] = [value, 180.0]
                else:
                    self.pathInfoDic[pathIndex][offset][0] = value
            elif isLongitude == False and self.pathInfoDic[pathIndex][offset][1] != value:
                if type(self.pathInfoDic[pathIndex][offset]) == tuple:
                    self.pathInfoDic[pathIndex][offset] = [180.0, value]
                else:
                    self.pathInfoDic[pathIndex][offset][1] = value
                
            if self.pathInfoDic[pathIndex][offset][0] != 180 and self.pathInfoDic[pathIndex][offset][1] != 180:
                self.pathInfoDic[pathIndex][offset] = tuple(self.pathInfoDic[pathIndex][offset])
                if (not offset in self.predictPathInfoDic[pathIndex]) or (self.predictPathInfoDic[pathIndex][offset] != self.pathInfoDic[pathIndex][offset]):
                    self.predictPathInfoDic[pathIndex][offset] = self.pathInfoDic[pathIndex][offset]
                    #新規位置確定。Stub infoでのpredictPathInfoも再更新をかける。
                    pathInfoOffsetList = sorted(self.pathInfoDic[pathIndex].keys())
                    pathInfoOffsetList.reverse()
                    beforeOffset = None
                    for targetOffset in pathInfoOffsetList:
                        if targetOffset < offset:
                            beforeOffset =  targetOffset
                            break
                    self.stubPositionUpdate_recursive(pathIndex, beforeOffset, offset)
                
    def addLongitudeInfo(self, pathIndex, offset, longitude):
        self.addLonLatInfo(pathIndex, offset, longitude, True)
            
    def addLatitudeInfo(self, pathIndex, offset, latitude):
        self.addLonLatInfo(pathIndex, offset, latitude, False)
    
    def stubPositionUpdate_recursive(self, pathIndex, minOffset, maxOffset):
        if not pathIndex in self.stubInfoDic:
            return
        for offset in sorted(self.stubInfoDic[pathIndex].keys()):
            if minOffset != None and offset < minOffset:
                continue
            if maxOffset != None and offset > maxOffset:
                break
            for subPathIndex in sorted(self.stubInfoDic[pathIndex][offset]['subPathIndex']):
                turnAngle = self.stubInfoDic[pathIndex][offset]['turnAngle'][subPathIndex]
                self.stubPositionUpdate(pathIndex, subPathIndex, offset, turnAngle)
                if subPathIndex >= 8:            
                    self.stubPositionUpdate_recursive(subPathIndex, None, None)
    
    def stubPositionUpdate(self, pathIndex, subPathIndex, offset, turnAngle): # ここに入ってくるoffsetはすでに補正されたoffset
        targetPos = self.getLonLat(pathIndex, offset, False)
        if self.isValidPosition(targetPos):
            self.predictPathInfoDic[pathIndex][offset] = targetPos
            if subPathIndex >= 8:
                self.predictPathInfoDic[subPathIndex][0] = targetPos
        
            beforePos = None
            if offset == 0:
                #offset 0 の場合は、以前位置がない。親の分岐位置の以前位置を持ってくる。
                if 'parent' in self.stubInfoDic[pathIndex][0]:
                    (parentPathIndex, parentOffset) = self.stubInfoDic[pathIndex][0]['parent']
                    predictPathInfoOffsetList = sorted(self.predictPathInfoDic[parentPathIndex].keys())
                    predictPathInfoOffsetList.reverse()
                    for targetOffset in predictPathInfoOffsetList:
                        if targetOffset < parentOffset:
                            beforePos = self.predictPathInfoDic[parentPathIndex][targetOffset]
                            break
            else:
                predictPathInfoOffsetList = sorted(self.predictPathInfoDic[pathIndex].keys())
                predictPathInfoOffsetList.reverse()
                for targetOffset in predictPathInfoOffsetList:
                    if targetOffset < offset:
                        beforePos = self.predictPathInfoDic[pathIndex][targetOffset]
                        break
            if self.isValidPosition(beforePos):
                if turnAngle < 254:
                    angle = -(2*math.pi*turnAngle/254) # 254 is 360 deg. but will be 0. 254 defined as unknown.
                    l = math.sqrt((targetPos[0]-beforePos[0])*(targetPos[0]-beforePos[0]) + (targetPos[1]-beforePos[1])*(targetPos[1]-beforePos[1]))
                    if l > 0:
                        x = 0.0000097*(targetPos[0]-beforePos[0])/l # 0.0000097 is almost 1m
                        y = 0.0000097*(targetPos[1]-beforePos[1])/l # 0.0000097 is almost 1m
                        turnPos = (targetPos[0] + x*math.cos(angle) - y*math.sin(angle), #現在のPathDirectionに対する回転
                               targetPos[1] + x*math.sin(angle) + y*math.cos(angle))
                
                        if subPathIndex < 8:
                            self.predictPathInfoDic[pathIndex][offset+1] = turnPos
                        elif subPathIndex >= 8:
                            self.predictPathInfoDic[subPathIndex][1] = turnPos
    
    def setStub(self, pathIndex, offset, subPathIndex, turnAngle):
        if not pathIndex in self.stubInfoDic:
            self.stubInfoDic[pathIndex] = {}
        if not pathIndex in self.predictPathInfoDic:
            self.predictPathInfoDic[pathIndex] = {}
        if not pathIndex in self.pathInfoDic:
            self.pathInfoDic[pathIndex] = {}
            
        offset = self.adjustOffset(pathIndex, offset)
        if not offset in self.stubInfoDic[pathIndex]:
            self.stubInfoDic[pathIndex][offset] = {}
            self.stubInfoDic[pathIndex][offset]['subPathIndex'] = []
            self.stubInfoDic[pathIndex][offset]['turnAngle'] = {}
        if not subPathIndex in self.stubInfoDic[pathIndex][offset]['subPathIndex']: 
            self.stubInfoDic[pathIndex][offset]['subPathIndex'].append(subPathIndex)
        self.stubInfoDic[pathIndex][offset]['turnAngle'][subPathIndex] = turnAngle
        
        if subPathIndex >= 8:
            # subPathの情報がこれから新しく送られて来るので、一旦クリア。Stubのサイクルと、他のサイクルが異なるため、pathInfoDicは消してはいけない。predictPathInfoDicは消していいかも。
            self.stubInfoDic[subPathIndex] = {}
            self.predictPathInfoDic[subPathIndex] = {}            
            if not subPathIndex in self.pathInfoDic:
                self.pathInfoDic[subPathIndex] = {}
                
            # subPathに0点追加。
            self.stubInfoDic[subPathIndex][0] = {}
            self.stubInfoDic[subPathIndex][0]['subPathIndex'] = [6]
            self.stubInfoDic[subPathIndex][0]['turnAngle'] = {}
            self.stubInfoDic[subPathIndex][0]['turnAngle'][6] = turnAngle
            self.stubInfoDic[subPathIndex][0]['parent'] = (pathIndex, offset)
            
        self.stubPositionUpdate(pathIndex, subPathIndex, offset, turnAngle) #subPathIndexを持つ場合、 subPath側のoffset 1にも回転位置が入る。
        
                        
    def isValidPosition(self, position):
        if position != None and position[0] != 180 and position[1] != 180:
            return True
        else:
            return False
    
    def getLonLat(self, pathIndex, offset, withOffsetAdjust = True):
        if not pathIndex in self.stubInfoDic:
            return (180, 180)
        
        if withOffsetAdjust == True:
            offset = self.adjustOffset(pathIndex, offset)
        
        #　優先度１。確定位置リストに存在すると、それを返す。
        if offset in self.pathInfoDic[pathIndex]:
            targetPos = self.pathInfoDic[pathIndex][offset]
            if self.isValidPosition(targetPos):
                return targetPos
        
        #　優先度２。前後の確定位置が存在すると、その中間点を算出し返す。(確定位置は、turn Angle位置は入れてないので、必ず前後がある場合のみ算出。)
        nextPos = None
        prevPos = None
        pathInfoOffsetList = sorted(self.pathInfoDic[pathIndex].keys())
        pathInfoOffsetList.reverse()
        for targetOffset in pathInfoOffsetList:
            if targetOffset > offset:
                targetPos = self.pathInfoDic[pathIndex][targetOffset]
                if self.isValidPosition(targetPos):
                    nextPos = targetPos
                    nextOffset = targetOffset
            elif targetOffset <= offset:
                targetPos = self.pathInfoDic[pathIndex][targetOffset]
                if self.isValidPosition(targetPos):
                    prevPos = targetPos
                    prevOffset = targetOffset
                    break
        if self.isValidPosition(nextPos) and self.isValidPosition(prevPos):
            rate = (offset-prevOffset)/(nextOffset-prevOffset)
            resultPos = (prevPos[0] + (nextPos[0]-prevPos[0])*rate, prevPos[1] + (nextPos[1]-prevPos[1])*rate) #lon, lat        
            return resultPos
        
        #　優先度３。推定位置として、すでに有ればそれを返す。
        if offset in self.predictPathInfoDic[pathIndex]:
            targetPos = self.predictPathInfoDic[pathIndex][offset]
            if self.isValidPosition(targetPos):
                return targetPos
        
        #　優先度４。推定位置として、前後または、前・前々位置がある場合、その内分点もしくは外分点を算出。
        nextPos = None
        prevPos = None
        predictPathInfoOffsetList = sorted(self.predictPathInfoDic[pathIndex].keys())
        predictPathInfoOffsetList.reverse()
        for targetOffset in predictPathInfoOffsetList:
            if targetOffset > offset:
                targetPos = self.predictPathInfoDic[pathIndex][targetOffset]
                if self.isValidPosition(targetPos):
                    nextPos = targetPos
                    nextOffset = targetOffset
            elif targetOffset <= offset:
                targetPos = self.predictPathInfoDic[pathIndex][targetOffset]
                if self.isValidPosition(targetPos):
                    if nextPos == None:
                        nextPos = targetPos
                        nextOffset = targetOffset
                    else:
                        prevPos = targetPos
                        prevOffset = targetOffset
                        break
        if self.isValidPosition(nextPos) and self.isValidPosition(prevPos):
            rate = (offset-prevOffset)/(nextOffset-prevOffset)
            if math.fabs(rate) < 500:
                resultPos = (prevPos[0] + (nextPos[0]-prevPos[0])*rate, prevPos[1] + (nextPos[1]-prevPos[1])*rate) #lon, lat        
                return resultPos
        
        # 算出できない場合は、無効値を返す
        return (180, 180)

    def getLonLat_StubLine(self, pathIndex, subPathIndex, offset): #lon, lat, targetLon, targetLat            
        if not pathIndex in self.stubInfoDic:
            return [(180, 180), (180, 180)]
        
        offset = self.adjustOffset(pathIndex, offset)
        
        if subPathIndex >= 8:
            #subPath方向の、10m地点を推定し、線を引く。
            targetPos = (180, 180)
            beforeStubPos = (180, 180)
            targetPos = self.getLonLat(subPathIndex, 10, False) #既にOffsetAdjustしたので、そのoffsetのままで抽出するためFalse指定
            beforeStubPos = self.getLonLat(pathIndex, offset, False) #既にOffsetAdjustしたので、そのoffsetのままで抽出するためFalse指定
            if self.isValidPosition(targetPos) and self.isValidPosition(beforeStubPos):
                return [targetPos, beforeStubPos] # Stub向きの推定線。実際のSubPath側のStubではないため、targetPosを前方に出力し、〇がbeforeStubPosに描画できるようにする。
            else:
                return [(180, 180), (180, 180)]
            
        else:
            targetPos = (180, 180)
            beforeStubPos = (180, 180)
            beforeTurnPos = (180, 180)
            stubInfoOffsetList = sorted(self.stubInfoDic[pathIndex].keys())
            stubInfoOffsetList.reverse()
            for targetOffset in stubInfoOffsetList:
                if targetOffset == offset:
                    targetPos = self.getLonLat(pathIndex, offset, False) #既にOffsetAdjustしたので、そのoffsetのままで抽出するためFalse指定
                elif targetOffset < offset:
                    beforeStubPos = self.getLonLat(pathIndex, targetOffset, False) #既にOffsetAdjustしたので、そのoffsetのままで抽出するためFalse指定
                    beforeTurnPos = self.getLonLat(pathIndex, targetOffset+1, False) #既にOffsetAdjustしたので、そのoffsetのままで抽出するためFalse指定
                    if self.isValidPosition(beforeStubPos):
                        break
            
            if self.isValidPosition(targetPos) and self.isValidPosition(beforeStubPos):
                if self.isValidPosition(beforeTurnPos):
                    return [beforeStubPos, beforeTurnPos, targetPos]
                else:
                    return [beforeStubPos, targetPos]
            else:
                return [(180, 180), (180, 180)]

def reset():
    global ADASISinfo_forEth
    global ADASISinfo_forCAN
    global ADASISinfo_forFrCamera
    ADASISinfo_forEth = ADASISinfoManager()
    ADASISinfo_forCAN = ADASISinfoManager() 
    ADASISinfo_forFrCamera = ADASISinfoManager()
    sys.setrecursionlimit(10000)
    
def getADASISinfo_forEth():
    return ADASISinfo_forEth

def getADASISinfo_forCAN():
    return ADASISinfo_forCAN

def getADASISinfo_forFrCamera():
    return ADASISinfo_forFrCamera