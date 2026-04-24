"""Synthetic environment builder for local evaluation benchmarks.

Mirrors the shape of the real environment document (262 features, one segment),
so we can exercise the local eval hot path without needing network access.
"""

from __future__ import annotations

import copy
import json
import os
import typing

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "data")
TEMPLATE_PATH = os.path.join(DATA_DIR, "environment.json")


def build_environment(
    n_features: int = 262,
    *,
    with_multivariate: int = 0,
) -> dict[str, typing.Any]:
    with open(TEMPLATE_PATH) as f:
        env: dict[str, typing.Any] = json.load(f)

    # Base feature state to clone.
    base_fs = copy.deepcopy(env["feature_states"][0])
    feature_states: list[dict[str, typing.Any]] = []
    for i in range(n_features):
        fs = copy.deepcopy(base_fs)
        fs["django_id"] = i + 1
        fs["feature"] = {
            "name": f"feature_{i:04d}",
            "type": "STANDARD",
            "id": i + 1,
        }
        fs["feature_state_value"] = f"value-{i}"
        if with_multivariate and i < with_multivariate:
            fs["multivariate_feature_state_values"] = [
                {
                    "multivariate_feature_option": {"value": f"mv-{i}-a"},
                    "percentage_allocation": 50.0,
                    "id": (i + 1) * 100 + 1,
                },
                {
                    "multivariate_feature_option": {"value": f"mv-{i}-b"},
                    "percentage_allocation": 50.0,
                    "id": (i + 1) * 100 + 2,
                },
            ]
        feature_states.append(fs)

    env["feature_states"] = feature_states
    # Strip the (irrelevant) identity override for a clean baseline.
    env["identity_overrides"] = []
    return env
