# 11.py  —— 把 Profile Message.csv.bak 转成 SJIS(CP932)，不改你的主程序
import os

src = r"D:\test\code_1\outputs\J42U_JPN_AD1Next_V001_01ALL_20250131_040542_130\Profile Message.csv.bak"
dst = src.replace(".bak", "_sjis.csv")

# 依次尝试的源编码（按概率从高到低）
candidates = [
    "gb18030",  # 覆盖 GBK/GB2312 的超集，最稳
    "gbk",
    "cp936",    # Windows 简体中文
    "utf-8-sig",
    "utf-8",
    "utf-16le",
    "utf-16be",
    "cp1252",   # 西欧
    "latin1"    # 兜底（仅用于确认，不推荐用作最终）
]

text = None
used_enc = None
last_err = None

# 逐个尝试解码
for enc in candidates:
    try:
        with open(src, "r", encoding=enc, errors="strict") as f:
            text = f.read()
        used_enc = enc
        print(f"[OK] decode with {enc}")
        break
    except Exception as e:
        last_err = e
        print(f"[fail] {enc}: {e.__class__.__name__}: {e}")

if text is None:
    raise RuntimeError(f"无法判定源编码，请把该 .bak 发我（最后错误：{last_err}）")

# 先用 strict 写 CP932，确保不丢字符；失败再降级 replace（仅极少数符号会变 ?）
try:
    with open(dst, "w", encoding="cp932", errors="strict", newline="") as f:
        f.write(text)
    print(f"[OK] write CP932 strict -> {dst}")
except UnicodeEncodeError as e:
    print(f"[warn] cp932 严格写入失败：{e} -> 将使用 replace 兼容写入")
    with open(dst, "w", encoding="cp932", errors="replace", newline="") as f:
        f.write(text)
    print(f"[OK] write CP932 replace -> {dst}")

print(f"\n[done] 源编码识别为：{used_enc}\n"
      f"      已导出 SJIS 文件：{dst}\n"
      f"      下一步：把它改名为 'Profile Message.csv' 覆盖原文件，然后直接跑你的主脚本。")
