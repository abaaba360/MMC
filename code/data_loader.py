"""
数据读取与预处理
功能：读取附件2（84样本 xlsx），统一列名，返回建模DataFrame
输入：problems/选题B/附件/附件 2：*.xlsx
输出：DataFrame[r, h, n, R, P, T]
运行方式：python code/data_loader.py
"""
import glob
import os
import pandas as pd


def load_problem_b_data():
    """读取选题B附件2，返回含设计变量与性能指标的DataFrame"""
    xlsx = glob.glob(os.path.join("problems", "选题B", "附件", "*.xlsx"))
    if not xlsx:
        raise FileNotFoundError("未找到选题B附件xlsx文件")
    df = pd.read_excel(xlsx[0], header=1)
    # 统一列名：针肋宽度比->r, 歧管深高比->h, 针肋排数->n, 无量纲热阻->R, 无量纲压降->P, 无量纲温度非均匀性->T
    rename = {
        "针肋宽度比": "r",
        "歧管深高比": "h",
        "单个歧管单元内沿流向的针肋排数": "n",
        "无量纲热阻": "R",
        "无量纲压降": "P",
        "无量纲温度非均匀性": "T",
    }
    df = df.rename(columns=rename)
    df = df[["r", "h", "n", "R", "P", "T"]].copy()
    df = df.dropna().reset_index(drop=True)
    # 类型安全
    for c in ["r", "h", "n", "R", "P", "T"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = load_problem_b_data()
    print(df.shape)
    print(df.describe().round(4))
