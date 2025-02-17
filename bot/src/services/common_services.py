import logging

from aiogram.types import User

from bot.src.utils.unitofwork import IUnitOfWork


logger = logging.getLogger(__name__)


async def save_user_to_db(uow: IUnitOfWork, user: User):
    user_exits = await uow.user_repo.find_one(id=user.id)
    if user_exits:
        return user_exits
    try:
        await uow.user_repo.add_one(
            {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
            }
        )
        await uow.commit()
    except Exception as ex:
        logger.info(f"Error while saving user to db: {ex}")
        await uow.rollback()
