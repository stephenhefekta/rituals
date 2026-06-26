# Focus

A small macOS app for weekly and quarterly rituals:

- **Sunday** — set your top three priorities for the week ahead, and check them off as you go.
- **Friday** — capture one win, something that went well.

Everything is archived automatically, grouped by year and month, so your history stays browsable instead of turning into an endless list. You can edit the current week's priorities or win inline at any time.

Everything is stored in **Supabase** (Postgres), so your priorities and wins sync across every computer running the app.

## How it's built

- **Frontend + data** — a single-page HTML/JS UI (Tailwind) that talks **directly to Supabase** via [`@supabase/supabase-js`](https://github.com/supabase/supabase-js), behind a Supabase Auth email/password login. Row-Level Security locks every row to your account. Quarterly targets, weekly priorities, and wins each live in their own table (the list items are a JSONB column).
- **Desktop shell** — `main.py` serves `static/` on a fixed local port and opens it in a native macOS WKWebView window via [pywebview](https://pywebview.flowrl.com/); `app.py` is just a thin static-file server. Packaged into a standalone `.app` with PyInstaller (`Focus.spec`).
- **Phone** — the same `static/` folder, deployed as an installable PWA on Cloudflare Pages (see [Phone app](#phone-app-installable-pwa) below).
- **Icon** — `icon.icns` (desktop) and `static/icons/` (web/PWA).

## Cloud setup (one time)

1. **Tables** — in your Supabase project, open **SQL Editor** and run [`schema.sql`](schema.sql) to create the `weeks`, `wins`, and `quarters` tables.
2. **Login** — Authentication → **Users** → add your account (Auto Confirm). Turn off "Allow new users to sign up" so it stays single-user.
3. **Access policies** — add Row-Level Security policies allowing only your account to read/write the three tables, e.g. `for all to authenticated using (auth.uid() = '<your-user-id>')`.
4. **Keys** — the app uses your project's **publishable** key, set in [`static/index.html`](static/index.html) next to the project URL. It's public by design — RLS guards the data, and the `service_role` key is never used by the app.

The app itself needs no server-side config or `.env` — install the desktop app (or open the PWA) and sign in. (The optional [reminders](#optional-weekly--quarterly-reminders) are the one exception: they read a `.env`.)

## Phone app (installable PWA)

The phone version is a static **PWA**: the same UI in `static/`, served from a CDN
and talking **directly to Supabase** behind a Supabase Auth login (Row-Level
Security locks the data to your account). There's no server in the path, so it
loads instantly — no cold start.

It's deployed to **Cloudflare Pages**:

```bash
# one-time: create the project
npx wrangler pages project create focus --production-branch main
# deploy (re-run after any change under static/)
npx wrangler pages deploy static --project-name focus --branch main
```

Open the resulting `*.pages.dev` URL in Chrome, sign in, then **⋮ → Install app**
(or **Share → Add to Home Screen** on iOS) for a home-screen icon.

> The Supabase **publishable** key embedded in `static/index.html` is public by
> design — RLS is what guards the data. The `service_role` key is never shipped to
> the client.

## Run in dev

```bash
pip install -r requirements.txt
python3 -m uvicorn app:app --reload --port 8011   # then open http://127.0.0.1:8011
# or run the native window:
python3 main.py
```

## Build the .app

```bash
./build.sh        # produces dist/Focus.app
```

## Optional: weekly & quarterly reminders

A `launchd` agent can nudge you to plan — Sunday (the week ahead), Friday (capture a win), and a month before / at the start of each quarter (set your 3 targets) — but only when that period's ritual isn't done yet. Notifications are delivered by a small signed agent, **Focus Notifier.app**, which posts via the modern `UserNotifications` framework — so the banner is branded "Focus", renders its text on current macOS, and opens the app when clicked. (terminal-notifier 2.0.0 was dropped: its deprecated `NSUserNotification` path delivers empty, textless banners on macOS 11+.)

```bash
./notifier/build-notifier.sh   # build + sign + install the notifier (once)
./install-reminders.sh         # schedule the reminders
./uninstall-reminders.sh       # remove them
```

The first reminder asks once to allow notifications for "Focus" — click **Allow**.

The "only when not done yet" check reads `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from `.env` (or `~/.rituals/.env`) — see [`.env.example`](.env.example). Without them the reminders still fire, just without that suppression.
