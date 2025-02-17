import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload

from bot.src.db.models.models import (
    GroupModel,
    GroupPartisipantsModel,
    ReportModel,
    TaskModel,
    UserModel,
)
from bot.src.db.redis import redis_cache
from bot.src.utils.repository import SQLAlchemyRepository


class UserRepo(SQLAlchemyRepository):
    model = UserModel


class GroupRepo(SQLAlchemyRepository):
    model = GroupModel

    @redis_cache()
    async def group_exist(self, group_id: int) -> bool | int:
        """return true if group exist in db"""
        stmt = select(self.model.id).where(self.model.group_id == group_id)
        res = await self.session.execute(stmt)
        result = res.scalar_one_or_none()
        return bool(result) if result is None else result

    async def get_groups_for_reminder(self):
        now = datetime.now()
        stmt = (
            select(GroupModel)
            .join(
                GroupPartisipantsModel,
                GroupModel.id == GroupPartisipantsModel.group_id,
            )
            .filter(GroupPartisipantsModel.exclude_from_reporters.is_(False))
            .options(joinedload(GroupModel.partisipants_of_group))
            .distinct()
        )
        result = await self.session.execute(stmt)
        groups = result.unique().scalars().all()

        pending_users = {}
        for group in groups:
            time_after_start_new_day = group.time_after_start_new_day
            report_deadline = now + timedelta(days=1)
            report_deadline = report_deadline.replace(
                hour=time_after_start_new_day.hour,
                minute=time_after_start_new_day.minute,
            )
            task_deadline = report_deadline + timedelta(hours=1)

            stmt_users = select(GroupPartisipantsModel.user_id).filter(
                GroupPartisipantsModel.group_id == group.id,
                GroupPartisipantsModel.exclude_from_reporters.is_(False),
            )
            result_users = await self.session.execute(stmt_users)
            pending_users[group.id] = result_users.unique().scalars().all()
        return groups, pending_users


class GroupPartisipantsRepo(SQLAlchemyRepository):
    model = GroupPartisipantsModel

    async def add_one(self, data: dict) -> None:
        stmt = insert(self.model).values(**data)
        await self.session.execute(stmt)

    async def edit_one(self, id: int, data: dict):
        logging.warning("Dont use this method with this model")
        pass

    async def update_model(self, user_id: int, group_id: int, data: dict):
        stmt = (
            update(self.model)
            .values(**data)
            .filter_by(user_id=user_id, group_id=group_id)
            .returning(self.model.id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class TaskRepo(SQLAlchemyRepository):
    model = TaskModel


class ReportRepo(SQLAlchemyRepository):
    model = ReportModel
