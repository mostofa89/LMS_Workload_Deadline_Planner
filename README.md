# LMS Workload & Deadline Planner

FastAPI + PostgreSQL backend for the LMS Workload & Deadline Planner.

## Backend layout

The application code is organized into three layers under `backend/app/`: `models/` contains SQLAlchemy models, `controllers/` contains business logic and its supporting services, and `views/` contains API routes, schemas, and request handling. The application entry point (`main.py`), configuration (`config.py`), and database setup (`database.py`) remain directly under `backend/app/`.

## Quick start

```bash
# 1. Start Postgres and Redis
docker compose up -d db redis

# 2. Create a virtualenv and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Create .env in the repo root (see "Environment variables" below)

# 4. Run migrations (from the repo root)
alembic upgrade head

# 5. Start the API
cd backend && uvicorn app.main:app --reload --port 3030
```

Run the whole stack in Docker instead with `docker compose up --build`. The API listens on `http://localhost:3030`, and its routes are mounted at both `/auth/...` and `/api/v1/auth/...`.

### Environment variables

Put these in `.env` at the repo root. Run commands from the repo root, or the app won't find `.env` and will use the defaults.

| Variable | Example |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/lms_workload_planner` |
| `JWT_SECRET` | a random string of at least 32 bytes |
| `JWT_AUDIENCE` | `lms-workload-planner` |
| `JWT_ISSUER` | `lms-api` |
| `TOKEN_PEPPER` | a random secret. **If you change it, every existing registration key stops working.** |
| `PASSWORD_MIN_LENGTH` | `8` |
| `ACCESS_TOKEN_MINUTES` | `15` |
| `REFRESH_TOKEN_DAYS` | `7` |
| `PUBLIC_APP_URL` | `http://localhost:3000` |
| `COOKIE_SECURE` | `false` (local), `true` (production) |
| `COOKIE_DOMAIN` | leave empty for localhost |

## Roles and registration keys

Students and staff sign up with a **registration key**. Each key belongs to one institution and one role. The key starts with that role's prefix, followed by random characters, for example `STU-XXXX-XXXX-...`.

| Role key (`role_key`) | Key prefix | `account_type` at signup |
| --- | --- | --- |
| `student` | `STU` | `student` |
| `instructor` | `INST` | `staff` |
| `teaching_assistant` | `TA` | `staff` |
| `coordinator` | `CORD` | `staff` |
| `department_head` | `DHOD` | `staff` |
| `advisor` | `ADV` | `staff` |
| `registrar` | `REG` | `staff` |
| `register` | `REG` | `staff` (duplicate of `registrar`, see TODO) |
| `admin` | `ADM` | `staff` |
| `superadmin` | `SADM` | `staff` |
| `support` | `SUP` | `staff` |
| parent / guardian | none | `parent`. Uses a `guardian_code` from a student invite, not a registration key. |

These are defined in `ROLE_KEY_PREFIX` and `SIGNUP_KEY_ROLES` in [backend/app/controllers/formatting.py](backend/app/controllers/formatting.py).

### How keys work

- The database stores only an HMAC hash of each key (`TOKEN_PEPPER` is the secret), so a key **can't be recovered after it's issued**. Save it when it's printed.
- Case, spaces and dashes are ignored when a key is checked. `STU-AB12-...` and `stu ab12...` are the same key.
- A key is rejected with `SIGNUP_REJECTED` if it doesn't exist in **your** database, is expired, is revoked, or has reached `max_uses`.
- Keys only work on the database that issued them. Keys from someone else's database won't work on yours.

### Generating keys for local development

`backend/scripts/seed_keys.py` creates a "Dev Institution" if there isn't one, then issues one key per role (30 days, 50 uses each):

```bash
PYTHONPATH=backend python backend/scripts/seed_keys.py
```

Each run issues a new set of keys, and older keys stay valid. The script is in `.gitignore`, so each developer keeps their own copy.

### Current local dev keys

These were issued on 2026-11-07 against the maintainer's local database and expire on 2026-12-07. **They won't work on any other database.** Run the seed script to get your own.

