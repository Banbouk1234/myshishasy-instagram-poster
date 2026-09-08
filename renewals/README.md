# 🔔 Renewals — a Dubai renewal reminder system

A small web app + automatic email reminders for everything that expires in Dubai:
cars (Mulkiya, insurance, licence), your company (trade licence, establishment card,
Ejari, VAT), and personal documents (Emirates ID, visa, passport, health insurance).

It emails you **10 days before**, **1 day before**, and **on the expiry day** — and
keeps nagging every day if something is overdue — with **"✅ I renewed it"** and
**"⏰ Not yet"** buttons in every email.

Right now it's set up for **Mohanad** and **Sara 🍒**. You can add more people any time.

---

## What's in here

| File | What it is |
|------|-----------|
| `index.html` | The web app (open it on your phone). Add/edit renewals, mark things renewed. |
| `reminders.py` | The robot that runs once a day and sends the emails. |
| `../.github/workflows/reminders.yml` | The daily schedule (08:00 Dubai time) that runs the robot — free, on GitHub. |
| `data/vault.enc` | Your data, **encrypted**. Created automatically when you first "Save to cloud". |
| `data/reminders_state.json` | Remembers which emails were already sent (so you don't get duplicates). |

---

## 1) Try it right now (no setup)

Just open `renewals/index.html` in a browser (or use the live preview link Claude gave you).
Everything you add is saved **on that device**. Great for trying it out — but the
**email reminders only start once you do step 3** (the app needs to be online so the
daily robot can read it).

---

## 2) Put it online (≈5 minutes, free)

We'll use **GitHub Pages**.

1. Go to the repo on GitHub → **Settings** → **Pages**.
2. Under "Build and deployment", set **Source = Deploy from a branch**,
   **Branch = `main`**, **Folder = `/ (root)`**, then **Save**.
3. After a minute your app is live at:
   `https://banbouk1234.github.io/myshishasy-instagram-poster/renewals/`
4. Open that link on your phone and **Add to Home Screen** so it feels like an app.

> ⚠️ **Privacy note:** this repo is **public**. That's OK here because your renewal
> **data is encrypted** before it's ever saved (step 3) — nobody can read your dates
> without your passphrase, even if they find the repo. If you'd rather make the repo
> **Private**, note that free GitHub Pages needs a public repo; a private repo needs a
> paid GitHub plan for Pages, or you can host `index.html` for free on Netlify or
> Cloudflare Pages instead. For most people: keep it public and rely on the encryption.

---

## 3) Turn on the automatic email reminders

Three quick things: an **access key**, a **passphrase**, and a **Gmail app password**.

### a. Create an access key (so the app can save your data)
1. GitHub → your avatar → **Settings** → **Developer settings** →
   **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Repository access → **Only select repositories** → pick this repo.
3. Permissions → **Repository permissions** → **Contents** → **Read and write**.
4. Generate, and **copy the token** (starts with `github_pat_...`).

### b. Set your passphrase (this encrypts your data)
Pick any secret phrase you and Sara will share, e.g. `shisha-cherry-2026`.

Now open the app → **⚙️ Settings** and fill in:
- **GitHub repo:** `Banbouk1234/myshishasy-instagram-poster`
- **Access token:** the `github_pat_...` from step (a)
- **Encryption passphrase:** your secret phrase
- Fill in each person's **email** (Mohanad is already there — add Sara's).

Tap **⬆ Save to cloud**. You should see "Saved to cloud ✓". That creates `data/vault.enc`.

### c. Add the secrets GitHub's robot needs
GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
Add these **three secrets**:

| Name | Value |
|------|-------|
| `VAULT_PASSPHRASE` | the **same** passphrase from step (b) |
| `GMAIL_USER` | the Gmail address that will send the reminders |
| `GMAIL_APP_PASSWORD` | a Gmail **app password** (see below) |

Then on the **Variables** tab (same page) → **New repository variable**:

| Name | Value |
|------|-------|
| `APP_URL` | your app link, e.g. `https://banbouk1234.github.io/myshishasy-instagram-poster/renewals` |

> **Gmail app password:** at [myaccount.google.com/security](https://myaccount.google.com/security)
> turn on **2-Step Verification**, then search "**App passwords**", create one called
> "Renewals", and copy the 16-character code. That's your `GMAIL_APP_PASSWORD`.
> (Your normal Gmail password won't work — Google requires an app password.)

### d. (Optional) Add WhatsApp reminders too
Every reminder can also arrive on **WhatsApp**, using the free **CallMeBot** service —
no Twilio or business account needed.

For **each person** who wants WhatsApp:
1. From that person's phone, send this exact message on WhatsApp to **+34 644 84 71 89**:
   `I allow callmebot to send me messages`
2. CallMeBot replies with a personal **API key** (a number).
3. In the app → **⚙️ Settings**, fill that person's **WhatsApp number** (e.g. `+9715…`)
   and **WhatsApp key**, then **⬆ Save to cloud**.

That's it — the daily robot will now send email **and** WhatsApp. (Nothing extra to add in
GitHub secrets; the WhatsApp key travels inside your encrypted vault.)

### e. Test it
GitHub repo → **Actions** → **Renewal Reminders** → **Run workflow**.
Tick **dry run** first to see it list who *would* get emailed (check the logs).
Then run it again **without** dry run to send real emails. After that it runs by
itself every morning at **08:00 Dubai time**.

Done 🎉

---

## How the "Did you renew?" buttons work

Every reminder email has two buttons:
- **✅ I renewed it** → opens the app and rolls the date forward to the next renewal
  automatically (e.g. +1 year for Mulkiya), so you're set for next time.
- **⏰ Not yet** → just closes; you'll get another nudge tomorrow.

---

## Ideas we can add next (tell me which you want)

- ✅ **WhatsApp reminders** in addition to email — **done** (see step 3d).
- 🔐 **Google login + public sign-up** — the "real website" version so anyone can
  register (this is *Phase 2*; the current version is built so we can add it cleanly).
- 💰 **Cost tracking** — estimated renewal cost per item, and a yearly total to budget.
- 📎 **Attach the document photo/PDF** to each item (needs a bit of storage).
- 🗓️ **Add to Google/Apple Calendar** (.ics export) for each renewal.
- 👨‍👩‍👧 **Family/company view** — group items by person or by company.
- 🧾 **Ready-made checklists** — "to renew your Mulkiya you need: …" for each Dubai item.
- ⛽ **Salik / fuel / fines** low-balance style nudges.

---

## Notes / troubleshooting

- **No emails?** Run the workflow with **dry run** and read the Actions log — it says
  exactly who it's emailing or why it skipped (usually a missing email address, or the
  passphrase in the app not matching the `VAULT_PASSPHRASE` secret).
- **"wrong passphrase?"** in the app → the passphrase you typed doesn't match what the
  data was encrypted with. Use the same phrase everywhere.
- Your data never leaves your phone un-encrypted. The token and passphrase are stored
  only in your own browser.
