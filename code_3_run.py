import os
import glob
import math
import re
import ast
import shutil
import sys
import traceback
from multiprocessing import Lock
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Union

import pandas as pd

HERE = Path(__file__).resolve().parent
CODE1_SRC = HERE / "code_1"
if str(CODE1_SRC) not in sys.path:
    sys.path.insert(0, str(CODE1_SRC))

try:  # Lazy import so the script still works without optional deps.
    from Process import logFileAnalyze  # type: ignore  # pylint: disable=import-error
    PROCESS_IMPORT_ERROR: Optional[Exception] = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    logFileAnalyze = None  # type: ignore[assignment]
    PROCESS_IMPORT_ERROR = exc

from GlobalVar import getResource, setProgramDir, setResource


DEFAULT_PROFILE_ROOT = HERE / "outputs"
DEFAULT_REGION_ROOT = HERE / "cloud_outputs"
DEFAULT_MESSAGE_IDS = (
    0x0000010A,
    0xCAF0054C,
    0xCAF0036D,
    0xCAF00370,
    0xCAF0025E,
    0xCAF0036A,
)

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

# ===== 内部辅助 =====
_RESOURCE_INITIALIZED = False


def _ensure_log_analyzer_resource() -> None:
    """确保 Process.logFileAnalyze 所需的全局资源已经正确初始化。"""

    global _RESOURCE_INITIALIZED
    if _RESOURCE_INITIALIZED:
        return

    resource = getResource()
    if not isinstance(resource, dict):
        resource = {}
    else:
        # Manager().dict() 等对象在子进程中使用时可能会返回代理，拷贝为普通 dict 更安全。
        resource = dict(resource)

    if "mutex" not in resource or resource["mutex"] is None:
        resource["mutex"] = Lock()

    setResource(resource)
    setProgramDir(str(HERE))
    _RESOURCE_INITIALIZED = True

# ===== 共通関数 =====
def interpolation(value):
    """Normalize raw cell values read from the profile CSV.

    The original CSV uses blank cells to indicate that the value should be
    inherited from the previous row.  When ``pandas`` reads the file with
    ``dtype="object"`` these blank cells become empty strings instead of
    ``NaN``.  The later ``ffill`` therefore skipped them which resulted in
    output rows with missing data.  By converting empty strings (and other
    obvious "missing" sentinels) to :data:`None`, the forward fill works in
    the same way as the previous multi-step pipeline.
    """

    if value is None:
        return None

    # ``pandas`` uses special scalar values (``NaN``, ``pd.NA``) to represent
    # missing data.  ``pd.isna`` gracefully handles these as well as ordinary
    # Python ``None``/``float('nan')`` values.
    try:
        if pd.isna(value):
            return None
    except TypeError:
        # Some custom objects are not hashable; fall back to the original
        # value for those cases.
        pass

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.startswith("="):
            return None
        return value

    return value

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
    if Profile_info_0_cols:
        df[Profile_info_0_cols] = df[Profile_info_0_cols].fillna(method='ffill')

    df = extract_dict_columns(df, "Profile_info_1")
    Profile_info_1_cols = list(
        set(df.columns.tolist())
        - set(df_columns)
        - set(Profile_info_0_cols)
    )
    if Profile_info_1_cols:
        df[Profile_info_1_cols] = df[Profile_info_1_cols].fillna(method='ffill')

    df = extract_dict_columns(df, "Profile_info_2")
    Profile_info_2_cols = list(
        set(df.columns.tolist())
        - set(df_columns)
        - set(Profile_info_0_cols)
        - set(Profile_info_1_cols)
    )
    if Profile_info_2_cols:
        df[Profile_info_2_cols] = df[Profile_info_2_cols].fillna(method='ffill')

    subset_columns = list(
        dict.fromkeys(
            Profile_info_0_cols + Profile_info_1_cols + Profile_info_2_cols
        )
    )
    if subset_columns:
        df = df.dropna(subset=subset_columns, how='all')

    output_columns = [x for x in df.columns.tolist() if x not in ["Profile Type","Profile Value","Profile_info_0","Profile_info_1","Profile_info_2"]]
    df = df[output_columns]
    return df

