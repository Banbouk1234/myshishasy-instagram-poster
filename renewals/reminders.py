#!/usr/bin/env python3
"""
Renewals reminder engine.

Runs once a day from GitHub Actions. It:
  1. reads the encrypted vault (renewals/data/vault.enc),
  2. decrypts it with VAULT_PASSPHRASE,
  3. finds items expiring in 10 / 1 / 0 days (configurable per item),
  4. keeps nagging daily once an item is overdue,
  5. emails the item's owner via Gmail SMTP,
  6. records what was sent in reminders_state.json (so nothing sends twice).

Secrets / env used:
  VAULT_PASSPHRASE   - same passphrase set in the web app (required to decrypt)
  GMAIL_USER         - the Gmail address that sends the mail
  GMAIL_APP_PASSWORD - a Gmail "app password" (not your normal password)
  APP_URL            - (optional) URL where the web app is hosted, for the buttons
  DRY_RUN            - (optional) "1" = print emails instead of sending
"""

import os, sys, json, base64, smtplib, ssl, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---- config -------------------------------------------------------------
HERE          = Path(__file__).parent
VAULT_FILE    = HERE / "data" / "vault.enc"
STATE_FILE    = HERE / "data" / "reminders_state.json"
DEFAULT_DAYS  = [10, 1, 0]        # remind 10 days before, 1 day before, same day
OVERDUE_MAX   = 30                # keep nagging up to 30 days past expiry
DUBAI_TZ      = timezone(timedelta(hours=4))   # Asia/Dubai (no DST)

PASSPHRASE = os.environ.get("VAULT_PASSPHRASE", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")
APP_URL    = (os.environ.get("APP_URL")
              or "https://banbouk1234.github.io/myshishasy-instagram-poster/renewals").rstrip("/")
DRY_RUN    = os.environ.get("DRY_RUN", "") == "1"


def log(msg):
    print(f"[{datetime.now(DUBAI_TZ):%Y-%m-%d %H:%M} GST] {msg}", flush=True)


# ---- crypto (must match the web app's format) ---------------------------
def decrypt_vault(b64str, passphrase):
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    blob = base64.b64decode(b64str.strip())
    salt, iv, ct = blob[:16], blob[16:28], blob[28:]
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
    key = kdf.derive(passphrase.encode("utf-8"))
    pt = AESGCM(key).decrypt(iv, ct, None)
    return json.loads(pt.decode("utf-8"))


# ---- state --------------------------------------------------------------
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"sent": {}, "lastRun": ""}


def save_state(state):
    # prune very old records to keep the file small
    cutoff = (date.today() - timedelta(days=400)).isoformat()
    state["sent"] = {k: v for k, v in state["sent"].items() if v[:10] >= cutoff}
    state["lastRun"] = datetime.now(DUBAI_TZ).isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---- helpers ------------------------------------------------------------
def days_until(expiry_iso, today):
    try:
        d = date.fromisoformat(expiry_iso)
    except Exception:
        return None
    return (d - today).days


def fmt(expiry_iso):
    try:
        return date.fromisoformat(expiry_iso).strftime("%-d %b %Y")
    except Exception:
        return expiry_iso


def phase_for(days, reminder_days):
    """Return a stable phase label if a reminder is due today, else None."""
    if days is None:
        return None
    if days >= 0 and days in reminder_days:
        return f"D{days}"
    if days < 0 and abs(days) <= OVERDUE_MAX:
        # overdue: one nag per day
        return f"OD{date.today().isoformat()}"
    return None


def subject_for(item, days):
    name = item["title"]
    if days is None:
        return f"Renewal reminder: {name}"
    if days > 1:
        return f"⏳ {name} expires in {days} days ({fmt(item['expiry'])})"
    if days == 1:
        return f"⚠️ {name} expires TOMORROW ({fmt(item['expiry'])})"
    if days == 0:
        return f"🚨 {name} expires TODAY ({fmt(item['expiry'])})"
    return f"❗ {name} EXPIRED {abs(days)} day(s) ago — did you renew?"


def html_body(person, item, days):
    when = ("in <b>%d days</b>" % days) if days and days > 1 else (
        "<b>tomorrow</b>" if days == 1 else (
        "<b>today</b>" if days == 0 else
        "<b>%d day(s) ago</b>" % abs(days)))
    banner = "#dc2626" if (days is not None and days <= 1) else "#0f766e"
    renew_link  = f"{APP_URL}/#renew={item['id']}"   if APP_URL else "#"
    snooze_link = f"{APP_URL}/#snooze={item['id']}"  if APP_URL else "#"
    notes = f"""<tr><td style="padding:6px 0;color:#475569;font-size:13px">
                📝 {item.get('notes','')}</td></tr>""" if item.get("notes") else ""
    buttons = ""
    if APP_URL:
        buttons = f"""
        <tr><td style="padding-top:18px">
          <a href="{renew_link}" style="background:#15803d;color:#fff;text-decoration:none;
             padding:12px 20px;border-radius:10px;font-weight:700;display:inline-block;margin-right:8px">
             ✅ I renewed it</a>
          <a href="{snooze_link}" style="background:#f1f5f9;color:#0f172a;text-decoration:none;
             padding:12px 20px;border-radius:10px;font-weight:700;display:inline-block">
             ⏰ Not yet</a>
        </td></tr>"""
    return f"""\
<!doctype html><html><body style="margin:0;background:#f6f7f9;padding:22px;
   font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#0f172a">
 <table role="presentation" width="100%" style="max-width:520px;margin:0 auto;background:#fff;
    border-radius:16px;overflow:hidden;box-shadow:0 4px 18px rgba(16,24,40,.08)">
  <tr><td style="background:{banner};color:#fff;padding:18px 22px;font-size:18px;font-weight:700">
      🔔 Renewal reminder</td></tr>
  <tr><td style="padding:22px">
    <table role="presentation" width="100%">
      <tr><td style="font-size:16px;padding-bottom:4px">Hi {person.get('name','there')},</td></tr>
      <tr><td style="font-size:16px;padding:6px 0">
          Your <b>{item['title']}</b> expires {when}.</td></tr>
      <tr><td style="color:#475569;font-size:14px;padding:2px 0">
          📅 Expiry date: <b>{fmt(item['expiry'])}</b></td></tr>
      {notes}
      {buttons}
      <tr><td style="padding-top:20px;color:#94a3b8;font-size:12px;border-top:1px solid #eef1f4">
          You're getting this because it's on your Renewals list.
          {"Open the app to update it." if not APP_URL else ""}</td></tr>
    </table>
  </td></tr>
 </table>
</body></html>"""


