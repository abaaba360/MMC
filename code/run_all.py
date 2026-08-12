"""
一键运行选题B全部求解流程
功能：依次运行 EDA、Q1-Q5 代码，生成全部结果与图表
运行方式：python code/run_all.py
依赖：results/models/surrogates.joblib 由 q2 生成
"""
import subprocess
import sys
import os
import time

SCRIPTS = ["eda.py", "q1_model.py", "q2_model.py", "q3_model.py",
           "q4_model.py", "q5_model.py"]
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def main():
    t0 = time.time()
    for s in SCRIPTS:
        print(f"\n{'='*60}\n>>> 运行 {s}\n{'='*60}")
        t1 = time.time()
        ret = subprocess.run([sys.executable, os.path.join(BASE, s)], cwd=os.path.dirname(BASE))
        print(f"  [{s}] 退出码={ret.returncode}, 耗时={time.time()-t1:.1f}s")
        if ret.returncode != 0:
            print(f"!! {s} 运行失败，终止")
            sys.exit(1)
    print(f"\n全部完成，总耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
