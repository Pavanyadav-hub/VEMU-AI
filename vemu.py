"""
VEMU AI - Stage 1 (Windows)
Voice-first assistant for wake word, app/site launching, web/YouTube search,
date/time, weather, and optional AI advice.

This is a local Windows program. It does not yet read/send WhatsApp or email.
Those integrations are planned for later stages and should use official APIs
where possible. Sending messages will require confirmation.
"""
import os
import re
import sys
import time
import json
import webbrowser
import subprocess
import urllib.parse
import datetime as dt
from pathlib import Path
from email.utils import parseaddr

try:
    import speech_recognition as sr
    import pyttsx3
    import requests
    from dotenv import load_dotenv
except ImportError as exc:
    print(f"Missing package: {exc}\nRun: python -m pip install -r requirements.txt")
    raise

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

WAKE_WORDS = ("vemu", "venu", "venmu", "vemmu", "veemu", "hey vemu")
STOP_PHRASES = ("bye vemu", "goodbye vemu", "stop listening", "exit vemu", "quit vemu")
VOICE_RATE = int(os.getenv("VEMU_VOICE_RATE", "175"))
WEATHER_CITY = os.getenv("VEMU_DEFAULT_CITY", "").strip()
AI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
EMAIL_PROVIDER = os.getenv("VEMU_EMAIL_PROVIDER", "gmail").strip().lower()
DAILY_BRIEFING_TIME = os.getenv("VEMU_DAILY_BRIEFING_TIME", "").strip()
_last_briefing_date = ""

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.7
engine = pyttsx3.init()
engine.setProperty("rate", VOICE_RATE)

def speak(text: str):
    """Speak and print every response."""
    print(f"\nVEMU: {text}\n")
    engine.say(text)
    engine.runAndWait()

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())

def open_url(url: str):
    webbrowser.open(url, new=2)

def open_app(app_name: str) -> bool:
    """Open a selection of common Windows apps; unknown apps fall back to Start search."""
    key = normalize(app_name)
    known = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "command prompt": ["cmd.exe"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "task manager": ["taskmgr.exe"],
        "settings": ["cmd", "/c", "start", "", "ms-settings:"],
        "control panel": ["control.exe"],
        "word": ["cmd", "/c", "start", "", "winword"],
        "microsoft word": ["cmd", "/c", "start", "", "winword"],
        "excel": ["cmd", "/c", "start", "", "excel"],
        "microsoft excel": ["cmd", "/c", "start", "", "excel"],
        "powerpoint": ["cmd", "/c", "start", "", "powerpnt"],
        "microsoft powerpoint": ["cmd", "/c", "start", "", "powerpnt"],
        "whatsapp": ["cmd", "/c", "start", "", "whatsapp:"],
        "outlook": ["cmd", "/c", "start", "", "outlook"],
        "microsoft outlook": ["cmd", "/c", "start", "", "outlook"],
        "chrome": ["cmd", "/c", "start", "", "chrome"],
        "edge": ["cmd", "/c", "start", "", "msedge"],
    }
    try:
        if key in known:
            subprocess.Popen(known[key], shell=False)
            return True
        # Use Windows Start menu search for other installed apps.
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder"], shell=False)
        speak(f"I opened the applications folder. You can select {app_name} there.")
        return True
    except Exception as exc:
        print("App launch error:", exc)
        return False

