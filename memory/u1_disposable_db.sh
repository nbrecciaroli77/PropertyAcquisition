#!/usr/bin/env bash
# Rebuilds the U1 throwaway PostgreSQL 17 database (127.0.0.1:5433/pa_u1_disposable) from scratch.
# Never targets Supabase: the URL comes from the supervisor backend entry and must be 127.0.0.1.
# Usage: bash /app/memory/u1_disposable_db.sh            (install if missing, wipe, migrate, seed)
set -euo pipefail
PRE_U1_COMMIT=32bf41d   # last commit before U1 code (live revision c8d5e2f9a4b1)
B=/usr/lib/postgresql/17/bin
DATA=/var/lib/u1pg/data
VENV=/root/.venv/bin

export DATABASE_URL=$(grep -o 'DATABASE_URL="[^"]*"' /etc/supervisor/conf.d/supervisord.conf | cut -d'"' -f2)
HOST=$(python3 -c "import os;from urllib.parse import urlparse;print(urlparse(os.environ['DATABASE_URL']).hostname)")
[ "$HOST" = "127.0.0.1" ] || { echo "REFUSING: DATABASE_URL host is $HOST"; exit 9; }
PW=$(python3 -c "import os;from urllib.parse import urlparse,unquote;print(unquote(urlparse(os.environ['DATABASE_URL']).password))")
export APP_ENV=development PGPASSWORD="$PW"

if [ ! -x "$B/postgres" ]; then
  sudo install -d /usr/share/postgresql-common/pgdg
  sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc
  echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
  sudo apt-get update -q >/dev/null && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q postgresql-17 >/dev/null
fi
if [ ! -f "$DATA/PG_VERSION" ]; then
  sudo mkdir -p /var/lib/u1pg && sudo chown postgres:postgres /var/lib/u1pg
  F=$(mktemp); echo "$PW" > "$F"; chmod 644 "$F"
  sudo -u postgres $B/initdb -D $DATA -A scram-sha-256 --pwfile="$F" -U postgres >/dev/null; rm -f "$F"
  sudo -u postgres openssl req -new -x509 -days 365 -nodes -subj "/CN=u1-disposable" -keyout $DATA/server.key -out $DATA/server.crt >/dev/null 2>&1
  sudo chmod 600 $DATA/server.key
  printf "listen_addresses='127.0.0.1'\nport=5433\nunix_socket_directories='/tmp'\nssl=on\n" | sudo -u postgres tee -a $DATA/postgresql.conf >/dev/null
fi
# Supervisor entry: runs as root and exits cleanly when PostgreSQL is absent, so a pod restart that wipes
# the packages can never stop supervisord (and with it the whole preview) from starting.
sudo tee /etc/supervisor/conf.d/u1_disposable_pg.conf >/dev/null <<'CONF'
[program:u1_disposable_pg]
command=/bin/sh -c 'id postgres >/dev/null 2>&1 && [ -x /usr/lib/postgresql/17/bin/postgres ] && [ -f /var/lib/u1pg/data/PG_VERSION ] || { echo "u1 disposable PostgreSQL not installed; run bash /app/memory/u1_disposable_db.sh"; exit 3; }; exec su postgres -s /bin/sh -c "exec /usr/lib/postgresql/17/bin/postgres -D /var/lib/u1pg/data"'
autostart=true
autorestart=unexpected
exitcodes=0
startretries=1
priority=10
stdout_logfile=/var/log/supervisor/u1_disposable_pg.out.log
stderr_logfile=/var/log/supervisor/u1_disposable_pg.err.log
stopsignal=INT
stopasgroup=true
CONF
sudo supervisorctl reread >/dev/null; sudo supervisorctl update >/dev/null
sudo supervisorctl restart u1_disposable_pg >/dev/null; sleep 3
PSQL="$B/psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -q"
$PSQL -c "select 1 from pg_roles where rolname='u1'" -At | grep -q 1 || $PSQL -c "create role u1 login password '$PW'"
$PSQL -c "select pg_terminate_backend(pid) from pg_stat_activity where datname='pa_u1_disposable'" >/dev/null
$PSQL -c "drop database if exists pa_u1_disposable" -c "create database pa_u1_disposable owner u1"

# 1) Pre-U1 schema + data with pre-U1 code (historical reports carry pre-U1 workspace keys).
rm -rf /tmp/pre_u1; git -C /app worktree prune; git -C /app worktree add --detach /tmp/pre_u1 $PRE_U1_COMMIT >/dev/null 2>&1
cp /app/backend/.env /tmp/pre_u1/backend/.env
cd /tmp/pre_u1/backend
$VENV/alembic upgrade head 2>&1 | grep -E "Running|Error" | tail -1
$VENV/python -m scripts.seed
$VENV/python - <<'PY'
import asyncio
from dotenv import load_dotenv
load_dotenv(".env")
from sqlalchemy import select
from app.db.base import dispose_engine, get_sessionmaker
from app.db.models import Journey, User, Workspace
from app.services.reports import generate_report
async def main():
    async with get_sessionmaker()() as db:
        user = (await db.execute(select(User).where(User.email == "owner@propertyacquisition-demo.com"))).scalar_one()
        ws = (await db.execute(select(Workspace).where(Workspace.owner_user_id == user.id))).scalar_one()
        house = (await db.execute(select(Journey).where(Journey.workspace_id == ws.id))).scalars().first()
        for rt in ("daily", "weekly", "monthly"):
            run = await generate_report(db, journey=house, report_type=rt, release_kind="preview", requested_by_user_id=user.id)
            print(f"pre-U1 historical {rt} run {run.id}")
        await db.commit()
    await dispose_engine()
asyncio.run(main())
PY

# 2) U1 migration + U1 seed (adds the synthetic land campaign).
cd /app/backend
$VENV/alembic upgrade head 2>&1 | grep -E "Running|Error" | tail -1
$VENV/alembic current 2>/dev/null | tail -1
$VENV/python -m scripts.seed
git -C /app worktree remove --force /tmp/pre_u1
