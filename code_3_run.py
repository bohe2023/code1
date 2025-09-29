import os, glob, math, ast, traceback
import pandas as pd

# ===== 固定値定義 =====
profileIdDic = {
    0x1000:{'name':'レーンリンク情報','class':'PROFILETYPE_MPU_ZGM_LANE_LINK_INFO'},
    0x1001:{'name':'区画線情報','class':'PROFILETYPE_MPU_ZGM_LANE_DIVISION_LINE'},
    0x1002:{'name':'線形状情報','class':'PROFILETYPE_MPU_LINE_GEOMETRY'},
    0x1003:{'name':'破線ペイント情報','class':'DotLinePaintInfoProfile'},
    0x1004:{'name':'信号機情報','class':'PROFILETYPE_MPU_ZGM_TRAFFIC_LIGHT'},
    0x1005:{'name':'道路標示','class':'PROFILETYPE_MPU_ZGM_TRAFFIC_PAINT'},
    0x1006:{'name':'標識情報','class':'PROFILETYPE_MPU_ZGM_SIGN_INFO'},
    0x1007:{'name':'停止線','class':'PROFILETYPE_MPU_ZGM_STOP_LINE'},
    0x1008:{'name':'曲率情報','class':'PROFILETYPE_MPU_ZGM_CURVATURE'},
    0x1009:{'name':'勾配情報','class':'PROFILETYPE_MPU_ZGM_SLOPE'},
    0x100A:{'name':'路肩幅員','class':'PROFILETYPE_MPU_ZGM_SHOULDER_WIDTH'},
    0x100B:{'name':'LanesGeometry','class':'LanesGeometryProfile'},
    0x100C:{'name':'TRANSFER_STS','class':'PROFILE_MPU_MAP_DATA_TRANSFER_STS'},
    0x100D:{'name':'BASE_POINT','class':'PROFILE_MPU_MAP_DATA_BASE_POINT'},
    0x100E:{'name':'不足データチェック用リスト情報','class':'PROFILE_MPU_MAP_ID_LIST'},
    0x1011:{'name':'IVI Stub Info','class':'IVIStubInfoProfile'},
    0x2000:{'name':'自車位置情報','class':'AbsoluteVehiclePositionProfile'},
    0x3000:{'name':'レーンリンク情報(US)','class':'PROFILETYPE_MPU_US_LANE_LINK_INFO'},
    0x3001:{'name':'Lane Line情報(US)','class':'PROFILETYPE_MPU_US_LANE_LINE'},
    0x3002:{'name':'Lane Line形状情報(US)','class':'PROFILETYPE_MPU_US_LANE_LINE_GEOMETRY'},
    0x3003:{'name':'Road Edge情報(US)','class':'PROFILETYPE_MPU_US_ROAD_EDGE'},
    0x3004:{'name':'Road Edge形状情報(US)','class':'PROFILETYPE_MPU_US_ROAD_EDGE_GEOMETRY'},
    0x3005:{'name':'信号機情報(US)','class':'PROFILETYPE_MPU_US_REGULATORY_TRRAFIC_DEVICE'},
    0x3006:{'name':'道路標示(US)','class':'PROFILETYPE_MPU_US_PAVEMENT_MARKING'},
    0x3007:{'name':'標識情報(US)','class':'PROFILETYPE_MPU_US_SIGN'},
    0x3008:{'name':'曲率情報(US)','class':'PROFILETYPE_MPU_US_CURVATURE'},
    0x3009:{'name':'勾配情報(US)','class':'PROFILETYPE_MPU_US_SLOPE'},
    0x300A:{'name':'レーン幅員(US)','class':'PROFILETYPE_MPU_US_LANE_WIDTH'},
    0x300B:{'name':'LanesGeometry(US)','class':'LanesGeometryProfile_US'},
    0x300C:{'name':'TRANSFER_STS(US)','class':'PROFILE_MPU_MAP_DATA_TRANSFER_STS'},
    0x300D:{'name':'BASE_POINT(US)','class':'PROFILE_MPU_MAP_DATA_BASE_POINT'},
    0x300E:{'name':'不足データチェック用リスト情報(US)','class':'PROFILE_MPU_MAP_ID_LIST'},
    0x300F:{'name':'IVI Stub Info(US)','class':'IVIStubInfoProfile'}
}

