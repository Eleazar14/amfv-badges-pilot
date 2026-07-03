#!/usr/bin/env python3
"""
Generate Open Badges (v2) hosted assertions + public credential pages + mailmerge CSV.

Input:
  data/attendees.csv with columns:
  full_name,email,issued_on,certificate_url

Output:
  - assertions/<EVENT_SLUG>/<uuid>.json
  - credentials/<EVENT_SLUG>/<uuid>.html
  - data/output_mailmerge.csv

Important:
  data/attendees.csv and data/output_mailmerge.csv contain personal data.
  Do NOT commit them to GitHub.
"""

import csv
import io
import json
import uuid
import hashlib
import html as html_lib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, quote


# =========================
# CONFIG — PRUEBA PERSONAL ELEAZAR
# =========================

HOST_BASE = "https://eleazar14.github.io/amfv-badges-pilot"

EVENT_SLUG = "ia-fv-test-2026-06"

ISSUER_NAME = "Prueba personal Eleazar - No válida como constancia oficial"

BADGE_NAME = "PRUEBA PERSONAL - IA aplicada en Farmacovigilancia: Casos prácticos e implementación"
BADGE_TITLE_SHORT = "PRUEBA PERSONAL - IA aplicada en Farmacovigilancia"
BADGE_SUBTITLE = "Casos prácticos e implementación"

ISSUE_ORG_FOR_LINKEDIN = "Prueba personal Eleazar - No válida como constancia oficial"

BADGE_IMAGE_URL = f"{HOST_BASE}/images/{EVENT_SLUG}-badge.png"
BADGECLASS_ID = f"{HOST_BASE}/badges/{EVENT_SLUG}.json"
EVIDENCE_URL = f"{HOST_BASE}/evidence/{EVENT_SLUG}.html"


# =========================
# FILES / FOLDERS
# =========================

ROOT = Path(__file__).resolve().parents[1]

IN_CSV = ROOT / "data" / "attendees.csv"

OUT_ASSERTIONS = ROOT / "assertions" / EVENT_SLUG
OUT_CREDENTIALS = ROOT / "credentials" / EVENT_SLUG

OUT_MAILMERGE = ROOT / "data" / "output_mailmerge.csv"


# =========================
# HELPERS
# =========================

def escape_html(value: str) -> str:
    return html_lib.escape(str(value or ""), quote=True)


def hash_email(email: str, salt: str) -> str:
    normalized_email = email.strip().lower()
    return hashlib.sha256((normalized_email + salt).encode("utf-8")).hexdigest()


def iso_z(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def format_date_es(date_str: str) -> str:
    months = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    dt = datetime.fromisoformat(date_str)
    return f"{dt.day} de {months[dt.month]} de {dt.year}"


def read_attendees_csv(csv_path: Path):
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_path}")

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

    text = None
    used_encoding = None

    for encoding in encodings:
        try:
            text = csv_path.read_text(encoding=encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise UnicodeDecodeError(
            "unknown",
            b"",
            0,
            1,
            "No se pudo leer attendees.csv con codificación compatible."
        )

    sample = text[:4096]

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ","

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)

    if reader.fieldnames:
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

    required_input_columns = {
        "full_name",
        "email",
        "issued_on",
        "certificate_url"
    }

    detected_columns = set(reader.fieldnames or [])
    missing_input_columns = required_input_columns - detected_columns

    if missing_input_columns:
        raise ValueError(
            "Faltan columnas en attendees.csv: "
            + ", ".join(sorted(missing_input_columns))
            + "\n\nColumnas detectadas: "
            + ", ".join(reader.fieldnames or [])
        )

    rows = []

    for row in reader:
        cleaned = {}
        for key, value in row.items():
            if key is None:
                continue
            cleaned[key.strip()] = str(value or "").strip()
        rows.append(cleaned)

    print(f"attendees.csv leído con codificación: {used_encoding}")
    print(f"Separador detectado: {repr(dialect.delimiter)}")

    return rows


