from aiogram.filters import Filter
from aiogram.types import Message

from bot.src.utils.unitofwork import IUnitOfWork


class GroupExistFilter(Filter):
    async def __call__(self, message: Message, uow: IUnitOfWork) -> bool:
        # async with uow:
        result = await uow.group_repo.group_exist(message.chat.id)
        return bool(result)


class IsGroupFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.type in ["supergroup", "group"]
