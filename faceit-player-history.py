import argparse
import json
import os.path
import sys
from datetime import datetime
from typing import List

from dateutil.relativedelta import relativedelta
from matplotlib import pyplot as plt

from faceit.faceit import Faceit


def main(argv: List[str]):
    parser = argparse.ArgumentParser(prog="faceit-tournament-analyzer", description='Facet tournament analyzer')
    parser.add_argument('-c', '--config', required=True, type=str, help="Path to config. file")
    parser.add_argument('-p', '--player', required=True, type=str, help="Player id")
    args = parser.parse_args(argv[1:])

    print(args)

    if not os.path.isfile(args.config):
        sys.exit(f"Configuration file {args.config} not found")

    with open(args.config, "rt") as file:
        config_data = json.loads(file.read())

    apikey = config_data["apikey"]

    faceit = Faceit(apikey)

    player = faceit.player(args.player)

    games = list(faceit.player_games(player.player_id))
    games.sort(key=lambda it: it.date)
    mm = filter(lambda it: it.mode == "5v5", games)
    history = [1000]
    elo = 1000
    for game in mm:
        if game.is_player_win(player):
            elo += 25
        else:
            elo -= 25
        history.append(elo)

    plt.plot(history)
    plt.show()


if __name__ == '__main__':
    # demo_test()
    main(sys.argv)
