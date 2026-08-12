"""
代理模型模块（Q2构建，Q3-Q5复用）
功能：封装3个高斯过程回归(GPR)代理模型 f(r,h,n)->(R,P,T)，含输入标准化与预测
输入：results/models/ 下由 q2_model.py 生成的模型文件
运行方式：作为模块被 q2/q3/q4/q5 引用
"""
import os
import numpy as np
import joblib

MODEL_DIR = os.path.join("results", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# 输入列顺序固定: 0=r, 1=h, 2=n
VAR_ORDER = ["r", "h", "n"]


class Surrogates:
    """R/P/T 三个GPR代理模型"""

    def __init__(self, gpr: dict, scaler, target_stats: dict, meta: dict = None):
        self.gpr = gpr          # {'R': GP, 'P': GP, 'T': GP}
        self.scaler = scaler    # StandardScaler 用于(r,h,n)
        self.target_stats = target_stats  # 每个指标的归一化统计
        self.meta = meta or {}

    def predict(self, X, return_std=False, denormalize=True):
        """X: (N,3) 原始尺度 (r,h,n)。返回各指标预测。
        return_std=True 时额外返回预测标准差。"""
        X = np.asarray(X, dtype=float)
        Xs = self.scaler.transform(X)
        out = {}
        out_std = {}
        for m in ["R", "P", "T"]:
            y, s = self.gpr[m].predict(Xs, return_std=True)
            # 目标归一化(0-1)反变换
            lo, hi = self.target_stats[m]["min"], self.target_stats[m]["max"]
            span = hi - lo if hi > lo else 1.0
            if denormalize:
                y = y * span + lo
                s = s * span
            out[m] = y
            out_std[m] = s
        if return_std:
            return out, out_std
        return out

    def predict_array(self, X, metric, denormalize=True):
        """返回单个指标的1维数组"""
        X = np.asarray(X, dtype=float)
        Xs = self.scaler.transform(X)
        y, _ = self.gpr[metric].predict(Xs, return_std=True)
        if denormalize:
            lo, hi = self.target_stats[metric]["min"], self.target_stats[metric]["max"]
            span = hi - lo if hi > lo else 1.0
            y = y * span + lo
        return y

    def save(self, tag="surrogates"):
        path = os.path.join(MODEL_DIR, f"{tag}.joblib")
        joblib.dump(self, path)
        return path


def load_surrogates(tag="surrogates"):
    path = os.path.join(MODEL_DIR, f"{tag}.joblib")
    return joblib.load(path)
