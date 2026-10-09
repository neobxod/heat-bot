from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.filters.command import CommandStart
from keyboards import main_menu

router = Router()


@router.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    await event.message.answer(
        text=(
            "Здравствуйте! Я информационный бот теплоснабжающей организации.\n\n"
            "Выберите раздел — я постараюсь ответить сразу. "
            "Если не найдёте ответ, просто напишите свой вопрос в чате."
        ),
        attachments=[main_menu()],
    )