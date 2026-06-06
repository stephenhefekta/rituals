# Rituals

A small macOS app for two weekly rituals:

- **Sunday** — set your top three priorities for the week ahead, and check them off as you go.
- **Friday** — capture one win, something that went well.

Everything is archived automatically, grouped by year and month, so your history stays browsable instead of turning into an endless list. You can edit the current week's priorities or win inline at any time.

Everything is stored in **Supabase** (Postgres), so your priorities and wins sync across every computer running the app.

## How it's built

- **Backend** — FastAPI + uvicorn. All week/win persistence goes through `store.py`, which talks to Supabase (one row per ISO week; priorities live in a JSONB column).
- **Frontend** — a single-page HTML/JS UI (Tailwind) with the week card, progress ring, and collapsible year/month archive.
- **Desktop shell** — `main.py` starts the server on a random local port in a background thread and opens it in a native macOS WKWebView window via [pywebview](https://pywebview.flowrl.com/). Packaged into a standalone `.app` with PyInstaller.
- **Icon** — generated from `assets/gen_icon.py` (Pillow).

## Cloud setup (one time)

1. In your Supabase project, open **SQL Editor**, paste the contents of [`schema.sql`](schema.sql), and run it to create the `weeks` and `wins` tables.
2. Copy `.env.example` to `.env` and fill in `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (Dashboard → Project Settings → API). `.env` is git-ignored.
3. (First machine only, if you had local data) push your existing `~/.rituals/data.json` to the cloud:
   ```bash
   python3 migrate.py
   ```

On any additional computer, just install the deps and add the same `.env` — no migration needed; it reads the shared cloud data.

## Use on a second computer (installed .app)

The credentials are **not** bundled inside `Rituals.app` — it reads them from
`~/.rituals/.env`. So copying just the app over gives you an empty screen (no
history) until you add that file. You do **not** need the project folder.

1. Copy `Rituals.app` to the other Mac (into `/Applications`).
2. Create the credentials file (Terminal):
   ```bash
   mkdir -p ~/.rituals && cat > ~/.rituals/.env <<'EOF'
   SUPABASE_URL=https://YOUR-PROJECT-ref.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   EOF
   chmod 600 ~/.rituals/.env
   ```
3. Quit and relaunch Rituals — your history appears, synced from the cloud.

> An empty screen means the app can't reach Supabase: missing/typo'd
> `~/.rituals/.env`, no internet (the app requires a connection), or a `SUPABASE_URL`
> that still has a trailing `/rest/v1/` (it shouldn't).

`store.py` reads credentials from both the project-folder `.env` (dev runs) and
`~/.rituals/.env` (the installed app).

## Run in dev

```bash
pip install -r requirements.txt
python3 -m uvicorn app:app --reload --port 8011   # then open http://127.0.0.1:8011
# or run the native window:
python3 main.py
```

## Build the .app

```bash
./build.sh        # produces dist/Rituals.app
```

## Optional: Sunday & Friday reminders

A `launchd` agent can nudge you on Sunday and Friday mornings (only if that week's ritual isn't done yet). Notifications are delivered via [`terminal-notifier`](https://github.com/julienXX/terminal-notifier) (`brew install terminal-notifier`).

```bash
./install-reminders.sh    # schedule them
./uninstall-reminders.sh  # remove them
```
