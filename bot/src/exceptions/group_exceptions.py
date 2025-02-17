class TwoHashtagsInOneMessageException(Exception):
    """
    Raised when user tries to send two hashtags in one message

    For example: підсумкидня та планинадень
    """

    pass


class MistakeInTaskDateException(Exception):
    """
    Raised when user tries to send task with wrong date format

    For example: 21.12.2021
    """

    pass


class DateCoudntBeBeforeNowException(Exception):
    """
    Raised when user tries to send task with date before now
    """

    pass


class GroupNotFoundException(Exception):
    """
    Raised when group not found in db
    """

    pass


class DateWrongFormat(Exception):
    """
    Raised when date has wrong format
    """

    pass


class ReportAlreadyExist(Exception):
    """
    Raised when user tries to send report for the same day
    """

    pass


class TaskForTodayNotFound(Exception):
    """
    Raised when user tries to send report for the task that not exist
    """

    pass


class CantPlanTaskBeforeNewDayDate(Exception):
    """
    Raised when user tries to plan task before new day date
    """

    pass
