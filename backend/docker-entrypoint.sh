#!/bin/sh
set -e

echo "Aguardando banco..."
python - <<'PY'
import os, time
import MySQLdb

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "3306") or "3306")
user = os.environ.get("DB_USER", "rastro")
password = os.environ.get("DB_PASSWORD", "")
name = os.environ.get("DB_NAME", "rastroglobus")

for i in range(60):
    try:
        conn = MySQLdb.connect(
            host=host, port=port, user=user, passwd=password, db=name
        )
        conn.close()
        print("Banco OK")
        break
    except Exception as e:
        print(f"Tentativa {i+1}/60: {e}")
        time.sleep(2)
else:
    raise SystemExit("Banco indisponível")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn rastroglobus.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
