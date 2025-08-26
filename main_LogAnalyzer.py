from multiprocessing import freeze_support, Lock
from GlobalVar import setResource, setProgramDir, setSomeIPHead
from Process import logFileAnalyze, showGUI
import sys
from os import listdir, getcwd
from os.path import isfile, join
ANALYZER_VERSION = '2.78'

#-----------------------------------------------#
#----   Main                                ----#
#-----------------------------------------------#
if __name__ == '__main__':    
    freeze_support() # for multiprocess with pyinstaller
    resource = {}
    resource['mutex'] = Lock()
    setResource(resource) #変数共有のため
    setProgramDir(getcwd())
    
    targetFolder = None
    targetFileList = None
    targetMessageID = None
    outputFolder = None
    try:
        for argIndex in range(1,len(sys.argv),2):
            if argIndex+1 >= len(sys.argv):
                print('Invalid argment')
                sys.exit()
                
            command = sys.argv[argIndex]
            param = sys.argv[argIndex+1]
            if command == '-d':
                targetFolder = param.strip()
                if targetFolder[-1] != '\\':
                    targetFolder += '\\'
            elif command == '-f':
                targetFileList = [x.strip() for x in param.split(',')]
                pass
            elif command == '-t':
                targetMessageID = [int(x,16) for x in param.split(',')]
                pass
            elif command == '-o':
                outputFolder = param.strip()
                if outputFolder[-1] != '\\':
                    outputFolder += '\\'
            elif command == '-someip':
                setSomeIPHead(int(param))
            else:
                print('Invalid argment')
                sys.exit()
        
        if targetFolder != None:
            if targetFileList == None:
                targetFileList = [f for f in listdir(targetFolder) 
                                 if isfile(join(targetFolder, f)) and 
                                 (f.endswith('.pcap') or f.endswith('.pcapng') or f.endswith('.blf') or  f.endswith('.asc'))]
            
            for i in range(len(targetFileList)):
                targetFileList[i] = targetFolder + targetFileList[i]
        
    except:
        sys.exit()
    
    showGUI('  v {0}  '.format(ANALYZER_VERSION))
    logFileAnalyze(targetFileList, targetMessageID, outputFolder)
    print("All complete. It is OK to close.")
    sys.exit()
