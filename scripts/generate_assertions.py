#!/usr/bin/env python3
"""
Generate Open Badges (v2) hosted assertions + pretty credential pages + mailmerge CSV.

Input:  data/attendees.csv with columns: full_name,email,issued_on (YYYY-MM-DD)
Output:
  - assertions/<uuid>.json
  - credentials/<uuid>.html
  - data/output_mailmerge.csv (DO NOT commit if it contains emails)

Replace HOST_BASE with your GitHub Pages URL.
"""

import csv
import json
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, quote

# =========================
# CONFIG (edit as needed)
# =========================
HOST_BASE = "https://eleazar14.github.io/amfv-badges-pilot"

ISSUER_NAME = "AMFV (Piloto)"
BADGE_NAME = "AMFV Piloto – PV 101 (Curso ficticio)"
ISSUE_ORG_FOR_LINKEDIN = "AMFV (Piloto)"  # En real: "Asociación Mexicana de Farmacovigilancia (AMFV)"

BADGE_IMAGE_URL = f"{HOST_BASE}/images/amfv-pilot-badge.png"
BADGECLASS_ID = f"{HOST_BASE}/badges/pv101.json"
EVIDENCE_URL = f"{HOST_BASE}/evidence/pv101.html"

# Files/folders
ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "data" / "attendees.csv"
OUT_ASSERTIONS = ROOT / "assertions"
OUT_CREDENTIALS = ROOT / "credentials"
OUT_MAILMERGE = ROOT / "data" / "output_mailmerge.csv"


def hash_email(email: str, salt: str) -> str:
    return hashlib.sha256((email.strip().lower() + salt).encode("utf-8")).hexdigest()


def iso_z(date_str: str) -> str:
    # date_str: YYYY-MM-DD
    dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def build_linkedin_add_url(name: str, org: str, issued_on_yyyy_mm_dd: str, credential_url: str, credential_id: str) -> str:
    dt = datetime.fromisoformat(issued_on_yyyy_mm_dd)
    params = {
        "startTask": "CERTIFICATION_NAME",
        "name": name,
        "organizationName": org,
        "issueYear": str(dt.year),
        "issueMonth": str(dt.month),
        "certUrl": credential_url,
        "certId": credential_id
    }
    return "https://www.linkedin.com/profile/add?" + urlencode(params, quote_via=quote)


def build_linkedin_share_url(url_to_share: str) -> str:
    return "https://www.linkedin.com/sharing/share-offsite/?url=" + quote(url_to_share, safe="")


