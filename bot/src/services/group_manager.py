import asyncio
import datetime
import logging
from typing import Literal, NamedTuple, Sequence

from aiogram.types import ChatJoinRequest, Message, MessageEntity, User

from bot.src.db.models.models import GroupModel, ReportModel, TaskModel
from bot.src.exceptions.group_exceptions import (
    CantPlanTaskBeforeNewDayDate,
    DateCoudntBeBeforeNowException,
    DateWrongFormat,
    GroupNotFoundException,
    MistakeInTaskDateException,
    TaskForTodayNotFound,
    TwoHashtagsInOneMessageException,
)
from bot.src.services.common_services import save_user_to_db
from bot.src.templates.texts import (
    ANSWER_ON_DAILY_REPORT,
    TASK_ACCEPTED_ANSWER_WITH_DATE,
    TASK_ALREADY_EXIST_WITH,
    TASK_ON_WEEKEND_ANSWER,
)
from bot.src.utils.consts import (
    day_plan_results_hashtags,
    new_day_task_hashtags,
)
from bot.src.utils.enum import TaskType
from bot.src.utils.unitofwork import IUnitOfWork

logger = logging.getLogger(__name__)


class TaskMessage(NamedTuple):
    task_type: TaskType
    task_deadline: datetime.datetime
    tasks: Sequence[str]


class ReportMessage(NamedTuple):
    task_type: TaskType
    task_deadline: datetime.datetime
    tasks: Sequence[str]


async def set_group_deadline_time(
    uow: IUnitOfWork, time: str, group_id: int
) -> str | None:
    group_model_id = await uow.group_repo.group_exist(group_id=group_id)
    if not group_model_id:
        raise GroupNotFoundException("Група не знайдена в БД")
    try:
        parsed_time = datetime.datetime.strptime(time, "%H:%M").time()
    except ValueError:
        raise DateWrongFormat("Неправильний формат часу")
    await uow.group_repo.edit_one(
        group_model_id, {"time_after_start_new_day": parsed_time}
    )
    await uow.commit()
    return parsed_time.strftime("%H:%M")


async def save_group_to_db(
    uow: IUnitOfWork,
    group_id: int,
    group_title: str,
    status: Literal["member", "left", "administrator"],
) -> None:
    group_db_id: bool | int = await uow.group_repo.group_exist(group_id=group_id)
    if group_db_id:
        await uow.group_repo.edit_one(group_db_id, {"status": status})
        await uow.commit()
        return
    time_after_start_new_day = datetime.time(hour=10, minute=0)
    await uow.group_repo.add_one(
        {
            "group_id": group_id,
            "group_title": group_title,
            "time_after_start_new_day": time_after_start_new_day,
        }
    )
    await uow.commit()


async def set_user_group_partisiption(
    uow: IUnitOfWork,
    user_id: int,
    group_id: int,
    status: Literal["member", "left", "administrator"],
):
    """
    Set user status in group

    :param uow: UnitOfWork
    :param user_id: int
    :param group_id: int
    :param status: str
    :return: None

    """
    user_group = await uow.group_partisipants_repo.find_one(
        user_id=user_id, group_id=group_id
    )
    exclude_from_reporters = False if status in ["member"] else True
    try:
        if user_group:
            await uow.group_partisipants_repo.update_model(
                user_id=user_id,
                group_id=group_id,
                data={"exclude_from_reporters": exclude_from_reporters},
            )
        else:
            await uow.group_partisipants_repo.add_one(
                {
                    "user_id": user_id,
                    "group_id": group_id,
                    "exclude_from_reporters": exclude_from_reporters,
                }
            )
        await uow.commit()
    except Exception as ex:
        logger.info(f"Error while saving user to db: {ex}")
        await uow.rollback()


async def proccess_user_updates_in_group(
    uow: IUnitOfWork,
    user: User,
    chat_id: int,
    new_chat_member_status: Literal["member", "left", "administrator"],
):
    group_exist = await uow.group_repo.find_one(group_id=chat_id)
    if not group_exist:
        return
    await save_user_to_db(uow, user)
    await set_user_group_partisiption(
        uow, user.id, group_exist.id, new_chat_member_status
    )


async def proccess_user_join_request(
    uow: IUnitOfWork,
    user: User,
    chat_id: int,
    update: ChatJoinRequest,
):
    group_exist = await uow.group_repo.find_one(group_id=chat_id)
    if not group_exist:
        return

    await save_user_to_db(uow, user)
    await set_user_group_partisiption(uow, user.id, group_exist.id, "member")


async def find_tasks_in_message(message_text: list[str]) -> Sequence[str]:
    tasks_list = []
    for task in message_text:
        if len(task) <= 1:
            continue
        if task[0].isdigit() and task[1] in {".", " ", ")"}:
            task_text = task[2:]
        else:
            task_text = task
        tasks_list.append(task_text.strip())
    return tasks_list


