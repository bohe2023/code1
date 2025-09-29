# -*- coding: utf-8 -*-
"""
从 Nissan Profile CSV 生成“能看”的最小 OpenDRIVE：
- 基于 LINE_GEOMETRY 提取经纬度 → local-XY
- 按距离抽稀 + 基于几何近似曲率做分段：line/arc
- 单个 laneSection，左右各一条 driving lane（固定或由 CSV 推断平均宽度）
- 仅在左/右车道各加 1 条 roadMark（避免复杂 pattern 造成渲染噪声）

用法示例：
python csv_to_xodr_v2_smooth.py ^
  --input "D:\\test\\code_1\\outputs\\J42U_JPN_AD1Next_V001_01ALL_20250131_040542_130\\Profile Message" ^
  --output "D:\\test\\demo_v2.xodr" ^
  --decim 10 ^
  --k_line 0.00008

参数解释：
- --decim   距离抽稀阈值(米)，默认 10
- --k_line  认为“直线”的曲率阈值(1/m)，默认 8e-5（可按数据调）
"""

import argparse, os, math, datetime, re
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

ENCODINGS = [None, "cp932", "shift_jis", "utf-8"]

def read_csv_any(path):
    last = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc) if enc else pd.read_csv(path)
        except Exception as e:
            last = e
    raise RuntimeError(f"Cannot read {path}: {last}")

def find_first_existing(base, names):
    for n in names:
        p = os.path.join(base, n)
        if os.path.exists(p):
            return p
    return None

def llh_to_local_xy(lat, lon, lat0, lon0):
    lat0r = math.radians(lat0)
    x = (lon - lon0) * math.cos(lat0r) * 111320.0
    y = (lat - lat0) * 110540.0
    return x, y

def cumulative_dist(xs, ys):
    s = [0.0]
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i-1]
        dy = ys[i] - ys[i-1]
        s.append(s[-1] + math.hypot(dx, dy))
    return np.array(s)

def rdp_decimate(xs, ys, step_m=10.0):
    """简单按累计距离抽稀（每 step_m 取一点），保证首尾保留"""
    if len(xs) < 2:
        return xs, ys
    keep_x = [xs[0]]; keep_y = [ys[0]]
    lastx, lasty = xs[0], ys[0]
    acc = 0.0
    for i in range(1, len(xs)):
        dx = xs[i]-lastx; dy = ys[i]-lasty
        d = math.hypot(dx, dy)
        acc += d
        if acc >= step_m or i == len(xs)-1:
            keep_x.append(xs[i]); keep_y.append(ys[i])
            lastx, lasty = xs[i], ys[i]
            acc = 0.0
    return np.array(keep_x), np.array(keep_y)

def headings(xs, ys):
    hdg = [0.0]
    for i in range(1, len(xs)):
        dx = xs[i]-xs[i-1]; dy = ys[i]-ys[i-1]
        hdg.append(math.atan2(dy, dx))
    return np.array(hdg)

def unwrap_angles(a):
    """解除角度跳变"""
    out = [a[0]]
    for i in range(1, len(a)):
        d = a[i] - out[-1]
        while d > math.pi:  d -= 2*math.pi
        while d < -math.pi: d += 2*math.pi
        out.append(out[-1] + d)
    return np.array(out)

def curvature_from_polyline(xs, ys):
    """根据相邻航向差与段长近似曲率 k ≈ Δhdg / ds"""
    s = cumulative_dist(xs, ys)
    hdg = unwrap_angles(headings(xs, ys))
    k = np.zeros_like(s)
    for i in range(1, len(s)):
        ds = max(1e-6, s[i]-s[i-1])
        k[i] = (hdg[i]-hdg[i-1]) / ds
    return s, hdg, k

def group_segments(s, hdg, k, k_line=8e-5, k_tol=2e-5, min_len=5.0):
    """
    分两类：line / arc
    - 绝对曲率小于 k_line → line
    - 否则 → arc，合并相邻曲率符号一致且变化不大的段
    """
    groups = []
    i = 0
    n = len(s)
    while i < n-1:
        j = i+1
        if abs(k[j]) < k_line:
            # line: 向前合并到曲率再次显著非零或结束
            while j < n-1 and abs(k[j]) < k_line:
                j += 1
            if s[j]-s[i] >= min_len:
                groups.append(("line", i, j))
            else:
                # 太短，就并到后续（避免碎片）
                pass
        else:
            sign = 1 if k[j] >= 0 else -1
            kvals = [k[j]]
            while j < n-1 and (k[j]*sign > 0) and (abs(k[j]-np.mean(kvals)) < k_tol):
                kvals.append(k[j]); j += 1
            if s[j]-s[i] >= min_len:
                groups.append(("arc", i, j, float(np.mean(kvals))))
            else:
                # 太短归并：当作 line
                groups.append(("line", i, j))
        i = j
    # 如果一个都没分出来，fallback 为整段线
    if not groups:
        groups.append(("line", 0, n-1))
    return groups

