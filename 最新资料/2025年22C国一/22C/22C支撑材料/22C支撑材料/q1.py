import os, re, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.regression.mixed_linear_model import MixedLM
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")

plt.rcParams['font.sans-serif'] = [
    'SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei',
    'Noto Sans CJK SC', 'Source Han Sans CN', 'DejaVu Sans'
]
plt.rcParams['axes.unicode_minus'] = False

# 统一用浅色风格
plt.style.use("seaborn-v0_8-pastel")

EXCEL_PATH = "./附件.xlsx"
SHEET_NAME = "男胎检测数据"
OUT_DIR = "./"
os.makedirs(OUT_DIR, exist_ok=True)

# --- 小工具函数 ---
def find_col(cols, candidates):
    cols = list(cols)
    for cand in candidates:
        if cand in cols:
            return cand
    def norm(s): return re.sub(r"\s+", "", str(s)).lower()
    nmap = {c: norm(c) for c in cols}
    for cand in candidates:
        nc = norm(cand)
        for c, v in nmap.items():
            if nc in v or v in nc:
                return c
    return None

def parse_weeks(s):
    if pd.isna(s): return np.nan
    t = str(s).strip().lower()
    m = re.match(r"^\s*(\d+)\s*w(?:\s*\+\s*(\d+))?\s*$", t)
    if m:
        return int(m.group(1)) + (int(m.group(2))/7.0 if m.group(2) else 0.0)
    m2 = re.match(r"^\s*(\d+)\s*\+\s*(\d+)\s*$", t)
    if m2:
        return int(m2.group(1)) + int(m2.group(2))/7.0
    m3 = re.match(r"^\s*(\d+)\s*周(?:\s*\+\s*(\d+)\s*天)?\s*$", t)
    if m3:
        return int(m3.group(1)) + (int(m3.group(2))/7.0 if m3.group(2) else 0.0)
    try:
        return float(t)
    except:
        return np.nan

def to_float_strip_percent(x):
    if pd.isna(x): return np.nan
    s = str(x).replace("%","").replace(",","").strip()
    try:
        return float(s)
    except:
        return np.nan

def normalize_rate(series):
    v = pd.to_numeric(series.astype(str).str.replace("%","").str.replace(",",""), errors="coerce")
    return v/100.0 if (np.nanmax(v) > 1.5) else v

