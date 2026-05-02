# Threshold Calibration Framework

**Status:** Implemented — dataset and calibration runner both exist  
**Relevant code:** `skill_mcp/tools/find_skills.py`, `src/worker.py` (`_skills_find_relevant`), `skill_mcp/eval/calibrate.py`, `tests/eval/threshold_calibration.json`

---

## The Problem with Current Thresholds

The similarity thresholds currently documented and used in the master-skill files:

| Threshold | Interpretation |
|-----------|---------------|
| > 0.6     | Strong match — call `skills_get_body` |
| 0.4–0.6   | Possible match — inspect description |
| < 0.4     | No match — proceed without a skill |

These values were set by judgment, not measurement. The CONTRIBUTING.md acknowledges this:

> "The 0.6 strong / 0.4 review thresholds were set by judgment, not measurement. For a given embedding model and skill corpus, there's a distribution of match scores. The thresholds should be derived from that distribution."

The consequence: thresholds that are too high cause agents to miss relevant skills (false negatives); thresholds that are too low cause agents to load irrelevant skills and waste context (false positives). Neither failure mode is visible without an evaluation set.

---

## Quality Metrics

The right metrics for threshold calibration are precision and recall at the **top-1 retrieval** level, since agents are instructed to load the top-scoring result when the score exceeds the threshold.

### Definitions

For a query `q` with expected skill `s*`:

- **True positive (TP):** top-1 result is `s*` and score > threshold
- **False positive (FP):** top-1 result is not `s*` but score > threshold (wrong skill loaded)
- **False negative (FN):** `s*` exists in registry but score < threshold (skill missed)
- **True negative (TN):** no relevant skill exists and score < threshold (correctly passed)

### Primary metrics

```
Precision = TP / (TP + FP)   # Of skills loaded, what fraction were correct?
Recall    = TP / (TP + FN)   # Of relevant skills, what fraction were found?
F1        = 2 * P * R / (P + R)
```

For a skills registry, **precision matters more than recall** at the strong-match threshold (> T_high). A loaded skill that does not match the task wastes context and may introduce wrong instructions. A missed skill is recoverable — the agent proceeds without it.

At the weak-match threshold (T_low < score < T_high), recall matters more — the agent is asked to inspect the description before proceeding.

Proposed targets (to be validated against an actual eval set):

| Threshold | Target precision | Target recall |
|-----------|-----------------|---------------|
| T_high (strong match) | ≥ 0.90 | ≥ 0.70 |
| T_low (possible match) | ≥ 0.60 | ≥ 0.85 |

---

## Evaluation Dataset Design

### Structure

A calibration dataset is a list of `(query, expected_skill_id, relevance)` triples:

```json
[
  {
    "query": "write pytest unit tests for a FastAPI endpoint with dependency injection",
    "expected_skill_id": "test-writer",
    "relevance": "strong",
    "notes": "primary skill for this task"
  },
  {
    "query": "write pytest unit tests for a FastAPI endpoint with dependency injection",
    "expected_skill_id": "fastapi",
    "relevance": "secondary",
    "notes": "may co-fire but test-writer should rank first"
  },
  {
    "query": "implement a checkout flow with Stripe",
    "expected_skill_id": "stripe-integration",
    "relevance": "strong"
  },
  {
    "query": "set up CI/CD for a Python project",
    "expected_skill_id": "github-actions",
    "relevance": "strong"
  },
  {
    "query": "write a Python script to process CSV data",
    "expected_skill_id": null,
    "relevance": "none",
    "notes": "data-analysis exists but CSV processing is general Python — should be below T_low"
  }
]
```

`relevance` values:
- `"strong"`: agent should load this skill (score should be > T_high)
- `"secondary"`: agent should see this skill in results but not necessarily load it
- `"none"`: no skill should be loaded for this query

### Coverage requirements

A useful evaluation set must cover:

1. **True positives at high confidence** — queries that clearly match a specific skill (one per skill minimum)
2. **True positives at borderline confidence** — queries that should match but use different phrasing
3. **True negatives** — queries where no skill should fire (general programming tasks, common knowledge)
4. **Near-duplicate queries** — queries that are close to two different skills' trigger phrases (tests disambiguation)
5. **Cross-skill queries** — multi-step tasks that involve more than one skill

Minimum dataset size: 3 positive queries × 30 skills + 30 true-negative queries = **120 queries**.

### Building the dataset