async def find_task_deadline(
    first_msg_line: list[str], time_after_start_new_day: datetime.time
) -> datetime.datetime:
    datetime_now = datetime.datetime.now()
    task_on: Literal["next_day", "current_day"] = (
        "next_day" if datetime_now.time() > time_after_start_new_day else "current_day"
    )
    if len(first_msg_line) == 2 and len(first_msg_line[1]) > 1:
        task_deadline = first_msg_line[1]
        try:
            task_deadline = datetime.datetime.strptime(task_deadline, "%d.%m")
        except ValueError:
            raise MistakeInTaskDateException("Неправильний формат дати")
        if task_deadline.date() == datetime_now.date() and task_on == "next_day":
            raise CantPlanTaskBeforeNewDayDate(
                f"Ви можете планувати завдання тільки на завтра, або на сьогодні не пізніше {time_after_start_new_day}"
            )
        task_deadline += datetime.timedelta(days=1)
        task_deadline = task_deadline.replace(
            hour=time_after_start_new_day.hour,
            minute=time_after_start_new_day.minute,
            second=0,
            microsecond=0,
            year=datetime_now.year,
        )
    else:
        if task_on == "current_day":
            task_deadline = datetime_now
        elif task_on == "next_day":
            task_deadline = datetime_now + datetime.timedelta(days=1)
        else:
            raise ValueError("Unknown task_on value")
        if task_deadline.weekday() in [5, 6]:
            task_deadline += datetime.timedelta(
                days=(7 - task_deadline.weekday())
            ) + datetime.timedelta(days=1)
        task_deadline = task_deadline.replace(
            hour=time_after_start_new_day.hour,
            minute=time_after_start_new_day.minute,
            second=0,
            microsecond=0,
            year=datetime_now.year,
        )
    if task_deadline < datetime_now:
        raise DateCoudntBeBeforeNowException("Дата не може бути раніше поточної")

    return task_deadline


async def find_report_deadline(
    first_msg_line: list[str], time_after_start_new_day: datetime.time
) -> datetime.datetime:
    datetime_now = datetime.datetime.now()
    datetime_now += datetime.timedelta(days=3)
    task_on: Literal["previous_day", "current_day"] = (
        "previous_day"
        if datetime_now.time() < time_after_start_new_day
        else "current_day"
    )
    print(task_on)
    if (
        task_on == "current_day"
    ):  # коли людина робить звіт на завдання яке планувала на сьогодні,
        # час до якого можна робити звіт - це сьогодні + завтра до 10 години
        task_deadline = datetime_now + datetime.timedelta(days=1)
    elif (
        task_on == "previous_day"
    ):  # коли людина робить звіт на завдання яке планувала на вчора, але на годиннику
        # ще немає 10 годин - цей звіт робиться за минулий день
        task_deadline = datetime_now - datetime.timedelta(days=1)
    else:
        raise ValueError("Unknown task_on value")
    task_deadline = task_deadline.replace(
        hour=time_after_start_new_day.hour,
        minute=time_after_start_new_day.minute,
        second=0,
        microsecond=0,
        year=datetime_now.year,
    )
    return task_deadline


async def generate_task_message(
    message_text: str, time_after_start_new_day: datetime.time
) -> TaskMessage:
    splited_msg = message_text.split("\n")
    task_type = TaskType.DAILY
    first_msg_line = splited_msg[0].split(" ")
    task_deadline = await find_task_deadline(first_msg_line, time_after_start_new_day)
    tasks_list = await find_tasks_in_message(splited_msg[1:])
    return TaskMessage(
        task_type=task_type, task_deadline=task_deadline, tasks=tasks_list
    )


async def generate_report_message(
    message_text: str, time_after_start_new_day: datetime.time
) -> ReportMessage:
    splited_msg = message_text.split("\n")
    task_type = TaskType.DAILY
    first_msg_line = splited_msg[0].split(" ")
    task_deadline = await find_report_deadline(first_msg_line, time_after_start_new_day)
    tasks_reports_list = await find_tasks_in_message(splited_msg[1:])
    return ReportMessage(
        task_type=task_type,
        task_deadline=task_deadline,
        tasks=tasks_reports_list,
    )


async def find_hashtags(
    message_entities: list[MessageEntity], message_text: str
) -> Sequence[str]:
    """Ищет хештеги в сообщении и редактирует их для дальнейшей работы"""
    found_hashtags = []
    for entity in message_entities:
        hashtag_start = entity.offset
        hashtag_end = entity.length + entity.offset
        logging.debug(f"Found hashtag: {message_text[hashtag_start:hashtag_end]}")
        hashtag = message_text[hashtag_start:hashtag_end].replace("#", "").lower()
        found_hashtags.append(hashtag)

    await find_double_not_same_hashtags(found_hashtags)
    return found_hashtags


async def find_double_not_same_hashtags(
    found_hashtags: Sequence[str],
):
    """Ищет два или более хештегов которые разные по смыслу и будут ломать логику"""
    found_new_day_plan_hashtags_list = []
    found_day_plan_results_hashtags_list = []
    for new_day_hashtag in new_day_task_hashtags:
        if new_day_hashtag in found_hashtags:
            found_new_day_plan_hashtags_list.append(new_day_hashtag)

    for day_plan_results_hashtag in day_plan_results_hashtags:
        if day_plan_results_hashtag in found_hashtags:
            found_day_plan_results_hashtags_list.append(day_plan_results_hashtag)

    if (
        len(found_new_day_plan_hashtags_list) >= 1
        and len(found_day_plan_results_hashtags_list) >= 1
    ):
        raise TwoHashtagsInOneMessageException(
            "Не можна використовувати два хештеги в одному повідомленні"
        )


