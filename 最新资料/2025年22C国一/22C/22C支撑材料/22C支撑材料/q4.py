# -*- coding: utf-8 -*-
"""
女胎异常判定 - TabNet + FocalLoss + 分组分层划分 + F2阈值优化
"""

# 导入依赖
try:
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import torch
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 roc_curve, precision_recall_curve,
                                 confusion_matrix, classification_report,
                                 fbeta_score)
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import calibration_curve
    from sklearn.linear_model import LogisticRegression
    from pytorch_tabnet.tab_model import TabNetClassifier
except Exception:
    import subprocess, sys
    pkgs = ["numpy","pandas","matplotlib","seaborn","scikit-learn>=1.1",
            "torch","pytorch-tabnet","openpyxl"]
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + pkgs)
    # 重新导入
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import torch
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 roc_curve, precision_recall_curve,
                                 confusion_matrix, classification_report,
                                 fbeta_score)
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import calibration_curve
    from sklearn.linear_model import LogisticRegression
    from pytorch_tabnet.tab_model import TabNetClassifier

import os, re, warnings, json, random
warnings.filterwarnings("ignore")
sns.set_style("whitegrid")
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def set_seed(seed=2025):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(2025)

# 数据路径配置
DATA_CSV = "./女胎_清洗标准化.csv"
DATA_XLSX = "./附件.xlsx"
OUTPUT_DIR = "./outputs_q4_tabnet_improved"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 工具函数
def find_column(cols, candidates):
    for c in candidates:
        if c in cols: return c
    for c in candidates:
        pattern = re.compile(c.replace(" ", "").replace("_", ""))
        for col in cols:
            if re.sub(r"[ _]", "", str(col)) == c or re.search(pattern, str(col).replace(" ", "")):
                return col
    return None

def parse_gestational_week(x):
    if pd.isna(x): return np.nan
    s = str(x).strip().lower()
    try:
        if re.fullmatch(r"\d+(\.\d+)?", s):
            return float(s)
        m = re.match(r"(\d+)\s*(w|周)?\s*\+?\s*(\d+)", s)
        if m:
            return float(m.group(1)) + float(m.group(3))/7.0
        m2 = re.match(r"(\d+)\s*周\s*(\d+)\s*天", s)
        if m2:
            return float(m2.group(1)) + float(m2.group(2))/7.0
    except:
        return np.nan
    return np.nan

def convert_to_float(x):
    if pd.isna(x): return np.nan
    s = str(x).strip()
    try:
        if s.endswith("%"): return float(s[:-1]) / 100.0
        return float(s)
    except:
        return np.nan

def load_data():
    if os.path.exists(DATA_CSV):
        return pd.read_csv(DATA_CSV)
    if not os.path.exists(DATA_XLSX):
        raise FileNotFoundError("数据文件未找到")
    xls = pd.ExcelFile(DATA_XLSX)
    sheet_name = None
    for sh in xls.sheet_names:
        if "女" in sh or "female" in sh.lower():
            sheet_name = sh; break
    if sheet_name is None:
        sheet_name = xls.sheet_names[1] if len(xls.sheet_names) > 1 else xls.sheet_names[0]
    return pd.read_excel(DATA_XLSX, sheet_name=sheet_name)

# 数据加载和预处理
df_raw = load_data()
df_raw = df_raw.rename(columns=lambda c: str(c).strip())
cols = set(df_raw.columns)

