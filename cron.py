# cron.py
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from django.db import connections, close_old_connections
from django.db.utils import OperationalError, InterfaceError

# ---- Django setup ----
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "managerPanel.settings")
import django  # noqa: E402
django.setup()

from django.core.management import call_command  # noqa: E402
from apscheduler.schedulers.blocking import BlockingScheduler  # noqa: E402
from apscheduler.triggers.cron import CronTrigger  # noqa: E402

# -------------------- Logging --------------------
LOG_DIR = os.getenv("LOG_DIR", "/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "cron.log")

logger = logging.getLogger("cron")
logger.setLevel(logging.INFO)

# Console output
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))

# Rotating file (5MB × 5)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))

logger.addHandler(console)
logger.addHandler(file_handler)

# -------------------- Command Runner --------------------
def run_command(name: str):
    logger.info(f"→ Running management command: {name}")
    start = datetime.now()
    try:
        # make sure we’re not holding an idle/stale connection
        close_old_connections()
        call_command(name)
    except (OperationalError, InterfaceError) as e:
        logger.warning("DB connection issue on %s: %s — retrying once...", name, e)
        # hard-close every alias, then try again
        for alias in connections:
            try:
                connections[alias].close()
            except Exception:
                pass
        close_old_connections()
        call_command(name)
    except SystemExit as e:
        code = getattr(e, "code", 1)
        if code != 0:
            logger.error(f"Command {name} exited with code {code}")
            raise
    except Exception:
        logger.exception(f"Command {name} failed")
        raise
    else:
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"✓ Finished {name} in {duration:.1f}s")

# -------------------- Scheduler --------------------
if __name__ == "__main__":
    tz = os.getenv("TZ", "Asia/Tehran")
    scheduler = BlockingScheduler(
        timezone=tz,
        job_defaults={"max_instances": 1, "coalesce": True, "misfire_grace_time": 3600},
    )
    
    scheduler.add_job(
        lambda: run_command("check-expired-devices"),
        CronTrigger(hour=2, minute=0),  # every minute at second 0
        id="check-expired-devices-every-6h",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: run_command("send-expiry-sms"),
        CronTrigger(hour=18, minute=0),  # every minute at second 0
        id="send-expiry-sms-daily",
        replace_existing=True,
    )
    
    logger.info(f"Scheduler started (TZ={tz})")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