def search_web(query: str):
    open_url("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
    speak(f"Searching the web for {query}.")

def search_youtube(query: str):
    open_url("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query))
    speak(f"Searching YouTube for {query}.")

def get_weather(city: str):
    """Fetch current conditions and today's forecast from Open-Meteo; no API key required."""
    city = city.strip()
    if not city:
        city = WEATHER_CITY
    if not city:
        speak("Which city should I check the weather for?")
        city = listen_once(timeout=7, phrase_time_limit=5)
        if not city:
            speak("I did not hear the city. Say weather in followed by a city name.")
            return
        city = re.sub(r"^(in|for)\s+", "", city.strip(), flags=re.I)
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10
        )
        geo.raise_for_status()
        results = geo.json().get("results", [])
        if not results:
            speak(f"I couldn't find the city {city}. Please try another city.")
            return
        place = results[0]
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 1
            },
            timeout=10
        )
        forecast.raise_for_status()
        data = forecast.json()
        cur = data.get("current", {})
        daily = data.get("daily", {})
        code = int(cur.get("weather_code", -1))
        descriptions = {
            0:"clear sky", 1:"mainly clear", 2:"partly cloudy", 3:"overcast",
            45:"fog", 48:"depositing rime fog", 51:"light drizzle", 53:"moderate drizzle",
            55:"dense drizzle", 61:"slight rain", 63:"moderate rain", 65:"heavy rain",
            71:"slight snow", 73:"moderate snow", 75:"heavy snow", 80:"rain showers",
            81:"moderate rain showers", 82:"violent rain showers", 95:"thunderstorm",
            96:"thunderstorm with hail", 99:"strong thunderstorm with hail"
        }
        desc = descriptions.get(code, "conditions not specified")
        msg = (f"Weather in {place.get('name', city)}: {cur.get('temperature_2m', 'unknown')} degrees Celsius, "
               f"{desc}. Feels like {cur.get('apparent_temperature', 'unknown')} degrees. "
               f"Today's high is {daily.get('temperature_2m_max', ['unknown'])[0]} degrees and low is "
               f"{daily.get('temperature_2m_min', ['unknown'])[0]} degrees Celsius. "
               f"Maximum chance of precipitation is {daily.get('precipitation_probability_max', ['unknown'])[0]} percent.")
        speak(msg)
    except Exception as exc:
        print("Weather error:", exc)
        speak("I couldn't get the weather right now. Please check your internet connection and try again.")

def ask_ai(question: str):
    """Optional OpenAI-compatible advice. Works when OPENAI_API_KEY is configured."""
    if not AI_API_KEY:
        speak("AI advice is not configured yet. Add your API key to the .env file to enable it. I can still search the web for information.")
        return
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": "You are VEMU, a helpful, concise personal assistant. Give practical advice, explain tradeoffs, and do not claim to have performed actions you did not perform."},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.5
            },
            timeout=45
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"].strip()
        speak(answer)
    except Exception as exc:
        print("AI API error:", exc)
        speak("I couldn't reach the AI service. Check your API key, internet connection, and account access.")

def email_read(unread_only=False):
    """Read a short list of email headers/snippets through configured provider."""
    provider = EMAIL_PROVIDER if EMAIL_PROVIDER in ("gmail", "outlook") else "gmail"
    try:
        from email_connectors import gmail_latest, outlook_latest
        getter = gmail_latest if provider == "gmail" else outlook_latest
        messages = getter(max_results=5, unread_only=unread_only)
        if not messages:
            speak(f"You have no matching {provider} emails.")
            return
        speak(f"Here are {len(messages)} {provider} emails.")
        for index, item in enumerate(messages[:5], 1):
            sender = item.get("from", "unknown sender")
            subject = item.get("subject", "no subject")
            print(f"{index}. From: {sender}\n   Subject: {subject}\n   Date: {item.get('date', '')}\n   Preview: {item.get('snippet', '')}\n")
            speak(f"Email {index}. From {sender}. Subject {subject}.")
    except Exception as exc:
        print("Email error:", exc)
        speak("I couldn't access your email. Check the setup instructions in the README and your account authorization.")


def email_send_interactive():
    """Collect email fields in terminal and require exact confirmation before sending."""
    provider = EMAIL_PROVIDER if EMAIL_PROVIDER in ("gmail", "outlook") else "gmail"
    print("\nVEMU EMAIL COMPOSER")
    to = input("Recipient email: ").strip()
    subject = input("Subject: ").strip()
    body = input("Message body: ").strip()
    address = parseaddr(to)[1]
    if not address or "@" not in address or not subject or not body:
        speak("Recipient, subject, and message are required. Nothing was sent.")
        return
    print(f"\nREVIEW BEFORE SENDING\nTo: {address}\nSubject: {subject}\n\n{body}\n")
    if input("Type SEND to send this exact email: ").strip() != "SEND":
        speak("Cancelled. Nothing was sent.")
        return
    try:
        from email_connectors import gmail_send, outlook_send
        sender = gmail_send if provider == "gmail" else outlook_send
        sender(address, subject, body)
        speak(f"Email sent through {provider}.")
    except Exception as exc:
        print("Email send error:", exc)
        speak("The email could not be sent. Check the account setup and internet connection.")


