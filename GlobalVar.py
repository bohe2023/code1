import re
from datetime import datetime
import locale
resource = {}
resource['processMessageList'] = {}

def addProcessMessageList(messageID, period = 0):
    global resource
    try:
        resource['processMessageList'][messageID] = period
    except:
        resource['processMessageList'] = {}
        resource['processMessageList'][messageID] = period

def getProcessMessageList():
    global resource
    try:
        return resource['processMessageList']
    except:
        return {}

def setResource(res):
    global resource
    resource = res

def getResource():
    global resource
    return resource

def setLocal(localStr):
    global resource
    resource['local'] = localStr

def getLocal():
    global resource
    try:
        return resource['local']
    except:
        return locale.getdefaultlocale()[0]

def setLogger(logger):
    global resource
    resource['logger'] = logger
    
def getLogger():
    global resource
    try:
        return resource['logger']
    except:
        return None

def setLogIndex(index):
    global logIndex
    logIndex = index
    
def getLogIndex():
    global logIndex
    try:
        return logIndex
    except:
        return 0

def setProgramDir(path):
    global resource
    resource['programDir'] = path
    
def getProgramDir():
    global resource
    try:
        return resource['programDir']
    except:
        return ''

def setEthernetSpecVer(date):
    global resource
    resource['ethernetSpecVer'] = date
    
def getEthernetSpecVer():
    global resource
    try:
        return resource['ethernetSpecVer']
    except:
        return datetime(9999, 12, 31)

def setSrcMAC(val):
    global resource
    if val == "":
        resource['srcMAC'] = []
    else:
        resource['srcMAC'] = [x.upper() for x in re.split('[,\n ]',val)]

def getSrcMAC():
    global resource
    try:
        return resource['srcMAC']
    except:
        return []
    
def setDstMAC(val):
    global resource
    if val == "":
        resource['dstMAC'] = []
    else:
        resource['dstMAC'] = [x.upper() for x in re.split('[,\n ]',val)]

def getDstMAC():
    global resource
    try:
        return resource['dstMAC']
    except:
        return []

def setSrcIP(val):
    global resource
    if val == "":
        resource['srcIP'] = []
    else:
        resource['srcIP'] = re.split('[,\n ]',val)

def getSrcIP():
    global resource
    try:
        return resource['srcIP']
    except:
        return []

def setDstIP(val):
    global resource
    if val == "":
        resource['dstIP'] = []
    else:
        resource['dstIP'] = re.split('[,\n ]',val)

def getDstIP():
    global resource
    try:
        return resource['dstIP']
    except:
        return []

def setSrcPort(val):
    global resource
    if val == "":
        resource['srcPort'] = []
    else:
        resource['srcPort'] = [int(x) for x in re.split('[,\n ]',val)]

def getSrcPort():
    global resource
    try:
        return resource['srcPort']
    except:
        return []

def setDstPort(val):
    global resource
    if val == "":
        resource['dstPort'] = []
    else:
        resource['dstPort'] = [int(x) for x in re.split('[,\n ]',val)]

def getDstPort():
    global resource
    try:
        return resource['dstPort']
    except:
        return []

def setSomeIPHead(val):
    global resource
    resource['someipHead'] = val
    
def getSomeIPHead():
    global resource
    try:
        return resource['someipHead']
    except:
        return 1

def setIgnoreSameMsgcnt(val):
    global resource
    resource['ignoreSameMsgcnt'] = val
    
def getIgnoreSameMsgcnt():
    global resource
    try:
        return resource['ignoreSameMsgcnt']
    except:
        return 1

def setSaveFilteredLogData(val):
    global resource
    resource['saveFilteredLogData'] = val
    
def getSaveFilteredLogData():
    global resource
    try:
        return resource['saveFilteredLogData']
    except:
        return 0
    
def setRecommandLaneViewerClear(val):
    global resource
    resource['recommandLaneViewerClear'] = val
    
def getRecommandLaneViewerClear():
    global resource
    try:
        return resource['recommandLaneViewerClear']
    except:
        return 0
    
def setRecommendedLaneShowTarget(val):
    global resource
    resource['recommendedLaneShowTarget'] = val
    
def getRecommendedLaneShowTarget():
    global resource
    try:
        return resource['recommendedLaneShowTarget']
    except:
        return 'All'
    
def setVehicleType(val):
    global resource
    resource['vehicleType'] = val
    
def getVehicleType():
    global resource
    try:
        return resource['vehicleType']
    except:
        return ''
    
def setADASISanalyze(flag):
    global resource
    resource['ADASISanalyze'] = flag
    
def setDebugEtherAnalyze(flag):
    global resource
    resource['DebugEtherAnalyze'] = flag
    
def setREDRanalyze(flag):
    global resource
    resource['REDRanalyze'] = flag
    
def getADASISanalyze():
    global resource
    try:
        return resource['ADASISanalyze']
    except:
        return False
    
def getDebugEtherAnalyze():
    global resource
    try:
        return resource['DebugEtherAnalyze']
    except:
        return False
    
def getREDRanalyze():
    global resource
    try:
        return resource['REDRanalyze']
    except:
        return False
