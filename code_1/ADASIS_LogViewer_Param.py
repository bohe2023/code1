#import sys
#sys.path.append('C:/Programs/...')  # ADASIS_LogViewerが見つからないエラーが出る場合は、直接これでパスを追加してください。
from datetime import datetime

class Structure:
    pass
def getParam():
    param = Structure()
        
    #######################################################################################
    ##                            Setting                                                ##
    #######################################################################################
    
    # モード選択。　1：ログファイル描画モード、　2：リアルタイム走行描画モード、3:GNSS誤差解析
    param.mode = 1
    
    # ーーーーー＜モード１の場合＞ーーーーー    
    # 描画するログファイル指定。　Noneの場合は、FileOpenダイアログでファイル選択可能。    
    #param.logFile = None
    # Ex> logFile = 'C:/Users/AD2Gen2-19/Desktop/2020-08-26_14-02-22_L002.pcapng'
    
    # 描画区間を指定。指定はdatetimeを使い[年月日時分秒]指定、もしくは、logIndex番号で指定可能。　Noneの場合は、全体区間を描画。
    # 時間はUTC時間で入力してください。（ex> 日本時間 - 9時間）
    #param.startPoint = None
    #param.endPoint = None
    # Ex> startPoint = 500000
    # Ex> startPoint = datetime(2020, 11, 25, 14, 23, 0) #年月日時分秒
    # Ex> endPoint = datetime(2020, 8, 6, 11, 21, 0) #年月日時分秒
    
    #推奨レーンは、更新されていく情報だが、過去の描画内容を消さず、残しておくかどうかを指定できます。残しておく場合は False を指定してください。
    #realTimeViewの場合は、常にTrueとして動作します。
    #param.recommendLaneLayerRedraw = True
    
    #ADASISメッセージ解析を行うかを選択します（CNAメッセージもあればその解析も行います）
    param.ADASISanalyze = False
    
    #DebugEtherAnalyzeを行うかを選択します。解析する場合、ログ読み込みにさらに時間がかかります。
    param.DebugEtherAnalyze = False
    
    #REDRanalyzeを行うかを選択します。解析する場合、ログ読み込みにさらに時間がかかります。
    param.REDRanalyze = True
    
    # ーーーーー＜モード２の場合＞ーーーーー
    # パケットキャプチャInterfaceを指定
    param.interfaceName = 'イーサネット'
    # Ex> interfaceName = 'イーサネット'
    
    # ーーーーー＜モード３の場合＞ーーーーー
    # Refファイルを指定しなかった場合、代わりにログデータからRefとして使う位置情報。(LaneProjection : MAPECUのレーン投影位置, ADPosition : ADECUのDR位置, MAPECUGNSS : MAPECUの補正後のGNSS位置)
    # もしくは、特定のfilePathを指定可能
    param.useDefaultRef = 'LaneProjection'
    #param.useDefaultRef = 'C:/Users/N200797/workspace/ADASIS_Data/ref.csv'
    
    # ーーーーー＜共通＞ーーーーー
    #車種を記載。記載なしの場合は、PZ1Aはデフォルト。（ActionFlag表示に使用） (Vehicle Parameterメッセージがある場合、自動検知可能)
    param.vehicle = 'PZ1A'
    #param.vehicle = 'J32V'
    
    # SomeIP込みのパケットかどうかを指定。L53H走行ログの場合は、someIPヘッダなしのため、someipmode = False
    #param.someipmode = True
    
    # 通信パケットの中、特定のデバイスからの送信パケットのみフィルタ可能。初期値(ADAS,HDMAP)のままで良ければ、None。
    #param.filter_srcMAC = None
    # Ex> filter_srcMAC = ["AA:BB:CC:DD:00:06", "AA:BB:CC:DD:10:06", "AA:BB:CC:DD:00:0C"]
    # Ex> filter_srcMAC = ["11:11:11:11:11:11"]
    
    # CAN特定のチャネルのみ解析します。 フィルタしない場合は、Noneか注釈にしてください。
    #param.CAN_chanel_filter = [1, 12]
    
    # Filter Message ID。 特定のメッセージのみ描画し、描画速度を上げる。　（ex: 0x00000501 = GNSSメッセージ）
    #param.MessageID_filter = [0x00000501]
    
    # メッセージフォーマット指定。台帳の変更前の日付を入力。　Noneの場合は、最新仕様で解析。
    #param.ethernetSpecVer = None
    # Ex> ethernetSpecVer = datetime(2020, 12, 25) #(VehicleParameter追加)
    
    # 推奨レーン（IVI/AD/MPU経路）の7km描画のため、事前にHDMAPを読み込ませる。(geojsonもしくは、shpファイル指定可能)
    # 読み込みに数分かかります。
    param.HDMAP_Geojson = None #地図更新検証時は、更新後の地図。通常は現在地図。
    param.HDMAP_Geojson_old = None #地図更新検証時は、更新前の地図。通常は指定不要。
    param.laneIDconvert = False #HDMAPを読み込む際に、北米UshrのHDMAPの場合、lane_number + road_segme でln_idを変換する。
    # Ex> HDMAP_Geojson = 'C:/Users/N200797/workspace/ADASIS_Data/hdmapv3001.geojson'
    # Ex> HDMAP_Geojson = 'C:/Users/AD2Gen2-19/Desktop/work/QGIS/HDMAP v3000 M20/shape/01_HDMAP/40110251_HDMAP.shp'
    
    #描画速度を上げるため、簡略描画を使うかどうかを指定。Noneの場合は：logViewの場合は簡略描画しない、realTimeViewの場合は、簡略描画として動作する
    #param.simpleDrawMode = None
    
    #描画時に解析したメッセージをcsvファイルとして出力するなど、デバッグのためのフラグです。
    #param.debugMode = True
    #######################################################################################
    
    return param
    
    

