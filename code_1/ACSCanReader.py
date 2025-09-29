'''
Created on 2021/02/01

@author: N200797
'''
import struct

class ACSCanReader():
    
    #MINIMUM_TS = 0.086400
    MINIMUM_TS = 0.0
    
    def __init__(self, file):
        self.logFile = file
        
    def __iter__(self):
        while True:
            readLine = self.logFile.readline()
            if not readLine:
                break
            
            data = readLine.split()
            try:
                time = float(data[0]) + ACSCanReader.MINIMUM_TS # sec
                if data[1] == 'CANFD':
                    yield self.acs_purse_canFD(data[2:], time)
                elif data[1] == 'ETH':
                    continue
                elif data[1] == 'CAN':
                    yield self.acs_purse_can(data[2:], time)
                elif data[1].isdigit():
                    yield self.acs_purse_can(data[1:], time)
                else:
                    continue
            except:
                continue    
    
    def acs_purse_can(self, data, ts):
        mChannel = int(data[0])
        mID = int(data[1], 16)
        #rxtx = data[2]
        #d = data[3]
        mDlc = int(data[4])
        mData = bytearray([int(x,16) for x in data[5:5+mDlc]])
        return (ts, 
                b'\xFF\x0C\xAF\x00' + #Return Format
                struct.pack('>H', mChannel) + #Chanel
                struct.pack('>H', mDlc) +  #Data Length
                struct.pack('>I', mID) + #ID
                struct.pack('>Q', int(ts*1000000)) + #timestamp
                mData) #Data
        
    def acs_purse_canFD(self, data, ts):
        mChannel = int(data[0])
        #rxtx = data[1]
        mID = int(data[2], 16)
        #1 = data[3]
        #0 = data[4]
        #dlc = data[5]
        mLength = int(data[6])
        mData = bytearray([int(x,16) for x in data[7:7+mLength]])
        return (ts, 
                b'\xFF\x0C\xAF\x00' + #Return Format
                struct.pack('>H', mChannel) + #Chanel
                struct.pack('>H', mLength) +  #Data Length
                struct.pack('>I', mID) + #ID
                struct.pack('>Q', int(ts*1000000)) + #timestamp
                mData) #Data
        