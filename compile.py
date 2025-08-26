import py_compile
import os

path = os.path.abspath(__file__)
path = path[:path.rfind('\\')+1]
py_compile.compile(path + 'QgisADASIS_Process.py')
py_compile.compile(path + 'Logger.py')
py_compile.compile(path + 'GlobalVar.py')
py_compile.compile(path + 'MessageType.py')
py_compile.compile(path + 'ProfileType.py')
py_compile.compile(path + 'TypeDef.py')
py_compile.compile(path + 'PCAPLoader.py')
py_compile.compile(path + 'ACSCanReader.py')
py_compile.compile(path + 'ADASISinfoManager.py')
py_compile.compile(path + 'BLF_Eethernet.py')
py_compile.compile(path + 'shapefile.py')
py_compile.compile(path + 'LayerManager.py')
py_compile.compile(path + 'ControlPanel.py')
py_compile.compile(path + 'ExcelFileCtrl.py')
py_compile.compile(path + 'QGISplugin__init__.py')