def whatsapp_text(person, item, days):
    if days is None:      when = "soon"
    elif days > 1:        when = f"in {days} days"
    elif days == 1:       when = "TOMORROW"
    elif days == 0:       when = "TODAY"
    else:                 when = f"{abs(days)} day(s) AGO"
    lines = [f"🔔 Renewal reminder for {person.get('name','you')}",
             f"*{item['title']}* expires {when} ({fmt(item['expiry'])})."]
    if item.get("notes"):
        lines.append(f"📝 {item['notes']}")
    if APP_URL:
        lines.append(f"Did you renew? {APP_URL}/#renew={item['id']}")
    return "\n".join(lines)


def send_whatsapp(phone, key, text):
    """Send a WhatsApp message via CallMeBot (free personal API)."""
    if DRY_RUN:
        log(f"   (dry-run) would WhatsApp {phone}")
        return True
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
        {"phone": phone, "text": text, "apikey": key})
    with urllib.request.urlopen(url, timeout=30) as r:
        r.read()
    return True


def send_email(to_addr, subject, html):
    if DRY_RUN or not (GMAIL_USER and GMAIL_PASS):
        log(f"   (dry-run) would email {to_addr}: {subject}")
        return True
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Renewals <{GMAIL_USER}>"
    msg["To"] = to_addr
    msg.attach(MIMEText("Open the Renewals app to see this reminder.", "plain"))
    msg.attach(MIMEText(html, "html"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls(context=ctx)
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, [to_addr], msg.as_string())
    return True


# ---- main ---------------------------------------------------------------
def main():
    log("=== Renewals reminder run ===")

    if not VAULT_FILE.exists():
        log("No vault.enc yet — nothing to check. (Set up cloud sync in the app first.)")
        return 0
    if not PASSPHRASE:
        log("ERROR: VAULT_PASSPHRASE is not set.")
        return 1

    try:
        vault = decrypt_vault(VAULT_FILE.read_text(), PASSPHRASE)
    except Exception as e:
        log(f"ERROR: could not decrypt vault (wrong passphrase?): {e}")
        return 1

    people = {p["id"]: p for p in vault.get("people", [])}
    items = [i for i in vault.get("items", []) if i.get("status") != "archived"]
    today = datetime.now(DUBAI_TZ).date()
    state = load_state()
    sent_now = 0

    log(f"Today (Dubai): {today.isoformat()} — {len(items)} active item(s)")

    for item in items:
        days = days_until(item.get("expiry", ""), today)
        rdays = item.get("reminderDays") or DEFAULT_DAYS
        phase = phase_for(days, rdays)
        if not phase:
            continue

        key = f"{item['id']}|{item.get('expiry')}|{phase}"
        if key in state["sent"]:
            continue

        owner = people.get(item.get("ownerId"), {})
        to_addr = (owner.get("email") or "").strip()
        phone   = (owner.get("phone") or "").strip()
        wa_key  = (owner.get("waKey") or "").strip()
        subject = subject_for(item, days)

        if not to_addr and not (phone and wa_key):
            log(f" - SKIP '{item['title']}' — owner '{owner.get('name','?')}' has no email or WhatsApp set")
            continue

        delivered = []
        if to_addr:
            try:
                send_email(to_addr, subject, html_body(owner, item, days))
                delivered.append(f"email:{to_addr}")
            except Exception as e:
                log(f"   email failed for '{item['title']}' -> {to_addr}: {e}")
        if phone and wa_key:
            try:
                send_whatsapp(phone, wa_key, whatsapp_text(owner, item, days))
                delivered.append(f"whatsapp:{phone}")
            except Exception as e:
                log(f"   whatsapp failed for '{item['title']}' -> {phone}: {e}")

        if delivered:
            sent_now += 1
            if DRY_RUN:
                # a test run must never consume a real reminder
                log(f" - WOULD SEND '{item['title']}' via {', '.join(delivered)} ({subject})")
            else:
                state["sent"][key] = datetime.now(DUBAI_TZ).isoformat()
                log(f" - SENT '{item['title']}' via {', '.join(delivered)} ({subject})")
        else:
            log(f" - FAILED '{item['title']}' — no channel delivered")

    save_state(state)
    log(f"Done. {sent_now} reminder(s) sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
