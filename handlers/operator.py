import logging

from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback

from config import OPERATOR_CHAT_ID, OPERATOR_WORK_HOURS
from keyboards import main_menu, confirm_send, reply_button
from database import create_ticket, get_ticket, save_answer_by_ticket

router = Router()
logger = logging.getLogger(__name__)

# Текст, ожидающий подтверждения: user_id -> текст
_pending_confirms: dict[int, str] = {}

# Операторы, ожидающие ввода ответа: operator_user_id -> ticket_id
_pending_replies: dict[int, int] = {}

# Дедупликация
_processed_mids: set[int] = set()
_MAX_PROCESSED = 2000


def _get_user_id(event) -> int | None:
    """Достаёт user_id автора события (для callback — из callback.user)."""
    callback = getattr(event, "callback", None)
    if callback is not None:
        user_obj = getattr(callback, "user", None)
        if user_obj is not None:
            uid = getattr(user_obj, "user_id", None)
            if uid is not None:
                return uid
    if getattr(event, "message", None) and getattr(event.message, "sender", None):
        return event.message.sender.user_id
    return None


# ============================================================
# Обработка ВХОДЯЩИХ СООБЩЕНИЙ
# ============================================================

@router.message_created()
async def handle_message(event: MessageCreated):
    if not event.message or not event.message.sender:
        return

    # Дедупликация
    mid = getattr(event.message.body, "mid", None) if event.message.body else None
    if mid is not None:
        if mid in _processed_mids:
            return
        _processed_mids.add(mid)
        if len(_processed_mids) > _MAX_PROCESSED:
            _processed_mids.clear()

    chat_id = None
    if event.message.recipient is not None:
        chat_id = getattr(event.message.recipient, "chat_id", None)

    user_id = event.message.sender.user_id
    user_name = event.message.sender.first_name or "—"
    text = (event.message.body.text or "").strip() if event.message.body else ""

    is_operator_group = bool(OPERATOR_CHAT_ID and chat_id == OPERATOR_CHAT_ID)

    # === Сообщение из группы операторов ===
    if is_operator_group:
        # В группе принимаем только /reply N текст. Никаких «просто сообщений».
        await handle_operator_reply(event, text)
        return

    # === Личка с ботом ===
    # Оператор печатает ответ в личке после клика по кнопке
    if user_id in _pending_replies:
        ticket_id = _pending_replies.pop(user_id)
        await _deliver_answer(event, ticket_id, text)
        return

    # Абонент пишет текст → предлагаем отправить оператору
    if not text or text.startswith("/"):
        return

    _pending_confirms[user_id] = text

    await event.message.answer(
        text=(
            f"📝 Ваше сообщение:\n\n"
            f"«{text}»\n\n"
            f"Отправить его оператору?\n\n"
            f"⏰ Операторы работают: {OPERATOR_WORK_HOURS}."
        ),
        attachments=[confirm_send()],
    )


# ============================================================
# Обработка CALLBACK-КНОПОК
# ============================================================