def whatsapp_send_interactive():
    """Prepare a WhatsApp Web message; user manually reviews and clicks Send."""
    print("\nVEMU WHATSAPP COMPOSER")
    phone = input("Recipient phone with country code, e.g. +919876543210: ").strip()
    message = input("Message: ").strip()
    if not phone or not message:
        speak("A phone number and message are required.")
        return
    print(f"\nREVIEW MESSAGE\nTo: {phone}\nMessage: {message}\n")
    if input("Type OPEN to prepare this message in WhatsApp Web: ").strip() != "OPEN":
        speak("Cancelled. No chat was opened.")
        return
    try:
        from whatsapp_connector import send_message
        result = send_message(phone, message)
        speak(result)
    except Exception as exc:
        print("WhatsApp error:", exc)
        speak("I couldn't prepare the WhatsApp message. Check the phone number format.")


def daily_briefing():
    """Give a basic daily briefing and, if configured, summarize email headers."""
    now = dt.datetime.now()
    parts = [f"Good day sir. Today is {now.strftime('%A, %d %B %Y')}. The time is {now.strftime('%I:%M %p')}."]
    provider = EMAIL_PROVIDER if EMAIL_PROVIDER in ("gmail", "outlook") else ""
    if provider:
        try:
            from email_connectors import gmail_latest, outlook_latest
            getter = gmail_latest if provider == "gmail" else outlook_latest
            unread = getter(max_results=5, unread_only=True)
            parts.append(f"You have {len(unread)} unread {provider} email messages in the latest results.")
            for item in unread[:3]:
                parts.append(f"From {item.get('from', 'unknown sender')}, subject {item.get('subject', 'no subject')}.")
        except Exception as exc:
            print("Briefing email error:", exc)
            parts.append("I could not load your email summary. Check your email authorization.")
    else:
        parts.append("Email briefing is disabled. Set VEMU_EMAIL_PROVIDER in your .env file to gmail or outlook after configuring access.")
    for part in parts:
        speak(part)


def maybe_run_scheduled_briefing():
    """Runs once per local date when the configured HH:MM time is reached."""
    global _last_briefing_date
    if not DAILY_BRIEFING_TIME or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", DAILY_BRIEFING_TIME):
        return
    now = dt.datetime.now()
    if now.strftime("%H:%M") == DAILY_BRIEFING_TIME and _last_briefing_date != now.date().isoformat():
        _last_briefing_date = now.date().isoformat()
        daily_briefing()