async def save_task_to_db(
    message_text: str,
    time_after_start_new_day: datetime.time,
    group_model: GroupModel,
    uow: IUnitOfWork,
    user_id: int,
):
    task_data: TaskMessage = await generate_task_message(
        message_text, group_model.time_after_start_new_day
    )
    task_exist: Sequence[TaskModel] = await uow.task_repo.find_all(
        user_id=user_id,
        group_id=group_model.id,
        task_deadline=task_data.task_deadline,
    )
    if task_exist:
        return TASK_ALREADY_EXIST_WITH.format(
            task_date=(task_data.task_deadline - datetime.timedelta(days=1)).strftime(
                "%d.%m.%Y"
            ),
            tasks="\n".join(
                [
                    f"{index + 1}. {task.task_text}"
                    for index, task in enumerate(task_exist)
                ]
            ),
        )
    for index, task in enumerate(task_data.tasks):
        await uow.task_repo.add_one(
            {
                "group_id": group_model.id,
                "user_id": user_id,
                "task_deadline": task_data.task_deadline,
                "task_text": task,
                "task_type": task_data.task_type,
                "task_number": index + 1,
            }
        )
    await uow.commit()
    temp_test_deadline = task_data.task_deadline - datetime.timedelta(days=1)
    if temp_test_deadline.weekday() in [5, 6]:
        result_text = TASK_ON_WEEKEND_ANSWER.format(
            task_date=temp_test_deadline.strftime("%d.%m.%Y")
        )
    else:
        result_text = TASK_ACCEPTED_ANSWER_WITH_DATE.format(
            task_date=temp_test_deadline.strftime("%d.%m.%Y"),
            task_count=len(task_data.tasks),
        )
    return result_text


async def save_task_result_to_db(
    message_text: str,
    time_after_start_new_day: datetime.time,
    group_model: GroupModel,
    uow: IUnitOfWork,
    user_id: int,
):
    report_data = await generate_report_message(
        message_text, group_model.time_after_start_new_day
    )
    print(report_data.task_deadline)
    tasks_model_list: Sequence[TaskModel] = await uow.task_repo.find_all(
        user_id=user_id,
        group_id=group_model.id,
        task_deadline=report_data.task_deadline,
    )
    if not tasks_model_list:
        raise TaskForTodayNotFound(
            f"Завдання на {report_data.task_deadline.strftime('%d.%m.%Y')} не знайдено."
        )
    for index, report in enumerate(report_data.tasks):
        task_model = await uow.task_repo.find_one(
            user_id=user_id,
            group_id=group_model.id,
            task_deadline=report_data.task_deadline,
            task_number=index + 1,
        )
        if not task_model:
            continue
        report_exist: ReportModel = await uow.report_repo.find_one(
            user_id=user_id,
            group_id=group_model.id,
            task_id=task_model.id,
        )
        if report_exist:
            await uow.report_repo.edit_one(report_exist.id, {"report_text": report})
            continue
        await uow.report_repo.add_one(
            {
                "user_id": user_id,
                "group_id": group_model.id,
                "task_id": task_model.id,
                "report_text": report,
                "task_number": index + 1,
                "task_type": TaskType.DAILY,
            }
        )
    await uow.commit()
    return ANSWER_ON_DAILY_REPORT


async def handle_group_message(
    message: Message,
    uow: IUnitOfWork,
) -> str | None:
    """Обработка сообщения в группе которая есть в БД"""
    group_model: GroupModel = await uow.group_repo.find_one(group_id=message.chat.id)
    group_partisiption = await uow.group_partisipants_repo.find_one(
        user_id=message.from_user.id, group_id=group_model.id
    )
    if not group_partisiption:
        await uow.group_partisipants_repo.add_one(
            {
                "user_id": message.from_user.id,
                "group_id": group_model.id,
            }
        )
        await uow.commit()
    message_text = message.text
    found_hashtags = await find_hashtags(message.entities, message_text)
    if not found_hashtags:
        return None
    # хештег для планів на новий день
    if found_hashtags[0] in new_day_task_hashtags:
        answer_text = await save_task_to_db(
            message_text,
            group_model.time_after_start_new_day,
            group_model,
            uow,
            message.from_user.id,
        )
    # хештег для результатів планів на день
    elif found_hashtags[0] in day_plan_results_hashtags:
        answer_text = await save_task_result_to_db(
            message_text,
            group_model.time_after_start_new_day,
            group_model,
            uow,
            message.from_user.id,
        )
    else:
        return None
    return answer_text


async def send_reply_message(
    message: Message,
    message_text: str,
):
    msg = await message.reply(message_text)
    await asyncio.sleep(5)
    await msg.delete()
