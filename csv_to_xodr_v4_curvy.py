# -*- coding: utf-8 -*-
"""
v4-curvy：从全路轨里自动挑“最弯的一段”生成 OpenDRIVE
- 读取 LINE_GEOMETRY / LanesGeometryProfile 的经纬度（度）
- 全段计算 heading，滑窗(长度 clip_m)寻找总转角最大的窗口
- 窗口内做平滑 + 抽稀；用 paramPoly3 拟合成一段平滑几何
- 仅建右侧 1 条车道（常宽），适合做报告截图
Python 3.8+，依赖 pandas、numpy
"""

import argparse, os, math, datetime, re
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

ENCODINGS=[None,"cp932","shift_jis","utf-8"]

def read_csv_any(p):
    last=None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(p, encoding=enc) if enc else pd.read_csv(p)
        except Exception as e:
            last=e
    raise RuntimeError(f"Cannot read {p}: {last}")

def find_first_existing(base,names):
    for n in names:
        p=os.path.join(base,n)
        if os.path.exists(p): return p
    return None

def llh_to_local_xy(lat,lon,lat0,lon0):
    lat0r = math.radians(lat0)
    x = (lon - lon0) * math.cos(lat0r) * 111320.0
    y = (lat - lat0) * 110540.0
    return x, y

def cumulative_dist(xs,ys):
    s=[0.0]
    for i in range(1,len(xs)):
        s.append(s[-1]+math.hypot(xs[i]-xs[i-1], ys[i]-ys[i-1]))
    return np.array(s)

def unwrap(a):
    out=[a[0]]
    for i in range(1,len(a)):
        d=a[i]-out[-1]
        while d> math.pi: d -= 2*math.pi
        while d<-math.pi: d += 2*math.pi
        out.append(out[-1]+d)
    return np.array(out)

def moving_avg_xy(xs,ys,win_m):
    if len(xs)<5 or win_m<=0: return xs,ys
    s=cumulative_dist(xs,ys)
    ox=[]; oy=[]
    for i in range(len(xs)):
        m=(s>=s[i]-win_m/2) & (s<=s[i]+win_m/2)
        if m.sum()<3:
            ox.append(xs[i]); oy.append(ys[i])
        else:
            ox.append(float(np.mean(xs[m]))); oy.append(float(np.mean(ys[m])))
    return np.array(ox), np.array(oy)

def decimate_xy(xs,ys,step_m):
    keepx=[xs[0]]; keepy=[ys[0]]
    lastx,lasty=xs[0],ys[0]; acc=0.0
    for i in range(1,len(xs)):
        d=math.hypot(xs[i]-lastx, ys[i]-lasty)
        acc+=d
        if acc>=step_m or i==len(xs)-1:
            keepx.append(xs[i]); keepy.append(ys[i])
            lastx,lasty=xs[i],ys[i]; acc=0.0
    return np.array(keepx), np.array(keepy)

def poly_fit_arcparam(s, v, deg):
    L=float(s[-1]) if s[-1]>0 else 1.0
    t=s/L
    A=np.vstack([t**i for i in range(deg,-1,-1)]).T
    coef,_res,_rank,_s = np.linalg.lstsq(A, v, rcond=None)
    # 把 t 的系数换回 s 的系数：v(s)=sum(ai*(s/L)^p)=sum((ai/L^p)*s^p)
    deg_n=len(coef)-1
    out=[]
    for i,ai in enumerate(coef):
        p=deg_n-i
        out.append(ai/(L**p))
    return out, L

def to_cubic(arr):
    if len(arr)<4:
        arr = [0.0]*(4-len(arr)) + list(arr)
    return arr[-4:]  # a3,a2,a1,a0

def _indent(elem, level=0):
    i="\n"+level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text=i+"  "
        for ch in elem:
            _indent(ch, level+1)
        if not ch.tail or not ch.tail.strip():
            ch.tail=i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail=i