def handle_command(command: str):
    c = normalize(command)
    if not c:
        return

    # Email, WhatsApp, and daily briefing features (Stages 2-4).
    if c in ("read emails", "read email", "read gmail", "read outlook", "check emails", "check my email"):
        email_read(unread_only=False)
        return
    if c in ("unread emails", "read unread emails", "check unread emails", "unread mail"):
        email_read(unread_only=True)
        return
    if c in ("send email", "compose email", "write email"):
        email_send_interactive()
        return
    if c in ("send whatsapp", "send whatsapp message", "whatsapp message", "message on whatsapp"):
        whatsapp_send_interactive()
        return
    if c in ("daily briefing", "morning briefing", "give me my briefing", "today briefing"):
        daily_briefing()
        return

    if any(phrase in c for phrase in STOP_PHRASES):
        speak("Goodbye sir. VEMU is stopping.")
        raise SystemExit

    # Strip wake words if speech recognition includes them in the command.
    for word in WAKE_WORDS:
        c = re.sub(r"\b" + re.escape(word) + r"\b", "", c).strip()
    c = re.sub(r"^[,.\s]+", "", c)

    if c in ("", "hello", "hi", "hey"):
        speak("Yes sir, how can I help?")
    elif "what time" in c or c == "time" or "current time" in c:
        speak("The time is " + dt.datetime.now().strftime("%I:%M %p"))
    elif "what date" in c or "today's date" in c or c == "date" or "what day" in c:
        speak("Today is " + dt.datetime.now().strftime("%A, %d %B %Y"))
    elif c.startswith("weather") or "weather today" in c or "temperature" in c:
        city_match = re.search(r"(?:weather|temperature)(?:\s+(?:in|for))?\s+(.+)$", c)
        city = city_match.group(1) if city_match else ""
        get_weather(city)
    elif c.startswith("open youtube"):
        query = re.sub(r"^open youtube\s*", "", c).strip()
        if query:
            search_youtube(query)
        else:
            open_url("https://www.youtube.com")
            speak("Opening YouTube.")
    elif c.startswith("search youtube for "):
        search_youtube(c[len("search youtube for "):].strip())
    elif c.startswith("search the web for "):
        search_web(c[len("search the web for "):].strip())
    elif c.startswith("search for "):
        search_web(c[len("search for "):].strip())
    elif c.startswith("google "):
        search_web(c[len("google "):].strip())
    elif c.startswith("open website "):
        site = c[len("open website "):].strip()
        if "." not in site:
            site += ".com"
        if not site.startswith(("http://", "https://")):
            site = "https://" + site
        open_url(site)
        speak(f"Opening {site}.")
    elif c.startswith("open "):
        target = c[len("open "):].strip()
        sites = {
            "gmail": "https://mail.google.com",
            "google mail": "https://mail.google.com",
            "outlook": "https://outlook.office.com/mail/",
            "whatsapp web": "https://web.whatsapp.com",
            "whatsapp": "https://web.whatsapp.com",
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
            "chatgpt": "https://chatgpt.com",
            "github": "https://github.com",
            "google drive": "https://drive.google.com",
        }
        if target in sites:
            open_url(sites[target])
            speak(f"Opening {target}.")
        elif open_app(target):
            speak(f"Trying to open {target}.")
        else:
            speak(f"I couldn't open {target}.")
    elif c.startswith("advise me ") or c.startswith("give me advice about "):
        question = re.sub(r"^(advise me|give me advice about)\s*", "", c).strip()
        ask_ai(question)
    elif c.startswith("which is better") or c.startswith("compare "):
        ask_ai(c)
    elif c.startswith("ask vemu ") or c.startswith("tell me "):
        ask_ai(c)
    elif c.startswith("help") or "what can you do" in c:
        speak("I can open apps and websites, search YouTube or Google, tell the date and time, check weather, give AI advice, read email, prepare emails and WhatsApp messages, and give a daily briefing. Sending email requires typing SEND. WhatsApp messages open in WhatsApp Web for you to review and click Send. Say Bye VEMU to stop.")
    else:
        # Treat unrecognized natural language as a question for the optional AI, otherwise search.
        if AI_API_KEY:
            ask_ai(command)
        else:
            search_web(command)
            speak("I searched the web because AI advice is not configured yet.")

def listen_once(timeout=8, phrase_time_limit=8):
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            speak("Speech recognition needs an internet connection.")
            return ""
    except sr.WaitTimeoutError:
        return ""
    except (OSError, AttributeError) as exc:
        print("Microphone error:", exc)
        speak("I can't access your microphone. Check Windows microphone permissions and the selected input device.")
        time.sleep(2)
        return ""

def main():
    if os.name != "nt":
        print("This project is designed for Windows. Some app-launch commands may not work on other systems.")
    print("=" * 58)
    print("VEMU AI - FULL PROJECT (Stages 1-5)")
    print("Say 'Hey VEMU' followed by a command. Ctrl+C exits.")
    print("Examples: open YouTube; read emails; send email; send WhatsApp; daily briefing; weather in Hyderabad.")
    if DAILY_BRIEFING_TIME:
        print(f"Automatic daily briefing is configured for {DAILY_BRIEFING_TIME} while VEMU is running.")
    print("=" * 58)
    speak("Hi sir, VEMU here. I am ready. Say Hey VEMU followed by a command.")
    try:
        while True:
            maybe_run_scheduled_briefing()
            heard = listen_once(timeout=2, phrase_time_limit=8)
            if not heard:
                continue
            print("Heard:", heard)
            text = normalize(heard)
            if any(p in text for p in STOP_PHRASES):
                speak("Goodbye sir. VEMU is stopping.")
                break
            if any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in WAKE_WORDS):
                command = text
                # If only the wake phrase was heard, listen for the actual request.
                stripped = text
                for w in WAKE_WORDS:
                    stripped = re.sub(r"\b" + re.escape(w) + r"\b", "", stripped).strip(" ,.")
                if not stripped:
                    speak("Yes sir?")
                    command = listen_once(timeout=7, phrase_time_limit=10)
                    if not command:
                        continue
                handle_command(command)
    except KeyboardInterrupt:
        print("\nExiting VEMU.")
        speak("Goodbye sir.")

if __name__ == "__main__":
    main()
