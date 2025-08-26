'''
Created on 2021/07/17

@author: N200797
'''
try:
    from qgis.core import *
    from qgis.gui import *
    from qgis.PyQt import QtGui
except:
    pass
from GlobalVar import getRecommandLaneViewerClear
from TypeDef import EtherID

class LayerManager:
    def __init__(self):
        self.layerOrderList = []
        self.currentLayerDic = {}
        self.layerGroupDic = {}
        self.recommendLaneLayerOrderList = []
        self.recommendLaneLayerDic = {}
        self.recommendLaneGroup = None
        
        self.root = QgsProject.instance().layerTreeRoot()
        self.model = QgsLayerTreeModel(self.root)
        self.view = QgsLayerTreeView()
        self.view.setModel(self.model)
    
    def makeLayerGroup(self, name, isShpFile = False):
        recommandLaneViewerClear = getRecommandLaneViewerClear()
        if recommandLaneViewerClear == True and self.recommendLaneGroup == None:
            groupTemp = self.root.addGroup('RecommendLane')
            groupParent = groupTemp.clone()
            self.root.insertChildNode(0, groupParent)
            self.root.removeChildNode(groupTemp)
            self.recommendLaneGroup = groupParent
            self.recommendLaneLayerOrderList = []
            self.recommendLaneLayerDic = {}
        
        groupTemp = self.root.addGroup(name)
        groupParent = groupTemp.clone()
        self.root.insertChildNode(0, groupParent)
        self.root.removeChildNode(groupTemp)
        self.group = groupParent
        self.layerOrderList = []
        self.currentLayerDic = {}
        if isShpFile == True:
            self.layerGroupDic[name] = {'layer':self.currentLayerDic, 'type':'shp'}
        else:
            self.layerGroupDic[name] = {'layer':self.currentLayerDic, 'type':'raw'}
        
    def addLayer(self, layerID, layerList):
        if layerList == None:
            return
        
        recommandLaneViewerClear = getRecommandLaneViewerClear()
        if (recommandLaneViewerClear == True) and ((layerID == EtherID.RecommendLaneMessage_JP.value) or (layerID == EtherID.RecommendLaneMessage_US.value)):
            targetDic = self.recommendLaneLayerDic
            targetGroup = self.recommendLaneGroup
            targetOrderList = self.recommendLaneLayerOrderList
        else:
            targetDic = self.currentLayerDic
            targetGroup = self.group
            targetOrderList = self.layerOrderList
        
        if type(layerList[0]) != type([]):
            layerList = [layerList]
            
        if layerID in targetDic:
            for layerListItem in layerList:
                if layerListItem != None:
                    targetDic[layerID].append(layerListItem)
        else:
            targetDic[layerID] = layerList
        
        for layer_item in layerList:
            if layer_item == None:
                continue
            self.layerInsertToGropu(layer_item, targetGroup, targetOrderList)
            order = layer_item[1]
            matched = False
            for i in range(len(targetOrderList)):
                if order <= targetOrderList[i]:
                    targetOrderList.insert(i, order)
                    matched = True
                    break
            if matched == False:
                targetOrderList.append(order)

        self.sortLayer(targetGroup)
        self.sortLayer(targetGroup)
        
        self.view.collapseAll()
        self.view.expand(self.model.node2index(self.group))
        self.view.expand(self.model.node2index(self.recommendLaneGroup))
                
    def getLayer(self, layerID):
        recommandLaneViewerClear = getRecommandLaneViewerClear()
        if (recommandLaneViewerClear == True) and ((layerID == EtherID.RecommendLaneMessage_JP.value) or (layerID == EtherID.RecommendLaneMessage_US.value)):
            targetDic = self.recommendLaneLayerDic
        else:
            targetDic = self.currentLayerDic
            
        if layerID in targetDic:
            return targetDic[layerID]
        else:
            return None
        
    def layerInsertToGropu(self, targetLayerStruct, group, orderList):
        targetLayer = targetLayerStruct[0]
        if targetLayer == None:
            return 
        order = targetLayerStruct[1]
        index = 999
        for i in range(len(orderList)):
            if order == orderList[i]:
                index = i+1
                break

        target = self.root.findLayer(targetLayer.id())
        if target == None:
            return targetLayer
        clone = target.clone()
        parent = target.parent()
        group.insertChildNode(index, clone)
        parent.removeChildNode(target)
        return clone.layer()
        
    def sortLayer(self, targetGroup):
        #値が小さいほど、上に出る。 (描画対象レイヤを選ぶ際にこの番号を使うため、同じ番号を重複して付与してはいけない)
        # GNSS_Vehicle_Speed 1
        # GNSS_Location 2
        # CarPosition_CarPos 3
        # ADPosition 4
        # CarPosition_LaneProj 5
        # CarPosition_CameraPos 6
        # IVIPosition 7
        # RouteInfo_IVIPosition 8
        # GPS_Location 9
        # CarPosition_ErrProb 15
        # GPS_ErrProb 16
        # GNSS_AUGACC_ErrProb = 17
        # GNSS_ErrDist 18
        # CarPosition_ErrDist 19
        # ADASIS_Segment 32
        # ADASIS_ProfileLong 33
        # ADASIS_Stub_Zero 34
        # ADASIS_StubInfo 35
        # ADASIS_Stub 36
        # ADASIS_ProfileShort 37
        # ADASIS_ProfileShort_Curvature 38
        # ADASIS_Position 39
        # Road_Link_Type 40
        # ADASIS_Segment_FoW 41
        # Performance MCPU_load 45
        # ErrorMessage MPUError 50
        # Cam_LeftRight_Lane 51
        # Cam_LeftRight_Lane_ADAS 52
        # ExternalLonLatinfo_Pos = 60
        # ExternalLonLatinfo_ErrDist = 61
        # VehicleInfoLayer 70
        # PathControl 78
        # ReconstructorLaneList 79
        # ProfileData       80
        # Profile_TSR       81
        # Profile_Sign      82
        # Profile_LaneLine 83
        # ProfileData_GeoInfo 84
        # RouteConversionStatus = 85
        # ADASIS_GlobalData_MPUPos = 86
        # ADASIS_GlobalData_ADPos = 87
        # GlobalDataMessage 89
        # RecommendLaneMessage 90
        # VehicleDirection(RDR) = 91
        # RDR_info = 92
        # Hands_off_prohibit = 93
        # ND2_code = 94
        # Cancel_code = 95
        # GPS = 96
        # RDR_pos = 97
        # HDMAP_freshness = 98
        # WithWithoutHDMAP = 99
        # LaneProjectionState = 100
        # Wide_control_state = 101
        # Long_control_state = 102
        # AF_Camera_unstable = 103
        # AF_MAP_freshness = 104
        # AF_Dependancy_of_road = 105
        # AF_Dependancy_of_software = 106
        # AF_Type_of_construction = 107
        # MPU_Error = 109
        # <Template> DefaultLine  150~190
        # AD_status = 199
        # ActionFlag = 200
        
        if targetGroup == self.recommendLaneGroup:
            targetDic = self.recommendLaneLayerDic
            targetOrderList = self.recommendLaneLayerOrderList
        else:
            targetDic = self.currentLayerDic
            targetOrderList = self.layerOrderList
            
        for layer in targetDic.values():
            if layer == None:
                continue
            if type(layer[0]) == type([]):
                for layer_item in layer:
                    if layer_item != None:
                        layer_item[0] = self.layerInsertToGropu(layer_item, targetGroup, targetOrderList)
            else:
                layer[0] = self.layerInsertToGropu(layer, targetGroup, targetOrderList)

    def closeLayer(self):
        try:
            for dic in [self.currentLayerDic, self.recommendLaneLayerDic]:
                for layer in dic.values():
                    if layer == None:
                        continue
                    if type(layer[0]) == type([]):
                        for layer_item in layer:
                            if layer_item != None:
                                layer_item[0].endEditCommand()
                    else:
                        layer[0].endEditCommand()
                dic = {}
                #self.view.collapse(self.model.node2index(self.group))
        except:
            pass
        
    def refreshLayer(self):
        try:
            for dic in [self.currentLayerDic, self.recommendLaneLayerDic]:
                for layer in dic.values():
                    if layer == None:
                        continue
                    if type(layer[0]) == type([]):
                        for layer_item in layer:
                            if layer_item != None:
                                layer_item[0].triggerRepaint()
                    else:
                        layer[0].triggerRepaint()
        except:
            pass
    
    def shpSave(self, groupName, savePath):
        try:
            for layer in self.layerGroupDic[groupName]['layer'].values():
                if layer == None:
                    continue
                if type(layer[0]) == type([]):
                    for layer_item in layer:
                        if layer_item != None:
                            error = QgsVectorFileWriter.writeAsVectorFormat(layer_item[0], savePath + '/' + layer_item[0].name() + '.shp', 'utf-8', layer_item[0].crs(), 'ESRI Shapefile')
                            if error[0] != QgsVectorFileWriter.NoError:
                                print("Fail to save {0} : error {1}".format(layer_item[0].name(), error))
                else:
                    error = QgsVectorFileWriter.writeAsVectorFormat(layer[0], savePath + '/' + layer[0].name() + '.shp', 'utf-8', layer[0].crs(), 'ESRI Shapefile')
                    if error[0] != QgsVectorFileWriter.NoError:
                        print("Fail to save {0} : error {1}".format(layer[0].name(), error))
            print('Save completed : ' + groupName)
        except Exception as e:
            print(e)
    
    def setFilter(self, groupName, filterStartTime, filterEndTime):
        try:
            if filterStartTime != None and filterEndTime != None:
                if self.layerGroupDic[groupName]['type'] == 'shp':
                    filterStr = '"Time" >= \'{0}\' AND "Time" <= \'{1}\''.format(filterStartTime.strftime("%Y/%m/%d %H:%M:%S"), filterEndTime.strftime("%Y/%m/%d %H:%M:%S"))
                else:
                    filterStr = '"Time" >= \'{0}\' AND "Time" <= \'{1}\''.format(filterStartTime.strftime("%Y-%m-%dT%H:%M:%S"), filterEndTime.strftime("%Y-%m-%dT%H:%M:%S"))
            else:
                filterStr = ''
        
            
            
            for layer in self.layerGroupDic[groupName]['layer'].values():
                if layer == None:
                    continue
                if type(layer[0]) == type([]):
                    for layer_item in layer:
                        try:
                            if self.root.findLayer(layer_item[0]).isVisible() == True:
                                if layer_item != None and layer_item[0].name() != 'Recommend Lane Message(ActionFlag)':
                                    layer_item[0].setSubsetString(filterStr)
                            else:
                                layer_item[0].setSubsetString('')
                        except:
                            pass
                else:
                    try:
                        if self.root.findLayer(layer[0]).isVisible() == True:
                            if layer[0].name() != 'Recommend Lane Message(ActionFlag)':
                                layer[0].setSubsetString(filterStr)
                        else:
                            layer[0].setSubsetString('')
                    except:
                        pass
                
        except Exception as e:
            print(e)
            
    def clearFilter(self, groupName):
        self.setFilter(groupName, None, None)

                    