# 列名映射
col_mapping = {
    "AB": ["染色体的非整倍体","AB","非整倍体"],
    "Z13": ["13号染色体的Z值","13 号染色体的 Z 值","Q","Z13"],
    "Z18": ["18号染色体的Z值","18 号染色体的 Z 值","R","Z18"],
    "Z21": ["21号染色体的Z值","21 号染色体的 Z 值","S","Z21"],
    "ZX": ["X染色体的Z值","X 染色体的 Z 值","T","ZX"],
    "X_conc": ["X染色体浓度","X 染色体浓度","W","X_conc"],
    "GC_total": ["GC含量","GC 含量","P","GC_total"],
    "GC13": ["13号染色体的GC含量","13 号染色体的 GC 含量","X","GC13"],
    "GC18": ["18号染色体的GC含量","18 号染色体的 GC 含量","Y","GC18"],
    "GC21": ["21号染色体的GC含量","21 号染色体的 GC 含量","Z","GC21"],
    "filter_ratio": ["被过滤掉读段数的比例","被过滤掉的读段数占总读段数的比例","AA","filter_ratio"],
    "reads_total": ["原始测序数据的总读段数（个）","原始测序数据的总读段数","原始读段数","L","reads_total"],
    "map_ratio": ["在参考基因组上比对的比例","总读段数中在参考基因组上比对的比例","M","map_ratio"],
    "dup_ratio": ["重复读段的比例","总读段数中重复读段的比例","N","dup_ratio"],
    "reads_unique": ["唯一比对的读段数（个）","唯一比对的读段数","O","reads_unique"],
    "age": ["孕妇年龄","年龄","C","age"],
    "height": ["孕妇身高","身高","D","height"],
    "weight": ["孕妇体重","体重","E","weight"],
    "BMI": ["孕妇BMI","孕妇 BMI 指标","BMI","K","bmi"],
    "week": ["检测孕周","孕妇本次检测时的孕周（周数+天数）","J","week"],
    "pid": ["孕妇代码","样本序号","B","A","pid"]
}

# 查找并重命名列
found_cols = {}
for new_name, candidates in col_mapping.items():
    found_col = find_column(cols, candidates)
    if found_col:
        found_cols[found_col] = new_name

df = df_raw[[col for col in found_cols.keys()]].copy()
df.rename(columns=found_cols, inplace=True)

# 创建标签
def create_label(x):
    if pd.isna(x) or str(x).strip() == "": return 0
    s = str(x).upper()
    return 1 if any(k in s for k in ["T13","T18","T21"]) else 0

if "AB" not in df.columns:
    raise ValueError("未找到AB列")
df["label"] = df["AB"].apply(create_label).astype(int)
print(f"数据形状: {df.shape}")
print(f"标签分布: {df['label'].value_counts()}")

# 特征工程
if "week" in df.columns:
    df["week_num"] = df["week"].apply(parse_gestational_week)

# 数据类型转换
percentage_cols = ["GC_total","GC13","GC18","GC21","filter_ratio","map_ratio","dup_ratio","X_conc"]
for c in percentage_cols:
    if c in df.columns: df[c] = df[c].apply(convert_to_float)

count_cols = ["reads_total","reads_unique"]
for c in count_cols:
    if c in df.columns: df[c] = df[c].apply(convert_to_float)

numeric_cols = ["Z13","Z18","Z21","ZX","BMI","age","height","weight"]
for c in numeric_cols:
    if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")

# 派生特征
if all(c in df.columns for c in ["reads_unique","reads_total"]):
    df["uniq_ratio"] = df["reads_unique"]/df["reads_total"]

for c in ["reads_total","reads_unique"]:
    if c in df.columns: df[f"log_{c}"] = np.log1p(df[c])

if "X_conc" in df.columns:
    df["X_conc"] = df["X_conc"].clip(-1, 1)

# 特征选择
feature_cols = [c for c in [
    "Z13","Z18","Z21","ZX","X_conc",
    "GC_total","GC13","GC18","GC21",
    "filter_ratio","map_ratio","dup_ratio","uniq_ratio",
    "log_reads_total","log_reads_unique",
    "BMI","age","height","weight","week_num"
] if c in df.columns]

X_raw = df[feature_cols].copy()
y_all = df["label"].astype(int).values
groups = df["pid"].astype(str).values if "pid" in df.columns else np.arange(len(df))

# 数据分割 - 分组分层
sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=2025)
folds = list(sgkf.split(X_raw, y_all, groups))

# 使用前3折训练，第4折验证，第5折测试
train_idx = np.concatenate([folds[0][0], folds[1][0], folds[2][0]])
valid_idx = folds[3][0]
test_idx = folds[4][0]

