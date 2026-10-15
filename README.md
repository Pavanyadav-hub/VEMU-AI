# VEMU AI — Full Windows Assistant

VEMU is a local Windows voice assistant starter project. This repository combines the core assistant, optional AI advice, Gmail/Outlook connectors, WhatsApp Web message preparation, and a simple scheduled daily briefing.

## Included features

- Wake phrases: `vemu`, `hey vemu`, `venu`, `venmu`, `vemmu`, `veemu`
- Spoken greeting: **“Hi sir, VEMU here”**
- Open common Windows apps and websites
- Search Google and YouTube
- Date, time, and weather lookup
- Optional AI answers/advice using an OpenAI API key
- Gmail: list recent or unread email headers/snippets; send after a typed `SEND` confirmation
- Outlook: same email features through Microsoft Graph, if configured
- WhatsApp: open WhatsApp Web with a prefilled message after typed confirmation; **you review the chat and click Send yourself**
- Daily briefing on demand, plus optional automatic briefing at a configured time while the program is running
- `.gitignore` excludes credentials and token files

## Important limitations

- This is a **local Windows program**, not a GitHub-hosted web app. It must be running on your laptop to hear voice commands, open desktop apps, and run the scheduled briefing.
- Voice recognition uses Google's online Speech Recognition endpoint; internet is required.
- Gmail/Outlook access requires your own OAuth setup and consent. This project never asks you to paste your account password into the code.
- WhatsApp does **not** have a general consumer API for reading a personal inbox. This project does not scrape incoming WhatsApp chats or automatically click Send. It prepares a message in WhatsApp Web for you to review and send.
- The automatic daily briefing runs only while VEMU is running. For startup-at-boot or reliable scheduled startup, configure Windows Task Scheduler separately.
- AI answers require your own API key and may incur provider charges.

## 1. Install on Windows

Install Python 3.11 (64-bit) from https://www.python.org/downloads/windows/ and enable **Add Python to PATH**.

Open Command Prompt inside the repository folder, then run:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`. Edit `.env` in Notepad. Leave keys blank until you configure the related service.

```bat
python vemu.py
```

Say **“Hey VEMU”** followed by a command. Say **“Bye VEMU”** to exit. Press `Ctrl+C` to stop.

## 2. Example voice commands

- `Hey VEMU, open YouTube`
- `Hey VEMU, search YouTube for ESP32 projects`
- `Hey VEMU, open Notepad`
- `Hey VEMU, what time is it?`
- `Hey VEMU, weather in Hyderabad`
- `Hey VEMU, advise me which laptop is better for EEE`
- `Hey VEMU, read emails`
- `Hey VEMU, unread emails`
- `Hey VEMU, send email` (then complete the prompts in the terminal)
- `Hey VEMU, send WhatsApp message` (then complete the prompts in the terminal)
- `Hey VEMU, daily briefing`
- `Bye VEMU`

Email and WhatsApp message composition uses terminal prompts, so keep the Command Prompt window visible.

## 3. Configure AI advice (optional)

1. Create an API key with your chosen compatible provider.
2. Put it in `.env` as `OPENAI_API_KEY=your_key_here`.
3. Set `OPENAI_MODEL` to a model available to your account.
4. Never commit `.env` to GitHub.

## 4. Configure Gmail

1. Open Google Cloud Console: https://console.cloud.google.com/
2. Create/select a project and enable **Gmail API**.
3. Configure OAuth consent screen and add your Google account as a test user if the app is in testing.
4. Create an OAuth Client ID with application type **Desktop app**.
5. Download the client JSON into this project folder and name it `credentials.json`.
6. Run `python vemu.py`, then say `Hey VEMU, read emails`. A browser window will ask you to sign in and consent.
7. The generated `gmail_token.json` is private. Do not upload it to GitHub.

The app requests Gmail read-only access and send access. Only approve if you understand and want these permissions.

## 5. Configure Outlook (optional instead of Gmail)

1. Register an app in Microsoft Entra: https://entra.microsoft.com/
2. Enable public-client/device-code flow as required by your tenant.
3. Add delegated Microsoft Graph permissions: `User.Read`, `Mail.Read`, `Mail.Send`.
4. Put the app's client ID in `.env` as `OUTLOOK_CLIENT_ID=...`.
5. Set `VEMU_EMAIL_PROVIDER=outlook` in `.env`.
6. Run VEMU and use an email command. Follow the device-code sign-in instructions printed in the terminal.

Use `VEMU_EMAIL_PROVIDER=gmail` if you prefer Gmail. Only one provider is selected for voice commands at a time.

## 6. WhatsApp

1. Ensure WhatsApp Web is available in your browser and sign in yourself.
2. Say `Hey VEMU, send WhatsApp message`.
3. Enter the phone number with country code, such as `+919876543210`, and the message in the terminal.
4. Type `OPEN` after reviewing the recipient and message.
5. WhatsApp Web opens with the message prefilled. Check the recipient/content and click **Send** yourself.

VEMU does not automatically send the message or read your incoming WhatsApp inbox.

## 7. Daily briefing

Set these values in `.env`:

```dotenv
VEMU_DAILY_BRIEFING_TIME=08:00
VEMU_EMAIL_PROVIDER=gmail
```

Change `08:00` to your preferred local 24-hour time. Keep VEMU running at that time. You can also request `daily briefing` at any time. To disable automatic briefings, leave `VEMU_DAILY_BRIEFING_TIME` blank.

## 8. Push to GitHub safely

Create an empty repository on https://github.com/new. In Command Prompt, inside this folder:

```bat
git init
git add .
git commit -m "Initial VEMU AI full project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the URL with your repository URL. **Before `git add .`, make sure `.env`, `credentials.json`, `gmail_token.json`, and `outlook_token_cache.json` are not present in Git's staged files.** `.gitignore` excludes them by default. Never publish API keys, OAuth credentials, or tokens.

## Troubleshooting

- **`requirements.txt` not found:** run commands in the folder containing this README and `requirements.txt`.
- **Microphone not working:** enable Windows Settings → Privacy & security → Microphone → desktop app access.
- **PyAudio install error:** use Python 3.11 64-bit, then retry installation.
- **Gmail OAuth error:** verify Gmail API is enabled, the OAuth client is a Desktop app, and your account is allowed on the consent screen.
- **Outlook sign-in error:** check tenant settings and delegated Graph permissions.
- **Daily briefing did not run:** VEMU must be running and the configured time must be valid `HH:MM`.

## Stage map

- **Stage 1:** voice assistant, apps, web/YouTube search, date/time, weather, optional AI advice.
- **Stage 2:** Gmail and Outlook read/send with authentication and send confirmation.
- **Stage 3:** WhatsApp Web message preparation with user review and manual send.
- **Stage 4:** daily briefing and optional scheduled briefing while running.
- **Stage 5:** integration foundation for expanding workflows; this repository does not claim full autonomous control of every app or a finished avatar UI.
