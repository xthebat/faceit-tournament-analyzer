from typing import Iterable, Optional

import pandas as pd

from faceit.faceit import Player, Game
from faceit.functions import faceit_win_history


def calc_faceit_score_history(player: Player, games: Iterable[Game]) -> pd.DataFrame:
    df = pd.DataFrame((index, game.date, elo) for index, (game, elo) in enumerate(faceit_win_history(player, games)))
    df.columns = ["Index", "Date", "Score"]
    df["Score"] = df["Score"].cumsum()
    return df
