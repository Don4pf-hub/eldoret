# Eldoret Clinical Laboratory — Flask Revamp

Same UI, same workflow, new engine. The original PHP/MySQL/localStorage
prototype has been rebuilt on Flask + SQLAlchemy (SQLite by default, Postgres
via `DATABASE_URL` — same pattern as your other Render/Neon apps).

## What changed under the hood
- **PHP → Flask**: every `.php` page is now a Jinja2 template rendered by a
  Flask route in `app.py`.
- **MySQL (`mysqli`) → SQLAlchemy**: `models.py` defines `User`, `Patient`,
  `LabRequest`, `Sample`, `LabResult`, `ResultValidation`, `ResultApproval`.
- **localStorage → real database**: every workflow step that used to write to
  the browser's `localStorage` (lab requests, sample tracking, result entry,
  validation, approval, dashboard counts, notifications, reports) now writes
  to and reads from the database, so data is shared across users/devices and
  survives a page refresh — it didn't before.
- **Hardcoded JS login (`Lazarus` / `Donrover`) → real session auth**: same
  credentials still work out of the box (seeded on first run), but the check
  now happens server-side with a hashed password (`werkzeug.security`)
  instead of a plaintext string sitting in `script.js`.
- **Raw SQL string concatenation in `save_patient.php` (SQL-injection prone)
  → SQLAlchemy ORM** with parameterized queries.
- Empty stub files (`delete_patient.php`, `logout.php`) are now fully wired:
  delete actually deletes, logout actually clears the session.

## What stayed the same
- Every page, field, button, label, sidebar link, and Bootstrap class.
- The same navigation flow: Dashboard → Patients → Lab Requests → Sample
  Tracking → Result Entry → Validation → Approval → Notifications → Reports.
- Same default login: `Lazarus` / `Donrover`.

## Run it locally
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --break-system-packages   # or just pip install inside the venv
python3 app.py
```
Visit http://localhost:5000 — the SQLite file `eldoret_lab.db` is created
automatically with the seed user on first run.

## Deploy (Render, same as your other apps)
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Env var `SECRET_KEY` — set a real secret in production.
- Optional: point `DATABASE_URL` at a Neon Postgres connection string to swap
  out SQLite, exactly like your other client migrations — no code changes
  needed, `app.py` already rewrites `postgres://` → `postgresql://`.

## Notes / things worth flagging to the client
- Passwords are now hashed — if they want more users, add rows to `User` via
  a shell/`flask shell` script rather than the DB directly.
- The old `add-patient.php` hardcoded `PAT003` as the next patient number;
  the Flask version now computes it from the real patient count, so numbering
  won't collide.
- Delete on the patients page now actually removes the row (previously it
  only worked against a per-browser `localStorage` array).