def infer_lane_width(in_dir):
    f = find_first_existing(in_dir, ["PROFILETYPE_MPU_ZGM_LANE_LINK_INFO.csv"])
    if not f:
        return 3.5
    df = read_csv_any(f)
    for c in df.columns:
        if ("幅" in c) or ("Width" in c):
            s = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(s) == 0: continue
            m = float(s.mean())
            return m/100.0 if m > 20 else m
    return 3.5

def infer_mark_simple(in_dir):
    f = find_first_existing(in_dir, ["PROFILETYPE_MPU_ZGM_LANE_DIVISION_LINE.csv"])
    if not f:
        return "broken", "white", 0.15
    df = read_csv_any(f)
    t, col, w = "broken", "white", 0.15
    try:
        if "区画線種別" in df.columns:
            vc = df["区画線種別"].value_counts(dropna=False)
            if len(vc) > 0 and int(vc.index[0]) == 2:
                t = "solid"
        width_cols = [c for c in df.columns if "線幅" in c]
        vals = []
        for c in width_cols:
            v = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(v): vals.append(float(v.mean()))
        if vals:
            w_cm = float(np.mean(vals))
            if w_cm > 0.5: w = max(0.05, min(0.3, w_cm/100.0))
    except:
        pass
    return t, col, w

def _indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for ch in elem:
            _indent(ch, level+1)
        if not ch.tail or not ch.tail.strip():
            ch.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def build_xodr(xs, ys, groups, lane_w=3.5, mark=("broken","white",0.15)):
    op = ET.Element("OpenDRIVE")
    ET.SubElement(op, "header", {
        "revMajor":"1","revMinor":"6","name":"csv_demo_v2","version":"1.6",
        "date": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "north":"0","south":"0","east":"0","west":"0"
    })
    # road length
    s = cumulative_dist(xs, ys)
    road = ET.SubElement(op, "road", {"name":"demo_v2","length":f"{float(s[-1]):.3f}","id":"1","junction":"-1"})
    plan = ET.SubElement(road, "planView")

    # geometry elements
    for g in groups:
        kind = g[0]
        i = g[1]; j = g[2]
        x0, y0 = float(xs[i]), float(ys[i])
        # 起始航向
        hdg = math.atan2(float(ys[i+1]-ys[i]), float(xs[i+1]-xs[i]))
        s0 = float(s[i])
        length = float(s[j]-s[i])
        geo = ET.SubElement(plan, "geometry", {
            "s": f"{s0:.3f}",
            "x": f"{x0:.3f}",
            "y": f"{y0:.3f}",
            "hdg": f"{hdg:.9f}",
            "length": f"{length:.3f}"
        })
        if kind == "line":
            ET.SubElement(geo, "line")
        else:
            k = float(g[3])
            ET.SubElement(geo, "arc", {"curvature": f"{k:.9f}"})

    # lanes
    lanes = ET.SubElement(road, "lanes")
    lsec = ET.SubElement(lanes, "laneSection", {"s":"0.000"})
    center = ET.SubElement(lsec, "center")
    ET.SubElement(center, "lane", {"id":"0","type":"none","level":"false"})
    # 左右各一条简单驾驶车道
    left = ET.SubElement(lsec, "left")
    laneL = ET.SubElement(left, "lane", {"id":"1","type":"driving","level":"false"})
    ET.SubElement(laneL, "width", {"sOffset":"0.000","a":f"{lane_w:.3f}","b":"0","c":"0","d":"0"})
    right = ET.SubElement(lsec, "right")
    laneR = ET.SubElement(right, "lane", {"id":"-1","type":"driving","level":"false"})
    ET.SubElement(laneR, "width", {"sOffset":"0.000","a":f"{lane_w:.3f}","b":"0","c":"0","d":"0"})

    # 简单 roadMark（两侧各一条）
    t, col, w = mark
    ET.SubElement(laneL, "roadMark", {"sOffset":"0.000","type":t,"weight":"standard","color":col,"width":f"{w:.3f}"})
    ET.SubElement(laneR, "roadMark", {"sOffset":"0.000","type":t,"weight":"standard","color":col,"width":f"{w:.3f}"})
    return op

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Profile Message 目录")
    ap.add_argument("--output", required=True, help="输出 .xodr")
    ap.add_argument("--decim", type=float, default=10.0, help="距离抽稀阈值(米)")
    ap.add_argument("--k_line", type=float, default=8e-5, help="曲率阈值(1/m)，小于该值视作直线")
    args = ap.parse_args()

    in_dir = args.input
    out_xodr = args.output

    f_geom = find_first_existing(in_dir, ["PROFILETYPE_MPU_LINE_GEOMETRY.csv", "LanesGeometryProfile.csv"])
    if not f_geom:
        raise FileNotFoundError("找不到几何 CSV（PROFILETYPE_MPU_LINE_GEOMETRY.csv / LanesGeometryProfile.csv）")

    df = read_csv_any(f_geom)

    # 猎列名（日/英两套都支持）
    def find_col(cands):
        for c in df.columns:
            for pat in cands:
                if re.search(pat, c, re.IGNORECASE):
                    return c
        return None

    lat_col = find_col([r"緯度", r"\blat"])
    lon_col = find_col([r"経度", r"\blon"])
    if not lat_col or not lon_col:
        raise RuntimeError(f"经纬度列未找到（前几列：{df.columns.tolist()[:10]}）")

    # --- 新增：去空 → 去重 → 选一条线 → 排序 ---

    # 1) 去空
    df = df.dropna(subset=[lat_col, lon_col]).copy()

    # 2) 去重：排除随发送变化的列（时间戳、序号等）
    volatile = [c for c in df.columns if
                re.search(r'(time|timestamp|send|seq|frame|msg|publish|receive)', str(c), re.I)]
    subset = [c for c in df.columns if c not in volatile]
    if subset:
        before = len(df)
        df = df.drop_duplicates(subset=subset, keep='last').reset_index(drop=True)
        print(f"[dedup] {before} -> {len(df)} (-{before - len(df)})")

    # 3) 选“一条线”（避免把多条几何混在一起）
    for pat in [r'Line\s*ID', r'ラインID|線形ID', r'Lane\s*ID', r'レーンID',
                r'poly.*id|segment.*id|shape.*id']:
        gid = next((c for c in df.columns if re.search(pat, str(c), re.I)), None)
        if gid:
            key = df[gid].value_counts().idxmax()
            df = df[df[gid] == key].copy()
            print(f"[group] use {gid}={key}")
            break

    # 4) 排序：优先点序/里程，其次时间
    order_col = next((c for c in df.columns if re.search(r'(point|頂点|vertex|index|順番|距離|里程)', str(c), re.I)),
                     None)
    if not order_col:
        order_col = next((c for c in df.columns if re.search(r'time|timestamp', str(c), re.I)), None)
    if order_col:
        df = df.sort_values(order_col).reset_index(drop=True)
    # --- 新增结束 ---

    g = df[[lat_col, lon_col]].dropna()
    if len(g) < 3:
        raise RuntimeError("几何点太少")

    lat0 = float(g.iloc[0][lat_col]); lon0 = float(g.iloc[0][lon_col])
    xs, ys = [], []
    for _, r in g.iterrows():
        x, y = llh_to_local_xy(float(r[lat_col]), float(r[lon_col]), lat0, lon0)
        xs.append(x); ys.append(y)
    xs = np.array(xs); ys = np.array(ys)

    # 抽稀 + 曲率分段
    xs, ys = rdp_decimate(xs, ys, step_m=args.decim)
    s, hdg, k = curvature_from_polyline(xs, ys)
    groups = group_segments(s, hdg, k, k_line=args.k_line)

    # 车道宽 & 标线
    lane_w = infer_lane_width(in_dir)
    mark = infer_mark_simple(in_dir)

    # 生成 XODR
    op = build_xodr(xs, ys, groups, lane_w=lane_w, mark=mark)
    tree = ET.ElementTree(op)
    _indent(op)
    os.makedirs(os.path.dirname(out_xodr), exist_ok=True)
    tree.write(out_xodr, encoding="utf-8", xml_declaration=True)
    print(f"[OK] {out_xodr}")

if __name__ == "__main__":
    main()
