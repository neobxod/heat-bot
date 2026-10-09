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
            "Выберите интересующую тему — я постараюсь ответить сразу. "
            "Если не найдёте ответ, нажмите «Задать вопрос оператору»."
        ),
        attachments=[main_menu()],
    )