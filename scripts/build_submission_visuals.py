"""Render measured-result figures in a separate matplotlib tools environment."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--course-template", action="store_true")
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
NAMES = ["Baseline v2", "Original BERT", "Defended BERT", "HF DistilBERT"]
KEYS = ["baseline_v2", "finetuned", "defended", "pretrained"]
COLORS = ["#12535b", "#328a94", "#d99b4e", "#7476a7"]
if args.course_template:
    COLORS = ["#23727b", "#3cb3aa", "#eda900", "#333e47"]
    font_manager.findfont("Calibri", fallback_to_default=False)
final = json.loads((ROOT / "docs/reports/final-evaluation.json").read_text())
previous = json.loads((ROOT / "docs/reports/current-comparison.json").read_text())
plt.rcParams.update(
    {
        "font.family": "Calibri" if args.course_template else "DejaVu Sans",
        "font.size": 16 if args.course_template else 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "text.color": "#333e47" if args.course_template else "#183b40",
        "axes.labelcolor": "#333e47" if args.course_template else "#183b40",
        "axes.edgecolor": "#333e47" if args.course_template else "black",
        "xtick.color": "#333e47" if args.course_template else "black",
        "ytick.color": "#333e47" if args.course_template else "black",
        "grid.color": "#333e47" if args.course_template else "#b0b0b0",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def save(fig, name):
    if args.course_template:
        name = "course-" + name
    fig.savefig(ASSETS / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(ASSETS / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


fig, ax = plt.subplots(figsize=(12, 4.7))
cohorts = ["Historical (423)", "Challenge (2,000)", "Final reserve (703)"]
x = np.arange(3)
for i, key in enumerate(KEYS):
    values = [
        previous["cohorts"][c]["results"][key]["metrics"]["accuracy"] * 100
        for c in ["test", "challenge"]
    ]
    values.append(final["clean"][key]["metrics"]["accuracy"] * 100)
    bars = ax.bar(x + (i - 1.5) * 0.19, values, 0.18, label=NAMES[i], color=COLORS[i])
    ax.bar_label(
        bars,
        labels=[f"{v:.2f}" for v in values],
        padding=3,
        fontsize=14 if args.course_template else 9,
    )
ax.set(xticks=x, xticklabels=cohorts, ylim=(0, 111), ylabel="Accuracy (%)")
ax.set_yticks(range(0, 101, 20))
ax.grid(axis="y", alpha=0.17)
ax.set_axisbelow(True)
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.21), frameon=False)
fig.text(
    0.5,
    -0.04,
    "Different cohorts, not a time trend. Source/era and synthetic-template limits apply.",
    ha="center",
    fontsize=14 if args.course_template else 11,
)
save(fig, "accuracy-by-cohort")

fig, ax = plt.subplots(figsize=(12, 4.7))
x = np.arange(4)
for offset, metric, color, label in [
    (
        -0.19,
        "fn",
        "#eda900" if args.course_template else "#bd6255",
        "Missed phishing / 1,000 phishing",
    ),
    (
        0.19,
        "fp",
        "#23727b" if args.course_template else "#328a94",
        "False alarms / 1,000 legitimate",
    ),
]:
    values = [
        previous["cohorts"]["challenge"]["results"][k]["metrics"]["confusion"][metric] for k in KEYS
    ]
    bars = ax.bar(x + offset, values, 0.36, color=color, label=label)
    ax.bar_label(bars, padding=3, fontsize=16 if args.course_template else 12)
ax.set(xticks=x, xticklabels=NAMES, ylim=(0, 420), ylabel="Number of errors")
ax.grid(axis="y", alpha=0.17)
ax.set_axisbelow(True)
ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.17), frameon=False)
fig.text(
    0.5,
    -0.04,
    "Challenge cohort: 2,000 messages; 1,900 synthetic and 100 of unverified origin.",
    ha="center",
    fontsize=14 if args.course_template else 11,
)
save(fig, "challenge-error-tradeoff")
print("Rendered two measured-result figures as PNG and SVG from committed reports.")
