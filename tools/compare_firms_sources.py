"""Compare re-downloaded inputs with provenance in committed exports; never export."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    committed = subprocess.check_output(
        ["git", "show", "HEAD:web/data/regions.json"], cwd=ROOT)
    index = json.loads(committed)
    report = {"commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "regions": {}}
    failed = False
    for region in index["regions"]:
        rid = region["id"]
        if rid not in ("portugal", "lebanon"):
            continue
        raw = ROOT / "data/raw" / rid
        manifest_path = raw / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        records = []
        for original in region["provenance"]["files"]:
            name = original["name"]
            path = raw / name
            record = {"file": name, "committed_source_sha256": original["sha256"],
                      "original_retrieved": original["retrieved"], "url": original["url"]}
            if not path.exists():
                record["status"] = "missing"
            else:
                body = path.read_bytes()
                digest = hashlib.sha256(body).hexdigest()
                record.update(bytes=len(body), downloaded_sha256=digest,
                              manifest_matches=digest == manifest.get(name, {}).get("sha256"),
                              downloaded_retrieved=manifest.get(name, {}).get("retrieved"))
                record["status"] = "identical" if digest == original["sha256"] else "changed"
                if not record["manifest_matches"]:
                    record["status"] = "invalid_local_manifest"
            failed |= record["status"] != "identical"
            records.append(record)
        report["regions"][rid] = {"files": records,
            "counts": {status: sum(r["status"] == status for r in records)
                       for status in ("identical", "changed", "missing", "invalid_local_manifest")},
            "bytes": sum(r.get("bytes", 0) for r in records)}
    exported = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "web/data"], cwd=ROOT, text=True).splitlines()
    differences = []
    checkout_line_endings = []
    for name in exported:
        prior = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        path = ROOT / name
        current = path.read_bytes() if path.exists() else None
        if current is not None and current != prior and current.replace(b"\r\n", b"\n") == prior.replace(b"\r\n", b"\n"):
            checkout_line_endings.append(name)
        elif current != prior:
            differences.append(name)
    report["changed_export_files"] = differences
    report["checkout_line_endings_only"] = checkout_line_endings
    failed |= bool(differences)
    out = ROOT / "analysis/tier1/redownload_comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for rid, result in report["regions"].items():
        print(f"{rid}: {result['counts']}; {result['bytes']} bytes")
    print(f"Changed committed exports: {len(differences)}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