# ====== 入力ディレクトリ設定 ======
csv_save_path = str(DEFAULT_PROFILE_ROOT)
message_file_name = "Profile Message"


def _detect_region(profile_type_value: int) -> str:
    """Return region tag based on profile type value."""
    if 0x3000 <= profile_type_value < 0x4000:
        return "US"
    return "JPN"


StrSequence = Union[Sequence[str], str]
IntSequence = Union[Sequence[int], str]


def _normalise_encodings(encodings: Optional[StrSequence]) -> List[str]:
    if encodings is None:
        candidates: Sequence[str] = (
            "cp932",
            "shift_jis",
            "euc_jp",
            "gbk",
            "utf-8-sig",
            "utf-8",
        )
    elif isinstance(encodings, str):
        candidates = (encodings,)
    else:
        candidates = tuple(enc for enc in encodings if enc)

    # ``dict.fromkeys`` keeps the order of the first occurrence which allows us
    # to keep the user provided priority while removing duplicates.
    normalised = list(dict.fromkeys(candidates))
    if not normalised:
        return ["cp932", "shift_jis", "euc_jp", "gbk", "utf-8-sig", "utf-8"]
    return normalised


def _parse_message_ids(raw_ids: Optional[IntSequence]) -> List[int]:
    if raw_ids is None:
        return list(DEFAULT_MESSAGE_IDS)
    if isinstance(raw_ids, str):
        values: List[int] = []
        for chunk in raw_ids.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            base = 16 if chunk.lower().startswith("0x") else 10
            values.append(int(chunk, base))
        return values

    return [int(v) for v in raw_ids]


def convert_profile_message_file(
    prf_csv_path: os.PathLike,
    *,
    message_name: Optional[str] = None,
    target_root: Optional[os.PathLike] = None,
    output_encoding: str = "cp932",
    input_encodings: Optional[StrSequence] = None,
    use_region_folders: bool = True,
) -> List[Path]:
    """Convert one ``Profile Message.csv`` into detailed tables.

    Parameters
    ----------
    prf_csv_path:
        Path to ``Profile Message.csv``.
    message_name:
        Optional custom message name (defaults to :data:`message_file_name`).
    target_root:
        When provided, the output CSV files are written to one of the
        following locations:

        * ``<target_root>/<region>/<dataset_name>/`` when
          :data:`use_region_folders` is :data:`True`.
        * ``<target_root>/<dataset_name>/<message_name>/`` when
          :data:`use_region_folders` is :data:`False`.

        When omitted, the legacy behaviour is kept and the CSV files are
        stored under ``<profile_dir>/<message_name>/``.
    output_encoding:
        Encoding used when writing CSV files.

    Returns
    -------
    List[Path]
        A list with the generated CSV file paths.
    """

    message = message_name or message_file_name
    prf_path = Path(prf_csv_path)
    encoding_candidates = _normalise_encodings(input_encodings)
    df_prf = None
    used_encoding: Optional[str] = None
    last_error: Optional[UnicodeDecodeError] = None
    for enc in encoding_candidates:
        try:
            df_prf = pd.read_csv(
                prf_path,
                header=None,
                skiprows=[0, 1],
                names=prf_col,
                usecols=[
                    "logTime",
                    "Instance ID",
                    "Is Retransmission",
                    "Path Id",
                    "Offset[cm]",
                    "End Offset[cm]",
                    "Lane Number",
                    "Profile Type",
                    "Profile Value",
                    "Profile_info_0",
                    "Profile_info_1",
                    "Profile_info_2",
                ],
                encoding=enc,
                dtype="object",
                engine="python",
            )
            used_encoding = enc
            print(f"[info] decoded {prf_path} using encoding='{enc}'")
            break
        except UnicodeDecodeError as exc:
            print(f"[warn] failed to decode {prf_path} with encoding='{enc}': {exc}")
            last_error = exc
    if df_prf is None:
        raise UnicodeError(
            f"Failed to decode {prf_path} using encodings: {', '.join(encoding_candidates)}"
        ) from last_error

    assert used_encoding is not None  # For type-checkers

    profile_types = (
        df_prf["Profile Type"].apply(interpolation).dropna().unique().tolist()
    )
    outputs: List[Path] = []

    for profile_type in profile_types:
        try:
            table_name = profileIdDic[int(profile_type, 16)]["class"]
        except Exception:
            print(f"[warn] 未定義の Profile Type: {profile_type}")
            continue

        df_out = Profile_info_to_df(df_prf.copy(), profile_type).convert_dtypes()

        if target_root is None:
            output_directory = prf_path.parent / message
        else:
            dataset_name = prf_path.parent.name
            if use_region_folders:
                region = _detect_region(int(profile_type, 16))
                output_directory = Path(target_root) / region / dataset_name
            else:
                output_directory = Path(target_root) / dataset_name / message

        output_directory.mkdir(parents=True, exist_ok=True)
        out_csv = output_directory / f"{table_name}.csv"
        df_out.to_csv(out_csv, index=False, encoding=output_encoding)
        print(
            f"     saved: {out_csv} (rows={len(df_out)}, region={_detect_region(int(profile_type, 16))})"
        )
        outputs.append(out_csv)

    return outputs


