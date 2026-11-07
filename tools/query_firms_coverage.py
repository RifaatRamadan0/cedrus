"""Snapshot FIRMS metadata, redacting credentials from every persisted response."""
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/tier1/coverage_services"


def main():
    key = None
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("FIRMS_MAP_KEY="):
            key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise SystemExit("FIRMS_MAP_KEY is absent from local .env")
    OUT.mkdir(parents=True, exist_ok=True)
    audit = []
    requests = [(sensor, f"https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{key}/{sensor}", {})
                for sensor in ("MODIS_SP", "VIIRS_SNPP_SP", "VIIRS_NOAA20_SP")]
    requests.append(("missing_data", "https://firms.modaps.eosdis.nasa.gov/api/missing_data/?action=fetch_data", {"X-Requested-With": "XMLHttpRequest"}))
    for name, url, headers in requests:
        record = {"service": name, "url_template": url.replace(key, "[REDACTED]"),
                  "retrieved": datetime.now(timezone.utc).isoformat(), "attempts": []}
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "cedrus-source-audit/1.0", **headers})
                with urllib.request.urlopen(req, timeout=90) as response:
                    body = response.read().decode("utf-8-sig").replace(key, "[REDACTED]")
                    record["http_status"] = response.status
                    record["content_type"] = response.headers.get("Content-Type")
                file = OUT / (name + ".txt")
                file.write_text(body, encoding="utf-8")
                record.update(snapshot=file.name, sha256=hashlib.sha256(file.read_bytes()).hexdigest())
                record["attempts"].append("success")
                print(name, "HTTP", record["http_status"], "saved sanitized response", flush=True)
                break
            except Exception as exc:
                # Exception URLs can include credentials: never stringify them.
                record["attempts"].append({"error_class": type(exc).__name__, "http_code": getattr(exc, "code", None)})
                if attempt < 2:
                    time.sleep(2 ** attempt)
        audit.append(record)
        (OUT / "requests.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