X_train_raw, y_train = X_raw.iloc[train_idx], y_all[train_idx]
X_valid_raw, y_valid = X_raw.iloc[valid_idx], y_all[valid_idx]
X_test_raw, y_test = X_raw.iloc[test_idx], y_all[test_idx]

print(f"训练集: {X_train_raw.shape}, 验证集: {X_valid_raw.shape}, 测试集: {X_test_raw.shape}")

# 数据预处理 - 避免数据泄露
imp = SimpleImputer(strategy="median")
X_train_imputed = imp.fit_transform(X_train_raw)
X_valid_imputed = imp.transform(X_valid_raw)
X_test_imputed = imp.transform(X_test_raw)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train_imputed)
X_valid = scaler.transform(X_valid_imputed)
X_test = scaler.transform(X_test_imputed)

# 正类过采样
def oversample_positive(X, y, target_ratio=0.30, max_rep=20):
    y = np.asarray(y)
    pos_idx = np.where(y==1)[0]
    neg_idx = np.where(y==0)[0]
    n_pos, n_neg = len(pos_idx), len(neg_idx)
    if n_pos == 0: return X, y
    current_ratio = n_pos/(n_pos+n_neg)
    if current_ratio >= target_ratio: return X, y
    
    target_pos = int(target_ratio/(1-target_ratio) * n_neg)
    need = max(0, target_pos - n_pos)
    reps = min(max_rep, int(np.ceil(need / n_pos)))
    add_idx = np.tile(pos_idx, reps)[:need] if need>0 else np.array([], dtype=int)
    
    X_new = np.concatenate([X, X[add_idx]], axis=0)
    y_new = np.concatenate([y, y[add_idx]], axis=0)
    return X_new, y_new

X_train_os, y_train_os = oversample_positive(X_train, y_train)

# Focal Loss定义
pos = (y_train_os==1).sum()
neg = (y_train_os==0).sum()
w_pos = neg / (pos + 1e-9)
class_weights = torch.tensor([1.0, float(w_pos)], dtype=torch.float32)

class FocalLoss(torch.nn.Module):
    def __init__(self, alpha=None, gamma=2.0, reduction="mean"):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
    
    def forward(self, logits, targets):
        ce = torch.nn.functional.cross_entropy(logits, targets, weight=self.alpha, reduction="none")
        pt = torch.exp(-ce)
        loss = ((1-pt)**self.gamma) * ce
        return loss.mean() if self.reduction=="mean" else loss.sum()

loss_fn = FocalLoss(alpha=class_weights, gamma=2.0)

# TabNet参数
tabnet_params = {
    "n_d": 16, "n_a": 16, "n_steps": 4, "gamma": 1.6, "lambda_sparse": 1e-3,
    "optimizer_params": {"lr": 8e-4, "weight_decay": 1e-5},
    "mask_type": "entmax"
}

fit_params = {
    "eval_metric": ["balanced_accuracy"],
    "max_epochs": 150,
    "patience": 50,
    "batch_size": 512,
    "virtual_batch_size": 128,
    "num_workers": 0,
    "drop_last": False
}

# 模型训练
device_name = 'cuda' if torch.cuda.is_available() else 'auto'
clf = TabNetClassifier(
    **tabnet_params,
    scheduler_params={"step_size": 60, "gamma": 0.9},
    scheduler_fn=torch.optim.lr_scheduler.StepLR,
    device_name=device_name
)

clf.fit(
    X_train=X_train_os, y_train=y_train_os,
    eval_set=[(X_valid, y_valid)],
    eval_name=["valid"],
    loss_fn=loss_fn,
    **fit_params
)

# F2阈值优化
p_valid = clf.predict_proba(X_valid)[:, 1]
ths = np.linspace(0.05, 0.95, 91)
f2s = [fbeta_score(y_valid, (p_valid>=t).astype(int), beta=2.0) for t in ths]
best_t = float(ths[int(np.argmax(f2s))])

# 测试集评估
p_test = clf.predict_proba(X_test)[:, 1]
y_pred_default = (p_test >= 0.5).astype(int)
y_pred_best = (p_test >= best_t).astype(int)

