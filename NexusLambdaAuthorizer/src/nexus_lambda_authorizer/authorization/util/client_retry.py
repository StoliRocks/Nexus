from datetime import datetime

from com.amazon.coral.availability.throttlingexception import ThrottlingException
from requests import ReadTimeout


def is_throttled_or_timed_out(ex, func_name):
    """
    Check if the given function is getting throttled or having a timeout.

    :param ex: exception
    :type ex: Exception instance

    :param func_name: function name
    :type func_name: str

    :return: True if is a throttling exception; False otherwise.
    """

    if isinstance(ex, ThrottlingException):
        print(
            func_name
            + " call has been throttled, at time: "
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return True
    elif isinstance(ex, ReadTimeout):
        print(
            func_name
            + " call has timed out, at time: "
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return True

    return False