def _iter_blf_files(csv_root: Path) -> Iterable[Path]:
    return (p for p in sorted(csv_root.glob("*.blf")) if p.is_file())


def _normalize_message_name(message: str) -> str:
    """将消息文件名规范化，以便进行宽松匹配。"""

    message = message.strip()
    if message.lower().endswith(".csv"):
        message = message[:-4]
    return "".join(ch for ch in message.lower() if ch.isalnum())


def _tokenize_message_name(message: str) -> List[str]:
    """将消息文件名拆分为更宽松的关键字。"""

    # 与 :func:`_normalize_message_name` 不同，这里保留空格分割的信息以便
    # 进行 "Profile Message" ↔ "PROFILE LONG" 这类弱相关匹配。
    return [
        token
        for token in re.split(r"[^0-9a-z]+", message.lower())
        if token
    ]


def _locate_profile_csv(intermediate_dir: Path, dataset_name: str, message: str) -> Path:
    candidate = intermediate_dir / dataset_name / f"{message}.csv"
    if candidate.exists():
        return candidate

    fallback = intermediate_dir / f"{message}.csv"
    if fallback.exists():
        return fallback

    nested_candidates = [
        intermediate_dir / dataset_name / message / f"{message}.csv",
        intermediate_dir / message / f"{message}.csv",
    ]
    for nested in nested_candidates:
        if nested.exists():
            return nested

    target_key = _normalize_message_name(message)
    exact_matches: List[Path] = []
    suffix_matches: List[Path] = []
    partial_matches: List[Path] = []
    token_matches: List[Path] = []
    discovered: List[Path] = []

    target_tokens = set(_tokenize_message_name(message))
    token_scores: Dict[Path, int] = {}

    for csv_path in intermediate_dir.rglob("*.csv"):
        discovered.append(csv_path)
        stem_key = _normalize_message_name(csv_path.stem)
        if stem_key == target_key:
            exact_matches.append(csv_path)
        elif stem_key.endswith(target_key):
            suffix_matches.append(csv_path)
        elif target_key in stem_key:
            partial_matches.append(csv_path)
        elif target_tokens:
            tokens = set(_tokenize_message_name(csv_path.stem))
            score = len(target_tokens & tokens)
            if score:
                token_scores[csv_path] = score

    def _select_best(paths: List[Path]) -> Path:
        if len(paths) > 1:
            print(
                "[warn] 找到多个候选的 Profile Message CSV，选择最新修改的一个："
                + ", ".join(str(p) for p in paths)
            )
            paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return paths[0]

    if exact_matches:
        return _select_best(exact_matches)
    if suffix_matches:
        print(
            "[warn] 未找到与消息名完全一致的 CSV，尝试使用后缀匹配的文件："
            + ", ".join(str(p) for p in suffix_matches)
        )
        return _select_best(suffix_matches)
    if partial_matches:
        print(
            "[warn] 未找到与消息名完全一致的 CSV，尝试使用模糊匹配的文件："
            + ", ".join(str(p) for p in partial_matches)
        )
        return _select_best(partial_matches)
    if token_scores:
        best_score = max(token_scores.values())
        token_matches = [
            path for path, score in token_scores.items() if score == best_score
        ]
        print(
            "[warn] 未找到名称接近的 CSV，尝试基于关键字匹配的文件："
            + ", ".join(str(p) for p in token_matches)
        )
        return _select_best(token_matches)

    available = ", ".join(str(p) for p in discovered) or "<empty>"
    raise FileNotFoundError(
        "Profile Message CSV not found for "
        f"{dataset_name}. Checked: {candidate} and {fallback}. "
        f"Available files: {available}"
    )