def build_xodr_parampoly3(x0,y0,hdg,L,ax,bx,cx,dx, ay,by,cy,dy, lane_w, mark_w=0.15):
    op=ET.Element("OpenDRIVE")
    ET.SubElement(op,"header",{
        "revMajor":"1","revMinor":"6","name":"csv_demo_curvy","version":"1.6",
        "date":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "north":"0","south":"0","east":"0","west":"0"
    })
    road=ET.SubElement(op,"road",{"name":"demo_curvy","length":f"{L:.3f}","id":"1","junction":"-1"})
    plan=ET.SubElement(road,"planView")
    geo=ET.SubElement(plan,"geometry",{
        "s":"0.000","x":f"{x0:.3f}","y":f"{y0:.3f}","hdg":f"{hdg:.9f}","length":f"{L:.3f}"
    })
    ET.SubElement(geo,"paramPoly3",{
        "aU":f"{ax:.12f}","bU":f"{bx:.12f}","cU":f"{cx:.12f}","dU":f"{dx:.12f}",
        "aV":f"{ay:.12f}","bV":f"{by:.12f}","cV":f"{cy:.12f}","dV":f"{dy:.12f}",
        "pRange":"arcLength"
    })
    lanes=ET.SubElement(road,"lanes")
    lsec=ET.SubElement(lanes,"laneSection",{"s":"0.000"})
    center=ET.SubElement(lsec,"center")
    ET.SubElement(center,"lane",{"id":"0","type":"none","level":"false"})
    right=ET.SubElement(lsec,"right")
    laneR=ET.SubElement(right,"lane",{"id":"-1","type":"driving","level":"false"})
    ET.SubElement(laneR,"width",{"sOffset":"0.000","a":f"{lane_w:.3f}","b":"0","c":"0","d":"0"})
    ET.SubElement(laneR,"roadMark",{"sOffset":"0.000","type":"broken","weight":"standard","color":"white","width":f"{mark_w:.3f}"})
    return op

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--clip_m", type=float, default=600.0, help="窗口长度(米)")
    ap.add_argument("--smooth_m", type=float, default=40.0, help="平滑窗口")
    ap.add_argument("--decim", type=float, default=20.0, help="抽稀间距")
    ap.add_argument("--deg", type=int, default=3, help="多项式阶数(3或5)")
    ap.add_argument("--lane_w", type=float, default=3.5, help="车道宽")
    args=ap.parse_args()

    in_dir=args.input; out_xodr=args.output
    f_geom=find_first_existing(in_dir,["PROFILETYPE_MPU_LINE_GEOMETRY.csv","LanesGeometryProfile.csv"])
    if not f_geom: raise FileNotFoundError("几何CSV未找到")
    df=read_csv_any(f_geom)

    def find_col(pats):
        for c in df.columns:
            for p in pats:
                if re.search(p,c,re.IGNORECASE): return c
        return None
    lat_col=find_col([r"緯度", r"\blat"])
    lon_col=find_col([r"経度", r"\blon"])
    if not lat_col or not lon_col: raise RuntimeError("经纬度列未找到")

    g=df[[lat_col,lon_col]].dropna()
    if len(g)<8: raise RuntimeError("几何点太少")

    # 全段坐标
    lat0=float(g.iloc[0][lat_col]); lon0=float(g.iloc[0][lon_col])
    xs=[]; ys=[]
    for _,r in g.iterrows():
        x,y=llh_to_local_xy(float(r[lat_col]), float(r[lon_col]), lat0, lon0)
        xs.append(x); ys.append(y)
    xs=np.array(xs); ys=np.array(ys)
    s_all=cumulative_dist(xs,ys)
    # 计算 heading
    hdg=np.array([math.atan2(ys[i]-ys[i-1], xs[i]-xs[i-1]) if i>0 else 0.0 for i in range(len(xs))])
    hdg=unwrap(hdg)

    # 滑窗寻找“总转角”最大的区间
    clip=args.clip_m
    best_i=0; best_score=-1.0; j0=0
    for i in range(0,len(xs)-2):
        # 找到 j: s[j]-s[i] >= clip
        while j0 < len(xs)-1 and s_all[j0]-s_all[i] < clip:
            j0 += 1
        if j0 <= i+2: continue
        d = np.diff(hdg[i:j0])
        score = np.sum(np.abs(d))
        if score > best_score:
            best_score = score; best_i = i; best_j = j0

    # 切出窗口
    xs=xs[best_i:best_j]; ys=ys[best_i:best_j]
    # 平滑 + 抽稀
    xs,ys = moving_avg_xy(xs,ys,args.smooth_m)
    xs,ys = decimate_xy(xs,ys,args.decim)
    s=cumulative_dist(xs,ys)
    if len(xs)<5: raise RuntimeError("窗口内有效点太少")

    # 以窗口首点为原点
    x0,y0 = float(xs[0]), float(ys[0])
    hdg0  = math.atan2(float(ys[1]-ys[0]), float(xs[1]-xs[0]))
    x_fit = xs - x0; y_fit = ys - y0

    # 拟合 x(s), y(s) 并换算到 paramPoly3 系数
    coef_x, L = poly_fit_arcparam(s, x_fit, args.deg)
    coef_y, _ = poly_fit_arcparam(s, y_fit, args.deg)
    ax,bx,cx,dx = to_cubic(coef_x)
    ay,by,cy,dy = to_cubic(coef_y)

    # 生成 XODR
    op=build_xodr_parampoly3(x0,y0,hdg0,float(s[-1]), ax,bx,cx,dx, ay,by,cy,dy, lane_w=args.lane_w)
    tree=ET.ElementTree(op); _indent(op)
    os.makedirs(os.path.dirname(out_xodr), exist_ok=True)
    tree.write(out_xodr, encoding="utf-8", xml_declaration=True)
    print(f"[OK] {out_xodr}  window_turn={best_score:.3f} rad  L={float(s[-1]):.1f} m  pts={len(xs)}")
if __name__=="__main__":
    main()