def build_linkedin_add_url(
    name: str,
    org: str,
    issued_on_yyyy_mm_dd: str,
    credential_url: str,
    credential_id: str
) -> str:
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
    full_name: str,
    badge_title_short: str,
    badge_subtitle: str,
    badge_name: str,
    issuer_name: str,
    issued_date_display: str,
    credential_id: str,
    credential_url: str,
    assertion_url: str,
    evidence_url: str,
    badge_image_url: str
) -> str:
    safe_full_name = escape_html(full_name)
    safe_badge_title_short = escape_html(badge_title_short)
    safe_badge_subtitle = escape_html(badge_subtitle)
    safe_badge_name = escape_html(badge_name)
    safe_issuer_name = escape_html(issuer_name)
    safe_issued_date_display = escape_html(issued_date_display)
    safe_credential_id = escape_html(credential_id)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />

  <title>{safe_badge_name} | Constancia digital de prueba</title>

  <meta property="og:title" content="{safe_badge_name}" />
  <meta property="og:description" content="Constancia digital de prueba personal. No válida como constancia oficial." />
  <meta property="og:image" content="{badge_image_url}" />
  <meta property="og:image:secure_url" content="{badge_image_url}" />
  <meta property="og:url" content="{credential_url}" />
  <meta property="og:type" content="website" />
  <meta name="twitter:card" content="summary_large_image" />

  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; background: #f7f8fb; color: #111111; }}
    .card {{ max-width: 920px; margin: auto; border: 1px solid #dddddd; border-radius: 16px; padding: 28px; background: #ffffff; box-shadow: 0 6px 24px rgba(0,0,0,0.06); }}
    .row {{ display: flex; gap: 30px; align-items: center; flex-wrap: wrap; }}
    .badge-image {{ width: 260px; height: 260px; object-fit: contain; flex-shrink: 0; }}
    .content {{ flex: 1; min-width: 280px; }}
    h1 {{ margin: 0 0 8px 0; font-size: 28px; line-height: 1.2; color: #111111; }}
    .subtitle {{ color: #1d2a5c; font-weight: 600; margin: 0 0 18px 0; font-size: 18px; }}
    .recipient {{ font-size: 18px; margin: 14px 0; }}
    .meta {{ color: #444444; margin: 7px 0; }}
    .id {{ font-family: Consolas, monospace; background: #f1f3f6; padding: 8px 10px; border-radius: 8px; display: inline-block; word-break: break-all; }}
    .btns {{ margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; }}
    a.btn {{ display: inline-block; padding: 10px 14px; border-radius: 10px; border: 1px solid #1d2a5c; color: #1d2a5c; text-decoration: none; font-weight: 600; }}
    a.btn:hover {{ background: #f2f5ff; }}
    .warning {{ margin-top: 24px; padding: 14px 16px; background: #fff3cd; border-left: 4px solid #856404; color: #856404; border-radius: 8px; font-weight: bold; }}
    .note {{ margin-top: 24px; color: #444444; border-top: 1px solid #eeeeee; padding-top: 18px; }}
  </style>
</head>

<body>
  <div class="card">
    <div class="row">
      <img class="badge-image" src="{badge_image_url}" alt="Insignia de prueba IA aplicada en Farmacovigilancia" />

      <div class="content">
        <h1>{safe_badge_title_short}</h1>
        <p class="subtitle">{safe_badge_subtitle}</p>

        <p class="recipient"><b>Otorgada a:</b> {safe_full_name}</p>

        <div class="meta"><b>Emisor:</b> {safe_issuer_name}</div>
        <div class="meta"><b>Fecha de emisión:</b> {safe_issued_date_display}</div>
        <div class="meta"><b>Credential ID:</b> <span class="id">{safe_credential_id}</span></div>

        <div class="btns">
          <a class="btn" href="{assertion_url}" target="_blank" rel="noopener">Ver assertion (JSON)</a>
          <a class="btn" href="{evidence_url}" target="_blank" rel="noopener">Ver evidencia</a>
        </div>
      </div>
    </div>

    <div class="warning">
      PRUEBA PERSONAL. Esta página no constituye una constancia oficial emitida por AMFV.
    </div>

    <p class="note">
      Esta constancia digital de prueba es verificable mediante su assertion hospedada y evidencia asociada.
    </p>
  </div>
</body>
</html>
"""


def main():
    OUT_ASSERTIONS.mkdir(parents=True, exist_ok=True)
    OUT_CREDENTIALS.mkdir(parents=True, exist_ok=True)

    attendees = read_attendees_csv(IN_CSV)

    rows_out = []

    for row in attendees:
        full_name = row.get("full_name", "").strip()
        email = row.get("email", "").strip()
        issued_on = row.get("issued_on", "").strip()
        certificate_url = row.get("certificate_url", "").strip()

        if not full_name or not email or not issued_on or not certificate_url:
            print("Fila omitida por datos incompletos:", row)
            continue

        credential_id = str(uuid.uuid4())
        salt = uuid.uuid4().hex
        hashed_email = hash_email(email, salt)

        issued_on_iso = iso_z(issued_on)
        issued_date_display = format_date_es(issued_on)

        assertion_url = f"{HOST_BASE}/assertions/{EVENT_SLUG}/{credential_id}.json"
        credential_url = f"{HOST_BASE}/credentials/{EVENT_SLUG}/{credential_id}.html"

        assertion = {
            "@context": "https://w3id.org/openbadges/v2",
            "type": "Assertion",
            "id": assertion_url,
            "recipient": {
                "type": "email",
                "hashed": True,
                "salt": salt,
                "identity": f"sha256${hashed_email}"
            },
            "issuedOn": issued_on_iso,
            "badge": BADGECLASS_ID,
            "verification": {
                "type": "hosted"
            },
            "evidence": [
                {
                    "id": EVIDENCE_URL,
                    "narrative": (
                        "Evidencia de prueba personal para validar el flujo técnico de constancias digitales. "
                        "No constituye una constancia oficial emitida por AMFV."
                    )
                }
            ]
        }

        linkedin_add_url = build_linkedin_add_url(
            BADGE_NAME,
            ISSUE_ORG_FOR_LINKEDIN,
            issued_on,
            credential_url,
            credential_id
        )

        linkedin_share_url = build_linkedin_share_url(credential_url)

        credential_html = render_credential_html(
            full_name=full_name,
            badge_title_short=BADGE_TITLE_SHORT,
            badge_subtitle=BADGE_SUBTITLE,
            badge_name=BADGE_NAME,
            issuer_name=ISSUER_NAME,
            issued_date_display=issued_date_display,
            credential_id=credential_id,
            credential_url=credential_url,
            assertion_url=assertion_url,
            evidence_url=EVIDENCE_URL,
            badge_image_url=BADGE_IMAGE_URL
        )

        (OUT_ASSERTIONS / f"{credential_id}.json").write_text(
            json.dumps(assertion, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        (OUT_CREDENTIALS / f"{credential_id}.html").write_text(
            credential_html,
            encoding="utf-8"
        )

        rows_out.append({
            "full_name": full_name,
            "email": email,
            "issued_on": issued_on,
            "credential_id": credential_id,
            "credential_url": credential_url,
            "assertion_url": assertion_url,
            "linkedin_add_url": linkedin_add_url,
            "linkedin_share_url": linkedin_share_url,
            "evidence_url": EVIDENCE_URL,
            "certificate_url": certificate_url
        })

        print("Issued:", full_name, "->", credential_url)

    fieldnames = [
        "full_name",
        "email",
        "issued_on",
        "credential_id",
        "credential_url",
        "assertion_url",
        "linkedin_add_url",
        "linkedin_share_url",
        "evidence_url",
        "certificate_url"
    ]

    with open(OUT_MAILMERGE, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows_out:
            writer.writerow(row)

    print("\nTotal credentials issued:", len(rows_out))
    print("Mailmerge CSV created at:", OUT_MAILMERGE)


if __name__ == "__main__":
    main()
