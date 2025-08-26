echo Y | pyinstaller --clean -n ADASIS_LogAnalyzer main_LogAnalyzer.py --hidden-import=Process,GlobalVar
copy vbaProject.bin dist\ADASIS_LogAnalyzer\vbaProject.bin
echo Y | pyinstaller --clean --noconsole -n ADASIS_RealtimeViewer main_RealtimeViewer.py --paths="C:/Users/AD2Gen2-19/AppData/Local/Programs/Python/Python38/lib/site-packages/cv2"
echo A | xcopy res dist\ADASIS_RealtimeViewer\res\ /E
echo A | copy lib\*.* dist\ADASIS_RealtimeViewer\
mkdir dist\ADASIS_LogViewer
copy ADASIS_LogViewer_Param.py dist\ADASIS_LogViewer\ADASIS_LogViewer_Param.py
mkdir dist\ADASIS_LogViewer\forQGIS3.00~
mkdir dist\ADASIS_LogViewer\forQGIS3.00~\ADASIS_LogViewer
copy ADASIS_LogViewer.py dist\ADASIS_LogViewer\forQGIS3.00~\ADASIS_LogViewer\ADASIS_LogViewer.py
echo A | xcopy xlsxwriter dist\ADASIS_LogViewer\forQGIS3.00~\xlsxwriter\ /E
echo A | xcopy dpkt dist\ADASIS_LogViewer\forQGIS3.00~\dpkt\ /E
echo A | xcopy scapy dist\ADASIS_LogViewer\forQGIS3.00~\scapy\ /E
mkdir dist\ADASIS_LogViewer\forQGIS3.20~
mkdir dist\ADASIS_LogViewer\forQGIS3.20~\ADASIS_LogViewer
copy ADASIS_LogViewer.py dist\ADASIS_LogViewer\forQGIS3.20~\ADASIS_LogViewer\ADASIS_LogViewer.py
echo A | xcopy xlsxwriter dist\ADASIS_LogViewer\forQGIS3.20~\xlsxwriter\ /E
echo A | xcopy dpkt dist\ADASIS_LogViewer\forQGIS3.20~\dpkt\ /E
echo A | xcopy scapy dist\ADASIS_LogViewer\forQGIS3.20~\scapy\ /E
build_onlyViewer_compile
