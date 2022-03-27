import enum
import os.path
import threading
from tempfile import NamedTemporaryFile
from typing import Dict, Optional

import pandas as pd
from matplotlib import pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from faceit.faceit import Faceit
from faceit.functions import statistics2dataframe
from faceit.visualization import draw_faceit_score_history
from tg.wrapper import playgame
from utils.functions import list_get_or_throw, list_get_or_default
from utils.logging import logger


log = logger()


def savefig(fig) -> NamedTemporaryFile:
    file = NamedTemporaryFile(delete=False)
    fig.savefig(file.name, format="png")
    file.close()
    return file


class State(enum.Enum):
    IDLE = 0
    WAIT_NICKNAME = 1
    ANALYZING = 2


_history_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Date", callback_data='HISTORY_date'),
            InlineKeyboardButton("Month", callback_data='HISTORY_month'),
            InlineKeyboardButton("Index", callback_data='HISTORY_index')
        ],
    ]
)

_start_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("history", callback_data='START_HISTORY'),
        ],
    ]
)


class Job(threading.Thread):

    def __init__(self, parent: "UserContext", update: Update, nickname: str, count: int):
        super().__init__()
        self.parent = parent
        self.nickname = nickname
        self.count = count
        self.update = update
        self.message = None
        self.df: Optional[pd.DataFrame] = None
        self.view_type = "date"

    def run(self) -> None:
        player = self.parent.faceit.player(self.nickname)
        if player is None:
            self.update.message.reply_text(f"Не нашел игрока с никнеймом {self.nickname} :(")
            return

        statistics = self.parent.faceit.matches_stats(player.player_id, self.count)
        self.df = statistics2dataframe(statistics)

        fig, plot = draw_faceit_score_history(self.df, view_type="date")
        file = savefig(fig)

        plt.close(fig)

        with open(file.name, "rb") as picture:
            self.message = self.update.message.reply_photo(
                photo=picture,
                caption=self.nickname,
                reply_markup=_history_keyboard
            )

        os.unlink(file.name)

    def change_view(self, view_type: str):
        if self.df is not None and view_type != self.view_type:
            fig, plot = draw_faceit_score_history(self.df, view_type=view_type)
            file = savefig(fig)
            plt.close(fig)

            with open(file.name, "rb") as picture:
                media = InputMediaPhoto(media=picture, caption=self.nickname)
                self.message.edit_media(
                    media=media,
                    reply_markup=_history_keyboard
                )

            os.unlink(file.name)

            self.view_type = view_type

    def stop(self):
        pass


class UserContext:

    def __init__(self, telegram: "FaceitHistoryTelegramBot", faceit: Faceit):
        self.telegram = telegram
        self.faceit = faceit
        self.state = State.IDLE
        self.job: Optional[Job] = None

    def stop_analyze(self):
        pass

    def idle(self):
        self.state = State.IDLE

    def wait_nickname(self):
        self.stop_analyze()
        self.state = State.WAIT_NICKNAME

    def change_view(self, view_type: str):
        if self.job is not None:
            self.job.change_view(view_type)

    def on_message(self, update: Update):
        if self.state == State.WAIT_NICKNAME:
            tokens = update.message.text.split()
            nickname: str = list_get_or_throw(tokens, 0, f"Необходимо указать имя игрока первым аргументом")
            count: Optional[int] = list_get_or_default(tokens, 1, default=None, convert=int)
            self.start_analyze(update, nickname, count)

    def start_analyze(self, update: Update, nickname: str, count: int = 0):
        self.stop_analyze()
        self.state = State.ANALYZING

        self.job = Job(self, update, nickname, count)
        self.job.start()

        self.state = State.IDLE


class FaceitHistoryTelegramBot:

    def __init__(self, faceit_api_key: str, telegram_token: str, start_message: str):
        self.faceit = Faceit(faceit_api_key)

        self.start_message = start_message

        self.updater = Updater(telegram_token)
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(
            CommandHandler("start", lambda update, ctxt: self.start(update, ctxt))
        )

        self.dispatcher.add_handler(
            CommandHandler("history", lambda update, ctxt: self.history_command(update, ctxt)))

        self.updater.dispatcher.add_handler(
            CallbackQueryHandler(lambda update, ctxt: self.button(update, ctxt))
        )

        self.dispatcher.add_handler(
            MessageHandler(
                Filters.text & ~Filters.command,
                lambda update, ctxt: self.on_message(update, ctxt))
        )

        self.workers: Dict[str, UserContext] = dict()

    def _get_or_create_worker(self, user: str) -> UserContext:
        if user not in self.workers:
            self.workers[user] = UserContext(self, self.faceit)
        return self.workers[user]

    @playgame()
    def on_message(self, update: Update, context: CallbackContext) -> None:
        log.info(f"User {update.effective_user.username} send message '{update.message.text}'")
        worker = self._get_or_create_worker(update.effective_user.username)
        worker.on_message(update)

    @playgame()
    def start(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        self._get_or_create_worker(user.username).idle()
        log.info(f"User {user.username} execute start command")
        message = self.start_message.format(username=user.mention_markdown_v2())
        update.message.reply_markdown_v2(message, reply_markup=ForceReply(selective=True))

    @playgame()
    def button(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()

        data = query.data

        log.info(f"User {update.effective_user.username} clicked on {data}")

        if data.startswith("HISTORY_"):
            view_type = data.removeprefix("HISTORY_")
            worker = self._get_or_create_worker(update.effective_user.username)
            worker.change_view(view_type)

    @playgame()
    def history_command(self, update: Update, context: CallbackContext) -> None:
        username = update.effective_user.username
        log.info(f"User {username} execute history command")
        if not context.args:
            worker = self._get_or_create_worker(username)
            worker.wait_nickname()
            update.message.reply_text("Окей, кидай мне никнейм игрока для анализа")
        else:
            worker = self._get_or_create_worker(username)

            nickname: str = list_get_or_throw(context.args, 0, f"Необходимо указать имя игрока первым аргументом")
            count: Optional[int] = list_get_or_default(context.args, 1, default=None, convert=int)

            worker.start_analyze(update, nickname, count)

    def run(self):
        # Start the Bot
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        self.updater.idle()