SDLinkageString = {0x0000:'有効', 0x8000:'無効'}
PROFILE_MPU_MAP_ID_LIST_classifyDic = {0x00:'無効値', 0x01:'周辺情報　(MPU経路)', 0x02:'周辺情報  (ADECU経路)', 0x03:'周辺情報（SDMAP/MPU経路）', 0x04:'周辺情報（SDMAP/ADECU経路）'}
AbsoluteVehiclePositionProfile_classifyDic = {0x00:'MPU', 0x01:'AD'}
PROFILE_MPU_MAP_DATA_TRANSFER_STS_classifyDic = {0x00:'無効値', 0x01:'周辺情報　(MPU経路)', 0x02:'周辺情報  (ADECU経路)', 0x03:'経路情報（IVI経路）', 0x04:'経路情報（MPU経路）', 0x05:'経路情報（ADECU経路）', 0x06:'周辺情報（SDMAP:MPU経路)', 0x07:'周辺情報（SDMAP:ADECU経路)'}
PROFILE_MPU_MAP_DATA_TRANSFER_STS_startEndflagDic = {0x00:'無効値', 0x01:'データ送信開始', 0x02:'データ送信完了'}
PROFILE_MPU_MAP_DATA_TRANSFER_STS_initFlagDic = {0x00:'初期化を実施しない', 0x01:'初期化を実施する'}
PROFILE_MPU_MAP_DATA_TRANSFER_STS_outputClassifyDic = {0x01:{0x00:'通常出力', 0x01:'全出力', 0x02:'差分出力(再送)'}, 0x02:{0x00:'未完了', 0x01:'完了'}}

RouteChangeStatusString = {0:'変換成功',1:'変換不可（対応する地図が無い）',2:'変換不可（変換候補の評価値が低い）',3:'変換不可（隣のLRPまでの距離が離れすぎている）',4:'変換不可（隣のLRPに接続できるレーンが無い）',5:'変換不可（IVI経路情報異常）',6:'変換不可（その他）'}
RoadTypeString = {0:'(0) Controlled Access Divided',1:'(1) Non-Controlled Access Divided',2:'(2) Interchange',3:'(3) Ramp',4:'(4) Controlled Access Non-Divided',5:'(5) Non-Controlled Access Non-Divided',6:'(6) Local Divided',7:'(7) Local Non-Divided'}
LaneTypeString = {1:'(1) Normal Driving Lane',2:'(2) HOV Lane',4:'(4) Bidirectional Lane',8:'(8) Bus/Taxi Lane',16:'(16) Toll Booth Lane',32:'(32) Convertible To Shoulder ',64:'(64) Turn Only Lane',128:'(128) Other'}

# JP/US の LaneLineType 定義（JP/US でキーが衝突するので別名で持つ）
LaneLineTypeDic_JP = {
    0:'(0)線無し',1:'(1)単線-白実線',2:'(2)単線-白破線(細)',3:'(3)単線-白破線(太)',4:'(4)黄実線',
    11:'(11)二重線(同種)-白実線',22:'(22)二重線(同種)-白破線(細)',44:'(44)二重線(同種)-黄実線',
    12:'(12)二重線(別種)-白実線×白破線(細)',21:'(21)二重線(別種)-白破線(細)×白実線',
    14:'(14)二重線(別種)-白実線×黄実線',41:'(41)二重線(別種)-黄実線×白実線',
    24:'(24)二重線(別種)-白破線(細)×黄実線',42:'(42)二重線-黄実線×白破線(細)',
    414:'(414)三重線-黄実線×白実線×黄実線',424:'(424)三重線-黄実線×白破線(細)×黄実線',
    4114:'(4114)四重線-黄実線×白実線×白実線×黄実線'
}
LaneLineTypeDic_US = {
    0:'(0)Virtual',1:'(1)Single Solid Paint Line',2:'(2)Single Dashed Paint Line',
    3:'(3)Double Paint Line, Left Solid, Right Solid',4:'(4)Double Paint Line, Left Dashed, Right Solid',
    5:'(5)Double Paint Line, Left Solid, Right Dashed',6:'(6)Double Paint Line, Left Dashed, Right Dashed',
    7:'(7)Triple Paint Line All Solid',8:'(8)Other'
}

