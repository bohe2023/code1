'''
Created on 2021/02/01

@author: N200797
'''
import zlib
import re
import struct

class BLFEtherReader():
    MINIMUM_TS = 86400 #86400は、datetimeが認識可能な最小値
     
    def __init__(self, file, etherAnalyze = True, canAnalyze = True):
        self.dataList = self.blf_unzlib(file)
        self.etherAnalyze = etherAnalyze
        self.canAnalyze = canAnalyze
        
    def __iter__(self):
        bin_data = b''
        
        for data in self.dataList:
            bin_data += data
            
            nextIndex = re.search(b'LOBJ',bin_data)
            if nextIndex != None:
                bin_data = bin_data[nextIndex.span()[0]:]
            else:
                bin_data = b''
                continue
            
            while True:
                if 12 > len(bin_data):
                    break
                obj_size = bin_data[8] + (bin_data[9]<<8) + (bin_data[10]<<16) + (bin_data[11]<<24)
                if obj_size > len(bin_data):
                    break

                mObjectType = bin_data[0x0C] +  (bin_data[0x0D]<<8) +  (bin_data[0x0E]<<16) + (bin_data[0x0F]<<24)
                
                # yield
                if self.etherAnalyze == True and mObjectType == 0x78: # BL_OBJ_TYPE_ETHERNET_FRAME_EX
                    yield self.blf_purse_ethernet(bin_data[:obj_size])
                elif self.etherAnalyze == True and mObjectType == 0x47: # BL_OBJ_TYPE_ETHERNET_FRAME
                    yield self.blf_purse_VBLEthernetFrame(bin_data[:obj_size])
                elif self.canAnalyze == True and (mObjectType == 0x01 or mObjectType == 0x56): # BL_OBJ_TYPE_CAN_MESSAGE or BL_OBJ_TYPE_CAN_MESSAGE2
                    yield self.blf_purse_can(bin_data[:obj_size])
                elif self.canAnalyze == True and (mObjectType == 0x64): # BL_OBJ_TYPE_CAN_FD_MESSAGE
                    yield self.blf_purse_canFD(bin_data[:obj_size])
                elif self.canAnalyze == True and (mObjectType == 0x65): # BL_OBJ_TYPE_CAN_FD_MESSAGE_64
                    yield self.blf_purse_canFD64(bin_data[:obj_size])
                else:
                    pass
    
                if obj_size+8 > len(bin_data):
                    break

                nextIndex = re.search(b'LOBJ',bin_data[obj_size:])
                if nextIndex != None:
                    bin_data = bin_data[obj_size+nextIndex.span()[0]:]
                else:
                    #raise ValueError("Invalid BLF format : LOBJ not found!")
                    bin_data = b''
                    break
        
    def blf_unzlib(self, fileobj):
        blf_data = fileobj.read()
        fileobj.close()
        
        offset = 0
        filesize = len(blf_data)
        decompress_data = []
        
        header_size = (blf_data[5]<<8) + blf_data[4] 
        offset += header_size
    
        while True:
            if offset >= filesize:
                break
            
            obj_size = blf_data[offset+8] + (blf_data[offset+9]<<8) + (blf_data[offset+10]<<16) + (blf_data[offset+11]<<24)
            decompress_data.append(zlib.decompress(blf_data[offset+0x20:offset+obj_size]))
            
            offset += obj_size
            
            if offset+4 >= filesize:
                break;
            
            i = 0
            while True:
                if b'LOBJ' == blf_data[offset+i:offset+i+4]:
                    offset += i
                    break
                elif i >= 4:
                    raise ValueError("Invalid BLF format : LOBJ not found!")
                else:
                    i += 1
            
        return decompress_data
    
    def blf_purse_Header(self, data):
        headerSize = data[4] + (data[5]<<8)
        #headerVersion = data[6] + (data[7]<<8)
        mObjectFlags = data[16] + (data[17]<<8) + (data[18]<<16) + (data[19]<<24)
        if mObjectFlags == 1:
            rate = 0.00001
        elif mObjectFlags == 2:
            rate = 0.000000001
        mObjectTimeStamp_lo = data[24] + (data[25]<<8) + (data[26]<<16) + (data[27]<<24)
        mObjectTimeStamp_hi = data[28] + (data[29]<<8) + (data[30]<<16) + (data[31]<<24)
        mObjectTimeStamp = (mObjectTimeStamp_hi << 32 | mObjectTimeStamp_lo)
        return (mObjectTimeStamp*rate + BLFEtherReader.MINIMUM_TS, data[headerSize:])
    
    def blf_purse_can(self, data):
        (ts, data) = self.blf_purse_Header(data)
        mChannel = data[0] + (data[1]<<8)
        #mFlag = data[2]
        mDlc = data[3]
        mID = data[4] + (data[5]<<8) + (data[6]<<16) + (data[7]<<24)
        mData = data[8:16]
        return (ts, 
                b'\xFF\x0C\xAF\x00' + #Return Format
                struct.pack('>H', mChannel) + #Chanel
                struct.pack('>H', mDlc) +  #Data Length
                struct.pack('>I', mID) + #ID
                struct.pack('>Q', int((ts-BLFEtherReader.MINIMUM_TS)*1000000)) + #timestamp
                mData) #Data
    
    def blf_purse_canFD(self, data):
        (ts, data) = self.blf_purse_Header(data)
        mChannel = data[0]
        mDlc = data[3]
        if mDlc <= 8: mDlc = mDlc
        elif mDlc == 9: mDlc = 12
        elif mDlc == 10: mDlc = 16
        elif mDlc == 11: mDlc = 20
        elif mDlc == 12: mDlc = 24
        elif mDlc == 13: mDlc = 32
        elif mDlc == 14: mDlc = 48
        elif mDlc == 15: mDlc = 64
        mID = data[4] + (data[5]<<8) + (data[6]<<16) + (data[7]<<24)
        mData = data[20:20+mDlc]
        return (ts, 
                b'\xFF\x0C\xAF\x00' + #Return Format
                struct.pack('>H', mChannel) + #Chanel
                struct.pack('>H', mDlc) +  #Data Length
                struct.pack('>I', mID) + #ID
                struct.pack('>Q', int((ts-BLFEtherReader.MINIMUM_TS)*1000000)) + #timestamp
                mData) #Data
    
    def blf_purse_canFD64(self, data):
        (ts, data) = self.blf_purse_Header(data)
        mChannel = data[0]
        mDlc = data[1]
        if mDlc <= 8: mDlc = mDlc
        elif mDlc == 9: mDlc = 12
        elif mDlc == 10: mDlc = 16
        elif mDlc == 11: mDlc = 20
        elif mDlc == 12: mDlc = 24
        elif mDlc == 13: mDlc = 32
        elif mDlc == 14: mDlc = 48
        elif mDlc == 15: mDlc = 64
        #mValidDataBytes = data[2]
        mID = data[4] + (data[5]<<8) + (data[6]<<16) + (data[7]<<24)
        mData = data[40:40+mDlc]
        return (ts, 
                b'\xFF\x0C\xAF\x00' + #Return Format
                struct.pack('>H', mChannel) + #Chanel
                struct.pack('>H', mDlc) +  #Data Length
                struct.pack('>I', mID) + #ID
                struct.pack('>Q', int((ts-BLFEtherReader.MINIMUM_TS)*1000000)) + #timestamp
                mData) #Data
    
    def blf_purse_ethernet(self, data):
        (ts, data) = self.blf_purse_Header(data)
        mFramelength = data[22] + (data[23]<<8)
        mData = data[32:32+mFramelength]
        return (ts, mData)
    
    def blf_purse_VBLEthernetFrame(self, data):
        (ts, data) = self.blf_purse_Header(data)
        # make ethernet header
        srcMac = data[0:6]
        #channel = data[6:8]
        dstMac = data[8:14]
        #mDir = data[14:16]
        etherHead = bytearray()
        etherHead.append(data[19])
        etherHead.append(data[18])
        etherHead.append(data[21])
        etherHead.append(data[20])
        etherHead.append(data[17])
        etherHead.append(data[16])
        payload = data[32:]
        return (ts, dstMac + srcMac + etherHead + payload)
    