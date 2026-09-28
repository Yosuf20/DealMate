"""Controlled WhatsApp messaging abstraction for local seller outreach."""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

SERVICE_URL = os.environ.get("WHATSAPP_SERVICE_URL", "http://127.0.0.1:3001").rstrip("/")
AUTO_SEND = os.environ.get("WHATSAPP_AUTO_SEND", "false").lower() == "true"
MESSAGE_DELAY_MS = max(0, int(os.environ.get("WHATSAPP_MESSAGE_DELAY_MS", "3000")))
MAX_MESSAGES_PER_REQUEST = max(1, int(os.environ.get("WHATSAPP_MAX_MESSAGES_PER_REQUEST", "10")))
PENDING_FILE = Path(__file__).resolve().parents[2] / "data" / "whatsapp-pending.json"


def normalize_phone_number(phone_number: str) -> str:
    """Normalize a phone number to international digits without a plus sign."""
    normalized = re.sub(r"[^0-9]", "", str(phone_number or ""))
    if normalized.startswith("00"):
        normalized = normalized[2:]
    if not re.fullmatch(r"[1-9][0-9]{7,14}", normalized):
        raise ValueError("Invalid phone number. Use international format, for example 919876543210.")
    return normalized


def build_seller_message(seller_name: str, product: str, variant: Optional[str] = None) -> str:
    requested_product = " ".join(part for part in [product, variant] if part).strip()
    return (
        f"Hi {seller_name}, I'm looking for {requested_product}. "
        "Do you currently have it in stock? If yes, please share your best price."
    )


def _message_id(seller_name: str, phone: str, message: str, request_id: str) -> str:
    raw = f"{request_id}|{seller_name}|{phone}|{message}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _read_pending() -> List[Dict[str, Any]]:
    try:
        return json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _write_pending(entries: List[Dict[str, Any]]) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps(entries[-500:], indent=2), encoding="utf-8")


def whatsapp_request(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call the internal Node service and convert transport failures to clean errors."""
    try:
        response = requests.request(
            method,
            f"{SERVICE_URL}{path}",
            json=payload,
            timeout=10,
        )
        data = response.json()
    except requests.RequestException as error:
        raise RuntimeError("WhatsApp service is unavailable. Start the WhatsApp service first.") from error
    except ValueError as error:
        raise RuntimeError("WhatsApp service returned an invalid response.") from error
    if response.status_code >= 400:
        raise RuntimeError(data.get("error", "WhatsApp request failed."))
    return data


def send_seller_whatsapp_message(
    seller_name: str,
    phone_number: str,
    message: str,
    request_id: str = "adhoc",
) -> Dict[str, Any]:
    """Controlled send operation exposed to application code, never raw LLM commands."""
    normalized_phone = normalize_phone_number(phone_number)
    if not str(message or "").strip():
        raise ValueError("Message cannot be empty.")
    return whatsapp_request(
        "POST",
        "/whatsapp/send",
        {
            "seller": seller_name,
            "phone": normalized_phone,
            "message": message.strip(),
            "requestId": request_id,
        },
    )


def prepare_seller_messages(
    sellers: List[Dict[str, Any]],
    product: str,
    variant: Optional[str],
    request_id: str,
) -> List[Dict[str, Any]]:
    """Create approval records, or send them sequentially when explicitly enabled."""
    pending = _read_pending()
    prepared: List[Dict[str, Any]] = []
    eligible_sellers = [seller for seller in sellers if seller.get("phone")]
    if len(eligible_sellers) > MAX_MESSAGES_PER_REQUEST:
        eligible_sellers = eligible_sellers[:MAX_MESSAGES_PER_REQUEST]

    for index, seller in enumerate(eligible_sellers):
        seller_name = str(seller.get("seller_name") or seller.get("name") or "Local seller")
        phone = normalize_phone_number(seller["phone"])
        message = build_seller_message(seller_name, product, variant)
        item = {
            "id": _message_id(seller_name, phone, message, request_id),
            "request_id": request_id,
            "seller": seller_name,
            "phone": phone,
            "message": message,
            "status": "PENDING",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        existing = next((entry for entry in pending if entry.get("id") == item["id"]), None)
        if existing:
            item = existing
        elif AUTO_SEND:
            try:
                item["status"] = "SENDING"
                result = send_seller_whatsapp_message(seller_name, phone, message, request_id)
                item["status"] = "SENT" if result.get("success") else "FAILED"
                item["message_id"] = result.get("messageId")
                item["error"] = result.get("error")
            except (RuntimeError, ValueError) as error:
                item["status"] = "FAILED"
                item["error"] = str(error)
            if index < len(eligible_sellers) - 1:
                time.sleep(MESSAGE_DELAY_MS / 1000)
            pending.append(item)
        else:
            pending.append(item)
        prepared.append(item)

    _write_pending(pending)
    return prepared


def list_pending_messages() -> List[Dict[str, Any]]:
    return [entry for entry in _read_pending() if entry.get("status") == "PENDING"]


def approve_pending_message(message_id: str) -> Dict[str, Any]:
    pending = _read_pending()
    item = next((entry for entry in pending if entry.get("id") == message_id), None)
    if not item:
        raise ValueError("Pending WhatsApp message was not found.")
    if item.get("status") == "SENT":
        return item
    if item.get("status") != "PENDING":
        raise ValueError(f"Message cannot be sent from status {item.get('status')}.")
    item["status"] = "SENDING"
    _write_pending(pending)
    try:
        result = send_seller_whatsapp_message(item["seller"], item["phone"], item["message"], item["request_id"])
        item["status"] = "SENT" if result.get("success") else "FAILED"
        item["message_id"] = result.get("messageId")
        item["error"] = result.get("error")
    except (RuntimeError, ValueError) as error:
        item["status"] = "FAILED"
        item["error"] = str(error)
    _write_pending(pending)
    return item


def cancel_pending_message(message_id: str) -> Dict[str, Any]:
    pending = _read_pending()
    item = next((entry for entry in pending if entry.get("id") == message_id), None)
    if not item:
        raise ValueError("Pending WhatsApp message was not found.")
    if item.get("status") == "PENDING":
        item["status"] = "CANCELLED"
        _write_pending(pending)
    return item
