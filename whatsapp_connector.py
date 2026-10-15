"""WhatsApp Web helper for VEMU. Requires user login and explicit send confirmation."""
import re
import webbrowser
from urllib.parse import quote


def normalize_phone(phone: str) -> str:
    # pywhatkit expects a country code, e.g. +919876543210
    cleaned = re.sub(r"[\s()-]", "", phone)
    if not cleaned.startswith("+") or not cleaned[1:].isdigit():
        raise ValueError("Enter the phone number with country code, e.g. +919876543210.")
    return cleaned


def open_chat(phone: str, message: str = "") -> None:
    phone = normalize_phone(phone)
    url = f"https://web.whatsapp.com/send?phone={phone[1:]}"
    if message:
        url += "&text=" + quote(message)
    webbrowser.open(url, new=2)


def send_message(phone: str, message: str) -> str:
    """Open a prefilled WhatsApp Web chat; user manually reviews and clicks Send."""
    if not message.strip():
        raise ValueError("Message cannot be empty.")
    open_chat(phone, message)
    return "Opened WhatsApp Web with the message prefilled. Review it and click Send yourself."
