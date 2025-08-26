'''
Created on 2024/04/23

@author: N200797
'''
from datetime import datetime
import subprocess
import logging
import logging.handlers
import multiprocessing as mp
from enum import Enum
from GlobalVar import setLogger, getLogger

class LogLevel(Enum):
    ERROR = logging.ERROR
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    
def initLogger(filePath = None, forMultiProcess = False, logLevel = LogLevel.INFO):
    logger = Logger(filePath, forMultiProcess, logLevel)
    setLogger(logger)
    return logger
    
def loadLogger():
    logger = getLogger()
    logger.setupLoggerforSubProcess()
    return logger

def closeLogger():
    logger = getLogger()
    logger.close()

listenerProcess = None
def listener(filePath, control, logQueue):
    logger = logging.getLogger()
    h = logging.handlers.TimedRotatingFileHandler(filePath, when="midnight", backupCount=20)
    f = logging.Formatter("%(asctime)s,%(processName)-15s,%(levelname)-8s,%(message)s")
    h.setFormatter(f)
    logger.addHandler(h)
    
    while True:
        if control['processCancel']:
            while not logQueue.empty():
                log = logQueue.get()
                logger.handle(log)
            break
        try:
            log = logQueue.get(False, 0)
            logger.handle(log)
        except Exception: # Queue empty
            pass

class Logger:
    def __init__(self, filePath = None, forMultiProcess = False, logLevel = LogLevel.INFO):
        global listenerProcess
        self.forMultiProcess = forMultiProcess
        self.logLevel = logLevel.value
        self.errorOccured = False
        self.filePath = filePath
        self.active = True
        if forMultiProcess:
            manager = mp.Manager()
            self.control = manager.dict()
            self.control['processCancel'] = False
            
            self.logQueue = mp.Queue()
            listenerProcess = mp.Process(name="listener",target=listener,args=(filePath, self.control, self.logQueue))
            listenerProcess.start()
            
            self.setupLoggerforSubProcess()
        else:
            #単一ファイルログ
            if filePath != None:
                self.logFile = open(filePath, 'w')
            else:
                self.logFile = None
            
    def disableLogger(self):
        self.active = False
        
    def enableLogger(self):
        self.active = True
    
    def setupLoggerforSubProcess(self):
        if self.forMultiProcess:
            h = logging.handlers.QueueHandler(self.logQueue)
            self.logger = logging.getLogger()
            self.logger.addHandler(h)
            self.logger.setLevel(self.logLevel)
        
    def logPrint(self, strLog):
        if self.active == False: return
        if self.forMultiProcess:
            self.logger.info(strLog)
        else:
            if self.logLevel == logging.ERROR:
                return
            if self.logFile != None:
                self.logFile.write('{},INFO    ,{}\n'.format(datetime.now(), strLog))
        
    def logPrintWithConsol(self, strLog):
        if self.active == False: return
        print(strLog)
        self.logPrint(strLog)
        
    def errLog(self, strLog, showConsole = True):
        if self.active == False: return
        self.errorOccured = True
        if showConsole: print('(Error) ' + strLog)
        if self.forMultiProcess:
            self.logger.error(strLog)
        else:
            if self.logFile != None:
                self.logFile.write('{},ERROR   ,{}\n'.format(datetime.now(), strLog))
                self.logFile.flush()
            
    def debugLog(self, strLog):
        if self.active == False: return
        if self.forMultiProcess:
            self.logger.debug(strLog)
        else:
            if self.logLevel != logging.DEBUG:
                return
            if self.logFile != None:
                self.logFile.write('{},DEBUG   ,{}\n'.format(datetime.now(), strLog))

    def getErrExist(self):
        return self.errorOccured
    
    def openErrlogFile(self):
        subprocess.run('explorer "{}"'.format(self.filePath.replace('/','\\')))
    
    def flush(self):
        if self.forMultiProcess:
            pass
        else:
            if self.logFile != None:
                self.logFile.flush()
    
    def close(self):
        global listenerProcess
        if self.forMultiProcess:
            if listenerProcess != None:
                self.control['processCancel'] = True
                listenerProcess.join(1)
                listenerProcess = None
        else:
            if self.logFile != None:
                self.logFile.close()

