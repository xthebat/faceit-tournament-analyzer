import argparse
import json
import logging
import os
import sys
from typing import List

import matplotlib

from tg.bot import FaceitHistoryTelegramBot
from utils.logging import logger, set_log_file


matplotlib.use('Agg')


log = logger()


def main(argv: List[str]):
    parser = argparse.ArgumentParser(prog="faceit-tournament-analyzer", description='Facet tournament analyzer')
    parser.add_argument('-c', '--config', required=True, type=str, help="Path to config. file")
    parser.add_argument('-l', '--logfile', type=str, default=None, help="Path to log file")
    args = parser.parse_args(argv[1:])

    log.info(args)

    if not os.path.isfile(args.config):
        sys.exit(f"Configuration file {args.config} not found")

    with open(args.config, "rt") as file:
        config_data = json.loads(file.read())

    if args.logfile is not None:
        set_log_file(args.logfile, logging.DEBUG)

    apikey = config_data["apikey"]
    telegram_token = config_data["telegram_token"]
    start_message = config_data["start_message"]

    telegram_bot = FaceitHistoryTelegramBot(apikey, telegram_token, start_message)

    telegram_bot.run()


if __name__ == '__main__':
    main(sys.argv)