@router.message_callback(
    (F.callback.payload == "confirm_send")
    | (F.callback.payload == "cancel_send")
    | F.callback.payload.startswith("reply:")
)
async def handle_callback(event: MessageCallback):
    payload = event.callback.payload
    logger.info("Operator callback payload=%r", payload)

    # Кнопка ответа в группе операторов
    if payload.startswith("reply:"):
        await handle_reply_button(event)
        return

    user_id = _get_user_id(event)
    if user_id is None:
        return

    # Подтверждение отправки вопроса
    if payload == "confirm_send":
        text = _pending_confirms.pop(user_id, None)
        if not text:
            await event.edit(
                text="⌛ Сообщение устарело. Напишите вопрос заново.",
                attachments=[main_menu()],
            )
            return

        user_name = "—"
        if event.callback and getattr(event.callback, "user", None):
            user_name = getattr(event.callback.user, "first_name", None) or "—"

        ticket_id = create_ticket(user_id, user_name, text)
        logger.info("Создан тикет #%s от %s (%s)", ticket_id, user_id, user_name)

        operator_message = (
            f"📩 Новый вопрос от абонента (#{ticket_id})\n"
            f"ID абонента: {user_id}\n"
            f"Имя: {user_name}\n"
            f"---\n{text}"
        )

        if OPERATOR_CHAT_ID:
            try:
                await event.bot.send_message(
                    chat_id=OPERATOR_CHAT_ID,
                    text=operator_message,
                    attachments=[reply_button(ticket_id)],
                )
            except Exception as e:
                logger.exception("Не удалось отправить вопрос оператору: %s", e)

        await event.edit(
            text=(
                "✅ Спасибо! Ваш вопрос передан оператору.\n\n"
                f"⏰ Операторы работают: {OPERATOR_WORK_HOURS}.\n"
                "Ответ придёт в рабочее время."
            ),
            attachments=[main_menu()],
        )
        return

    if payload == "cancel_send":
        _pending_confirms.pop(user_id, None)
        await event.edit(
            text="Отменено. Выберите тему или напишите новый вопрос.",
            attachments=[main_menu()],
        )
        return


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def _deliver_answer(event, ticket_id: int, answer_text: str):
    """Отправляет ответ оператора абоненту и закрывает тикет."""
    answer_text = (answer_text or "").strip()
    if not answer_text:
        await event.message.answer("⚠️ Текст ответа пустой.")
        return

    logger.info("_deliver_answer: тикет=%s, текст=%r", ticket_id, answer_text)

    ticket = get_ticket(ticket_id)
    if ticket is None:
        logger.warning("Тикет #%s не найден в БД", ticket_id)
        await event.message.answer(f"⚠️ Тикет #{ticket_id} не найден в базе.")
        return

    if ticket["status"] == "answered":
        logger.info("Тикет #%s уже закрыт (%s)", ticket_id, ticket["answered_at"])
        await event.message.answer(
            f"⚠️ По тикету #{ticket_id} уже был отправлен ответ "
            f"({ticket['answered_at']}). Повторная отправка не выполнена."
        )
        return

    target_user_id = ticket["user_id"]
    logger.info("Тикет #%s → user_id=%s, отправляю ответ", ticket_id, target_user_id)

    try:
        await event.bot.send_message(
            user_id=target_user_id,
            text=(
                f"📩 Ответ оператора (по обращению #{ticket_id}):\n\n"
                f"{answer_text}\n\n"
                f"Если остались вопросы — напишите снова."
            ),
            attachments=[main_menu()],
        )
        logger.info("Ответ доставлен абоненту %s по тикету #%s", target_user_id, ticket_id)
    except Exception as e:
        logger.exception("Не удалось отправить ответ абоненту %s: %s", target_user_id, e)
        await event.message.answer(
            f"⚠️ Не удалось отправить ответ абоненту {target_user_id}.\n"
            f"Ошибка: {e}"
        )
        return

    ok = save_answer_by_ticket(ticket_id, answer_text)
    if ok:
        logger.info("Тикет #%s закрыт в БД", ticket_id)
        await event.message.answer(
            f"✅ Ответ по тикету #{ticket_id} отправлен абоненту {target_user_id}."
        )
    else:
        logger.warning("Не удалось обновить тикет #%s в БД", ticket_id)
        await event.message.answer(
            f"⚠️ Ответ отправлен, но не удалось обновить тикет #{ticket_id} в БД."
        )


async def handle_operator_reply(event: MessageCreated, text: str):
    """Резервный вариант: /reply <ticket_id> <текст>."""
    if not text.startswith("/reply"):
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await event.message.answer(
            "⚠️ Формат: /reply <номер тикета> <текст ответа>."
        )
        return

    try:
        ticket_id = int(parts[1])
    except ValueError:
        await event.message.answer(f"⚠️ Номер тикета должен быть числом: {parts[1]}")
        return

    await _deliver_answer(event, ticket_id, parts[2].strip())


async def handle_reply_button(event: MessageCallback):
    """Нажатие кнопки '✍️ Ответить на #N' в группе операторов."""
    operator_id = _get_user_id(event)
    if operator_id is None:
        return

    payload = event.callback.payload  # "reply:6"
    try:
        ticket_id = int(payload.split(":", 1)[1])
    except (ValueError, IndexError):
        return

    _pending_replies[operator_id] = ticket_id

    try:
        await event.bot.send_message(
            user_id=operator_id,
            text=(
                f"✍️ Введите текст ответа для тикета #{ticket_id}.\n\n"
                f"Просто отправьте сообщение сюда — оно будет доставлено абоненту."
            ),
        )
        # Сообщаем в группу
        await event.bot.send_message(
            chat_id=OPERATOR_CHAT_ID,
            text=f"📩 Оператору отправлено личное сообщение для ввода ответа по #{ticket_id}.",
        )
    except Exception as e:
        logger.exception("Не удалось написать оператору %s: %s", operator_id, e)
        _pending_replies.pop(operator_id, None)
        await event.bot.send_message(
            chat_id=OPERATOR_CHAT_ID,
            text=(
                f"⚠️ Не удалось отправить личное сообщение оператору.\n"
                f"Скорее всего, оператор ещё не начинал чат с ботом в личке.\n"
                f"Откройте бота в личке, нажмите /start и попробуйте снова."
            ),
        )