#!/usr/bin/env python3
"""
Generate Open Badges (v2) hosted assertions from a CSV.
- Input: data/attendees.csv with columns: full_name,email,issued_on (YYYY-MM-DD)
- Output: assertions/<uuid>.json for each row
Replace HOST_BASE with your GitHub Pages URL.
"""
import csv, json, uuid, hashlib
from datetime import datetime, timezone

HOST_BASE = "https://TU_USUARIO.github.io/amfv-badges-pilot"
ISSUER_ID = f"{HOST_BASE}/issuer.json"
BADGECLASS_ID = f"{HOST_BASE}/badges/pv101.json"

def hash_email(email: str, salt: str) -> str:
    return hashlib.sha256((email.strip().lower() + salt).encode("utf-8")).hexdigest()

def iso_z(date_str: str) -> str:
    # date_str: YYYY-MM-DD
    dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00","Z")

def main():
    in_path = "data/attendees.csv"
    out_dir = "assertions"
    with open(in_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assertion_uuid = str(uuid.uuid4())
            salt = uuid.uuid4().hex
            hashed = hash_email(row["email"], salt)
            issued_on = iso_z(row["issued_on"])

            assertion = {
                "@context": "https://w3id.org/openbadges/v2",
                "type": "Assertion",
                "id": f"{HOST_BASE}/assertions/{assertion_uuid}.json",
                "recipient": {
                    "type": "email",
                    "hashed": True,
                    "salt": salt,
                    "identity": f"sha256${hashed}"
                },
                "issuedOn": issued_on,
                "badge": BADGECLASS_ID,
                "verification": {"type": "hosted"},
                "evidence": [{
                    "id": f"{HOST_BASE}/evidence/pv101.html",
                    "narrative": "Evidencia ficticia: finalización de PV 101 y mini‑quiz."
                }]
            }

            out_path = f"{out_dir}/{assertion_uuid}.json"
            with open(out_path, "w", encoding="utf-8") as out:
                json.dump(assertion, out, ensure_ascii=False, indent=2)

            print("Issued:", row["full_name"], row["email"], "->", assertion["id"])

if __name__ == "__main__":
    main()
