import functools
from typing import Optional

from telegram import Update


def playgame():

    def decorator(function):

        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            update: Optional[Update] = args[1] if len(args) > 0 and isinstance(args[1], Update) else None

            try:
                function(*args, **kwargs)
            except Exception as error:
                if update is not None and update.message is not None:
                    reply = f"Что-то пошло не так, обратитесь к разработчику:\n{error}"
                    update.message.reply_text(reply)

                raise

        return wrapped

    return decorator
