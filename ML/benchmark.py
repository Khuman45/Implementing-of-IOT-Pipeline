import time
import platform
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.svm import SVC

print("=" * 55)
print("  ML TIMING TEST  —  Supercomputer vs Personal PC")
print("=" * 55)
print(f"  Machine   : {platform.node()}")
print(f"  OS        : {platform.system()} {platform.release()}")
print(f"  Processor : {platform.processor()}")
print("=" * 55)

results = {}

# ── Task 1: Generate large dataset ────────────────────────────────
print("\nTask 1: Generating dataset (200,000 samples, 25 features)...")
t0 = time.time()
X, y = make_classification(
    n_samples=200_000,
    n_features=25,
    n_informative=12,
    n_redundant=5,
    random_state=42
)
results["Dataset generation"] = round(time.time() - t0, 3)
print(f"  Done: {results['Dataset generation']} sec")

# ── Task 2: Random Forest — 150 trees ─────────────────────────────
print("\nTask 2: Random Forest (150 trees, full dataset)...")
t0 = time.time()
rf = RandomForestClassifier(
    n_estimators=150,
    max_depth=20,
    n_jobs=1,
    random_state=42
)
rf.fit(X, y)
results["Random Forest (150 trees)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Random Forest (150 trees)']} sec")

# ── Task 3: Gradient Boosting ─────────────────────────────────────
print("\nTask 3: Gradient Boosting (100 estimators)...")
t0 = time.time()
gb = GradientBoostingClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42
)
gb.fit(X[:50_000], y[:50_000])
results["Gradient Boosting"] = round(time.time() - t0, 3)
print(f"  Done: {results['Gradient Boosting']} sec")

# ── Task 4: Neural Network — deep, more epochs ────────────────────
print("\nTask 4: Neural Network (4 hidden layers, 50 epochs)...")
X_scaled = StandardScaler().fit_transform(X)
t0 = time.time()
mlp = MLPClassifier(
    hidden_layer_sizes=(256, 128, 64, 32),
    max_iter=15,
    learning_rate_init=0.001,
    random_state=42,
    verbose=False
)
mlp.fit(X_scaled, y)
results["Neural Network (MLP)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Neural Network (MLP)']} sec")

# ── Task 5: SVM on medium dataset ─────────────────────────────────
print("\nTask 5: SVM classifier (30,000 samples)...")
t0 = time.time()
svm = SVC(kernel="rbf", C=1.0, gamma="scale")
svm.fit(X_scaled[:30_000], y[:30_000])
results["SVM (RBF kernel)"] = round(time.time() - t0, 3)
print(f"  Done: {results['SVM (RBF kernel)']} sec")

# ── Task 6: Cross-validation — 5 folds ───────────────────────────
print("\nTask 6: 5-fold Cross-validation (Random Forest, 80k samples)...")
t0 = time.time()
scores = cross_val_score(
    RandomForestClassifier(n_estimators=50, n_jobs=1, random_state=42),
    X[:80_000], y[:80_000],
    cv=5,
    scoring="accuracy"
)
results["Cross-validation (5-fold)"] = round(time.time() - t0, 3)
print(f"  Done: {results['Cross-validation (5-fold)']} sec")
print(f"  Accuracy: {round(scores.mean()*100, 2)}% +/- {round(scores.std()*100, 2)}%")

# ── Summary ───────────────────────────────────────────────────────
total = round(sum(results.values()), 3)
total_min = round(total / 60, 2)

print("\n" + "=" * 55)
print("  FINAL RESULTS SUMMARY")
print("=" * 55)
for task, sec in results.items():
    print(f"  {task:<35} {sec:>7.3f} sec")
print("-" * 55)
print(f"  {'TOTAL':<35} {total:>7.3f} sec  ({total_min} min)")
print("=" * 55)
print("\n  Record this result and compare with the other machine!")
print("=" * 55)