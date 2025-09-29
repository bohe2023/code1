import xlsxwriter
from xlsxwriter.worksheet import Worksheet
from xlsxwriter.format import Format
import csv
from GlobalVar import getProgramDir
import io # <-- ioライブラリをインポート
class MyWorkSheet(Worksheet):
    def __init__(self):
        super().__init__()
        self.useMultiLine = False
        self.useMacro = False
        self.onlyOutputCSV = False
        
    def init(self, name, workbook, useMultiLine, useMacro, outputCSV):
        self.useMultiLine = useMultiLine
        self.useMacro = useMacro
        if outputCSV == True:
            self.csvfile = open(name + '.csv', 'w', newline='')
            self.csvSheet = csv.writer(self.csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        else:
            self.csvSheet = None
        self.csvSheetRowBuffer = []
        self.csvSheetLastRowIndex = 0
        
        # Add a general format
        self.formatDic = {}
        if (workbook != None):
            self.formatDic['merge'] = workbook.add_format({
                'bold': 1,
                'align': 'left',
                'valign': 'top'})
            
            self.formatDic['default'] = workbook.add_format({
                'align': 'left',
                'valign': 'top'})
            
            self.formatDic['header'] = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#D7E4BC',
                'border': 1,
                'text_wrap': True})
        
            self.formatDic['bold'] = workbook.add_format({'bold': True})
            self.formatDic['italic'] = workbook.add_format({'italic': True})
            self.formatDic['red'] = workbook.add_format({'bold': True,'color': 'red'})
            self.formatDic['blue'] = workbook.add_format({'bold': True,'color': 'blue'})
        #     self.formatDic['unlock'] = workbook.add_format({'locked': False})
        #     self.formatDic['wrap'] = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            self.formatDic['wrap'] = workbook.add_format({})
        
    def initAsOnlyCSVmode(self, name):
        self.init(name, None, False, False, True)
        self.onlyOutputCSV = True
    
    def write(self, row, col, *args):
        if self.onlyOutputCSV == False: super().write(row, col, *args)
        if self.csvSheet != None:
            if self.csvSheetLastRowIndex != row:
                self.csvSheet.writerow(self.csvSheetRowBuffer)
                self.csvSheetLastRowIndex = row
                self.csvSheetRowBuffer = []
            while len(self.csvSheetRowBuffer) < col + 1:
                self.csvSheetRowBuffer.append('')
            content = ''
            for val in list(args):
                if not isinstance(val, Format) and val != None:
                    content += val
            self.csvSheetRowBuffer[col] = content
    
    def write_row(self, row, col, valArray, cell_format=None):
        if self.onlyOutputCSV == False: super().write_row(row, col, valArray, cell_format)
        if self.csvSheet != None:
            if self.csvSheetLastRowIndex != row:
                self.csvSheet.writerow(self.csvSheetRowBuffer)
                self.csvSheetLastRowIndex = row
                self.csvSheetRowBuffer = []
            while len(self.csvSheetRowBuffer) < col + len(valArray):
                self.csvSheetRowBuffer.append('')
            for i in range(len(valArray)):
                self.csvSheetRowBuffer[col+i] = valArray[i]

    def write_rich_string(self, row, col, *args):
        if self.onlyOutputCSV == False: super().write_rich_string(row, col, *args)
        if self.csvSheet != None:
            if self.csvSheetLastRowIndex != row:
                self.csvSheet.writerow(self.csvSheetRowBuffer)
                self.csvSheetLastRowIndex = row
                self.csvSheetRowBuffer = []
            while len(self.csvSheetRowBuffer) < col + 1:
                self.csvSheetRowBuffer.append('')
            content = ''
            for val in list(args):
                if not isinstance(val, Format) and val != None:
                    content += val
            self.csvSheetRowBuffer[col] = content
            
    def write_number(self, row, col, val, cell_format=None):
        if self.onlyOutputCSV == False: super().write_number(row, col, val, cell_format)
        if self.csvSheet != None:
            if self.csvSheetLastRowIndex != row:
                self.csvSheet.writerow(self.csvSheetRowBuffer)
                self.csvSheetLastRowIndex = row
                self.csvSheetRowBuffer = []
            while len(self.csvSheetRowBuffer) < col + 1:
                self.csvSheetRowBuffer.append('')
            self.csvSheetRowBuffer[col] = val
            
    def close(self):
        if self.csvSheet != None:
            if len(self.csvSheetRowBuffer) > 0:
                self.csvSheet.writerow(self.csvSheetRowBuffer)
            self.csvfile.close()

    def cellFormats(self, name):
        if name in self.formatDic:
            return self.formatDic[name]
        elif 'default' in self.formatDic:
            return self.formatDic['default']
        else:
            return None

def openExcelFile(fileName, useMultiLine = False, useMacro = False, outputOnlyCSV = False):
    if useMacro == True:
        fileType = ".xlsm"
    else:
        fileType = ".xlsx"

    # まず基本となるオプションを定義
    options = {"nan_inf_to_errors": True}
    
    if outputOnlyCSV:
        # CSVのみ出力する場合
        output_target = io.BytesIO()
        options['constant_memory'] = True # 省メモリモード
    else:
        # 通常通りファイルに出力する場合
        output_target = fileName + fileType
        if useMultiLine == False:
            options['constant_memory'] = True # 省メモリモード
            
    # 決定した出力先とオプションでWorkbookを作成
    workbook = xlsxwriter.Workbook(output_target, options)

    # if useMultiLine == True:
    #     workbook = xlsxwriter.Workbook(fileName + fileType, {"nan_inf_to_errors": True})
    # else:
    #     workbook = xlsxwriter.Workbook(fileName + fileType, {"nan_inf_to_errors": True, 'constant_memory': True})
        
    if useMacro == True:
        workbook.add_vba_project(getProgramDir() + '\\vbaProject.bin')
           
    workbook.use_zip64()

    return workbook

