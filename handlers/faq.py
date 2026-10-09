import logging

from maxapi import Router, F
from maxapi.types import MessageCallback

from keyboards import main_menu, back_to_menu, cancel_operator
from config import OPERATOR_WORK_HOURS
from utils.schedule import working_status_text

router = Router()
logger = logging.getLogger(__name__)


FAQ_ANSWERS = {
    "faq_heating": (
        "🔥 Отопление\n\n"
        "Отопительный сезон начинается, когда среднесуточная температура "
        "держится ниже +8 °C в течение 5 дней.\n\n"
        "Если у вас нет отопления или батареи холодные:\n"
        "1. Проверьте, не отключён ли стояк в подвале.\n"
        "2. Убедитесь, что краны на радиаторах открыты.\n"
        "3. Если проблема не решена — напишите свой вопрос в чате."
    ),
    "faq_hot_water": (
        "💧 Горячая вода\n\n"
        "Горячее водоснабжение подаётся круглосуточно. "
        "Плановые отключения проводятся летом (не более 14 дней).\n\n"
        "О датах отключений мы уведомляем заранее через объявления "
        "и на сайте организации."
    ),
    "faq_tariffs": (
        "📊 Тарифы и оплата\n\n"
        "Тарифы утверждаются региональной службой по тарифам и "
        "публикуются на официальном сайте.\n\n"
        "Способы оплаты: через банк, онлайн-банкинг, терминалы. "
        "Для уточнения суммы по лицевому счёту напишите свой вопрос в чате."
    ),
    "faq_facility": (
        "🏢 Комплексная эксплуатация объектов\n\n"
        "Мы обслуживаем коммерческую недвижимость: инженерные системы, "
        "клининг, охрану, текущий ремонт.\n\n"
        "По вопросам заключения договора на обслуживание "
        "напишите свой вопрос в чате."
    ),
}


@router.message_callback(
    (F.callback.payload == "main_menu")
    | (F.callback.payload == "contact_operator")
    | F.callback.payload.in_({
        "faq_heating", "faq_hot_water", "faq_tariffs", "faq_facility",
    })
)
async def handle_callback(event: MessageCallback):
    payload = event.callback.payload
    logger.info("FAQ callback payload=%r", payload)

    # --- Возврат в главное меню ---
    if payload == "main_menu":
        await event.edit(
            text=(
                "Выберите интересующую тему — я постараюсь ответить сразу. "
                "Если не найдёте ответ, просто напишите свой вопрос в чате."
            ),
            attachments=[main_menu()],
        )
        return

    # --- Кнопка "Задать вопрос оператору" ---
    if payload == "contact_operator":
        await event.edit(
            text=(
                "📝 Напишите ваш вопрос в чате — я предложу отправить его оператору.\n\n"
                f"{working_status_text()}"
            ),
            attachments=[back_to_menu()],
        )
        return

    # --- FAQ-ответы ---
    if payload in FAQ_ANSWERS:
        await event.edit(
            text=FAQ_ANSWERS[payload],
            attachments=[back_to_menu()],
        )
        return