def _convert_single_blf(
    blf_file: Path,
    *,
    final_root: Path,
    intermediate_root: Path,
    message_name: str,
    output_encoding: str,
    input_encodings: Optional[StrSequence],
    message_ids: Sequence[int],
    keep_intermediate: bool,
    use_region_folders: bool,
) -> List[Path]:
    if logFileAnalyze is None:  # pragma: no cover - optional dependency not available
        raise RuntimeError(
            "Process.py could not be imported. Install its dependencies (e.g. dpkt) before running the conversion."
        ) from PROCESS_IMPORT_ERROR

    dataset_name = blf_file.stem
    intermediate_dir = intermediate_root / dataset_name
    if intermediate_dir.exists():
        shutil.rmtree(intermediate_dir)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    print(f"[code1] converting {blf_file}")
    cwd = Path.cwd()
    try:
        _ensure_log_analyzer_resource()
        logFileAnalyze([str(blf_file)], list(message_ids), str(intermediate_dir))
    finally:
        os.chdir(cwd)

    profile_csv = _locate_profile_csv(intermediate_dir, dataset_name, message_name)
    print(f"[code3] refining {profile_csv}")
    outputs = convert_profile_message_file(
        profile_csv,
        message_name=message_name,
        target_root=final_root,
        output_encoding=output_encoding,
        input_encodings=input_encodings,
        use_region_folders=use_region_folders,
    )

    if not keep_intermediate:
        shutil.rmtree(intermediate_dir, ignore_errors=True)

    return outputs


def convert_blf_sources(
    source: Path,
    *,
    target_root: Optional[os.PathLike] = None,
    message_name: str,
    output_encoding: str,
    input_encodings: Optional[StrSequence],
    message_ids: Sequence[int],
    workdir: Optional[os.PathLike],
    keep_intermediate: bool,
    use_region_folders: bool = True,
) -> List[Path]:
    blf_files: List[Path]
    if source.is_file():
        blf_files = [source]
    else:
        blf_files = list(_iter_blf_files(source))

    if not blf_files:
        print(f"[warn] no .blf files found under {source}")
        return []

    final_root = Path(target_root) if target_root else DEFAULT_REGION_ROOT
    final_root.mkdir(parents=True, exist_ok=True)

    intermediate_root = Path(workdir) if workdir else final_root / "_intermediate"
    intermediate_root.mkdir(parents=True, exist_ok=True)

    results: List[Path] = []
    for blf_file in blf_files:
        results.extend(
            _convert_single_blf(
                blf_file,
                final_root=final_root,
                intermediate_root=intermediate_root,
                message_name=message_name,
                output_encoding=output_encoding,
                input_encodings=input_encodings,
                message_ids=message_ids,
                keep_intermediate=keep_intermediate,
                use_region_folders=use_region_folders,
            )
        )

    print(
        f"[done] processed {len(blf_files)} file(s). Final CSVs stored in {final_root}"
    )
    return results


def iter_profile_csv_paths(
    csv_root: os.PathLike,
    message_name: Optional[str] = None,
) -> Iterable[Path]:
    message = message_name or message_file_name
    pattern = Path(csv_root) / "**" / f"{message}.csv"
    return sorted(Path(p) for p in glob.glob(str(pattern), recursive=True))


