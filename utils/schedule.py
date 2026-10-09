from datetime import datetime
from zoneinfo import ZoneInfo

# Укажите свой часовой пояс. Для Москвы — Europe/Moscow,
# для Екатеринбурга — Asia/Yekaterinburg и т.д.
TIMEZONE = ZoneInfo("Europe/Moscow")

WORK_START_HOUR = 9
WORK_END_HOUR = 18
WORK_DAYS = {0, 1, 2, 3, 4}  # Понедельник=0 ... Пятница=4


def is_working_time(now: datetime | None = None) -> bool:
    """True, если оператор сейчас на связи."""
    if now is None:
        now = datetime.now(TIMEZONE)
    if now.weekday() not in WORK_DAYS:
        return False
    return WORK_START_HOUR <= now.hour < WORK_END_HOUR


def working_status_text() -> str:
    """Текст статуса для абонента (используется в FAQ)."""
    if is_working_time():
        return (
            "🟢 Оператор на связи. Обычно отвечаем в течение 15 минут.\n"
            "⏰ График работы: будние дни с 9:00 до 18:00."
        )
    return (
        "🔴 Сейчас нерабочее время.\n"
        "Оставьте вопрос — ответим в ближайший рабочий день.\n"
        "⏰ График работы: будние дни с 9:00 до 18:00."
    )