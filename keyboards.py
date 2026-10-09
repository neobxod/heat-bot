from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def main_menu():
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="📖 Справочник", payload="open_reference"),
    )
    builder.row(
        CallbackButton(text="📞 Задать вопрос оператору", payload="contact_operator"),
    )
    return builder.as_markup()


def reference_menu():
    """Справочник — список тем."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="🚨 Аварийная служба", payload="ref_emergency"),
        CallbackButton(text="📟 Передача показаний", payload="ref_meters"),
    )
    builder.row(
        CallbackButton(text="🗓 Плановые отключения", payload="ref_schedule"),
        CallbackButton(text="📞 Контакты", payload="ref_contacts"),
    )
    builder.row(
        CallbackButton(text="🔥 Отопление", payload="faq_heating"),
        CallbackButton(text="💧 Горячая вода", payload="faq_hot_water"),
    )
    builder.row(
        CallbackButton(text="📊 Тарифы и оплата", payload="faq_tariffs"),
        CallbackButton(text="🏢 Эксплуатация зданий", payload="faq_facility"),
    )
    builder.row(
        CallbackButton(text="◀️ В главное меню", payload="main_menu"),
    )
    return builder.as_markup()


def back_to_reference():
    """Кнопка возврата в справочник."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="◀️ В справочник", payload="open_reference"))
    return builder.as_markup()


def back_to_menu():
    """Кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="◀️ В главное меню", payload="main_menu"))
    return builder.as_markup()


def cancel_operator():
    """Кнопка отмены отправки вопроса оператору."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="❌ Отменить", payload="main_menu"))
    return builder.as_markup()


def confirm_send():
    """Кнопки подтверждения отправки вопроса оператору."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✅ Отправить оператору", payload="confirm_send"),
        CallbackButton(text="❌ Отмена", payload="cancel_send"),
    )
    return builder.as_markup()


def reply_button(ticket_id: int):
    """Кнопка 'Ответить' под заявкой в группе операторов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text=f"✍️ Ответить на #{ticket_id}", payload=f"reply:{ticket_id}"),
    )
    return builder.as_markup()