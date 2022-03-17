from typing import Iterable, Tuple

import pandas as pd

from faceit.faceit import Game, Player, Statistic


def faceit_win_history(
        player: Player,
        games: Iterable[Game],
        mode: str = "5v5",
) -> Iterable[Tuple[Game, int]]:
    games = sorted(games, key=lambda it: it.date)
    games = filter(lambda it: it.mode == mode, games)

    for game in games:
        yield game, 1 if game.is_player_win(player) else -1


def statistics2dataframe(statistics: Iterable[Statistic]) -> pd.DataFrame:
    df = pd.DataFrame(it.__dict__ for it in statistics)
    df["elo"] = df["elo"].astype("Int64")
    df.sort_values(by="date", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df['index'] = df.index
    return df
