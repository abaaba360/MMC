"""Q3/Q4 共用的因果预测、滚动调整 MILP 与回测工具。

所有功率输入在读入后乘 1/6，内部决策量均为每十分钟电量（kWh）。
附件中的未来真实负荷、光伏和价格只进入事后结算，不进入预测函数。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from common_milp import solve_deterministic_dispatch


STEP_HOURS = 1.0 / 6.0
SLOTS_PER_DAY = 144
ORIGIN_SLOTS = (0, 36, 72, 108)
SOC_MIN = 1200.0
SOC_MAX = 10800.0
INTERVAL_LIMIT = 5000.0 * STEP_HOURS
ETA_C = 0.9
ETA_D = 0.9


@dataclass
class CData:
    dates: pd.DatetimeIndex
    load: np.ndarray
    pv_actual: np.ndarray
    fixed_price: np.ndarray
    realtime_price: np.ndarray
    typical_load: np.ndarray
    typical_pv: np.ndarray
    pv_hourly_forecast: np.ndarray


def load_c_data(root: Path) -> CData:
    """按工作表位置读取附件，避免依赖中文列名编码。"""
    a1 = pd.read_excel(root / "附件1.xlsx")
    typical_load = a1.iloc[:, 2].to_numpy(float) * STEP_HOURS
    typical_pv = a1.iloc[:, 3].to_numpy(float) * STEP_HOURS
    fixed_price = a1.iloc[:, 1].to_numpy(float)

    load_df = pd.read_excel(root / "附件2.xlsx", sheet_name=0)
    pv_df = pd.read_excel(root / "附件2.xlsx", sheet_name=1)
    dates = pd.DatetimeIndex(pd.to_datetime(load_df.iloc[:, 0]))
    load = load_df.iloc[:, 1:].to_numpy(float) * STEP_HOURS
    pv_actual = pv_df.iloc[:, 1:].to_numpy(float) * STEP_HOURS

    price_df = pd.read_excel(root / "附件4.xlsx")
    realtime_price = price_df.iloc[:, 1:].to_numpy(float)

    f = pd.read_excel(root / "附件3.xlsx")
    f.iloc[:, 0] = f.iloc[:, 0].ffill()
    f_dates = pd.to_datetime(f.iloc[:, 0])
    f_origins = f.iloc[:, 1].astype(str).str.extract(r"(\d+)", expand=False).astype(int)
    forecasts = f.iloc[:, 2:26].to_numpy(float) * STEP_HOURS
    pv_hourly = np.full((len(dates), 4, 24), np.nan)
    date_pos = {d.normalize(): i for i, d in enumerate(dates)}
    origin_pos = {0: 0, 6: 1, 12: 2, 18: 3}
    for i, d in enumerate(f_dates):
        di = date_pos[d.normalize()]
        pv_hourly[di, origin_pos[int(f_origins.iloc[i])], :] = forecasts[i]
    if np.isnan(pv_hourly).any():
        raise ValueError("附件3光伏预测存在未映射缺失值")
    return CData(
        dates=dates,
        load=load,
        pv_actual=pv_actual,
        fixed_price=fixed_price,
        realtime_price=realtime_price,
        typical_load=typical_load,
        typical_pv=typical_pv,
        pv_hourly_forecast=pv_hourly,
    )


def pv_forecast_10min(data: CData, day: int, origin: int) -> np.ndarray:
    """仅用本次发布的24个整点预测和发布时刻已观测锚点插值。"""
    oi = ORIGIN_SLOTS.index(origin)
    hourly = data.pv_hourly_forecast[day, oi]
    if origin == 0:
        anchor = data.pv_actual[day - 1, -1] if day > 0 else data.typical_pv[-1]
    else:
        anchor = data.pv_actual[day, origin - 1]
    horizon = SLOTS_PER_DAY - origin
    x = np.arange(25, dtype=float)
    y = np.r_[anchor, hourly]
    target = np.arange(1, horizon + 1, dtype=float) / 6.0
    return np.maximum(np.interp(target, x, y), 0.0)


def _seasonal_curve(values: np.ndarray, typical: np.ndarray, day: int, alpha: float) -> np.ndarray:
    if day <= 0:
        return typical.copy()
    lag1 = values[day - 1]
    lag7 = values[day - 7] if day >= 7 else typical
    return alpha * lag1 + (1.0 - alpha) * lag7


def predict_load(
    data: CData,
    day: int,
    origin: int,
    params: tuple[float, int, float],
) -> np.ndarray:
    """日前季节基线加仅由已实现前缀计算的稳健偏差校正。"""
    alpha, window, rho = params
    baseline = _seasonal_curve(data.load, data.typical_load, day, alpha)
    future = baseline[origin:].copy()
    if origin > 0:
        lo = max(0, origin - window)
        correction = float(np.median(data.load[day, lo:origin] - baseline[lo:origin]))
        lead = np.arange(1, len(future) + 1, dtype=float)
        future += np.power(rho, lead / 36.0) * correction
    return np.maximum(future, 0.0)


LOAD_PARAM_GRID = tuple(
    (a, w, r)
    for a in (0.0, 0.25, 0.5, 0.75, 1.0)
    for w in (6, 18, 36)
    for r in (0.25, 0.5, 0.75, 1.0)
)


def select_load_params(data: CData, day: int, lookback: int = 14) -> tuple[float, int, float]:
    """在预测日之前最近若干完整日上，以真正执行的首个6小时 WAPE 选参。"""
    if day < 2:
        return (0.5, 18, 0.75)
    val_days = range(max(1, day - lookback), day)
    best = None
    for params in LOAD_PARAM_GRID:
        ae = 0.0
        denom = 0.0
        for vd in val_days:
            for origin in ORIGIN_SLOTS:
                pred = predict_load(data, vd, origin, params)[:36]
                actual = data.load[vd, origin : origin + len(pred)]
                ae += float(np.abs(pred - actual).sum())
                denom += float(np.abs(actual).sum())
        score = ae / max(denom, 1e-9)
        if best is None or score < best[0] - 1e-12:
            best = (score, params)
    return best[1]


def predict_price_p1(
    data: CData, day: int, origin: int, alpha: float
) -> np.ndarray:
    baseline = _seasonal_curve(data.realtime_price, data.fixed_price, day, alpha)
    return np.maximum(baseline[origin:], 1e-4)


def predict_price_p2(
    data: CData,
    day: int,
    origin: int,
    params: tuple[int, int, float],
) -> np.ndarray:
    k, window, rho = params
    same_weekday = [day - 7 * j for j in range(1, k + 1) if day - 7 * j >= 0]
    if same_weekday:
        baseline = np.median(data.realtime_price[same_weekday], axis=0)
    elif day > 0:
        baseline = data.realtime_price[day - 1].copy()
    else:
        baseline = data.fixed_price.copy()
    future = baseline[origin:].copy()
    if origin > 0:
        lo = max(0, origin - window)
        correction = float(
            np.median(data.realtime_price[day, lo:origin] - baseline[lo:origin])
        )
        lead = np.arange(1, len(future) + 1, dtype=float)
        future += np.power(rho, lead / 36.0) * correction
    hist_max = (
        float(np.max(data.realtime_price[:day]))
        if day > 0
        else float(np.max(data.fixed_price))
    )
    return np.clip(future, 1e-4, hist_max)


PRICE_P1_GRID = tuple(("P1", a) for a in (0.0, 0.25, 0.5, 0.75, 1.0))
PRICE_P2_GRID = tuple(
    ("P2", (k, w, r))
    for k in (2, 4, 8)
    for w in (6, 18, 36)
    for r in (0.25, 0.5, 0.75, 1.0)
)


def select_price_params(data: CData, day: int, origin: int, lookback: int = 14):
    """仅在当前预测原点以前的完整日上比较 P1/P2 的 WAPE。"""
    if day < 2:
        return ("P1", 0.5)
    val_days = range(max(1, day - lookback), day)
    best = None
    for model, params in PRICE_P1_GRID + PRICE_P2_GRID:
        ae = 0.0
        denom = 0.0
        for vd in val_days:
            pred = (
                predict_price_p1(data, vd, origin, params)
                if model == "P1"
                else predict_price_p2(data, vd, origin, params)
            )
            actual = data.realtime_price[vd, origin:]
            ae += float(np.abs(pred - actual).sum())
            denom += float(np.abs(actual).sum())
        score = ae / max(denom, 1e-9)
        if best is None or score < best[0] - 1e-12:
            best = (score, model, params)
    return (best[1], best[2])


def predict_price(data: CData, day: int, origin: int, selected) -> np.ndarray:
    model, params = selected
    if model == "P1":
        return predict_price_p1(data, day, origin, params)
    return predict_price_p2(data, day, origin, params)


def solve_adjustment_dispatch(
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    price: np.ndarray,
    initial_soc: float,
    old_grid: np.ndarray,
    *,
    terminal_soc: float | None = None,
    binary_mode: bool = True,
    time_limit: float = 120.0,
) -> dict[str, np.ndarray | float | bool | str]:
    """最小化未来增减购结算与预测紧急购电费。"""
    load = np.asarray(load_kwh, float)
    pv = np.asarray(pv_kwh, float)
    tariff = np.asarray(price, float)
    old = np.asarray(old_grid, float)
    n = len(load)
    if not (len(pv) == len(tariff) == len(old) == n):
        raise ValueError("调整模型各输入长度不一致")

    # g,c,d,w,r,E,z,inc,dec
    g = slice(0, n)
    c = slice(n, 2 * n)
    d = slice(2 * n, 3 * n)
    w = slice(3 * n, 4 * n)
    emergency = slice(4 * n, 5 * n)
    e = slice(5 * n, 6 * n + 1)
    z = slice(6 * n + 1, 7 * n + 1)
    inc = slice(7 * n + 1, 8 * n + 1)
    dec = slice(8 * n + 1, 9 * n + 1)
    nvar = 9 * n + 1

    obj = np.zeros(nvar)
    obj[emergency] = 5.0 * tariff
    obj[inc] = 1.5 * tariff
    obj[dec] = -0.5 * tariff
    lower = np.zeros(nvar)
    upper = np.full(nvar, np.inf)
    upper[c] = INTERVAL_LIMIT
    upper[d] = INTERVAL_LIMIT
    upper[w] = pv
    lower[e], upper[e] = SOC_MIN, SOC_MAX
    lower[e.start] = upper[e.start] = initial_soc
    if terminal_soc is not None:
        lower[e.stop - 1] = upper[e.stop - 1] = terminal_soc
    upper[z] = 1.0

    # 能量平衡、SOC、计划差额恒等式。
    aeq = lil_matrix((3 * n, nvar), dtype=float)
    beq = np.zeros(3 * n)
    for t in range(n):
        aeq[t, g.start + t] = 1.0
        aeq[t, c.start + t] = -1.0
        aeq[t, d.start + t] = 1.0
        aeq[t, w.start + t] = -1.0
        aeq[t, emergency.start + t] = 1.0
        beq[t] = load[t] - pv[t]

        row = n + t
        aeq[row, e.start + t] = -1.0
        aeq[row, e.start + t + 1] = 1.0
        aeq[row, c.start + t] = -ETA_C
        aeq[row, d.start + t] = 1.0 / ETA_D

        row = 2 * n + t
        aeq[row, g.start + t] = 1.0
        aeq[row, inc.start + t] = -1.0
        aeq[row, dec.start + t] = 1.0
        beq[row] = old[t]

    aub = lil_matrix((2 * n, nvar), dtype=float)
    bub = np.zeros(2 * n)
    for t in range(n):
        aub[t, c.start + t] = 1.0
        aub[t, z.start + t] = -INTERVAL_LIMIT
        aub[n + t, d.start + t] = 1.0
        aub[n + t, z.start + t] = INTERVAL_LIMIT
        bub[n + t] = INTERVAL_LIMIT

    integrality = np.zeros(nvar, dtype=int)
    if binary_mode:
        integrality[z] = 1
    started = perf_counter()
    raw = milp(
        obj,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=[
            LinearConstraint(aeq.tocsr(), beq, beq),
            LinearConstraint(aub.tocsr(), -np.inf, bub),
        ],
        options={"time_limit": time_limit, "mip_rel_gap": 1e-8},
    )
    elapsed = perf_counter() - started
    if raw.x is None:
        raise RuntimeError(f"调整MILP求解失败：{raw.message}")
    x = raw.x
    balance = x[g] + pv + x[d] + x[emergency] - load - x[c] - x[w]
    soc_res = x[e][1:] - x[e][:-1] - ETA_C * x[c] + x[d] / ETA_D
    return {
        "grid": x[g],
        "charge": x[c],
        "discharge": x[d],
        "curtailment": x[w],
        "predicted_emergency": x[emergency],
        "soc": x[e],
        "increase": x[inc],
        "decrease": x[dec],
        "objective": float(raw.fun),
        "solve_seconds": elapsed,
        "success": bool(raw.success),
        "message": str(raw.message),
        "max_balance_residual": float(np.max(np.abs(balance))),
        "max_soc_residual": float(np.max(np.abs(soc_res))),
    }


def _initial_dispatch(load, pv, price, initial_soc, terminal_soc=None):
    raw = solve_deterministic_dispatch(
        load,
        pv,
        price,
        initial_soc,
        terminal_soc=terminal_soc,
        allow_emergency=True,
        emergency_multiplier=5.0,
        binary_mode=True,
    )
    return {
        "grid": raw.grid,
        "charge": raw.charge,
        "discharge": raw.discharge,
        "curtailment": raw.curtailment,
        "predicted_emergency": raw.emergency,
        "soc": raw.soc,
        "increase": np.zeros_like(raw.grid),
        "decrease": np.zeros_like(raw.grid),
        "objective": raw.objective,
        "solve_seconds": raw.solve_seconds,
        "success": raw.success,
        "message": raw.message,
        "max_balance_residual": raw.max_balance_residual,
        "max_soc_residual": raw.max_soc_residual,
    }


def simulate_mpc(
    data: CData,
    day_indices: Iterable[int],
    initial_soc: float,
    origins: tuple[int, ...],
    planning_price_provider: Callable[[int, int], np.ndarray],
    settlement_price: np.ndarray,
    *,
    keep_versions: bool = False,
) -> tuple[dict[str, np.ndarray], float, list[dict]]:
    """逐日、逐预测原点顺序回测，严格冻结已执行时段。"""
    days = list(day_indices)
    nday = len(days)
    shape = (nday, SLOTS_PER_DAY)
    out = {
        "initial_grid": np.zeros(shape),
        "effective_grid": np.zeros(shape),
        "charge": np.zeros(shape),
        "discharge": np.zeros(shape),
        "emergency": np.zeros(shape),
        "curtailment": np.zeros(shape),
        "soc": np.zeros((nday, SLOTS_PER_DAY + 1)),
        "planned_cost": np.zeros(nday),
        "adjustment_cost": np.zeros(nday),
        "emergency_cost": np.zeros(nday),
        "total_cost": np.zeros(nday),
        "solve_seconds": np.zeros(nday),
        "max_balance_residual": np.zeros(nday),
        "max_soc_residual": np.zeros(nday),
    }
    versions: list[dict] = []
    current_soc = float(initial_soc)
    selected_load_params: dict[int, tuple[float, int, float]] = {}
    for row, day in enumerate(days):
        selected_load_params[day] = select_load_params(data, day)
        g_eff = np.zeros(SLOTS_PER_DAY)
        c_eff = np.zeros(SLOTS_PER_DAY)
        d_eff = np.zeros(SLOTS_PER_DAY)
        day_soc = np.zeros(SLOTS_PER_DAY + 1)
        day_soc[0] = current_soc
        day_terminal_target = current_soc
        day_versions = []
        for oi, origin in enumerate(origins):
            next_origin = origins[oi + 1] if oi + 1 < len(origins) else SLOTS_PER_DAY
            load_hat = predict_load(data, day, origin, selected_load_params[day])
            pv_hat = pv_forecast_10min(data, day, origin)
            price_hat = planning_price_provider(day, origin)
            if not (len(load_hat) == len(pv_hat) == len(price_hat) == SLOTS_PER_DAY - origin):
                raise ValueError("预测时域长度不一致")
            if origin == 0:
                # 用48小时延伸窗估计跨日续接价值，仅执行前24小时。
                # 第二天曲线由当时可见的当前预测重复得到，不读取次日实际值；
                # 延伸窗末端回到窗初SOC，故日末SOC可随调度自然变化。
                tail_load = load_hat.copy()
                tail_pv = pv_hat.copy()
                tail_price = price_hat.copy()
                solved_long = _initial_dispatch(
                    np.r_[load_hat, tail_load],
                    np.r_[pv_hat, tail_pv],
                    np.r_[price_hat, tail_price],
                    current_soc,
                    terminal_soc=current_soc,
                )
                solved = {
                    key: (value[:SLOTS_PER_DAY] if isinstance(value, np.ndarray) and key != "soc" else value)
                    for key, value in solved_long.items()
                }
                solved["soc"] = solved_long["soc"][: SLOTS_PER_DAY + 1]
                day_terminal_target = float(solved_long["soc"][SLOTS_PER_DAY])
                g_eff[:] = solved["grid"]
                c_eff[:] = solved["charge"]
                d_eff[:] = solved["discharge"]
                out["initial_grid"][row] = g_eff
                old = np.zeros_like(g_eff)
            else:
                old = g_eff.copy()
                solved = solve_adjustment_dispatch(
                    load_hat,
                    pv_hat,
                    price_hat,
                    day_soc[origin],
                    old[origin:],
                    terminal_soc=day_terminal_target,
                )
                g_eff[origin:] = solved["grid"]
                c_eff[origin:] = solved["charge"]
                d_eff[origin:] = solved["discharge"]
                delta_plus = np.maximum(g_eff[origin:] - old[origin:], 0.0)
                delta_minus = np.maximum(old[origin:] - g_eff[origin:], 0.0)
                settle = settlement_price[day, origin:]
                out["adjustment_cost"][row] += float(
                    np.sum(1.5 * settle * delta_plus - 0.5 * settle * delta_minus)
                )
            out["solve_seconds"][row] += float(solved["solve_seconds"])
            out["max_balance_residual"][row] = max(
                out["max_balance_residual"][row], float(solved["max_balance_residual"])
            )
            out["max_soc_residual"][row] = max(
                out["max_soc_residual"][row], float(solved["max_soc_residual"])
            )
            if keep_versions:
                day_versions.append(
                    {
                        "origin": origin,
                        "old_grid": old[origin:].copy(),
                        "new_grid": g_eff[origin:].copy(),
                        "load_forecast": load_hat.copy(),
                        "pv_forecast": pv_hat.copy(),
                        "price_forecast": price_hat.copy(),
                    }
                )

            # 只执行到下一次允许更新的时刻；实际偏差仅用紧急购电/弃电平衡。
            sl = slice(origin, next_origin)
            supply_without_rec = g_eff[sl] + data.pv_actual[day, sl] + d_eff[sl]
            demand = data.load[day, sl] + c_eff[sl]
            emergency = np.maximum(demand - supply_without_rec, 0.0)
            curtailment = np.maximum(supply_without_rec - demand, 0.0)
            out["emergency"][row, sl] = emergency
            out["curtailment"][row, sl] = curtailment
            for t in range(origin, next_origin):
                day_soc[t + 1] = day_soc[t] + ETA_C * c_eff[t] - d_eff[t] / ETA_D

        out["effective_grid"][row] = g_eff
        out["charge"][row] = c_eff
        out["discharge"][row] = d_eff
        out["soc"][row] = day_soc
        prices = settlement_price[day]
        out["planned_cost"][row] = float(np.sum(prices * out["initial_grid"][row]))
        out["emergency_cost"][row] = float(np.sum(5.0 * prices * out["emergency"][row]))
        out["total_cost"][row] = (
            out["planned_cost"][row]
            + out["adjustment_cost"][row]
            + out["emergency_cost"][row]
        )
        actual_balance = (
            g_eff
            + data.pv_actual[day]
            + d_eff
            + out["emergency"][row]
            - data.load[day]
            - c_eff
            - out["curtailment"][row]
        )
        out["max_balance_residual"][row] = max(
            out["max_balance_residual"][row], float(np.max(np.abs(actual_balance)))
        )
        soc_res = day_soc[1:] - day_soc[:-1] - ETA_C * c_eff + d_eff / ETA_D
        out["max_soc_residual"][row] = max(
            out["max_soc_residual"][row], float(np.max(np.abs(soc_res)))
        )
        if np.min(day_soc) < SOC_MIN - 1e-5 or np.max(day_soc) > SOC_MAX + 1e-5:
            raise AssertionError("SOC越界")
        if np.max(np.minimum(c_eff, d_eff)) > 1e-5:
            raise AssertionError("出现同时充放电")
        current_soc = float(day_soc[-1])
        if keep_versions:
            versions.append({"day": day, "versions": day_versions})
    return out, current_soc, versions


def summarize_run(arrays: dict[str, np.ndarray], start_row: int = 0) -> dict[str, float]:
    s = slice(start_row, None)
    return {
        "total_cost_yuan": float(np.sum(arrays["total_cost"][s])),
        "planned_cost_yuan": float(np.sum(arrays["planned_cost"][s])),
        "adjustment_cost_yuan": float(np.sum(arrays["adjustment_cost"][s])),
        "emergency_cost_yuan": float(np.sum(arrays["emergency_cost"][s])),
        "emergency_energy_kwh": float(np.sum(arrays["emergency"][s])),
        "curtailment_energy_kwh": float(np.sum(arrays["curtailment"][s])),
        "grid_energy_kwh": float(np.sum(arrays["effective_grid"][s])),
        "minimum_soc_kwh": float(np.min(arrays["soc"][s])),
        "maximum_soc_kwh": float(np.max(arrays["soc"][s])),
        "solve_seconds": float(np.sum(arrays["solve_seconds"][s])),
        "max_balance_residual_kwh": float(np.max(arrays["max_balance_residual"][s])),
        "max_soc_residual_kwh": float(np.max(arrays["max_soc_residual"][s])),
    }
