import logging

from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback

from config import OPERATOR_CHAT_ID, OPERATOR_WORK_HOURS
from keyboards import (
    main_menu,
    confirm_send,
    operator_menu,
    tickets_list_menu,
    back_to_operator_menu,
    cancel_operator_reply,
    reply_button,
)
from database import (
    create_ticket,
    get_ticket,
    save_answer_by_ticket,
    get_user_history,
    get_open_tickets,
)

router = Router()
logger = logging.getLogger(__name__)

# Состояния операторов (in-memory)
_pending_confirms: dict[int, str] = {}    # user_id → текст, ожидающий подтверждения
_pending_replies: dict[int, int] = {}     # operator_id → ticket_id (ждём ввод ответа)
_pending_history: set[int] = set()        # operator_id, ожидающий ввода ID абонента

# Дедупликация входящих
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


def _get_chat_id(event) -> int | None:
    """Достаёт chat_id, куда пришло сообщение."""
    msg = getattr(event, "message", None)
    if msg is None:
        return None
    recipient = getattr(msg, "recipient", None)
    if recipient is None:
        return None
    return getattr(recipient, "chat_id", None)


# ============================================================
# ОБРАБОТКА ВХОДЯЩИХ СООБЩЕНИЙ
# ============================================================

@router.message_created()
async def handle_message(event: MessageCreated):
    if not event.message or not event.message.sender:
        return

    # Дедупликация по mid
    mid = getattr(event.message.body, "mid", None) if event.message.body else None
    if mid is not None:
        if mid in _processed_mids:
            return
        _processed_mids.add(mid)
        if len(_processed_mids) > _MAX_PROCESSED:
            _processed_mids.clear()

    chat_id = _get_chat_id(event)
    user_id = event.message.sender.user_id
    user_name = event.message.sender.first_name or "—"
    text = (event.message.body.text or "").strip() if event.message.body else ""

    is_operator_group = bool(OPERATOR_CHAT_ID and chat_id == OPERATOR_CHAT_ID)

    # ============================================================
    # ГРУППА ОПЕРАТОРОВ
    # ============================================================
    if is_operator_group:
        # 1. Оператор вводит ID абонента для истории
        if user_id in _pending_history:
            if text.isdigit():
                _pending_history.discard(user_id)
                await _show_history(event, int(text))
                return
            if text.startswith("/"):
                _pending_history.discard(user_id)
                # Продолжаем обработку как команды ниже
            else:
                await event.message.answer(
                    "⚠️ Введите ID абонента (только цифры) "
                    "или отправьте /menu для отмены."
                )
                return

        # 2. Команда /menu или /start — показать меню оператора
        if text.startswith("/menu") or text.startswith("/start"):
            await event.message.answer(
                text="🎛 Меню оператора:",
                attachments=[operator_menu()],
            )
            return

        # 3. Оператор в режиме ответа → любое не-командное сообщение = ответ
        if user_id in _pending_replies and not text.startswith("/"):
            ticket_id = _pending_replies.pop(user_id)
            await _deliver_answer(event, ticket_id, text)
            return

        # 4. Резервные команды /reply N текст и /history N
        await handle_operator_reply(event, text)
        return

    # ============================================================
    # ЛИЧКА С БОТОМ
    # ============================================================
    # Оператор печатает ответ после нажатия кнопки «Ответить»
    if user_id in _pending_history:
        logger.info("Оператор %s вводит ID абонента: %r", user_id, text)
        if text.isdigit():
            _pending_history.discard(user_id)
            await _show_history(event, int(text))
            return
        if text.startswith("/"):
            _pending_history.discard(user_id)
        else:
            await event.message.answer(
                "⚠️ Введите ID абонента (только цифры) "
                "или отправьте /menu для отмены."
            )
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
# ОБРАБОТКА CALLBACK-КНОПОК
# ============================================================