def zscore(x):
    mu = np.nanmean(x)
    sd = np.nanstd(x, ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return (x - mu)
    return (x - mu) / sd

def inv_logit(x):
    return 1.0 / (1.0 + np.exp(-x))

# --- 读数据 ---
df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

col_id   = find_col(df.columns, ["孕妇代码", "受检人编码", "样本编号"])
col_age  = find_col(df.columns, ["年龄", "孕妇年龄"])
col_bmi  = find_col(df.columns, ["孕妇BMI", "BMI"])
col_gw   = find_col(df.columns, ["检测孕周", "孕周"])
col_y    = find_col(df.columns, ["Y染色体浓度", "Y 浓度"])
col_gc   = find_col(df.columns, ["GC含量", "测序GC含量"])
col_map  = find_col(df.columns, ["在参考基因组上比对的比例", "比对比例"])
col_dup  = find_col(df.columns, ["重复读段的比例", "重复率"])
col_uniq = find_col(df.columns, ["唯一比对的读段数", "唯一比对读段数", "唯一比对的读段数  "])

# --- 数据清理 ---
dat = pd.DataFrame({
    "id":  df[col_id],
    "age": pd.to_numeric(df[col_age], errors="coerce"),
    "bmi": pd.to_numeric(df[col_bmi], errors="coerce"),
    "gw":  df[col_gw].map(parse_weeks),
    "y":   df[col_y].map(to_float_strip_percent),
    "gc":  pd.to_numeric(df[col_gc], errors="coerce"),
    "map": normalize_rate(df[col_map]),
    "dup": normalize_rate(df[col_dup]),
    "uniq": pd.to_numeric(df[col_uniq], errors="coerce"),
})
dat = dat.dropna(subset=["id","age","bmi","gw","y","gc","map","dup","uniq"]).copy()

eps = 1e-4
dat["y_clipped"] = dat["y"].clip(eps, 1-eps)
dat["logit_y"] = np.log(dat["y_clipped"]/(1-dat["y_clipped"]))
dat["log_uniq"] = np.log(dat["uniq"].clip(lower=1))
dat["gw_x_bmi"] = dat["gw"] * dat["bmi"]

for c in ["gw","bmi","gw_x_bmi","age","gc","map","dup","log_uniq"]:
    dat[c+"_z"] = zscore(dat[c])

# --- 模型 ---
X_cols = ["gw_z","bmi_z","gw_x_bmi_z","age_z","gc_z","map_z","dup_z","log_uniq_z"]
X = sm.add_constant(dat[X_cols])
y_vec = dat["logit_y"]
groups = dat["id"]

fit_info = {}
used_model = None
try:
    model = MixedLM(endog=y_vec, exog=X, groups=groups)
    result = model.fit(reml=False, method="lbfgs", maxiter=200)
    used_model = "MixedLM"
    fit_info["converged"] = bool(result.converged)
    fit_info["nobs"] = int(result.nobs)
except Exception as e:
    used_model = "OLS_fallback"
    fit_info["MixedLM_error"] = str(e)
    result = sm.OLS(y_vec, X).fit()

# --- R² ---
if used_model == "MixedLM":
    yhat_fixed = np.asarray(np.dot(X, result.fe_params))
    var_fixed = np.var(yhat_fixed, ddof=1)
    try:
        var_random = float(result.cov_re.iloc[0,0])
    except Exception:
        var_random = 0.0
    resid = y_vec - result.fittedvalues
    var_resid = np.var(resid, ddof=1)
    total = var_fixed + var_random + var_resid
    r2_marginal = float(var_fixed/total) if total>0 else np.nan
    r2_conditional = float((var_fixed+var_random)/total) if total>0 else np.nan
else:
    resid = y_vec - result.fittedvalues
    r2_marginal = float(result.rsquared) if hasattr(result, "rsquared") else np.nan
    r2_conditional = r2_marginal

# --- 模型摘要 ---
summary_table = result.summary().as_text()
summary_txt_path = os.path.join(OUT_DIR, "model_summary_q1.txt")
with open(summary_txt_path, "w", encoding="utf-8") as f:
    f.write(f"用的模型: {used_model}\n")
    f.write(f"模型情况: {fit_info}\n")
    f.write(f"边际R²(approx): {r2_marginal}\n条件R²(approx): {r2_conditional}\n\n")
    f.write(summary_table)

# --- 图表（你已有） ---
plt.figure()
sm.ProbPlot(resid).qqplot(line='45', color="lightcoral")
plt.title("残差QQ图")
plt.savefig(os.path.join(OUT_DIR, "q_q_resid.png"), dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.scatter(result.fittedvalues, resid, s=15, color="mediumseagreen", alpha=0.7)
plt.axhline(0, linestyle="--", color="gray")
plt.title("残差 vs 拟合值")
plt.savefig(os.path.join(OUT_DIR, "resid_vs_fitted.png"), dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.hist(dat["y"], bins=40, color="lightsalmon", edgecolor="k", alpha=0.8)
plt.title("Y浓度分布")
plt.savefig(os.path.join(OUT_DIR, "hist_y.png"), dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.hist(dat["gw"], bins=30, color="plum", edgecolor="k", alpha=0.8)
plt.title("孕周分布")
plt.savefig(os.path.join(OUT_DIR, "hist_gw.png"), dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.scatter(dat["gw"], dat["y"], s=12, color="lightskyblue", alpha=0.7)
plt.title("Y vs 孕周")
plt.savefig(os.path.join(OUT_DIR, "y_vs_gw_scatter.png"), dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
plt.scatter(dat["bmi"], dat["y"], s=12, color="khaki", alpha=0.7)
plt.title("Y vs BMI")
plt.savefig(os.path.join(OUT_DIR, "y_vs_bmi_scatter.png"), dpi=150, bbox_inches="tight")
plt.close()

plt.figure()
corr = dat[["y","gw","bmi","age","gc","map","dup","log_uniq"]].corr()
plt.imshow(corr, cmap="RdPu", interpolation="nearest")
plt.title("相关矩阵")
plt.colorbar()
plt.savefig(os.path.join(OUT_DIR, "corr_heatmap.png"), dpi=150, bbox_inches="tight")
plt.close()

# === 新增 1：导出“系数+显著性+OR”表 ===
if used_model == "MixedLM":
    fe = result.fe_params  # 固定效应系数
    se = result.bse_fe if hasattr(result, "bse_fe") else result.bse[fe.index]
    pv = result.pvalues[fe.index] if hasattr(result, "pvalues") else pd.Series(np.nan, index=fe.index)
    ci = result.conf_int().loc[fe.index] if hasattr(result, "conf_int") else pd.DataFrame(np.nan, index=fe.index, columns=[0,1])
else:
    fe = result.params
    se = result.bse
    pv = result.pvalues
    ci = result.conf_int()

coef_df = pd.DataFrame({
    "term": fe.index,
    "coef": fe.values,
    "std_err": se.values,
    "stat": (fe/se).values,             # z 或 t
    "p_value": pv.values,
    "ci_low": ci.iloc[:,0].values,
    "ci_high": ci.iloc[:,1].values
})

# 增加 OR 与其 CI（针对 logit 链接）
coef_df["OR"] = np.exp(coef_df["coef"])
coef_df["OR_ci_low"] = np.exp(coef_df["ci_low"])
coef_df["OR_ci_high"] = np.exp(coef_df["ci_high"])

# 排序：把 const 放顶部
coef_df["order"] = (coef_df["term"] != "const").astype(int)
coef_df = coef_df.sort_values(["order", "term"]).drop(columns="order").reset_index(drop=True)

coef_csv_path = os.path.join(OUT_DIR, "coef_table_q1.csv")
coef_df.to_csv(coef_csv_path, index=False, encoding="utf-8-sig")

# === 新增 2：输出显式模型方程（标准化自变量版本） ===
# 形式：logit(y) = beta0 + sum beta_i * z(X_i)
eq_lines = []
eq_lines.append("logit(y) = " + " + ".join([f"{row.coef:.6g}*{row.term}" if row.term!="const" else f"{row.coef:.6g}" for _,row in coef_df.iterrows()]))
eq_lines.append("")
eq_lines.append("说明：自变量均为标准化（z-score）后的变量：gw_z, bmi_z, gw_x_bmi_z, age_z, gc_z, map_z, dup_z, log_uniq_z。")
eq_lines.append("系数含义：在其他变量保持均值（z=0）时，自变量每提高1个标准差，logit(y) 增加 beta_i，对应 OR = exp(beta_i)。")
with open(os.path.join(OUT_DIR, "model_equation_q1.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(eq_lines))

# === 新增 3：VIF（多重共线性检查） ===
# 对标准化后的 X（去掉常数项）做 VIF
X_no_const = dat[[c for c in X_cols]]  # 这些列本身是 *_z
X_for_vif = sm.add_constant(X_no_const, has_constant="add").drop(columns=["const"])
vif_rows = []
for i, name in enumerate(X_for_vif.columns):
    vif_val = variance_inflation_factor(X_for_vif.values, i)
    vif_rows.append({"term": name, "VIF": vif_val})
vif_df = pd.DataFrame(vif_rows).sort_values("VIF", ascending=False)
vif_csv_path = os.path.join(OUT_DIR, "vif_q1.csv")
vif_df.to_csv(vif_csv_path, index=False, encoding="utf-8-sig")

# === 新增 4：系数森林图（不含常数项） ===
plot_df = coef_df[coef_df["term"]!="const"].copy()
plt.figure(figsize=(7, 0.6*len(plot_df)+1))
ypos = np.arange(len(plot_df))[::-1]
plt.errorbar(plot_df["coef"], ypos, xerr=[plot_df["coef"]-plot_df["ci_low"], plot_df["ci_high"]-plot_df["coef"]],
             fmt="o", capsize=3)
plt.yticks(ypos, plot_df["term"])
plt.axvline(0, ls="--", color="gray", lw=1)
plt.xlabel("系数估计（logit 量纲）")
plt.title("固定效应系数与95%置信区间")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "coef_forest_q1.png"), dpi=150, bbox_inches="tight")
plt.close()

# === 新增 5：条件效应图（其余变量固定为均值） ===
# gw 的效应：bmi_z=0，其它 z=0
gw_grid = np.linspace(dat["gw_z"].min(), dat["gw_z"].max(), 100)
# 构造输入行
def predict_from_z(gw_z, bmi_z, age_z=0, gc_z=0, map_z=0, dup_z=0, log_uniq_z=0, gw_x_bmi_z=None):
    # gw_x_bmi_z 并非 gw_z*bmi_z（因标准化），直接作为一个 z 变量输入
    row = pd.DataFrame({
        "const":[1.0],
        "gw_z":[gw_z],
        "bmi_z":[bmi_z],
        "gw_x_bmi_z":[gw_x_bmi_z if gw_x_bmi_z is not None else 0.0],
        "age_z":[age_z],
        "gc_z":[gc_z],
        "map_z":[map_z],
        "dup_z":[dup_z],
        "log_uniq_z":[log_uniq_z]
    })
    beta = result.fe_params if used_model=="MixedLM" else result.params
    logit_hat = float(np.dot(row[beta.index], beta))
    return inv_logit(logit_hat)

# 绘 gw
yhat_gw = [predict_from_z(gz, 0.0, gw_x_bmi_z=0.0) for gz in gw_grid]
plt.figure()
plt.plot(gw_grid, yhat_gw)
plt.xlabel("gw_z（孕周标准化）")
plt.ylabel("预测 Y 浓度")
plt.title("在其他变量为均值时：孕周对 Y 浓度的影响")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "effect_gw_q1.png"), dpi=150, bbox_inches="tight")
plt.close()

# 绘 bmi（取 gw_x_bmi_z=0 简化查看主效应）
bmi_grid = np.linspace(dat["bmi_z"].min(), dat["bmi_z"].max(), 100)
yhat_bmi = [predict_from_z(0.0, bz, gw_x_bmi_z=0.0) for bz in bmi_grid]
plt.figure()
plt.plot(bmi_grid, yhat_bmi)
plt.xlabel("bmi_z（BMI 标准化）")
plt.ylabel("预测 Y 浓度")
plt.title("在其他变量为均值时：BMI 对 Y 浓度的影响（不含交互项变化）")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "effect_bmi_q1.png"), dpi=150, bbox_inches="tight")
plt.close()