def main(
    csv_root: Optional[os.PathLike] = None,
    *,
    message_name: Optional[str] = None,
    target_root: Optional[os.PathLike] = None,
    output_encoding: str = "cp932",
    input_encodings: Optional[StrSequence] = None,
    message_ids: Optional[IntSequence] = None,
    workdir: Optional[os.PathLike] = None,
    keep_intermediate: bool = False,
) -> int:
    root = Path(csv_root or csv_save_path)
    message = message_name or message_file_name
    encoding_candidates = input_encodings
    ids = _parse_message_ids(message_ids)

    if (
        target_root is None
        and root.resolve() == DEFAULT_PROFILE_ROOT.resolve()
    ):
        data_dir = HERE / "data"
        pending_blf: List[Path] = []
        if data_dir.exists():
            for blf_file in _iter_blf_files(data_dir):
                dataset_dir = root / blf_file.stem
                if (dataset_dir / f"{message}.csv").exists():
                    continue
                pending_blf.append(blf_file)

        if pending_blf:
            print(
                f"[info] detected {len(pending_blf)} new BLF file(s) in {data_dir}. "
                "Running code①+code③ automatically."
            )
            for blf_file in pending_blf:
                convert_blf_sources(
                    blf_file,
                    target_root=root,
                    message_name=message,
                    output_encoding=output_encoding,
                    input_encodings=encoding_candidates,
                    message_ids=ids,
                    workdir=workdir,
                    keep_intermediate=keep_intermediate,
                    use_region_folders=False,
                )

    if root.is_file() and root.suffix.lower() == ".blf":
        convert_blf_sources(
            root,
            target_root=target_root,
            message_name=message,
            output_encoding=output_encoding,
            input_encodings=encoding_candidates,
            message_ids=ids,
            workdir=workdir,
            keep_intermediate=keep_intermediate,
        )
        return 0

    if root.is_dir():
        blf_files = list(_iter_blf_files(root))
        if blf_files:
            convert_blf_sources(
                root,
                target_root=target_root,
                message_name=message,
                output_encoding=output_encoding,
                input_encodings=encoding_candidates,
                message_ids=ids,
                workdir=workdir,
                keep_intermediate=keep_intermediate,
            )
            return 0

        prf_csv_list = list(iter_profile_csv_paths(root, message))
    elif root.is_file() and root.suffix.lower() == ".csv":
        prf_csv_list = [root]
    else:
        print(f"[ERROR] 入力パスが無効です: {root}")
        return 1

    print(f"[info] found {len(prf_csv_list)} files:")
    for p in prf_csv_list:
        print("  -", p)
    if not prf_csv_list:
        print("[ERROR] Profile Message.csv が見つかりません。csv_save_path / ファイル名 を確認してください。")
        return 1

    for prf_csv in prf_csv_list:
        print(f"\n[processing] {prf_csv}")
        convert_profile_message_file(
            prf_csv,
            message_name=message,
            target_root=target_root,
            output_encoding=output_encoding,
            input_encodings=encoding_candidates,
        )

    return 0


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Split 'Profile Message.csv' into detailed tables",
    )
    ap.add_argument(
        "--input",
        default=csv_save_path,
        help="Root directory that contains the Profile Message CSV files",
    )
    ap.add_argument(
        "--message-name",
        default=message_file_name,
        help="Profile Message base name (without .csv)",
    )
    ap.add_argument(
        "--target-root",
        help="Optional destination root. When provided, files are written to <target_root>/<region>/<dataset>",
    )
    ap.add_argument(
        "--encoding",
        default="cp932",
        help="Encoding for the generated CSV files",
    )
    ap.add_argument(
        "--input-encoding",
        nargs="+",
        help="Candidate encodings for reading Profile Message CSV files (default: cp932, shift_jis, euc_jp, gbk, utf-8-sig, utf-8)",
    )
    ap.add_argument(
        "--ids",
        default=",".join(f"0x{x:08X}" for x in DEFAULT_MESSAGE_IDS),
        help="Comma separated list of message IDs for BLF conversion",
    )
    ap.add_argument(
        "--workdir",
        help="Directory for intermediate outputs when converting BLF files",
    )
    ap.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep intermediate code① outputs instead of deleting them",
    )
    args = ap.parse_args()

    raise SystemExit(
        main(
            args.input,
            message_name=args.message_name,
            target_root=args.target_root,
            output_encoding=args.encoding,
            input_encodings=args.input_encoding,
            message_ids=args.ids,
            workdir=args.workdir,
            keep_intermediate=args.keep_intermediate,
        )
    )
