"""2026 C题正式数据读取器。

功能：读取附件1、附件2并执行结构、缺失和单位检查。
输入：problems/选题C_2026正式/附件/附件1.xlsx、附件2.xlsx
输出：内存中的日×时段数组；功率同时换算为10分钟电量。
运行：由 q2_model.py 导入。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "problems" / "选题C_2026正式" / "附件"
STEP_HOURS = 1.0 / 6.0
N_DAYS = 365
N_STEPS = 144


def _read_daily_sheet(path: Path, sheet_name: str) -> tuple[np.ndarray, np.ndarray]:
    """读取附件2的一个365×144宽表，返回日期与数值矩阵。"""

    frame = pd.read_excel(path, sheet_name=sheet_name)
    if frame.shape != (N_DAYS, N_STEPS + 1):
        raise ValueError(
            f"{path.name}/{sheet_name}形状应为(365,145)，实际为{frame.shape}"
        )
    if frame.iloc[:, 1:].isna().any().any():
        raise ValueError(f"{path.name}/{sheet_name}存在缺失数值")
    dates = pd.to_datetime(frame.iloc[:, 0], errors="raise").to_numpy()
    expected = pd.date_range("2025-01-01", "2025-12-31", freq="D").to_numpy()
    if not np.array_equal(dates.astype("datetime64[D]"), expected.astype("datetime64[D]")):
        raise ValueError(f"{path.name}/{sheet_name}日期不连续或不是2025全年")
    values = frame.iloc[:, 1:].to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError(f"{path.name}/{sheet_name}含非有限值或负功率")
    return dates, values


def load_typical_day() -> dict[str, np.ndarray]:
    """读取附件1的固定电价与典型日曲线。"""

    path = DATA_DIR / "附件1.xlsx"
    frame = pd.read_excel(path)
    expected_columns = ["时间", "电价", "小区负载", "光伏发电预测功率"]
    if list(frame.columns) != expected_columns or frame.shape[0] != N_STEPS:
        raise ValueError("附件1列结构或时段数异常")
    if frame.isna().any().any():
        raise ValueError("附件1存在缺失值")
    price = frame["电价"].to_numpy(dtype=float)
    load_kw = frame["小区负载"].to_numpy(dtype=float)
    pv_kw = frame["光伏发电预测功率"].to_numpy(dtype=float)
    if np.any(price < 0) or np.any(load_kw < 0) or np.any(pv_kw < 0):
        raise ValueError("附件1不应出现负的价格、负荷或光伏功率")
    return {
        "time": frame["时间"].astype(str).to_numpy(),
        "price": price,
        "load_kw": load_kw,
        "pv_kw": pv_kw,
        "load_kwh": load_kw * STEP_HOURS,
        "pv_kwh": pv_kw * STEP_HOURS,
        "net_kwh": (load_kw - pv_kw) * STEP_HOURS,
    }


def load_q2_data() -> dict[str, np.ndarray]:
    """读取Q2全年实际负荷/光伏，统一为kW与每时段kWh。"""

    path = DATA_DIR / "附件2.xlsx"
    dates_l, load_kw = _read_daily_sheet(path, "小区负载")
    dates_s, pv_kw = _read_daily_sheet(path, "光伏发电实际功率")
    if not np.array_equal(dates_l, dates_s):
        raise ValueError("附件2两个工作表的日期不一致")
    load_kwh = load_kw * STEP_HOURS
    pv_kwh = pv_kw * STEP_HOURS
    return {
        "dates": dates_l.astype("datetime64[D]"),
        "load_kw": load_kw,
        "pv_kw": pv_kw,
        "load_kwh": load_kwh,
        "pv_kwh": pv_kwh,
        "net_kwh": load_kwh - pv_kwh,
    }

