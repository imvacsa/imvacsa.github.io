# IDNT (아이덴트) - Wallet Pass Generator
# ---------------------------------------------------------------
# Dependencies:
#   pip install python-jose[cryptography] httpx
#
# Apple Wallet (.pkpass):
#   Requires Apple Developer certificates:
#     - Pass Type ID certificate (.pem)
#     - Private key (.pem)
#     - Apple WWDR intermediate certificate (.pem)
#   Set environment variables:
#     IDNT_APPLE_TEAM_ID, IDNT_APPLE_PASS_TYPE_ID,
#     IDNT_APPLE_CERT_PATH, IDNT_APPLE_KEY_PATH, IDNT_APPLE_WWDR_CERT_PATH
#
# Google Wallet:
#   Requires Google Cloud service account with Wallet API enabled.
#   Set environment variables:
#     IDNT_GOOGLE_ISSUER_ID, IDNT_GOOGLE_SERVICE_ACCOUNT_JSON
#
# Usage:
#   from wallet_generator import generate_pkpass, generate_google_wallet_jwt
#   pkpass_bytes = await generate_pkpass(card_image_bytes, employee_data)
#   google_url = await generate_google_wallet_jwt(card_image_bytes, employee_data)
# ---------------------------------------------------------------

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

from config import settings

logger = logging.getLogger("idnt.wallet_generator")


# ═══════════════════════════════════════════════════════════════
# Apple Wallet (.pkpass)
# ═══════════════════════════════════════════════════════════════


def _create_pass_json(employee_data: dict[str, Any]) -> dict[str, Any]:
    """Build the pass.json structure for an Apple Wallet generic pass.

    Reference: https://developer.apple.com/documentation/walletpasses
    """
    name = employee_data.get("name", "")
    department = employee_data.get("department", "")
    position = employee_data.get("position", "")
    employee_number = employee_data.get("employee_number", "")
    email = employee_data.get("email", "")

    # Expiry
    expires_at = employee_data.get("expires_at")
    if isinstance(expires_at, datetime):
        expiry_iso = expires_at.isoformat()
    elif isinstance(expires_at, str):
        expiry_iso = expires_at
    else:
        expiry_iso = None

    serial = employee_data.get("serial_number", str(uuid.uuid4()))

    pass_json: dict[str, Any] = {
        "formatVersion": 1,
        "passTypeIdentifier": settings.apple_pass_type_id,
        "serialNumber": serial,
        "teamIdentifier": settings.apple_team_id,
        "organizationName": settings.apple_organization_name,
        "description": f"IDNT 사원증 - {name}",
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": "rgb(17, 17, 17)",
        "labelColor": "rgb(160, 160, 160)",

        # Barcode
        "barcode": {
            "message": f"idnt://verify/{employee_number}",
            "format": "PKBarcodeFormatQR",
            "messageEncoding": "iso-8859-1",
        },
        "barcodes": [
            {
                "message": f"idnt://verify/{employee_number}",
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1",
            }
        ],

        # Generic pass type
        "generic": {
            "primaryFields": [
                {
                    "key": "name",
                    "label": "이름",
                    "value": name,
                }
            ],
            "secondaryFields": [
                {
                    "key": "department",
                    "label": "부서",
                    "value": department,
                },
                {
                    "key": "position",
                    "label": "직급",
                    "value": position,
                },
            ],
            "auxiliaryFields": [
                {
                    "key": "employee_id",
                    "label": "사번",
                    "value": employee_number,
                },
            ],
            "backFields": [
                {
                    "key": "email",
                    "label": "이메일",
                    "value": email,
                },
                {
                    "key": "issued_by",
                    "label": "발급",
                    "value": "IDNT 디지털 사원증 시스템",
                },
            ],
        },
    }

    if expiry_iso:
        pass_json["expirationDate"] = expiry_iso
        pass_json["generic"]["auxiliaryFields"].append({
            "key": "expiry",
            "label": "만료일",
            "value": expiry_iso,
            "dateStyle": "PKDateStyleShort",
        })

    return pass_json


def _compute_manifest(files: dict[str, bytes]) -> dict[str, str]:
    """Compute SHA-1 hashes for each file in the .pkpass bundle.

    Returns a dict of {filename: sha1_hex}.
    """
    manifest: dict[str, str] = {}
    for name, data in files.items():
        manifest[name] = hashlib.sha1(data).hexdigest()
    return manifest


