"""
VEMU Stage 2: Gmail + Outlook email integration.
Read latest/unread messages and send only after explicit confirmation.
Credentials are stored locally in token files; never share those files.
"""
import os
import base64
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

def gmail_service():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("Gmail packages missing. Run pip install -r requirements.txt") from exc

    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    token_path = ROOT / "gmail_token.json"
    credentials_path = ROOT / "credentials.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise RuntimeError(
                    "Missing credentials.json. Create a Google OAuth Desktop app in Google Cloud "
                    "and download its OAuth client JSON into this folder as credentials.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def gmail_latest(max_results=10, unread_only=False):
    service = gmail_service()
    query = "is:unread" if unread_only else "newer_than:2d"
    data = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = data.get("messages", [])
    output = []
    for item in messages:
        msg = service.users().messages().get(userId="me", id=item["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        output.append({
            "from": headers.get("from", "(unknown sender)"),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return output

def gmail_send(to, subject, body):
    from googleapiclient.errors import HttpError
    service = gmail_service()
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    try:
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return result.get("id", "sent")
    except HttpError as exc:
        raise RuntimeError(f"Gmail send failed: {exc}") from exc

def outlook_client():
    try:
        import msal
        import requests
    except ImportError as exc:
        raise RuntimeError("Outlook packages missing. Run pip install -r requirements.txt") from exc

    client_id = os.getenv("OUTLOOK_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("Set OUTLOOK_CLIENT_ID in .env after registering a Microsoft Entra app.")
    authority = "https://login.microsoftonline.com/consumers"
    cache_path = ROOT / "outlook_token_cache.json"
    cache = msal.SerializableTokenCache()
    if cache_path.exists():
        cache.deserialize(cache_path.read_text(encoding="utf-8"))
    app = msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)
    scopes = ["User.Read", "Mail.Read", "Mail.Send"]
    accounts = app.get_accounts()
    result = app.acquire_token_silent(scopes, account=accounts[0]) if accounts else None
    if not result:
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Could not start Microsoft sign-in: {flow}")
        print("\nOUTLOOK SIGN-IN: " + flow["message"] + "\n")
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError("Outlook sign-in failed: " + result.get("error_description", str(result)))
    if cache.has_state_changed:
        cache_path.write_text(cache.serialize(), encoding="utf-8")
    return result["access_token"]

def outlook_latest(max_results=10, unread_only=False):
    import requests
    token = outlook_client()
    params = {"$top": max_results, "$select": "from,subject,receivedDateTime,bodyPreview,isRead"}
    if unread_only:
        params["$filter"] = "isRead eq false"
    url = "https://graph.microsoft.com/v1.0/me/messages"
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=20)
    response.raise_for_status()
    output = []
    for msg in response.json().get("value", []):
        sender = (msg.get("from") or {}).get("emailAddress") or {}
        output.append({
            "from": sender.get("name") or sender.get("address", "(unknown sender)"),
            "subject": msg.get("subject") or "(no subject)",
            "date": msg.get("receivedDateTime", ""),
            "snippet": msg.get("bodyPreview", ""),
        })
    return output

def outlook_send(to, subject, body):
    import requests
    token = outlook_client()
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload, timeout=20
    )
    if response.status_code not in (200, 202):
        raise RuntimeError(f"Outlook send failed ({response.status_code}): {response.text}")
    return "sent"

def print_messages(provider, messages):
    if not messages:
        print(f"\nNo matching {provider} emails found.\n")
        return
    print(f"\n--- {provider.upper()} EMAILS ({len(messages)}) ---")
    for i, m in enumerate(messages, 1):
        print(f"\n{i}. From: {m['from']}\n   Subject: {m['subject']}\n   Date: {m['date']}\n   Preview: {m['snippet']}")
    print()

def main():
    print("VEMU Email Console — type gmail / outlook, then read / unread / send")
    provider = input("Provider (gmail/outlook): ").strip().lower()
    if provider not in ("gmail", "outlook"):
        print("Choose gmail or outlook.")
        return
    action = input("Action (read/unread/send): ").strip().lower()
    try:
        if action in ("read", "unread"):
            func = gmail_latest if provider == "gmail" else outlook_latest
            print_messages(provider, func(unread_only=(action == "unread")))
        elif action == "send":
            to = input("Recipient email address: ").strip()
            subject = input("Subject: ").strip()
            body = input("Email body: ").strip()
            if not to or "@" not in to or not subject or not body:
                print("Recipient, subject, and body are required.")
                return
            print(f"\nREVIEW EMAIL\nTo: {to}\nSubject: {subject}\nBody: {body}\n")
            confirm = input("Type SEND to send this exact email: ").strip()
            if confirm != "SEND":
                print("Cancelled. Nothing was sent.")
                return
            result = gmail_send(to, subject, body) if provider == "gmail" else outlook_send(to, subject, body)
            print("Email sent. Reference:", result)
        else:
            print("Action must be read, unread, or send.")
    except Exception as exc:
        print("\nERROR:", exc)

if __name__ == "__main__":
    main()
