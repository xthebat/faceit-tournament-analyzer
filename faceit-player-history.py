import argparse
import os.path
import sys
from typing import List

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from faceit.faceit import Faceit
from faceit.functions import statistics2dataframe
from faceit.visualization import draw_faceit_score_history
from utils.logging import logger

log = logger()


def show_player_statistics(faceit: Faceit, nickname: str):
    player = faceit.player(nickname)
    statistics = faceit.matches_stats(player.player_id)

    df = statistics2dataframe(statistics)
    draw_faceit_score_history(df)

    plt.show()


def show_player_kda_for_elo(faceit: Faceit, nickname: str):
    player = faceit.player(nickname)
    statistics = faceit.matches_stats(player.player_id, 300)

    table = []
    for index, stats in enumerate(statistics):
        log.info(f"Get {index + 1} match details for {stats.match_id}")
        match = faceit.match(stats.match_id)
        for teammate in match.get_players_team(player):
            entry = {
                "match_id": match.match_id,
                "date": match.date,
                "nickname": teammate.nickname,
                "elo": teammate.elo,
            }
            if teammate == player:
                entry["kd"] = stats.info.kills - stats.info.deaths
            table.append(entry)

    df = pd.DataFrame(table)

    fig, ax = plt.subplots()

    for name, group in df.groupby(by=pd.Grouper(key="date", freq='Q')):
        group_elo = group.groupby(by="match_id").aggregate({"elo": np.mean}).reset_index()
        group_elo.columns = ["match_id", "mean_elo"]
        group_merged = group.dropna() \
            .merge(group_elo, on="match_id", how="outer") \
            .sort_values(by=["mean_elo"]) \
            .reset_index()

        group_merged["level"] = (group_merged["mean_elo"] / 100).round(decimals=0) * 100

        group_hist = group_merged.groupby(by="level").aggregate({"kd": np.mean}).reset_index()
        group_hist.columns = ["elo", name]

        group_hist.plot(ax=ax, x="elo", y=name)

    plt.show()


def main(argv: List[str]):
    parser = argparse.ArgumentParser(prog="faceit-player-history")
    parser.add_argument('-c', '--config', required=True, type=str, help="Path to config. file")
    parser.add_argument('-p', '--player', required=True, type=str, help="Player id")
    args = parser.parse_args(argv[1:])

    log.info(args)

    nickname = args.player.strip("\\")

    if not os.path.isfile(args.config):
        sys.exit(f"Configuration file {args.config} not found")

    faceit = Faceit()
    # show_player_statistics(faceit, nickname)
    show_player_kda_for_elo(faceit, nickname)


if __name__ == '__main__':
    # demo_test()
    main(sys.argv)
