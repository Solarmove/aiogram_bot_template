import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from arq import cron
from sqlalchemy.ext.asyncio import create_async_engine

from bot.src.db.base import get_async_session
from bot.src.utils.unitofwork import UnitOfWork
from configreader import config, RedisConfig


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s (%(asctime)s) (Line: %(lineno)d) [%(filename)s] : %(message)s ",
    datefmt="%d/%m/%Y %I:%M:%S",
    encoding="utf-8",
    filemode="w",
)

logger = logging.getLogger(__name__)


async def startup(ctx):
    engine = create_async_engine(
        str(config.db_config.postgres_dsn), future=True, echo=False
    )
    session_factory = get_async_session
    ctx["session_factory"] = session_factory
    ctx["uow"] = UnitOfWork
    ctx["bot"] = Bot(
        token=config.bot_config.token,
        default=DefaultBotProperties(parse_mode=config.bot_config.parse_mode),
    )


async def shutdown(ctx):
    bot: Bot = ctx["bot"]
    await bot.session.close()


class WorkerSettings:
    redis_settings = RedisConfig.pool_settings
    on_startup = startup
    on_shutdown = shutdown
    functions = []
    cron_jobs = []
    allow_abort_jobs = True
