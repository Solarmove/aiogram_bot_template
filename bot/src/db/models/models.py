from sqlalchemy import BIGINT, BOOLEAN, ForeignKey, func, VARCHAR
from sqlalchemy.dialects.postgresql import ENUM, TIME, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, Relationship

from bot.src.db.base import Base
from bot.src.utils.enum import TaskType


class UserModel(Base):
    __tablename__ = "users"

    id = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    full_name = mapped_column(VARCHAR(255), nullable=False)
    username = mapped_column(VARCHAR(255), nullable=True, unique=True)
    is_admin = mapped_column(BOOLEAN, nullable=False, default=False)

    partisipant_of_groups: Mapped[list["GroupModel"]] = Relationship(
        back_populates="partisipants_of_group", secondary="group_partisipants"
    )


class GroupModel(Base):
    __tablename__ = "groups"

    id = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    group_id = mapped_column(BIGINT, nullable=False, unique=True)
    group_title = mapped_column(VARCHAR(255), nullable=False)
    time_after_start_new_day = mapped_column(TIME, nullable=False)
    partisipants_of_group: Mapped[list["UserModel"]] = Relationship(
        back_populates="partisipant_of_groups", secondary="group_partisipants"
    )
    status = mapped_column(VARCHAR(255), nullable=False, default="member")
    created_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), server_default=func.now()
    )
    update_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )


class GroupPartisipantsModel(Base):
    __tablename__ = "group_partisipants"

    user_id = mapped_column(
        BIGINT,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    group_id = mapped_column(
        BIGINT,
        ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    exclude_from_reporters = mapped_column(BOOLEAN, nullable=False, default=False)
    created_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), server_default=func.now()
    )
    update_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )


class TaskModel(Base):
    __tablename__ = "tasks"

    id = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    group_id = mapped_column(
        BIGINT, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id = mapped_column(
        BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_number = mapped_column(BIGINT, nullable=False)
    task_type = mapped_column(ENUM(TaskType), nullable=False)
    task_deadline = mapped_column(TIMESTAMP, nullable=False)
    task_text = mapped_column(VARCHAR(255), nullable=False)
    # is_task_completed = mapped_column(BOOLEAN, nullable=False, default=False)
    created_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), server_default=func.now()
    )
    update_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )


class ReportModel(Base):
    __tablename__ = "reports"

    id = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id = mapped_column(
        BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    group_id = mapped_column(
        BIGINT, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    task_id = mapped_column(
        BIGINT, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    task_number = mapped_column(BIGINT, nullable=False)
    task_type = mapped_column(ENUM(TaskType), nullable=False)
    report_text = mapped_column(VARCHAR(255), nullable=False)

    created_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), server_default=func.now()
    )
    update_at = mapped_column(
        TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now()
    )