def evaluate_and_save(prefix, y_true, p, y_pred):
    auc = roc_auc_score(y_true, p)
    ap = average_precision_score(y_true, p)
    cm = confusion_matrix(y_true, y_pred)
    rpt = classification_report(y_true, y_pred, digits=4)
    threshold = 0.5 if 'default' in prefix else best_t
    print(f"{prefix} | AUC={auc:.4f} | AP={ap:.4f} | 阈值={threshold:.2f}")
    print(cm)
    
    with open(os.path.join(OUTPUT_DIR, f"{prefix}_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({
            "AUC": float(auc), "AP": float(ap), "threshold": threshold,
            "confusion_matrix": cm.tolist(), "classification_report": rpt
        }, f, ensure_ascii=False, indent=2)
    return auc, ap, cm, rpt

auc_d, ap_d, cm_d, rpt_d = evaluate_and_save("test_default", y_test, p_test, y_pred_default)
auc_b, ap_b, cm_b, rpt_b = evaluate_and_save("test_bestT", y_test, p_test, y_pred_best)

# 保存结果
np.save(os.path.join(OUTPUT_DIR, "pred_proba_test.npy"), p_test)
np.save(os.path.join(OUTPUT_DIR, "pred_label_bestT.npy"), y_pred_best)
pd.DataFrame({
    "pred_proba": p_test, 
    "pred_label_bestT": y_pred_best, 
    "y_true": y_test
}).to_csv(os.path.join(OUTPUT_DIR, "test_predictions.csv"), index=False, encoding="utf-8-sig")

# 特征重要性
fi = pd.DataFrame({
    "feature": feature_cols, 
    "importance": clf.feature_importances_
}).sort_values("importance", ascending=False)
fi.to_csv(os.path.join(OUTPUT_DIR, "feature_importance.csv"), index=False, encoding="utf-8-sig")

# 基线模型
RUN_BASELINE = True
if RUN_BASELINE:
    logit = LogisticRegression(
        penalty="l1", solver="liblinear", class_weight="balanced", 
        max_iter=2000, random_state=2025
    )
    logit.fit(X_train, y_train)
    p_test_lr = logit.predict_proba(X_test)[:,1]
    
    # 基线模型F2阈值优化
    p_valid_lr = logit.predict_proba(X_valid)[:,1]
    ths_lr = np.linspace(0.05, 0.95, 91)
    f2s_lr = [fbeta_score(y_valid, (p_valid_lr>=t).astype(int), beta=2.0) for t in ths_lr]
    best_t_lr = float(ths_lr[int(np.argmax(f2s_lr))])
    y_pred_lr = (p_test_lr>=best_t_lr).astype(int)
    
    auc_lr = roc_auc_score(y_test, p_test_lr)
    ap_lr = average_precision_score(y_test, p_test_lr)
    cm_lr = confusion_matrix(y_test, y_pred_lr)
    rpt_lr = classification_report(y_test, y_pred_lr, digits=4)
    
    with open(os.path.join(OUTPUT_DIR, "baseline_logit_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({
            "AUC": float(auc_lr), "AP": float(ap_lr), "threshold": best_t_lr,
            "confusion_matrix": cm_lr.tolist(), "classification_report": rpt_lr
        }, f, ensure_ascii=False, indent=2)

# 可视化 - 使用新的配色方案
plt.figure(figsize=(18, 12))

# 定义新的颜色方案
colors = {
    'primary': '#2E86AB',      # 深蓝
    'secondary': '#A23B72',    # 紫红
    'accent': '#F18F01',       # 橙色
    'success': '#C73E1D',      # 深红
    'neutral': '#6C757D'       # 灰色
}

# ROC曲线
plt.subplot(2,3,1)
fpr, tpr, _ = roc_curve(y_test, p_test)
plt.plot(fpr, tpr, label=f"TabNet AUC={auc_b:.3f}", color=colors['primary'], linewidth=2.5)
if RUN_BASELINE:
    fpr_lr, tpr_lr, _ = roc_curve(y_test, p_test_lr)
    plt.plot(fpr_lr, tpr_lr, label=f"L1-Logit AUC={auc_lr:.3f}", 
             color=colors['secondary'], alpha=0.8, linewidth=2)
