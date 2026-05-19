import time
import platform
import os

print("=" * 60)
print("  ML BENCHMARK  —  Apple MacBook Air M4 vs CSC Puhti")
print("=" * 60)
print(f"  Machine   : {platform.node()}")
print(f"  OS        : {platform.system()} {platform.release()}")
print(f"  Chip      : Apple M4 (MacBook Air)")
print(f"  CPU Cores : {os.cpu_count()}  (4 performance + 4 efficiency)")
print("=" * 60)

from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.svm import SVC

results = {}

# ── Task 1: Dataset Generation ────────────────────────────────────
print("\nTask 1: Generating dataset (500,000 samples, 30 features)...")
t0 = time.time()
X, y = make_classification(
    n_samples=500_000,
    n_features=30,
    n_informative=15,
    n_redundant=6,
    random_state=42
)
results["Dataset Generation"] = round(time.time() - t0, 3)
print(f"  Done: {results['Dataset Generation']} sec")

# ── Task 2: Random Forest ─────────────────────────────────────────
# 400 trees / 40 Puhti cores  = 10 trees per core
# 400 trees / 8 M4 Air cores  = 50 trees per core  → ~5x more work per core
print("\nTask 2: Random Forest (400 trees, full dataset)...")
t0 = time.time()
rf = RandomForestClassifier(
    n_estimators=400,
    max_depth=25,
    n_jobs=-1,
    random_state=42
)
rf.fit(X, y)
results["Random Forest (400 trees)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Random Forest (400 trees)']} sec")

# ── Task 3: Extra Trees ───────────────────────────────────────────
print("\nTask 3: Extra Trees (300 trees, full dataset)...")
t0 = time.time()
et = ExtraTreesClassifier(
    n_estimators=300,
    max_depth=20,
    n_jobs=-1,
    random_state=42
)
et.fit(X, y)
results["Extra Trees (300 trees)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Extra Trees (300 trees)']} sec")

# ── Task 4: Gradient Boosting ─────────────────────────────────────
# Sequential by design — extra cores don't help, expect similar times on both
print("\nTask 4: Gradient Boosting (150 estimators, 80k samples)...")
t0 = time.time()
gb = GradientBoostingClassifier(
    n_estimators=150,
    max_depth=6,
    learning_rate=0.1,
    random_state=42
)
gb.fit(X[:80_000], y[:80_000])
results["Gradient Boosting"] = round(time.time() - t0, 3)
print(f"  Done: {results['Gradient Boosting']} sec")

# ── Task 5: Neural Network ────────────────────────────────────────
print("\nTask 5: Neural Network (512->256->128->64, 20 epochs)...")
X_scaled = StandardScaler().fit_transform(X)
t0 = time.time()
mlp = MLPClassifier(
    hidden_layer_sizes=(512, 256, 128, 64),
    max_iter=20,
    learning_rate_init=0.001,
    random_state=42,
    verbose=False
)
mlp.fit(X_scaled, y)
results["Neural Network (MLP)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Neural Network (MLP)']} sec")

# ── Task 6: SVM ───────────────────────────────────────────────────
print("\nTask 6: SVM classifier (RBF kernel, 40,000 samples)...")
t0 = time.time()
svm = SVC(kernel="rbf", C=1.0, gamma="scale")
svm.fit(X_scaled[:40_000], y[:40_000])
results["SVM (RBF kernel)"] = round(time.time() - t0, 3)
print(f"  Done: {results['SVM (RBF kernel)']} sec")

# ── Task 7: Cross-validation ──────────────────────────────────────
# Puhti runs all 10 folds at once (40 cores)
# MacBook Air M4 runs them in batches (8 cores) → biggest expected speedup
print("\nTask 7: 10-fold Cross-validation (Random Forest, 150k samples)...")
t0 = time.time()
scores = cross_val_score(
    RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=42),
    X[:150_000], y[:150_000],
    cv=10,
    n_jobs=-1,
    scoring="accuracy"
)
results["Cross-validation (10-fold)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Cross-validation (10-fold)']} sec")
print(f"  Accuracy: {round(scores.mean()*100, 2)}% +/- {round(scores.std()*100, 2)}%")

# ── Summary ───────────────────────────────────────────────────────
total = round(sum(results.values()), 3)
mins  = int(total // 60)
secs  = round(total % 60, 1)

print("\n" + "=" * 60)
print("  FINAL RESULTS SUMMARY")
print("=" * 60)
print(f"  {'Task':<35} {'Time':>8}")
print("-" * 60)
for task, sec in results.items():
    m = int(sec // 60)
    s = round(sec % 60, 1)
    time_str = f"{m}m {s}s" if m > 0 else f"{s}s"
    print(f"  {task:<35} {time_str:>8}")
print("-" * 60)
print(f"  {'TOTAL':<35} {mins}m {secs}s")
print("=" * 60)
print("\n  Copy these results into your report!")
print("=" * 60)
