"""微网调度的公共混合整数线性规划骨架。

变量统一使用每个离散时段内的电量（kWh）。储能充电量为交流母线侧
输入电量，放电量为交流母线侧输出电量，因此状态转移为
E[t+1] = E[t] + eta_c * charge[t] - discharge[t] / eta_d。
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


@dataclass
class DispatchResult:
    grid: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    curtailment: np.ndarray
    emergency: np.ndarray
    soc: np.ndarray
    mode: np.ndarray
    objective: float
    solve_seconds: float
    max_balance_residual: float
    max_soc_residual: float
    success: bool
    message: str


def solve_deterministic_dispatch(
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    price: np.ndarray,
    initial_soc: float,
    *,
    terminal_soc: float | None = None,
    eta_c: float = 0.9,
    eta_d: float = 0.9,
    soc_min: float = 1200.0,
    soc_max: float = 10800.0,
    max_power_kw: float = 5000.0,
    step_hours: float = 1.0 / 6.0,
    allow_emergency: bool = False,
    emergency_multiplier: float = 5.0,
    binary_mode: bool = True,
    time_limit: float = 120.0,
) -> DispatchResult:
    """求解一个确定性时域内的购电与储能联合调度。"""

    load = np.asarray(load_kwh, dtype=float)
    pv = np.asarray(pv_kwh, dtype=float)
    tariff = np.asarray(price, dtype=float)
    if not (load.ndim == pv.ndim == tariff.ndim == 1):
        raise ValueError("load_kwh、pv_kwh和price必须是一维数组")
    if not (len(load) == len(pv) == len(tariff)):
        raise ValueError("负荷、光伏和电价长度必须一致")
    if np.any(load < 0) or np.any(pv < 0) or np.any(tariff < 0):
        raise ValueError("负荷、光伏和电价不得为负")

    n = len(load)
    # g, c, d, q(弃光), r(紧急购电), E[0:n], z
    g = slice(0, n)
    c = slice(n, 2 * n)
    d = slice(2 * n, 3 * n)
    q = slice(3 * n, 4 * n)
    r = slice(4 * n, 5 * n)
    e = slice(5 * n, 6 * n + 1)
    z = slice(6 * n + 1, 7 * n + 1)
    nvar = 7 * n + 1

    obj = np.zeros(nvar)
    obj[g] = tariff
    obj[r] = emergency_multiplier * tariff

    lower = np.zeros(nvar)
    upper = np.full(nvar, np.inf)
    interval_limit = max_power_kw * step_hours
    upper[c] = interval_limit
    upper[d] = interval_limit
    upper[q] = pv
    upper[r] = np.inf if allow_emergency else 0.0
    lower[e], upper[e] = soc_min, soc_max
    lower[5 * n] = upper[5 * n] = initial_soc
    if terminal_soc is not None:
        lower[6 * n] = upper[6 * n] = terminal_soc
    upper[z] = 1.0

    # 供需平衡和SOC状态转移。
    aeq = lil_matrix((2 * n, nvar), dtype=float)
    beq = np.zeros(2 * n)
    for t in range(n):
        aeq[t, g.start + t] = 1.0
        aeq[t, c.start + t] = -1.0
        aeq[t, d.start + t] = 1.0
        aeq[t, q.start + t] = -1.0
        aeq[t, r.start + t] = 1.0
        beq[t] = load[t] - pv[t]

        row = n + t
        aeq[row, e.start + t] = -1.0
        aeq[row, e.start + t + 1] = 1.0
        aeq[row, c.start + t] = -eta_c
        aeq[row, d.start + t] = 1.0 / eta_d

    # c_t <= M z_t, d_t <= M(1-z_t)。LP对照时z连续。
    aub = lil_matrix((2 * n, nvar), dtype=float)
    bub = np.zeros(2 * n)
    for t in range(n):
        aub[t, c.start + t] = 1.0
        aub[t, z.start + t] = -interval_limit
        aub[n + t, d.start + t] = 1.0
        aub[n + t, z.start + t] = interval_limit
        bub[n + t] = interval_limit

    integrality = np.zeros(nvar, dtype=int)
    if binary_mode:
        integrality[z] = 1

    constraints = [
        LinearConstraint(aeq.tocsr(), beq, beq),
        LinearConstraint(aub.tocsr(), -np.inf, bub),
    ]
    started = perf_counter()
    raw = milp(
        obj,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=constraints,
        options={"time_limit": time_limit, "mip_rel_gap": 1e-8},
    )
    elapsed = perf_counter() - started
    if raw.x is None:
        raise RuntimeError(f"MILP求解失败：{raw.message}")

    x = raw.x
    grid = x[g]
    charge = x[c]
    discharge = x[d]
    curtailment = x[q]
    emergency = x[r]
    soc = x[e]
    mode = x[z]
    balance_residual = grid + pv + discharge + emergency - load - charge - curtailment
    soc_residual = soc[1:] - soc[:-1] - eta_c * charge + discharge / eta_d
    return DispatchResult(
        grid=grid,
        charge=charge,
        discharge=discharge,
        curtailment=curtailment,
        emergency=emergency,
        soc=soc,
        mode=mode,
        objective=float(raw.fun),
        solve_seconds=elapsed,
        max_balance_residual=float(np.max(np.abs(balance_residual))),
        max_soc_residual=float(np.max(np.abs(soc_residual))),
        success=bool(raw.success),
        message=str(raw.message),
    )