# 入力CSVの列名
prf_col = ["logTime","logTime_dup","ΔlogTime[ms]","length","timeStamp[s]","ΔtimeStamp[ms]","seq","ID","msgcnt","Δmsgcnt",
           "LaneID","分割数","分割番号","Number of Array","Instance ID","Is Retransmission","Is Update","Path Id",
           "Offset[cm]","End Offset[cm]","End Offset Final","Confidence[%]","Standard Deviation","Lane Number",
           "Profile Type","Available","Profile Value","Profile_info_0","Profile_info_1","Profile_info_2"]

message_file_name = "Profile Message"  # 这里必须和实际文件名匹配

# ===== 共通関数 =====
def interpolation(s):
    if s is not None and not str(s).startswith("="):
        return s
    return None

def str_to_dict(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, (dict, list)):
        return x
    if not isinstance(x, str):
        x = str(x)
        if x == 'nan':
            return None
    if not x.strip():
        return None
    if ':' not in x:
        return x
    try:
        return ast.literal_eval(x)
    except Exception as e:
        print(f"[literal_eval error] {e}\n data: {repr(x)}")
        print(traceback.format_exc())
        return x

def partial_quote_strings_from_dict_loop(df, col_name, definition_dict):
    sorted_values = sorted(definition_dict.values(), key=len, reverse=True)
    temp_col = df[col_name].astype(str)
    for value in sorted_values:
        temp_col = temp_col.str.replace(value, f"'{value}'", regex=False)
    df[col_name] = temp_col
    return df

def Profile_info_to_dict(df, col, Profile_Type):
    if Profile_Type == "0x100E":
        df = partial_quote_strings_from_dict_loop(df, col, PROFILE_MPU_MAP_ID_LIST_classifyDic)
    elif Profile_Type == "0x2000":
        df = partial_quote_strings_from_dict_loop(df, col, AbsoluteVehiclePositionProfile_classifyDic)
    elif Profile_Type == "0x300C":
        df = partial_quote_strings_from_dict_loop(df, col, PROFILE_MPU_MAP_DATA_TRANSFER_STS_classifyDic)
        df = partial_quote_strings_from_dict_loop(df, col, PROFILE_MPU_MAP_DATA_TRANSFER_STS_startEndflagDic)
        df = partial_quote_strings_from_dict_loop(df, col, PROFILE_MPU_MAP_DATA_TRANSFER_STS_initFlagDic)
        df = partial_quote_strings_from_dict_loop(df, col, PROFILE_MPU_MAP_DATA_TRANSFER_STS_outputClassifyDic)
    elif Profile_Type in ("0x1000", "0x3000"):
        df = partial_quote_strings_from_dict_loop(df, col, SDLinkageString)
        if Profile_Type == "0x3000":
            df = partial_quote_strings_from_dict_loop(df, col, RouteChangeStatusString)
            df = partial_quote_strings_from_dict_loop(df, col, RoadTypeString)
            df = partial_quote_strings_from_dict_loop(df, col, LaneTypeString)

    df[col]=df[col].str.replace("*","", regex=False)
    df[col]=df[col].str.replace("   ","", regex=False)
    df[col]=df[col].str.replace("\n$","", regex=True)
    df[col]=df[col].str.replace("\n",",'", regex=True)
    df[col]=df[col].str.replace(":", "':", regex=False)
    df[col]=df[col].str.replace("\[error\]","'\\[error\\]'", regex=True)
    df[col]=df[col].str.replace("Unknown","'Unknown'", regex=False)
    df[col]=df[col].str.replace("軽度","経度", regex=False)
    df[col]=df[col].str.replace("座業","座標", regex=False)

    df[col] = "{'" + df[col] + "}"
    df[col] = df[col].apply(str_to_dict)
    return df

def extract_dict_columns(df, dict_col_name):
    if dict_col_name not in df.columns:
        print(f"[warn] column not found: {dict_col_name}")
        return df
    normalized_df = pd.json_normalize(df[dict_col_name], errors='ignore')
    result_df = pd.concat([df, normalized_df], axis=1)
    return result_df