def getColumnName(col):
    return getCellName(-1, col)

def getCellName(row, col):
    if row == -1:
        if col < 26:
            return chr(col + 65)
        else:
            return chr(int(col/26)-1 + 65) + chr((col%26) + 65)
    else:
        if col < 26:
            return chr(col + 65) + str(row+1)
        else:
            return chr(int(col/26)-1 + 65) + chr((col%26) + 65) + str(row+1)

def merge_rows(sheet, row, col, count, duplicationCheck = False):
    flag = True
    if count > 1:
        if duplicationCheck == True:
            if [row, col, row+count-1, col] in sheet.merge: 
                flag = False
        if flag == True:
            for r in range(row+1,row+count):
                sheet.write(r, col, '=' + getCellName(row,col)) #for Filterling
            sheet.merge.append([row, col, row+count-1, col])
    
def merge_cols(sheet, row, col, count, duplicationCheck = False):
    flag = True
    if count > 1:
        if duplicationCheck == True:
            if [row, col, row, col+count-1] in sheet.merge: 
                flag = False
        if flag == True:
            sheet.merge.append([row, col, row, col+count-1])

def rowGroupingPrint(name, obj, printF, sheet, row, col, level):
    sheet.write(row, col, name, sheet.cellFormats('merge'))
    if obj == None:
        [afterRow, _, groupResult] = printF(sheet, row, col + 1, level + 1)
    else:
        [afterRow, _, groupResult] = printF(obj, sheet, row, col + 1, level + 1)
    if afterRow > row + 1:
        afterRow += 1
        merge_rows(sheet, row, col, afterRow - row)
        for r in range(row, afterRow-1):
            if not(r in groupResult):
                sheet.set_row(r, None, None, {'level': level, 'hidden': True, 'collapsed': True})
                groupResult += [r]
        
    return [afterRow, col, groupResult]

def colGroupingPrint(name, obj, printF, sheet, row, col, level):
    if obj == None:
        [_, afterCol, groupResult] = printF(sheet, row, col, level + 1)
    else:
        [_, afterCol, groupResult] = printF(obj, sheet, row, col, level + 1)
    sheet.write(row, afterCol, name, sheet.cellFormats('merge'))
    afterCol += 1
    for c in range(col, afterCol-1):
        if not(c in groupResult):
            sheet.set_column(c, c, None, None, {'level': level, 'hidden': True})
            groupResult += [c]
    return [row, afterCol, groupResult]


##---------##
## Example ##
##---------##
# def printLevel1_row(sheet, row, col, level = 1):
#     groupResult = []
#     
#     sheet.write(row, col+0, '1', default_format)
#     sheet.write(row, col+1, '2', default_format)
#     sheet.write(row, col+2, '3', default_format)
#         
#     [currentRow, _, result] = rowGroupingPrint('Data1', printLevel2_row, sheet, row, col + 3, level)
#     groupResult += result
#     
#     [currentRow, _, result] = rowGroupingPrint('Data2', printLevel2_row, sheet, currentRow, col + 3, level)
#     groupResult += result  
#     
#     for c in range(3):
#         merge_rows(sheet, row, currentRow-1, c)
#     
#     return [currentRow, 0, groupResult]
#     
# def printLevel2_row(sheet, row, col, level = 1):
#     groupResult = []
#     
#     sheet.write(row+0, col, 'x = 78')   
#     sheet.write(row+1, col, 'y = 234')
#     sheet.write(row+2, col, 'z = 678')
#     
#     [currentRow, _, result] = rowGroupingPrint('Profile1', printLevel3_row, sheet, row+3, col, level)
#     groupResult += result
#     
#     [currentRow, _, result] = rowGroupingPrint('Profile2', printLevel3_row, sheet, currentRow, col, level)
#     groupResult += result
#     
#     [currentRow, currentCol, result] = rowGroupingPrint('Profile3', printLevel3_row, sheet, currentRow, col, level)
#     groupResult += result
# 
#     return [currentRow, currentCol, groupResult]
# 
# def printLevel3_row(sheet, row, col, _):
#     sheet.write(row+0, col, 'a = 1')   
#     sheet.write(row+1, col, 'b = 1')
#     sheet.write(row+2, col, 'c = 1')
#     return [row+3, col, []]
# 
# 
# def printLevel1_col(sheet, row, col, level = 1):
#     groupResult = []
#     
#     sheet.write(row, col+0, '78')   
#     sheet.write(row, col+1, '234')   
#     sheet.write(row, col+2, '678')
#         
#     [_, currentCol, result] = colGroupingPrint('Data1', printLevel2_col, sheet, row, col+3, level)
#     groupResult += result
#     
#     [currentRow, currentCol, result] = colGroupingPrint('Data2', printLevel2_col, sheet, row, currentCol, level)
#     groupResult += result
#     
#     return [currentRow, currentCol, groupResult]
#     
# def printLevel2_col(sheet, row, col, _):  
#     sheet.write(row, col+0, 'sijef')    
#     sheet.write(row, col+1, '1.567')
#     sheet.write(row, col+2, 'hh')
#     return [row, col+3, []]