@router.message_callback(
    (F.callback.payload == "confirm_send")
    | (F.callback.payload == "cancel_send")
    | F.callback.payload.startswith("reply:")
    | F.callback.payload.startswith("op_")
)
async def handle_callback(event: MessageCallback):
    payload = event.callback.payload
    logger.info("Operator callback payload=%r", payload)

    operator_id = _get_user_id(event)

    # ---------- МЕНЮ ОПЕРАТОРА ----------

    if payload == "op_refresh":
        await event.edit(
            text="🎛 Меню оператора:",
            attachments=[operator_menu()],
        )
        return

    if payload == "op_list_tickets":
        tickets = get_open_tickets(limit=20)
        if not tickets:
            await event.edit(
                text="📋 Открытых тикетов нет.",
                attachments=[back_to_operator_menu()],
            )
            return
        await event.edit(
            text=f"📋 Открытые тикеты: {len(tickets)}",
            attachments=[tickets_list_menu(tickets)],
        )
        return

    if payload == "op_history_prompt":
        if operator_id is not None:
            _pending_history.add(operator_id)
        await event.edit(
            text=(
                "📜 Введите ID абонента для просмотра истории.\n\n"
                "Например: 193110397\n\n"
                "Для отмены отправьте /menu."
            ),
            attachments=[back_to_operator_menu()],
        )
        return

    if payload == "op_cancel_reply":
        if operator_id is not None:
            _pending_replies.pop(operator_id, None)
        await event.edit(
            text="❌ Ввод ответа отменён.",
            attachments=[back_to_operator_menu()],
        )
        return

    # ---------- ОТВЕТ НА ТИКЕТ ----------

    if payload.startswith("reply:"):
        if operator_id is None:
            return
        try:
            ticket_id = int(payload.split(":", 1)[1])
        except (ValueError, IndexError):
            return

        ticket = get_ticket(ticket_id)
        if ticket is None:
            await event.edit(text=f"⚠️ Тикет #{ticket_id} не найден в базе.")
            return
        if ticket["status"] == "answered":
            await event.edit(
                text=f"⚠️ По тикету #{ticket_id} уже отправлен ответ "
                     f"({ticket['answered_at']})."
            )
            return

        _pending_replies[operator_id] = ticket_id

        await event.edit(
            text=(
                f"✍️ Тикет #{ticket_id}\n"
                f"Абонент: {ticket.get('user_name') or '—'} "
                f"(ID {ticket['user_id']})\n"
                f"Вопрос: {ticket['question']}\n\n"
                f"Введите текст ответа следующим сообщением "
                f"или нажмите «Отменить»."
            ),
            attachments=[cancel_operator_reply()],
        )
        return

    # ---------- ПОДТВЕРЖДЕНИЕ ОТПРАВКИ ВОПРОСА (ЛИЧКА АБОНЕНТА) ----------

    if operator_id is None:
        return

    if payload == "confirm_send":
        text = _pending_confirms.pop(operator_id, None)
        if not text:
            await event.edit(
                text="⌛ Сообщение устарело. Напишите вопрос заново.",
                attachments=[main_menu()],
            )
            return

        user_name = "—"
        if event.callback and getattr(event.callback, "user", None):
            user_name = getattr(event.callback.user, "first_name", None) or "—"

        ticket_id = create_ticket(operator_id, user_name, text)
        logger.info("Создан тикет #%s от %s (%s)", ticket_id, operator_id, user_name)

        operator_message = (
            f"📩 Новый вопрос от абонента (#{ticket_id})\n"
            f"ID абонента: {operator_id}\n"
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
        _pending_confirms.pop(operator_id, None)
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
        await event.message.answer(f"⚠️ Тикет #{ticket_id} не найден в базе.")
        return

    if ticket["status"] == "answered":
        await event.message.answer(
            f"⚠️ По тикету #{ticket_id} уже был отправлен ответ "
            f"({ticket['answered_at']})."
        )
        return

    target_user_id = ticket["user_id"]

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
        logger.info(
            "Ответ доставлен абоненту %s по тикету #%s",
            target_user_id, ticket_id,
        )
    except Exception as e:
        logger.exception(
            "Не удалось отправить ответ абоненту %s: %s", target_user_id, e
        )
        await event.message.answer(
            f"⚠️ Не удалось отправить ответ абоненту {target_user_id}.\n"
            f"Ошибка: {e}"
        )
        return

    ok = save_answer_by_ticket(ticket_id, answer_text)
    if ok:
        logger.info("Тикет #%s закрыт в БД", ticket_id)
        await event.message.answer(
            f"✅ Ответ по тикету #{ticket_id} отправлен абоненту {target_user_id}.",
            attachments=[back_to_operator_menu()],
        )
    else:
        await event.message.answer(
            f"⚠️ Ответ отправлен, но не удалось обновить тикет #{ticket_id} в БД."
        )


async def _show_history(event, target_user_id: int):
    """Показывает историю обращений абонента."""
    logger.info("_show_history: запрос истории по user_id=%s", target_user_id)

    history = get_user_history(target_user_id, limit=5)
    logger.info("Найдено %d записей", len(history))

    if not history:
        await event.message.answer(
            text=f"📋 По абоненту {target_user_id} обращений не найдено.",
            attachments=[back_to_operator_menu()],
        )
        return

    lines = [f"📋 История обращений абонента {target_user_id}:\n"]
    for t in history:
        icon = "✅" if t["status"] == "answered" else "⏳"
        lines.append(f"{icon} #{t['id']} | {t['created_at']}")
        lines.append(f"Вопрос: {t['question']}")
        if t.get("answer"):
            lines.append(f"Ответ: {t['answer']}")
            lines.append(f"Закрыт: {t['answered_at']}")
        else:
            lines.append("Статус: ожидает ответа")
        lines.append("")

    full_text = "\n".join(lines)
    max_len = 3500

    if len(full_text) <= max_len:
        await event.message.answer(
            text=full_text,
            attachments=[back_to_operator_menu()],
        )
        logger.info("История отправлена одним сообщением")
        return

    chunks = [full_text[i:i + max_len] for i in range(0, len(full_text), max_len)]
    for chunk in chunks[:-1]:
        await event.message.answer(text=chunk)
    await event.message.answer(
        text=chunks[-1],
        attachments=[back_to_operator_menu()],
    )
    logger.info("История отправлена %d сообщениями", len(chunks))


async def handle_operator_reply(event: MessageCreated, text: str):
    """Резервные команды: /reply N текст и /history N. Основной интерфейс — кнопки."""
    # /history N
    if text.startswith("/history"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await event.message.answer(
                "📜 Формат: /history <ID абонента>.\n"
                "Либо воспользуйтесь меню: /menu."
            )
            return
        await _show_history(event, int(parts[1].strip()))
        return

    # /reply N текст
    if not text.startswith("/reply"):
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await event.message.answer(
            "⚠️ Формат: /reply <номер тикета> <текст ответа>.\n"
            "Либо воспользуйтесь меню: /menu."
        )
        return

    try:
        ticket_id = int(parts[1])
    except ValueError:
        await event.message.answer(
            f"⚠️ Номер тикета должен быть числом: {parts[1]}"
        )
        return

    await _deliver_answer(event, ticket_id, parts[2].strip())