def Profile_info_to_df(df, Profile_Type):
    df_columns = df.columns.tolist()
    profile_columns = ["Profile_info_0","Profile_info_1","Profile_info_2"]
    non_profile_columns = list(set(df.columns.tolist()) - set(profile_columns))

    df = df.applymap(interpolation)
    df[non_profile_columns]=df[non_profile_columns].fillna(method='ffill')
    df = df.dropna(subset=profile_columns, how='all')

    df = df[df["Profile Type"]==Profile_Type].reset_index(drop=True)

    for c in profile_columns:
        df = Profile_info_to_dict(df, c, Profile_Type)

    df = extract_dict_columns(df, "Profile_info_0")
    Profile_info_0_cols = list(set(df.columns.tolist()) - set(df_columns))
    df[Profile_info_0_cols] = df[Profile_info_0_cols].fillna(method='ffill')

    df = extract_dict_columns(df, "Profile_info_1")
    Profile_info_1_cols = list(set(df.columns.tolist()) - set(df_columns) - set(Profile_info_0_cols))

    df = extract_dict_columns(df, "Profile_info_2")
    Profile_info_2_cols = list(set(df.columns.tolist()) - set(df_columns) - set(Profile_info_0_cols) - set(Profile_info_1_cols))

    subset_columns = Profile_info_0_cols
    if len(Profile_info_1_cols)>0:
        subset_columns = Profile_info_1_cols
    if len(Profile_info_2_cols)>0:
        subset_columns = Profile_info_2_cols
        df[Profile_info_1_cols] = df[Profile_info_1_cols].fillna(method='ffill')

    df = df.dropna(subset=subset_columns, how='all')

    output_columns = [x for x in df.columns.tolist() if x not in ["Profile Type","Profile Value","Profile_info_0","Profile_info_1","Profile_info_2"]]
    df = df[output_columns]
    return df

# ====== 入力ディレクトリ設定 ======
# !!! Windows の場合: r"E:\xtech\AD2\JPN\output" のようにドライブレターで書くこと（/mnt/e/... は WSL 用）
csv_save_path = r"D:\test\code_1\outputs\J42U_JPN_AD1Next_V001_01ALL_20250131_040542_130"   # ← ここを実パスに
# csv_save_path = r"E:\xtech\AD2\US\output"  # US データの時はこちら
message_file_name = "Profile Message"

def main():
    pattern = os.path.join(csv_save_path, "**", f"{message_file_name}.csv")
    prf_csv_list = sorted(glob.glob(pattern, recursive=True))
    print(f"[info] found {len(prf_csv_list)} files:")
    for p in prf_csv_list:
        print("  -", p)
    if not prf_csv_list:
        print("[ERROR] Profile Message.csv が見つかりません。csv_save_path / ファイル名 を確認してください。")
        return
    for prf_csv in prf_csv_list:
        print(f"\n[processing] {prf_csv}")
        df_prf = pd.read_csv(
            prf_csv, header=None, skiprows=[0,1], names=prf_col,
            usecols=["logTime",'Instance ID','Is Retransmission','Path Id','Offset[cm]','End Offset[cm]',
                     'Lane Number','Profile Type','Profile Value',"Profile_info_0","Profile_info_1","Profile_info_2"],
            encoding="shift_jis", dtype="object", engine='python'
        )
        Profile_Types = df_prf["Profile Type"].apply(interpolation).dropna().unique().tolist()
        for Profile_Type in Profile_Types:
            try:
                table_name = profileIdDic[int(Profile_Type, 16)]['class']
            except Exception:
                print(f"[warn] 未定義の Profile Type: {Profile_Type}")
                continue
            print("  ->", table_name)
            df_out = Profile_info_to_df(df_prf.copy(), Profile_Type).convert_dtypes()
            directory, _ = os.path.split(prf_csv)
            output_directory = os.path.join(directory, message_file_name)
            os.makedirs(output_directory, exist_ok=True)
            out_csv = os.path.join(output_directory, f"{table_name}.csv")
            df_out.to_csv(out_csv, index=False, encoding="cp932")
            print(f"     saved: {out_csv} (rows={len(df_out)})")

if __name__ == "__main__":
    main()
