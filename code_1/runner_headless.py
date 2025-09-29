# runner_headless.py —— 无界面跑 Code①
import argparse, os, glob, sys

# 让 Python 能 import 到我们上传的源码目录
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Code① 真正的执行函数在 Process.py 里（main_LogAnalyzer 也是调它）
from Process import logFileAnalyze  # 如果你本地代码签名不同，按 main_LogAnalyzer.py 里的调用改一下即可

def parse_ids(s):
    ids = []
    for t in s.split(','):
        t = t.strip()
        if t:
            ids.append(int(t, 16))
    return ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Folder with .blf/.pcap/.pcapng/.asc")
    ap.add_argument("--output", required=True, help="Folder to write CSV outputs")
    ap.add_argument("--ids", required=True, help="Comma-separated hex IDs, e.g. 0xCAF0054C,0xCAF0036D")
    args = ap.parse_args()

    # 收集待解析的日志文件
    files = []
    for ext in ("*.blf", "*.pcap", "*.pcapng", "*.asc"):
        files.extend(glob.glob(os.path.join(args.input, ext)))
    if not files:
        raise SystemExit("No input logs found in {}".format(args.input))

    os.makedirs(args.output, exist_ok=True)

    # 解析并落盘（Process.py 里会启用 CSV-only 模式）
    target_ids = parse_ids(args.ids)
    logFileAnalyze(files, target_ids, args.output)
    print("Headless run complete.")

if __name__ == "__main__":
    main()