| Role | Key |
| --- | --- |
| student | `STU-2K27-M7ML-97X7-2-S2-SF9--X2M6` |
| instructor | `INST-X9XS-92L2-6XF2-LL9M-6FLX-2K62` |
| teaching_assistant | `TA-7-79-9-7K-K9FM-XX7--F9-M-2X--` |
| advisor | `ADV-F62--M9---S-7S-796M-FMF6-KFSF` |
| admin | `ADM-X97S--LM7-22KL--KS7-9-6X--FF9` |
| superadmin | `SADM-XK9X-S2-X-696--6--S-L-2L-XFL-` |
| coordinator | `CORD-772S-76KX---97-2K-S-2MS2-M2K-` |
| registrar | `REG-LM-7-26-7-ML2X-2622-69M2-9S--` |
| register | `REG-M6LK-9792-7MXK--M-6-M66F-K27M` |
| department_head | `DHOD--9F--67----S6--M6-S-7F2F-MF22` |
| support | `SUP-2-XX-MLKX--FL---9-2--FL--F26L` |

### Signup examples

`POST /api/v1/auth/signup`

Student:

```json
{
  "account_type": "student",
  "full_name": "Test Student",
  "email": "student@example.com",
  "password": "Str0ng!Passw0rd",
  "registration_key": "STU-...."
}
```

Staff (`role_key` is required and must match the key's role, or you get `ROLE_KEY_MISMATCH`):

```json
{
  "account_type": "staff",
  "role_key": "instructor",
  "full_name": "Test Instructor",
  "email": "instructor@example.com",
  "password": "Str0ng!Passw0rd",
  "registration_key": "INST-...."
}
```

Parent:

```json
{
  "account_type": "parent",
  "full_name": "Test Parent",
  "email": "parent@example.com",
  "password": "Str0ng!Passw0rd",
  "guardian_code": "...."
}
```

### Signup error codes

| Code | Meaning |
| --- | --- |
| `SIGNUP_REJECTED` | The key isn't in this database, or it's expired, revoked or used up |
| `REGISTRATION_KEY_REQUIRED` | No `registration_key` was sent for a student or staff signup |
| `ROLE_KEY_MISMATCH` | `role_key` doesn't match the key's role, or `role_key` is missing for staff |
| `WEAK_PASSWORD` | The password doesn't meet the strength rules |
| `USER_ALREADY_EXISTS` | The email is already registered |
| `INSTITUTION_MISMATCH` | `institution_id` was sent and doesn't match the key's institution |
| `EMAIL_DOMAIN_NOT_ALLOWED` | The student's email isn't on the institution's allowed domains |
| `INVALID_ACCOUNT_TYPE` | `account_type` isn't `student`, `staff` or `parent` |

## TODO: what still needs to be added or fixed

- [ ] **Assign the role at signup.** `signup()` in [backend/app/controllers/controls.py](backend/app/controllers/controls.py) checks the key's role but never creates a `UserRole`, so new users have no role. After the user is created, add `UserRole(user_id, role_id=get_role(...).id, scope_type=key_row.scope_type, scope_id=key_row.scope_id)`.
- [ ] **Add an endpoint for issuing keys.** Nothing in the API calls `issue_registration_key` yet. Add an admin-only route such as `POST /api/v1/admin/registration-keys`, plus routes to list and revoke keys.
- [ ] **Fix `KEY_ALPHABET`.** `"LMS-F26-9XK72"` has only 11 distinct characters and includes `-`, which makes keys weak and hard to read. Use something like `"ABCDEFGHJKLMNPQRSTUVWXYZ23456789"`.
- [ ] **Remove the `register` role,** which duplicates `registrar` and shares the `REG` prefix.
- [ ] **Decide whether `admin` and `superadmin` can self-sign up.** Right now anyone holding one of those keys can create an admin account.
- [ ] **Stop logging raw codes.** The signup audit record stores the full `registration_key` and `guardian_code` in `meta`. Store only a hint instead.
- [ ] **Staff `role_key`:** either derive it from `key_row.role_key` or keep it required and document it in the frontend.
- [ ] **Import `Any`** from `typing` in [backend/app/controllers/formatting.py](backend/app/controllers/formatting.py).
- [ ] **Implement throttling.** `check_throttle` and `register_failure` are empty stubs, so codes can be guessed without limit.
- [ ] **Store institution settings.** `get_settings(db, inst_id, key)` always returns hard-coded defaults and ignores `Institution.settings`.
- [ ] **Add tests** for signup, key issuing and login.