Start from two sources:

1. **Trigger phrases in SKILL.md** — each existing trigger phrase is a strong-match query for its skill. This gives ~150–300 positive examples directly.
2. **Paraphrased negatives** — take existing trigger phrases and rephrase them to be vaguer or out-of-scope. These should score below T_low.

Human annotation is needed for true negatives and near-duplicate disambiguation. An LLM can assist but a human should review all annotations in the ambiguous range (0.35–0.65 score).

---

## Calibration Procedure

Once the dataset exists:

```python
# Pseudocode — implements calibration sweep
import json
from skill_mcp.tools.find_skills import find_relevant_skills

def sweep_threshold(eval_set: list[dict], t_high: float, t_low: float) -> dict:
    tp_high = fp_high = fn_high = tn_high = 0
    for item in eval_set:
        results = json.loads(find_relevant_skills(query=item["query"], top_k=5))
        top1 = results["results"][0] if results["results"] else None
        top1_score = top1["score"] if top1 else 0.0
        top1_id = top1["skill_id"] if top1 else None

        if item["relevance"] == "strong":
            if top1_id == item["expected_skill_id"] and top1_score > t_high:
                tp_high += 1
            elif top1_score <= t_high:
                fn_high += 1
            else:
                fp_high += 1
        elif item["relevance"] == "none":
            if top1_score < t_low:
                tn_high += 1
            else:
                fp_high += 1

    precision = tp_high / (tp_high + fp_high) if (tp_high + fp_high) > 0 else 0
    recall = tp_high / (tp_high + fn_high) if (tp_high + fn_high) > 0 else 0
    return {"t_high": t_high, "t_low": t_low, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0}

# Sweep threshold range
results = []
for t_high in [0.5, 0.55, 0.6, 0.65, 0.7]:
    for t_low in [0.3, 0.35, 0.4, 0.45]:
        if t_low < t_high:
            results.append(sweep_threshold(eval_set, t_high, t_low))

# Select t_high that maximizes precision subject to recall >= 0.70
# Select t_low that maximizes recall subject to precision >= 0.60
```

The sweep should be run:
1. When new skills are added that might shift score distributions
2. When the embedding model changes
3. When the skill corpus grows past 50 skills (distribution shift expected)

---

## Relationship to Embedding Model

Score distributions are specific to the embedding model and the skill corpus. If the model changes from `@cf/baai/bge-small-en-v1.5` to any other model, all thresholds must be recalibrated from scratch. The evaluation dataset remains valid but the scores change entirely.

This is one reason [VERSIONING.md](VERSIONING.md) recommends tracking which embedding model was used at seed time.

---

## Where to Store the Evaluation Dataset

The evaluation dataset should live at `tests/eval/threshold_calibration.json`. It is not a unit test — it requires live Qdrant access — but it should be runnable as an optional CI check:

```bash
# Run calibration (requires QDRANT_URL, QDRANT_API_KEY, WORKERS_AI_* in env)
python -m skill_mcp.eval.calibrate --dataset tests/eval/threshold_calibration.json
```

Run calibration with:

```bash
make calibrate
# or:
python -m skill_mcp.eval.calibrate --dataset tests/eval/threshold_calibration.json
# CI mode (exit 0 = targets met):
python -m skill_mcp.eval.calibrate --quiet
```

Exit codes: `0` = at least one pair meets precision ≥ 0.90 and recall ≥ 0.85 · `1` = no pair meets targets · `2` = setup error.

---

## Implementation Status

- ✅ `tests/eval/threshold_calibration.json`: 120 triples — 90 strong-match (3 per skill × 30 skills) + 30 true negatives
- ✅ `skill_mcp/eval/__init__.py` + `skill_mcp/eval/calibrate.py`: full sweep with precision/recall/F1/specificity table, `--quiet` CI mode, exit codes 0/1/2
- ✅ `make calibrate` target added to `Makefile`
- ⏳ Run calibration after first full seeded deployment and record results here
- ⏳ Update master-skill files with calibrated threshold values once sweep results are known

---

## Current Threshold Status

Thresholds `T_high = 0.6` and `T_low = 0.4` remain judgment-based starting points — the calibration sweep has not yet been run against a fully seeded registry. Run `make calibrate` after seeding and record the best-pair output here.

**Do not change these values without running the sweep.** A threshold change that looks right on intuition can shift agent behavior in both directions across the 30-skill corpus.
