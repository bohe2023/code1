'''
Created on 2024/03/14

@author: AD2Gen2-19
'''
from dataclasses import dataclass
from enum import Enum
import re
class QtGui:
        class QColor:
            @dataclass
            class fromRgb:
                r:int
                g:int
                b:int
             
class QgsPoint:
    def __init__(self, lon, lat, z=0):
        self.lon = lon
        self.lat = lat
        self.z = z
        
class QgsPointXY:
    def __init__(self, lon, lat):
        self.lon = lon
        self.lat = lat
        self.z = 0
        
class QDateTime:
    def __init__(self, dateTime):
        self.dateTime = dateTime

class SymbolType(Enum):
    LINE = 0
    ARROW = 1
    
class Symbol:
    def __init__(self, symbolType = SymbolType.LINE):
        self.color = QtGui.QColor.fromRgb(255,255,255)
        self.width = 0.2
        self.order = 0
        self.opacity = 0
        self.symbolLabel = ''
        self.isCategoryItem = False
        self.symbolType = symbolType
    
    def setColor(self, color):
        self.color = color
        
    def setWidth(self, width):
        self.width = width
    
    def setSize(self, width):
        self.width = width
        
    def setOpacity(self, opacity):
        self.opacity = opacity
        
    def setCategory(self, order, symbolLabel):
        self.order = order
        self.symbolLabel = symbolLabel
        self.isCategoryItem = True
        
    def setRenderState(self, dummyParameter):
        pass
    
    def setIsCurved(self, dummyParameter):
        pass
    
    def setIsRepeated(self, dummyParameter):
        pass
    
    def changeSymbolLayer(self, dummyParameter, symbol):
        self.color = symbol.color
        self.width = symbol.width
        self.order = symbol.order
        self.opacity = symbol.opacity
        self.symbolLabel = symbol.symbolLabel
        self.isCategoryItem = symbol.isCategoryItem
        self.symbolType = symbol.symbolType
        
    def appendSymbolLayer(self, symbol):
        self.changeSymbolLayer(None, symbol)
        
    def createSimple(self, dummyParameter):
        return self
    
    def deleteSymbolLayer(self, dummyParameter):
        pass
    
    def setSubSymbol(self, dummyParameter):
        pass
    
    def setPlacement(self, dummyParameter):
        pass
    
class QgsMarkerLineSymbolLayer(Symbol):
    LastVertex = None
    
    def __init__(self):
        super().__init__(SymbolType.LINE)
    
class QgsSimpleMarkerSymbolLayer(Symbol):
    def __init__(self):
        super().__init__(SymbolType.LINE)
        
    @staticmethod
    def create(dummyParameter):
        return QgsSimpleMarkerSymbolLayer()

class QgsMarkerSymbol(Symbol):
    def __init__(self):
        super().__init__(SymbolType.LINE)
    
    @staticmethod
    def createSimple(dummyParameter):
        return QgsMarkerSymbol()

def QgsSimpleLineSymbolLayer():
    return Symbol(SymbolType.LINE)

def QgsArrowSymbolLayer():
    return Symbol(SymbolType.ARROW)

class QgsLineSymbol(Symbol):
    def __init__(self):
        super().__init__(SymbolType.LINE)
        
    def createSimple(self, dummyParameter):
        return self

class QgsSymbol:
    @staticmethod
    def defaultSymbol(dummyParameter):
        return Symbol()
    
class Category:
    def __init__(self):
        self.categoryValueName = '' 
        self.symbolList = {}

def QgsRendererCategory(order, sym, symbolLabel):
    sym.setCategory(order, symbolLabel)
    return sym

def QgsCategorizedSymbolRenderer(categoryValueName, categories):
    category = Category()
    category.categoryValueName = categoryValueName
    for categoryItem in categories:
        category.symbolList[categoryItem.order] = categoryItem
    return category

class FeatureType(Enum):
    COMMAND = 0
    SingleSolidPaintLine = 1
    SingleDashedPaintLine = 2
    RectanbleMaintananceArea = 3

class Feature:
    def __init__(self, featureType = FeatureType.SingleSolidPaintLine):
        self.type = featureType
        self.geometryList = []
        self.attribute = []
             
    def setGeometry(self, geometry):
        self.geometryList.append(geometry)
   
    def setAttributes(self, attribute):
        if type(attribute) == type([]):
            self.attribute = attribute
        else:
            self.attribute = [attribute]
        
    def getAttributes(self):
        return self.attribute
   
class Geometry:
    def __init__(self):
        self.pointList = []
        
class QgsGeometry:
    @staticmethod
    def fromPolyline(pointList):
        geometry = Geometry()
        geometry.pointList = pointList
        return geometry
    
    @staticmethod
    def fromMultiPolylineXY(pointLineList):
        geometry = Geometry()
        for pointLine in pointLineList:
            geometry.pointList.append(pointLine[0])
            geometry.pointList.append(pointLine[1])
        return geometry
        
def QgsFeature():
    return Feature()

class Layer:
    def __init__(self, name, valList):
        self.name = name
        self.valList = {}
        index = 0
        for var in valList:
            self.valList[var] = index
            index += 1            
        self.symbol = Symbol()
        self.category = None
        self.featureList = set()
        self.glCompile = set()
        self.layerType = 0
        
    def getFeatureCategoryValue(self, feature):
        if self.category == None:
            return None
#         if (self.categoryExpresstion == "feature.attribute[self.valList['group']]*10+feature.attribute[self.valList['order']]+(feature.attribute[self.valList['VerCheck']]*feature.attribute[self.valList['VerStat']])*5"):
#             print('here')
        return eval(self.categoryExpresstion)
        
    def indexFromName(self, varName):
        return self.valList.get(varName, 0)
        
    def renderer(self):
        return self
    
    def fields(self):
        return self
    
    def symbols(self, dummyParameter):
        return [self.symbol]
    
    def setRenderer(self, category):
        self.category = category
        self.categoryExpresstion = re.sub("([a-zA-Z]+[a-zA-Z0-9]*)", "feature.attribute[self.valList['\\1']]", category.categoryValueName)
    
    def geometryType(self):
        return 0
    
    def beginEditCommand(self, dummyParameter):
        pass
    
    def dataProvider(self):
        return self
    
    def deleteFeatures(self, listOfIds):
        feature = Feature(FeatureType.COMMAND)
        feature.setAttributes('deleteFeatures')
        self.featureList.add(feature)
    
    def addFeatures(self, featureList):
        self.featureList |= set(featureList)
        
    def getFeatures(self):
        return self.featureList
    
    def clearFeatures(self):
        self.featureList.clear()

class LayerManager:
    def __init__(self):
        self.layerList = {}
        self.layerListAsLayerTypeID = {}
        
    def getLayer(self, messageID):
        if messageID in self.layerList:
            return self.layerList[messageID]
        else:
            return None
        
    def getLayerFromLayerTypeID(self, typeID):
        if typeID in self.layerListAsLayerTypeID:
            return self.layerListAsLayerTypeID[typeID]
        else:
            return None
        
    def addLayer(self, messageID, newLayerGroup):
        self.layerList[messageID] = newLayerGroup
        for layer in newLayerGroup:
            self.layerListAsLayerTypeID[layer[1]] = layer[0]
            layer[0].layerType = layer[1]

    def addVectorLayer(self, attribute, name, flag):
        varList = []
        for param in attribute.split('&'):
            if param[:6] == 'field=':
                varList.append(param[6:].split(':')[0])
        return Layer(name, varList)
        
# dummy function
def QgsRenderContext():
    return 0
