import operator
from typing import Dict, Union, List, Tuple

import pandas as pd


def rounds_count(round_data: pd.DataFrame, round_filters: dict = None) -> int:
    round_filters = round_filters or dict()
    return len(calc_stats(round_data, round_filters, [], [], [], round_data.columns))


def players_teams(
        df: pd.DataFrame,
        team_column: str = "attackerTeam",
        name_column: str = "attackerName"
) -> pd.DataFrame:
    teams = df[[team_column, name_column]].drop_duplicates()
    teams.columns = ["team", "Player"]
    return teams


def rounds_by_player(
        round_data: pd.DataFrame,
        teams: pd.DataFrame,
        round_filters: dict = None
) -> pd.DataFrame:
    ct_win_rounds = filter_group_aggregate(
        round_data,
        filters=round_filters,
        groupby=["ctTeam"],
        aggregate={"ctTeam": ["size"]},
        rename=["team", "ct_wins"]
    )

    t_win_rounds = filter_group_aggregate(
        round_data,
        filters=round_filters,
        groupby=["tTeam"],
        aggregate={"tTeam": ["size"]},
        rename=["team", "t_wins"]
    )

    win_rounds = ct_win_rounds.merge(t_win_rounds, how="outer").fillna(0)

    win_rounds["rounds"] = win_rounds.t_wins + win_rounds.ct_wins

    rounds_stats = teams.merge(win_rounds, on="team", how="outer")
    return rounds_stats[["Player", "rounds"]]


def calc_impact_ex(df: pd.DataFrame) -> pd.DataFrame:
    return 2.13 * df.KPR + 0.42 * df.APR - 0.41


def calc_rating_ex(df: pd.DataFrame) -> pd.DataFrame:
    return 0.73 * df.KAST / 100.0 + 0.3591 * df.KPR - 0.5329 * df.DPR + 0.2372 * df.Impact + 0.0032 * df.ADR + 0.1587


def extract_num_filters(
        filters: Dict[str, Union[List[bool], List[str]]],
        key: str
) -> Tuple[List[str], List[float]]:
    sign_list = []
    val_list = []
    for index in filters[key]:
        if not isinstance(index, str):
            raise ValueError(f'Filter(s) for column "{key}" must be of type ' f"string.")
        i = 0
        sign = ""
        while i < len(index) and not index[i].isdecimal():
            sign += index[i]
            end_index = i
            i += 1
        if sign not in ("==", "!=", "<=", ">=", "<", ">"):
            raise Exception(f'Invalid logical operator in filters for "{key}"' f" column.")
        sign_list.append(sign)
        try:
            val_list.append(float(index[end_index + 1:]))
        except ValueError as ve:
            raise Exception(f'Invalid numerical value in filters for "{key}" ' f"column.") from ve

    return sign_list, val_list


def check_filters(df: pd.DataFrame, filters: Dict[str, Union[List[bool], List[str]]]):
    for key in filters:
        if df.dtypes[key] == "bool":
            for index in filters[key]:
                if not isinstance(index, bool):
                    raise ValueError(f'Filter(s) for column "{key}" must be ' f"of type boolean")
        elif df.dtypes[key] == "O":
            for index in filters[key]:
                if not isinstance(index, str):
                    raise ValueError(f'Filter(s) for column "{key}" must be ' f"of type string")
        else:
            extract_num_filters(filters, key)


def num_filter_df(df: pd.DataFrame, col: str, sign: str, val: float) -> pd.DataFrame:
    ops = {
        "==": operator.eq(df[col], val),
        "!=": operator.ne(df[col], val),
        "<=": operator.le(df[col], val),
        ">=": operator.ge(df[col], val),
        "<": operator.lt(df[col], val),
        ">": operator.gt(df[col], val),
    }
    filtered_df = df.loc[ops[sign]]
    return filtered_df


def filter_df(df: pd.DataFrame, filters: Dict[str, Union[List[bool], List[str]]]) -> pd.DataFrame:
    df_copy = df.copy()
    check_filters(df_copy, filters)
    for key in filters:
        if df_copy.dtypes[key] == "bool" or df_copy.dtypes[key] == "O":
            df_copy = df_copy.loc[df_copy[key].isin(filters[key])]
        else:
            for i, sign in enumerate(extract_num_filters(filters, key)[0]):
                val = extract_num_filters(filters, key)[1][i]
                df_copy = num_filter_df(df_copy, key, extract_num_filters(filters, key)[0][i], val)
    return df_copy


def filter_group_aggregate(
        df: pd.DataFrame,
        filters: Dict[str, Union[List[bool], List[str]]] = None,
        groupby: List[str] = None,
        aggregate: Dict[str, List[str]] = None,
        rename: List[str] = None,
) -> pd.DataFrame:
    filtered = filter_df(df, filters)
    if aggregate is not None:
        assert groupby is not None
        filtered = filtered \
            .groupby(groupby) \
            .agg(aggregate) \
            .reset_index()
    if rename is not None:
        filtered.columns = rename
    return filtered


def calc_stats(
        df: pd.DataFrame,
        filters: Dict[str, Union[List[bool], List[str]]],
        col_to_groupby: List[str],
        col_to_agg: List[str],
        agg: List[List[str]],
        col_names: List[str],
) -> pd.DataFrame:
    df_copy = filter_df(df, filters)
    agg_dict = dict(zip(col_to_agg, agg))
    if col_to_agg:
        df_copy = df_copy.groupby(col_to_groupby).agg(agg_dict).reset_index()
    df_copy.columns = col_names
    return df_copy