def _sign_manifest(manifest_bytes: bytes) -> bytes | None:
    """Sign the manifest.json using OpenSSL PKCS#7 (detached).

    Requires the Apple certificates configured in settings.
    Returns the DER-encoded signature bytes, or None if certs are not available.
    """
    cert_path = settings.apple_cert_path
    key_path = settings.apple_key_path
    wwdr_path = settings.apple_wwdr_cert_path

    if not all([cert_path, key_path, wwdr_path]):
        logger.warning(
            "Apple Wallet certificates not configured; "
            "skipping PKCS#7 signature (pass will not be installable)"
        )
        return None

    if not all(os.path.exists(p) for p in [cert_path, key_path, wwdr_path]):
        logger.warning("One or more Apple certificate files not found on disk")
        return None

    import subprocess

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as mf:
        mf.write(manifest_bytes)
        manifest_path = mf.name

    sig_path = manifest_path + ".sig"

    try:
        subprocess.run(
            [
                "openssl", "smime", "-binary", "-sign",
                "-certfile", wwdr_path,
                "-signer", cert_path,
                "-inkey", key_path,
                "-in", manifest_path,
                "-out", sig_path,
                "-outform", "DER",
                "-passin", "pass:",
            ],
            check=True,
            capture_output=True,
        )
        with open(sig_path, "rb") as sf:
            return sf.read()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.error("Failed to sign manifest: %s", exc)
        return None
    finally:
        for p in [manifest_path, sig_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


async def generate_pkpass(
    card_image: bytes,
    employee_data: dict[str, Any],
) -> bytes | None:
    """Create an Apple Wallet .pkpass file.

    The .pkpass is a ZIP archive containing:
        pass.json       - Pass metadata
        manifest.json   - SHA-1 hashes of all files
        signature       - PKCS#7 detached signature (if certs available)
        strip.png       - Card image used as strip image
        thumbnail.png   - Smaller version for notifications
        icon.png        - Pass icon (generated from card)

    Args:
        card_image: PNG bytes of the rendered ID card.
        employee_data: Employee information dict.

    Returns:
        Bytes of the .pkpass ZIP file, or None on failure.
    """
    try:
        from PIL import Image

        # Prepare images at required sizes
        img = Image.open(io.BytesIO(card_image))

        # strip.png: 375 x 123 for generic passes (@1x)
        strip = img.copy()
        strip.thumbnail((750, 246), Image.LANCZOS)
        strip_buf = io.BytesIO()
        strip.save(strip_buf, format="PNG")

        # thumbnail.png: smaller for list view
        thumb = img.copy()
        thumb.thumbnail((180, 180), Image.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb.save(thumb_buf, format="PNG")

        # icon.png: small square icon
        icon = img.copy()
        icon = icon.crop((0, 0, min(img.size), min(img.size)))
        icon = icon.resize((58, 58), Image.LANCZOS)
        icon_buf = io.BytesIO()
        icon.save(icon_buf, format="PNG")

        # Build file map
        pass_json = _create_pass_json(employee_data)
        pass_json_bytes = json.dumps(pass_json, ensure_ascii=False, indent=2).encode("utf-8")

        files: dict[str, bytes] = {
            "pass.json": pass_json_bytes,
            "strip.png": strip_buf.getvalue(),
            "strip@2x.png": card_image,  # Full-res as @2x
            "thumbnail.png": thumb_buf.getvalue(),
            "icon.png": icon_buf.getvalue(),
        }

        # Manifest
        manifest = _compute_manifest(files)
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        files["manifest.json"] = manifest_bytes

        # Signature (optional; requires Apple certs)
        signature = _sign_manifest(manifest_bytes)
        if signature:
            files["signature"] = signature

        # Build ZIP
        pkpass_buf = io.BytesIO()
        with zipfile.ZipFile(pkpass_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in files.items():
                zf.writestr(name, data)

        logger.info(
            "Generated .pkpass for %s (%d bytes)",
            employee_data.get("employee_number", "unknown"),
            pkpass_buf.tell(),
        )
        return pkpass_buf.getvalue()

    except Exception:
        logger.exception("Failed to generate .pkpass")
        return None


# ═══════════════════════════════════════════════════════════════
# Google Wallet
# ═══════════════════════════════════════════════════════════════


def _build_google_pass_object(
    card_image: bytes,
    employee_data: dict[str, Any],
) -> dict[str, Any]:
    """Build the Google Wallet Generic Pass object.

    Reference: https://developers.google.com/wallet/generic
    """
    name = employee_data.get("name", "")
    department = employee_data.get("department", "")
    position = employee_data.get("position", "")
    employee_number = employee_data.get("employee_number", "")

    expires_at = employee_data.get("expires_at")
    if isinstance(expires_at, datetime):
        expiry_iso = expires_at.isoformat()
    elif isinstance(expires_at, str):
        expiry_iso = expires_at
    else:
        expiry_iso = None

    object_id = f"{settings.google_issuer_id}.idnt-{employee_number}"

    # Encode card image as base64 data URI for heroImage
    card_b64 = base64.b64encode(card_image).decode("ascii")

    pass_object: dict[str, Any] = {
        "id": object_id,
        "classId": f"{settings.google_issuer_id}.idnt-employee-card",
        "genericType": "GENERIC_TYPE_UNSPECIFIED",
        "hexBackgroundColor": "#111111",
        "logo": {
            "sourceUri": {
                "uri": "https://idnt.io/logo.png",
                "description": "IDNT Logo",
            },
        },
        "cardTitle": {
            "defaultValue": {
                "language": "ko",
                "value": "IDNT 사원증",
            },
        },
        "subheader": {
            "defaultValue": {
                "language": "ko",
                "value": f"{department} | {position}",
            },
        },
        "header": {
            "defaultValue": {
                "language": "ko",
                "value": name,
            },
        },
        "barcode": {
            "type": "QR_CODE",
            "value": f"idnt://verify/{employee_number}",
        },
        "heroImage": {
            "sourceUri": {
                "uri": f"data:image/png;base64,{card_b64}",
                "description": "ID Card",
            },
        },
        "textModulesData": [
            {
                "id": "employee_number",
                "header": "사번",
                "body": employee_number,
            },
            {
                "id": "department",
                "header": "부서",
                "body": department,
            },
            {
                "id": "position",
                "header": "직급",
                "body": position,
            },
        ],
    }

    if expiry_iso:
        pass_object["validTimeInterval"] = {
            "end": {"date": expiry_iso},
        }

    return pass_object


async def generate_google_wallet_jwt(
    card_image: bytes,
    employee_data: dict[str, Any],
) -> str | None:
    """Create a signed JWT for the Google Wallet Save API.

    The returned URL can be used to add the pass to Google Wallet:
        https://pay.google.com/gp/v/save/{jwt}

    Args:
        card_image: PNG bytes of the rendered ID card.
        employee_data: Employee information dict.

    Returns:
        The full Google Wallet save URL, or None if configuration is missing.
    """
    if not settings.google_issuer_id or not settings.google_service_account_json:
        logger.warning(
            "Google Wallet not configured (missing issuer ID or service account); "
            "skipping JWT generation"
        )
        return None

    try:
        from jose import jwt as jose_jwt

        # Load service account credentials
        sa_path = settings.google_service_account_json
        if os.path.exists(sa_path):
            with open(sa_path, "r") as f:
                sa_info = json.load(f)
        else:
            # Try parsing as inline JSON
            sa_info = json.loads(sa_path)

        # Build the pass object
        pass_object = _build_google_pass_object(card_image, employee_data)

        # JWT claims
        now = datetime.now(timezone.utc)
        claims = {
            "iss": sa_info.get("client_email", ""),
            "aud": "google",
            "typ": "savetowallet",
            "iat": int(now.timestamp()),
            "payload": {
                "genericObjects": [pass_object],
            },
            "origins": ["https://idnt.io"],
        }

        # Sign with the service account private key (RS256)
        private_key = sa_info.get("private_key", "")
        token = jose_jwt.encode(claims, private_key, algorithm="RS256")

        save_url = f"https://pay.google.com/gp/v/save/{token}"

        logger.info(
            "Generated Google Wallet JWT for %s",
            employee_data.get("employee_number", "unknown"),
        )
        return save_url

    except Exception:
        logger.exception("Failed to generate Google Wallet JWT")
        return None
