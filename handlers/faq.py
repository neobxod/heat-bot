import logging

from maxapi import Router, F
from maxapi.types import MessageCallback

from keyboards import main_menu, reference_menu, back_to_reference, cancel_operator
from config import OPERATOR_WORK_HOURS
from utils.schedule import working_status_text

router = Router()
logger = logging.getLogger(__name__)


REFERENCE_ANSWERS = {
    "ref_emergency": (
        "🚨 Аварийная служба\n\n"
        "При аварии (прорыв трубы, отсутствие отопления, задымление):\n\n"
        "1. Позвоните в круглосуточную диспетчерскую службу.\n"
        "2. Сообщите точный адрес и характер проблемы.\n"
        "3. Если есть угроза жизни — звоните 112.\n\n"
        "📞 Телефон диспетчера: 8 (831) 461-91-95\n\n"
        "Если телефон занят — напишите свой вопрос, оператор перезвонит "
        "в рабочее время."
    ),
    "ref_meters": (
        "📟 Передача показаний счётчиков\n\n"
        "Показания принимаются ежемесячно с 15 по 25 число.\n\n"
        "📧 Электронная почта: energo@mayak-nn.ru\n\n"
        "В письме укажите:\n"
        "- номер лицевого счёта;\n"
        "- текущие показания;\n"
        "- дату снятия показаний.\n\n"
        "Если у вас нет лицевого счёта или возникли сложности — "
        "напишите свой вопрос в чате."
    ),
    "ref_schedule": (
        "🗓 Плановые отключения\n\n"
        "График плановых работ и отключений публикуется на официальном сайте.\n\n"
        "🌐 Сайт: http://enerserv-nn.ru/\n\n"
        "Также информация размещается в канале MAX «ООО ТЕПЛОЭНЕРГО».\n\n"
        "Если у вас аварийная ситуация — звоните в диспетчерскую: "
        "8 (831) 461-91-95."
    ),
    "ref_contacts": (
        "📞 Контакты\n\n"
        "Телефон (круглосуточно, аварийная служба):\n"
        "8 (831) 461-91-95\n\n"
        "Email для передачи показаний:\n"
        "energo@mayak-nn.ru\n\n"
        "Сайт:\n"
        "http://enerserv-nn.ru/\n\n"
        "Режим работы операторов:\n"
        "будние дни с 9:00 до 18:00."
    ),
}

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
    | (F.callback.payload == "open_reference")
    | (F.callback.payload == "contact_operator")
    | F.callback.payload.in_({
        "ref_emergency", "ref_meters", "ref_schedule", "ref_contacts",
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
                "Здравствуйте! Я информационный бот теплоснабжающей организации.\n\n"
                "Выберите раздел — я постараюсь ответить сразу. "
                "Если не найдёте ответ, просто напишите свой вопрос в чате."
            ),
            attachments=[main_menu()],
        )
        return

    # --- Открыть справочник ---
    if payload == "open_reference":
        await event.edit(
            text=(
                "📖 Справочник\n\n"
                "Выберите интересующую тему:"
            ),
            attachments=[reference_menu()],
        )
        return

    # --- Кнопка "Задать вопрос оператору" ---
    if payload == "contact_operator":
        await event.edit(
            text=(
                "📝 Напишите ваш вопрос в чате — я предложу отправить его оператору.\n\n"
                f"{working_status_text()}"
            ),
            attachments=[back_to_reference()],
        )
        return

    # --- Разделы справочника ---
    if payload in REFERENCE_ANSWERS:
        await event.edit(
            text=REFERENCE_ANSWERS[payload],
            attachments=[back_to_reference()],
        )
        return

    # --- Старые FAQ-ответы ---
    if payload in FAQ_ANSWERS:
        await event.edit(
            text=FAQ_ANSWERS[payload],
            attachments=[back_to_reference()],
        )
        return