def render_credential_html(
    badge_name: str,
    issuer_name: str,
    issued_month_year: str,
    credential_id: str,
    credential_url: str,
    assertion_url: str,
    evidence_url: str,
    linkedin_add_url: str,
    linkedin_share_url: str,
    badge_image_url: str
) -> str:
    # Includes Open Graph tags (preview) + buttons
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{badge_name} | Credencial</title>

  <meta property="og:title" content="{badge_name}" />
  <meta property="og:description" content="Credencial verificable. Incluye verificación y evidencia." />
  <meta property="og:image" content="{badge_image_url}" />
  <meta property="og:image:secure_url" content="{badge_image_url}" />
  <meta property="og:url" content="{credential_url}" />
  <meta property="og:type" content="website" />
  <meta name="twitter:card" content="summary_large_image" />

  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; }}
    .card {{ max-width: 800px; margin: auto; border: 1px solid #ddd; border-radius: 14px; padding: 24px; }}
    .row {{ display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }}
    img {{ width: 220px; height: 220px; object-fit: contain; }}
    h1 {{ margin: 0 0 8px 0; }}
    .meta {{ color: #444; margin: 6px 0; }}
    .id {{ font-family: Consolas, monospace; background: #f6f6f6; padding: 8px 10px; border-radius: 8px; display: inline-block; }}
    .btns {{ margin-top: 18px; display: flex; gap: 10px; flex-wrap: wrap; }}
    a.btn {{ display: inline-block; padding: 10px 14px; border-radius: 10px; border: 1px solid #1d2a5c; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="row">
      <img src="{badge_image_url}" alt="Badge" />
      <div>
        <h1>{badge_name}</h1>
        <div class="meta"><b>Emisor:</b> {issuer_name}</div>
        <div class="meta"><b>Fecha de emisión:</b> {issued_month_year}</div>
        <div class="meta"><b>Credential ID:</b> <span class="id">{credential_id}</span></div>

        <div class="btns">
          <a class="btn" href="{linkedin_add_url}" target="_blank" rel="noopener">Agregar a LinkedIn</a>
          <a class="btn" href="{linkedin_share_url}" target="_blank" rel="noopener">Compartir en LinkedIn</a>
          <a class="btn" href="{assertion_url}" target="_blank" rel="noopener">Ver assertion (JSON)</a>
          <a class="btn" href="{evidence_url}" target="_blank" rel="noopener">Ver evidencia</a>
        </div>
      </div>
    </div>

    <p style="margin-top:18px;">
      Esta credencial es verificable mediante su assertion hospedada y evidencia asociada.
    </p>
  </div>
</body>
</html>
"""


def main():
    OUT_ASSERTIONS.mkdir(parents=True, exist_ok=True)
    OUT_CREDENTIALS.mkdir(parents=True, exist_ok=True)

    rows_out = []

    with open(IN_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row["full_name"].strip()
            email = row["email"].strip()
            issued_on = row["issued_on"].strip()  # YYYY-MM-DD

            # IDs
            credential_id = str(uuid.uuid4())
            salt = uuid.uuid4().hex
            hashed = hash_email(email, salt)

            issued_on_iso = iso_z(issued_on)
            dt = datetime.fromisoformat(issued_on)
            issued_month_year = dt.strftime("%B %Y")  # e.g., March 2026

            assertion_url = f"{HOST_BASE}/assertions/{credential_id}.json"
            credential_url = f"{HOST_BASE}/credentials/{credential_id}.html"

            assertion = {
                "@context": "https://w3id.org/openbadges/v2",
                "type": "Assertion",
                "id": assertion_url,
                "recipient": {
                    "type": "email",
                    "hashed": True,
                    "salt": salt,
                    "identity": f"sha256${hashed}"
                },
                "issuedOn": issued_on_iso,
                "badge": BADGECLASS_ID,
                "verification": {"type": "hosted"},
                "evidence": [{"id": EVIDENCE_URL, "narrative": "Evidencia: finalización del curso y mini-quiz."}]
            }

            linkedin_add = build_linkedin_add_url(BADGE_NAME, ISSUE_ORG_FOR_LINKEDIN, issued_on, credential_url, credential_id)
            linkedin_share = build_linkedin_share_url(credential_url)

            html = render_credential_html(
                badge_name=BADGE_NAME,
                issuer_name=ISSUER_NAME,
                issued_month_year=issued_month_year,
                credential_id=credential_id,
                credential_url=credential_url,
                assertion_url=assertion_url,
                evidence_url=EVIDENCE_URL,
                linkedin_add_url=linkedin_add,
                linkedin_share_url=linkedin_share,
                badge_image_url=BADGE_IMAGE_URL
            )

            # Write files
            (OUT_ASSERTIONS / f"{credential_id}.json").write_text(json.dumps(assertion, ensure_ascii=False, indent=2), encoding="utf-8")
            (OUT_CREDENTIALS / f"{credential_id}.html").write_text(html, encoding="utf-8")

            rows_out.append({
                "full_name": full_name,
                "email": email,
                "issued_on": issued_on,
                "credential_id": credential_id,
                "credential_url": credential_url,
                "assertion_url": assertion_url,
                "linkedin_add_url": linkedin_add,
                "linkedin_share_url": linkedin_share,
                "evidence_url": EVIDENCE_URL
            })

            print("Issued:", full_name, "->", credential_url)

    # Write mailmerge CSV (LOCAL use; do not commit with emails)
    with open(OUT_MAILMERGE, "w", newline="", encoding="utf-8") as out:
        fieldnames = list(rows_out[0].keys()) if rows_out else []
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    print("\nMailmerge CSV created at:", OUT_MAILMERGE)


if __name__ == "__main__":
    main()
