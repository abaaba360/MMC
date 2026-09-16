"""2026年C题附件数据读取与单位转换。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "problems" / "选题C_2026正式" / "附件"
STEP_HOURS = 1.0 / 6.0


def load_q1() -> dict[str, np.ndarray]:
    frame = pd.read_excel(DATA_DIR / "附件1.xlsx")
    required = ["时间", "电价", "小区负载", "光伏发电预测功率"]
    if list(frame.columns) != required:
        raise ValueError(f"附件1列名异常：{list(frame.columns)}")
    if frame.shape[0] != 144 or frame.isna().any().any():
        raise ValueError("附件1应包含144个完整的10分钟时段")
    return {
        "time": frame["时间"].astype(str).to_numpy(),
        "price": frame["电价"].to_numpy(float),
        "load_kw": frame["小区负载"].to_numpy(float),
        "pv_kw": frame["光伏发电预测功率"].to_numpy(float),
        "load_kwh": frame["小区负载"].to_numpy(float) * STEP_HOURS,
        "pv_kwh": frame["光伏发电预测功率"].to_numpy(float) * STEP_HOURS,
    }

