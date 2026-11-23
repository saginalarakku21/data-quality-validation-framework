"""Apply a configurable data contract and write a JSON report."""
import argparse
import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path


def validate(path, rules):
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = sorted(set(rules["required"]) - set(reader.fieldnames or []))
        if missing:
            return {"passed": False, "rows": 0, "missing_columns": missing, "errors": []}
        rows = list(reader)

    key = rules["unique"]
    counts = Counter((row[key] or "").strip() for row in rows)
    errors = []
    for number, row in enumerate(rows, start=2):
        issues = [f"{field} is blank" for field in rules["required"]
                  if not (row[field] or "").strip()]
        if None in row:
            issues.append("extra CSV fields")
        value = (row[key] or "").strip()
        if value and counts[value] > 1:
            issues.append(f"{key} is duplicated")
        for field, minimum in rules["minimum"].items():
            try:
                amount = Decimal(row[field] or "")
                if not amount.is_finite() or amount < Decimal(str(minimum)):
                    issues.append(f"{field} must be finite and at least {minimum}")
            except InvalidOperation:
                issues.append(f"{field} must be numeric")
        if issues:
            errors.append({"record": number - 1, "issues": issues})
    if not rows:
        errors.append({"issues": ["input contains no records"]})
    return {"passed": not errors, "rows": len(rows), "missing_columns": [], "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--rules", type=Path, default=Path("rules.json"))
    parser.add_argument("--report", type=Path, default=Path("output/report.json"))
    args = parser.parse_args()
    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    report = validate(args.csv, rules)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.report)
    raise SystemExit(0 if report["passed"] else 1)
