import argparse
import json
import os.path
import sys
from typing import List

from matplotlib import pyplot as plt

from faceit.faceit import Faceit
from faceit.functions import statistics2dataframe
from faceit.visualization import draw_faceit_score_history
from utils.logging import logger


log = logger()


def main(argv: List[str]):
    parser = argparse.ArgumentParser(prog="faceit-player-history")
    parser.add_argument('-c', '--config', required=True, type=str, help="Path to config. file")
    parser.add_argument('-p', '--player', required=True, type=str, help="Player id")
    args = parser.parse_args(argv[1:])

    log.info(args)

    args.player = args.player.strip("\\")
    nickname = args.player

    if not os.path.isfile(args.config):
        sys.exit(f"Configuration file {args.config} not found")

    with open(args.config, "rt") as file:
        config_data = json.loads(file.read())

    apikey = config_data["apikey"]

    faceit = Faceit(apikey)

    player = faceit.player(nickname)
    statistics = faceit.matches_stats(player.player_id)

    df = statistics2dataframe(statistics)
    draw_faceit_score_history(df)

    plt.show()


if __name__ == '__main__':
    # demo_test()
    main(sys.argv)
