from typing import Iterable

import pandas as pd

from faceit.faceit import Statistic


def statistics2dataframe(statistics: Iterable[Statistic]) -> pd.DataFrame:
    df = pd.DataFrame(it.__dict__ for it in statistics)
    df["elo"] = df["elo"].astype("Int64")
    df.sort_values(by="date", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df['index'] = df.index
    return df
