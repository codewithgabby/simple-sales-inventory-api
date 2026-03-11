from fastapi import APIRouter
from app.notifications.daily_job import run_daily_notifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/test")
def test_notifications():
    run_daily_notifications()
    return {"message": "Notification job executed"}