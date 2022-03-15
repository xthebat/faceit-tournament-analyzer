from typing import Tuple

import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn'


def clear_rounds(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    df = df.loc[df.winningTeam.notna()]
    df.reset_index(inplace=True, drop=True)

    start_idx = ((df.tScore == 0) & (df.ctScore == 0)).idxmin() - 1

    offset = df.roundNum[start_idx] - 1

    df = df[start_idx:]

    df.roundNum = df.roundNum - offset

    df.reset_index(inplace=True, drop=True)
    df.sort_values(by="roundNum", ascending=True, inplace=True)

    return offset, df


def clear_data(df: pd.DataFrame, offset: int, rounds: pd.DataFrame) -> pd.DataFrame:
    if "attackerName" in df:
        df = df.loc[df.attackerName.notna()]

    df.roundNum = df.roundNum - offset

    df = df[df.roundNum.isin(rounds.roundNum)]
    df.reset_index(inplace=True, drop=True)

    return df
