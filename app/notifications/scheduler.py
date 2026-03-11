from apscheduler.schedulers.background import BackgroundScheduler
from app.notifications.daily_job import run_daily_notifications


scheduler = BackgroundScheduler()


def start_scheduler():

    scheduler.add_job(
        run_daily_notifications,
        trigger="cron",
        hour=21,
        minute=0,
    )

    scheduler.start()