"""Independently replay the critic's bounded CSV-error finding on both revisions.

Added by the host after review, separately from the unchanged acceptance suite.
"""
import argparse
import csv
import importlib.util
import json
import pathlib

p = argparse.ArgumentParser()
p.add_argument("artifacts", help="directory containing summary.py and reports/")
a = p.parse_args()
root = pathlib.Path(a.artifacts)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


first = load("first_summary", root / "reports/first-summary.py")
final = load("final_summary", root / "summary.py")
payload = "category,amount\n" + "x" * (csv.field_size_limit() + 1) + ",1.00\n"
outcomes = {}
for label, module, expected in (("first", first, csv.Error), ("final", final, ValueError)):
    try:
        module.summarize(payload)
    except Exception as error:
        assert isinstance(error, expected), f"{label}: expected {expected.__name__}, got {type(error).__name__}"
        outcomes[label] = type(error).__module__ + "." + type(error).__name__
    else:
        raise AssertionError(f"{label}: oversized field did not raise")
print(json.dumps({"finding": "CSV parser error normalization", "observed": outcomes, "verified": True}, indent=2))