plt.plot([0,1],[0,1], color=colors['neutral'], linestyle='--', alpha=0.6)
plt.title("ROC曲线", fontsize=12, fontweight='bold')
plt.xlabel("假阳性率"); plt.ylabel("真阳性率"); plt.legend()
plt.grid(True, alpha=0.3)

# PR曲线
plt.subplot(2,3,2)
prec, rec, _ = precision_recall_curve(y_test, p_test)
plt.plot(rec, prec, label=f"TabNet AP={ap_b:.3f}", color=colors['primary'], linewidth=2.5)
if RUN_BASELINE:
    prec_lr, rec_lr, _ = precision_recall_curve(y_test, p_test_lr)
    plt.plot(rec_lr, prec_lr, label=f"L1-Logit AP={ap_lr:.3f}", 
             color=colors['secondary'], alpha=0.8, linewidth=2)
plt.title("PR曲线", fontsize=12, fontweight='bold')
plt.xlabel("召回率"); plt.ylabel("精确率"); plt.legend()
plt.grid(True, alpha=0.3)

# 校准曲线
plt.subplot(2,3,3)
prob_true, prob_pred = calibration_curve(y_test, p_test, n_bins=10, strategy='quantile')
plt.plot(prob_pred, prob_true, marker='o', label="TabNet", 
         color=colors['primary'], markersize=6, linewidth=2)
if RUN_BASELINE:
    prob_true_lr, prob_pred_lr = calibration_curve(y_test, p_test_lr, n_bins=10, strategy='quantile')
    plt.plot(prob_pred_lr, prob_true_lr, marker='^', label="L1-Logit", 
             color=colors['secondary'], alpha=0.8, markersize=6, linewidth=2)
plt.plot([0,1],[0,1], color=colors['neutral'], linestyle='--', alpha=0.6, label="完美校准")
plt.title("校准曲线", fontsize=12, fontweight='bold')
plt.xlabel("预测概率"); plt.ylabel("实际命中率"); plt.legend()
plt.grid(True, alpha=0.3)

# 混淆矩阵 - 默认阈值
plt.subplot(2,3,4)
sns.heatmap(cm_d, annot=True, fmt="d", cmap="Oranges", cbar=False,
            xticklabels=["正常(0)","异常(1)"], yticklabels=["正常(0)","异常(1)"],
            annot_kws={'size': 11, 'weight': 'bold'})
plt.title("混淆矩阵（阈值=0.5）", fontsize=12, fontweight='bold')
plt.xlabel("预测"); plt.ylabel("真实")

# 混淆矩阵 - 最优阈值
plt.subplot(2,3,5)
sns.heatmap(cm_b, annot=True, fmt="d", cmap="Purples", cbar=False,
            xticklabels=["正常(0)","异常(1)"], yticklabels=["正常(0)","异常(1)"],
            annot_kws={'size': 11, 'weight': 'bold'})
plt.title(f"混淆矩阵（最优阈值={best_t:.2f}，F2最大）", fontsize=12, fontweight='bold')
plt.xlabel("预测"); plt.ylabel("真实")

# 特征重要性
plt.subplot(2,3,6)
topk = min(15, len(fi))
ax = sns.barplot(data=fi.head(topk), x="importance", y="feature", 
                 palette="plasma", alpha=0.8)
for i, v in enumerate(fi.head(topk)['importance']):
    ax.text(v + 0.001, i, f'{v:.3f}', va='center', fontsize=9, fontweight='bold')
plt.title("特征重要性（Top-15）", fontsize=12, fontweight='bold')
plt.xlabel("重要性"); plt.ylabel("特征")
plt.grid(True, alpha=0.3, axis='x')

plt.suptitle("女胎异常判定模型评估结果", fontsize=16, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig(os.path.join(OUTPUT_DIR, "tabnet_improved_plots.png"), 
            dpi=300, bbox_inches="tight", facecolor='white')
plt.close()

print("\n模型训练和评估完成！")
print(f"结果保存在: {OUTPUT_DIR}")
