# Helper functions for calc_stats()
# based on https://github.com/pnxenopoulos/awpy/blob/main/examples/01_Basic_CSGO_Analysis.ipynb

from typing import List, Dict, Union

import pandas as pd

from demo.functions import filter_df, filter_group_aggregate, rounds_by_player, players_teams, \
    calc_impact_ex, calc_rating_ex


def calc_accuracy(
        damage_data: pd.DataFrame,
        weapon_fire_data: pd.DataFrame,
        team: bool = False,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    damage_filters = damage_filters or dict()
    weapon_fire_filters = weapon_fire_filters or dict()
    stats = ["playerName", "attackerName", "Player"]
    if team:
        stats = ["playerTeam", "attackerTeam", "Team"]
    weapon_fires = filter_group_aggregate(
        weapon_fire_data,
        filters=weapon_fire_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[2], "Weapon Fires"],
    )
    strafe_fires = filter_group_aggregate(
        weapon_fire_data.loc[weapon_fire_data["playerStrafe"] == True],
        filters=weapon_fire_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[2], "Strafe Fires"],
    )
    hits = filter_group_aggregate(
        damage_data.loc[damage_data["attackerTeam"] != damage_data["victimTeam"]],
        filters=damage_filters,
        groupby=[stats[1]],
        aggregate={stats[1]: ["size"]},
        rename=[stats[2], "Hits"],
    )

    headshots_filter = \
        (damage_data["attackerTeam"] != damage_data["victimTeam"]) & \
        (damage_data["hitGroup"] == "Head")
    headshots = filter_group_aggregate(
        damage_data.loc[headshots_filter],
        filters=damage_filters,
        groupby=[stats[1]],
        aggregate={stats[1]: ["size"]},
        rename=[stats[2], "Headshots"],
    )

    acc = weapon_fires.merge(strafe_fires, how="outer").fillna(0)
    acc = acc.merge(hits, how="outer").fillna(0)
    acc = acc.merge(headshots, how="outer").fillna(0)
    acc["Strafe%"] = acc["Strafe Fires"] / acc["Weapon Fires"] * 100.0
    acc["ACC%"] = acc["Hits"] / acc["Weapon Fires"] * 100.0
    acc["HS ACC%"] = acc["Headshots"] / acc["Weapon Fires"] * 100.0
    acc = acc[[stats[2], "Weapon Fires", "Strafe%", "ACC%", "HS ACC%"]]
    acc.sort_values(by="ACC%", ascending=False, inplace=True)
    acc.reset_index(drop=True, inplace=True)
    return acc


def calc_kast(
        kill_data: pd.DataFrame,
        kast_string: str = "KAST",
        flash_assists: bool = True,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
        death_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    kill_filters = kill_filters or dict()
    death_filters = death_filters or dict()

    columns = ["Player", f"{kast_string.upper()}%"]
    kast_counts = dict()
    kast_rounds = dict()

    columns.extend(list(kast_string.upper()))

    killers = filter_group_aggregate(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=["roundNum"],
        aggregate={"attackerName": ["sum"]},
        rename=["RoundNum", "Killers"],
    )
    victims = filter_group_aggregate(
        kill_data,
        filters=kill_filters,
        groupby=["roundNum"],
        aggregate={"victimName": ["sum"]},
        rename=["RoundNum", "Victims"],
    )
    assisters = filter_group_aggregate(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]].fillna(""),
        filters=kill_filters,
        groupby=["roundNum"],
        aggregate={"assisterName": ["sum"]},
        rename=["RoundNum", "Assisters"],
    )
    traded = filter_group_aggregate(
        kill_data.loc[
            (kill_data["attackerTeam"] != kill_data["victimTeam"])
            & (kill_data["isTrade"] == True)
            ].fillna(""),
        filters=kill_filters,
        groupby=["roundNum"],
        aggregate={"playerTradedName": ["sum"]},
        rename=["RoundNum", "Traded"],
    )
    if flash_assists:
        flash_assisters_filter = kill_data["flashThrowerTeam"] != kill_data["victimTeam"]
        flash_assisters = filter_group_aggregate(
            kill_data.loc[flash_assisters_filter].fillna(""),
            filters=kill_filters,
            groupby=["roundNum"],
            aggregate={"flashThrowerName": ["sum"]},
            rename=["RoundNum", "Flash Assisters"],
        )
        assisters = assisters.merge(flash_assisters, on="RoundNum")
        assisters["Assisters"] = assisters["Assisters"] + assisters["Flash Assisters"]
        assisters = assisters[["RoundNum", "Assisters"]]
    kast_data = killers.merge(assisters, how="outer").fillna("")
    kast_data = kast_data.merge(victims, how="outer").fillna("")
    kast_data = kast_data.merge(traded, how="outer").fillna("")
    for player in kill_data["attackerName"].unique():
        kast_counts[player] = [[0, 0, 0, 0] for i in range(len(kast_data))]
        kast_rounds[player] = [0, 0, 0, 0, 0]
    for rd in kast_data.index:
        for player in kast_counts:
            if "K" in kast_string.upper():
                kast_counts[player][rd][0] = kast_data.iloc[rd]["Killers"].count(player)
                kast_rounds[player][1] += kast_data.iloc[rd]["Killers"].count(player)
            if "A" in kast_string.upper():
                kast_counts[player][rd][1] = kast_data.iloc[rd]["Assisters"].count(player)
                kast_rounds[player][2] += kast_data.iloc[rd]["Assisters"].count(player)
            if "S" in kast_string.upper():
                if player not in kast_data.iloc[rd]["Victims"]:
                    kast_counts[player][rd][2] = 1
                    kast_rounds[player][3] += 1
            if "T" in kast_string.upper():
                kast_counts[player][rd][3] = kast_data.iloc[rd]["Traded"].count(player)
                kast_rounds[player][4] += kast_data.iloc[rd]["Traded"].count(player)
    for player in kast_rounds:
        for rd in kast_counts[player]:
            if any(rd):
                kast_rounds[player][0] += 1
        kast_rounds[player][0] /= len(kast_data)
    kast = pd.DataFrame.from_dict(kast_rounds, orient="index").reset_index()
    kast.columns = ["Player", f"{kast_string.upper()}%", "K", "A", "S", "T"]
    kast = kast[columns]
    kast[f"{kast_string.upper()}%"] = kast[f"{kast_string.upper()}%"] * 100.0
    kast.fillna(0, inplace=True)
    kast.sort_values(by=f"{kast_string.upper()}%", ascending=False, inplace=True)
    kast.reset_index(drop=True, inplace=True)
    return kast


def calc_kill_stats(
        damage_data: pd.DataFrame,
        kill_data: pd.DataFrame,
        round_data: pd.DataFrame,
        weapon_fire_data: pd.DataFrame,
        team: bool = False,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
        death_filters: Dict[str, Union[List[bool], List[str]]] = None,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
        weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    damage_filters = damage_filters or dict()
    kill_filters = kill_filters or dict()
    death_filters = death_filters or dict()
    round_filters = round_filters or dict()
    weapon_fire_filters = weapon_fire_filters or dict()

    if not team:
        stats = [
            "attackerName",
            "victimName",
            "assisterName",
            "flashThrowerName",
            "Player"
        ]
    else:
        stats = [
            "attackerTeam",
            "victimTeam",
            "assisterTeam",
            "flashThrowerTeam",
            "Team",
        ]

    kills = filter_group_aggregate(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[4], "K"],
    )

    deaths = filter_group_aggregate(
        kill_data,
        filters=death_filters,
        groupby=[stats[1]],
        aggregate={stats[1]: ["size"]},
        rename=[stats[4], "D"],
    )

    assists = filter_group_aggregate(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats[2]],
        aggregate={stats[2]: ["size"]},
        rename=[stats[4], "A"],
    )

    flash_assists = filter_group_aggregate(
        kill_data.loc[kill_data["flashThrowerTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats[3]],
        aggregate={stats[3]: ["size"]},
        rename=[stats[4], "FA"],
    )

    first_kills_filter = \
        (kill_data["attackerTeam"] != kill_data["victimTeam"]) & \
        (kill_data["isFirstKill"] == True)
    first_kills = filter_group_aggregate(
        kill_data.loc[first_kills_filter],
        filters=kill_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[4], "FK"],
    )

    first_deaths_filter = \
        (kill_data["attackerTeam"] != kill_data["victimTeam"]) & \
        (kill_data["isFirstKill"] == True)
    first_deaths = filter_group_aggregate(
        kill_data.loc[first_deaths_filter],
        filters=kill_filters,
        groupby=[stats[1]],
        aggregate={stats[1]: ["size"]},
        rename=[stats[4], "FD"],
    )

    headshots_filter = \
        (kill_data["attackerTeam"] != kill_data["victimTeam"]) & \
        (kill_data["isHeadshot"] == True)
    headshots = filter_group_aggregate(
        kill_data.loc[headshots_filter],
        filters=kill_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[4], "HS"],
    )

    headshot_pct = filter_group_aggregate(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats[0]],
        aggregate={"isHeadshot": ["mean"]},
        rename=[stats[4], "HS%"],
    )

    acc_stats = calc_accuracy(damage_data, weapon_fire_data, team, damage_filters, weapon_fire_filters)

    kast_stats = calc_kast(
        kill_data,
        "KAST",
        flash_assists=True,
        kill_filters=kill_filters,
        death_filters=death_filters)

    teams = players_teams(damage_data)
    rounds = rounds_by_player(round_data, teams, round_filters)

    kill_stats = kills.merge(deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(rounds, on="Player", how="outer").fillna(0)
    kill_stats = kill_stats.merge(assists, how="outer").fillna(0)
    kill_stats = kill_stats.merge(flash_assists, how="outer").fillna(0)
    kill_stats = kill_stats.merge(first_kills, how="outer").fillna(0)
    kill_stats = kill_stats.merge(first_deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(headshots, how="outer").fillna(0)
    kill_stats = kill_stats.merge(headshot_pct, how="outer").fillna(0)
    kill_stats = kill_stats.merge(acc_stats, how="outer").fillna(0)

    if not team:
        # TODO: calc algorithm different for kast_stats and kill_stats
        kast_only = kast_stats[["Player", "KAST%", "T", "S"]]
        kill_stats = kill_stats.merge(kast_only, how="outer").fillna(0)

    kill_stats["+/-"] = kill_stats["K"] - kill_stats["D"]
    kill_stats["KDR"] = kill_stats["K"] / kill_stats["D"]
    kill_stats["KPR"] = kill_stats["K"] / kill_stats["rounds"]
    kill_stats["FK +/-"] = kill_stats["FK"] - kill_stats["FD"]
    int_stats = ["K", "D", "A", "FA", "+/-", "FK", "FK +/-", "HS", "T"]
    if team:
        int_stats = int_stats[0:-1]
    kill_stats[int_stats] = kill_stats[int_stats].astype(int)
    kill_stats["HS%"] = kill_stats["HS%"].astype(float) * 100.0
    order = [
        stats[4],
        "K",
        "D",
        "A",
        "FA",
        "+/-",
        "FK",
        "FK +/-",
        "T",
        "HS",
        "HS%",
        "ACC%",
        "HS ACC%",
        "KDR",
        "KPR",
        "KAST%",
    ]
    if team:
        order = order[0:8] + order[9:-1]
    kill_stats = kill_stats[order]
    kill_stats.sort_values(by="K", ascending=False, inplace=True)
    kill_stats.reset_index(drop=True, inplace=True)
    return kill_stats


def calc_adr(
        damage_data: pd.DataFrame,
        round_data: pd.DataFrame,
        team: bool = False,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    damage_filters = damage_filters or dict()
    round_filters = round_filters or dict()

    stats = ["attackerName", "Player"] if not team else ["attackerTeam", "Team"]

    adr_stats = filter_group_aggregate(
        damage_data.loc[damage_data["attackerTeam"] != damage_data["victimTeam"]],
        filters=damage_filters,
        groupby=[stats[0]],
        aggregate={"hpDamageTaken": ["sum"], "hpDamage": ["sum"]},
        rename=[stats[1], "Norm ADR", "Raw ADR"],
    )

    teams = players_teams(damage_data)
    rounds = rounds_by_player(round_data, teams, round_filters)

    adr_stats = adr_stats.merge(rounds, on="Player", how="outer")

    adr_stats["Norm ADR"] = adr_stats["Norm ADR"] / adr_stats["rounds"]
    adr_stats["Raw ADR"] = adr_stats["Raw ADR"] / adr_stats["rounds"]

    adr_stats.sort_values(by="Norm ADR", ascending=False, inplace=True)
    adr_stats.reset_index(drop=True, inplace=True)
    return adr_stats


def calc_rating(
        damage_data: pd.DataFrame,
        kill_data: pd.DataFrame,
        round_data: pd.DataFrame,
        kast_string: str = "KAST",
        flash_assists: bool = True,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        death_filters: Dict[str, Union[List[bool], List[str]]] = None,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    """Returns a dataframe with an HLTV-esque rating, found by doing:

    Rating = 0.0073*KAST + 0.3591*KPR + -0.5329*DPR + 0.2372*Impact + 0.0032*ADR + 0.1587
    where Impact = 2.13*KPR + 0.42*Assist per Round -0.41

    https://flashed.gg/posts/reverse-engineering-hltv-rating/

    Args:
        damage_data: A dataframe with damage data.
        kill_data: A dataframe with damage data.
        round_data: A dataframe with round data.
        kast_string: A string specifying which combination of KAST statistics
            to use.
        flash_assists: A boolean specifying if flash assists are to be
            counted as assists or not.
        damage_filters: A dictionary where the keys are the columns of the
            dataframe represented by damage_data to filter the damage data by
            and the values are lists that contain the column filters.
        death_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the death data by and
            the values are lists that contain the column filters.
        kill_filters: A dictionary where the keys are the columns of the
            dataframe represented by kill_data to filter the kill data by and
            the values are lists that contain the column filters.
        round_filters: A dictionary where the keys are the columns of the
            dataframe represented by round_data to filter the round data by and
            the values are lists that contain the column filters.
    """
    damage_filters = damage_filters or dict()
    death_filters = death_filters or dict()
    kill_filters = kill_filters or dict()
    round_filters = round_filters or dict()

    stats_kills = ["attackerName", "victimName", "assisterName", "flashThrowerName", "Player"]

    kast_stats = calc_kast(kill_data, "KAST", True, kill_filters, death_filters)
    kast_stats = kast_stats[["Player", "KAST%"]]
    kast_stats.columns = ["Player", "KAST"]

    adr_stats = calc_adr(damage_data, round_data, False, damage_filters, round_filters)
    adr_stats = adr_stats[["Player", "Norm ADR"]]
    adr_stats.columns = ["Player", "ADR"]
    stats = ["attackerName", "Player"]

    kills = filter_group_aggregate(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats_kills[0]],
        aggregate={stats_kills[0]: ["size"]},
        rename=[stats_kills[4], "K"],
    )
    deaths = filter_group_aggregate(
        kill_data,
        filters=death_filters,
        groupby=[stats_kills[1]],
        aggregate={stats_kills[1]: ["size"]},
        rename=[stats_kills[4], "D"],
    )
    assists = filter_group_aggregate(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats_kills[2]],
        aggregate={stats_kills[2]: ["size"]},
        rename=[stats_kills[4], "A"],
    )

    teams = players_teams(damage_data)
    rounds = rounds_by_player(round_data, teams, round_filters)

    kill_stats = kills.merge(deaths, how="outer").fillna(0)
    kill_stats = kill_stats.merge(assists, how="outer").fillna(0)
    kill_stats = kill_stats.merge(rounds, on="Player", how="outer").fillna(0)

    kill_stats["KPR"] = kill_stats["K"] / kill_stats["rounds"]
    kill_stats["DPR"] = kill_stats["D"] / kill_stats["rounds"]
    kill_stats["APR"] = kill_stats["A"] / kill_stats["rounds"]

    kill_stats = kill_stats[["Player", "KPR", "DPR", "APR"]]
    kill_stats = kill_stats.merge(adr_stats, how="outer").fillna(0)
    kill_stats = kill_stats.merge(kast_stats, how="outer").fillna(0)

    kill_stats["Impact"] = calc_impact_ex(kill_stats)
    kill_stats["Rating"] = calc_rating_ex(kill_stats)

    kill_stats = kill_stats[["Player", "Impact", "Rating"]]

    kill_stats.sort_values(by="Rating", ascending=False, inplace=True)
    kill_stats.reset_index(drop=True, inplace=True)
    return kill_stats


def calc_util_dmg(
        damage_data: pd.DataFrame,
        grenade_data: pd.DataFrame,
        team: bool = False,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        grenade_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    damage_filters = damage_filters or dict()
    grenade_filters = grenade_filters or dict()

    stats = ["attackerName", "throwerName", "Player"] if not team \
        else ["attackerTeam", "throwerTeam", "Team"]

    damage_data_filter = \
        (damage_data["attackerTeam"] != damage_data["victimTeam"]) & \
        (damage_data["weapon"].isin(["HE Grenade", "Incendiary Grenade", "Molotov"]))
    util_dmg = filter_group_aggregate(
        damage_data.loc[damage_data_filter],
        filters=damage_filters,
        groupby=[stats[0]],
        aggregate={"hpDamageTaken": ["sum"], "hpDamage": ["sum"]},
        rename=[stats[2], "Given UD", "UD"],
    )

    nades_thrown_filter = grenade_data["grenadeType"].isin(["HE Grenade", "Incendiary Grenade", "Molotov"])
    nades_thrown = filter_group_aggregate(
        grenade_data.loc[nades_thrown_filter],
        filters=grenade_filters,
        groupby=[stats[1]],
        aggregate={stats[1]: ["size"]},
        rename=[stats[2], "Nades Thrown"],
    )
    util_dmg_stats = util_dmg.merge(nades_thrown, how="outer").fillna(0)
    util_dmg_stats["Given UD Per Nade"] = (
            util_dmg_stats["Given UD"] / util_dmg_stats["Nades Thrown"]
    )
    util_dmg_stats["UD Per Nade"] = (
            util_dmg_stats["UD"] / util_dmg_stats["Nades Thrown"]
    )
    util_dmg_stats.sort_values(by="Given UD", ascending=False, inplace=True)
    util_dmg_stats.reset_index(drop=True, inplace=True)
    return util_dmg_stats


def calc_flash_stats(
        flash_data: pd.DataFrame,
        grenade_data: pd.DataFrame,
        kill_data: pd.DataFrame,
        team: bool = False,
        flash_filters: Dict[str, Union[List[bool], List[str]]] = None,
        grenade_filters: Dict[str, Union[List[bool], List[str]]] = None,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    flash_filters = flash_filters or dict()
    grenade_filters = grenade_filters or dict()
    kill_filters = kill_filters or dict()

    stats = ["attackerName", "flashThrowerName", "throwerName", "Player"] if not team \
        else ["attackerTeam", "flashThrowerTeam", "throwerTeam", "Team"]

    enemy_flashes = filter_group_aggregate(
        flash_data.loc[flash_data["attackerTeam"] != flash_data["playerTeam"]],
        filters=flash_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[3], "EF"],
    )
    flash_assists = filter_group_aggregate(
        kill_data.loc[kill_data["flashThrowerTeam"] != kill_data["victimTeam"]],
        filters=kill_filters,
        groupby=[stats[1]],
        aggregate={stats[1]: ["size"]},
        rename=[stats[3], "FA"],
    )
    blind_time = filter_group_aggregate(
        flash_data.loc[flash_data["attackerTeam"] != flash_data["playerTeam"]],
        filters=flash_filters,
        groupby=[stats[0]],
        aggregate={"flashDuration": ["sum"]},
        rename=[stats[3], "EBT"],
    )
    team_flashes = filter_group_aggregate(
        flash_data.loc[flash_data["attackerTeam"] == flash_data["playerTeam"]],
        filters=flash_filters,
        groupby=[stats[0]],
        aggregate={stats[0]: ["size"]},
        rename=[stats[3], "TF"],
    )
    flashes_thrown = filter_group_aggregate(
        grenade_data.loc[grenade_data["grenadeType"] == "Flashbang"],
        filters=flash_filters,
        groupby=[stats[2]],
        aggregate={stats[2]: ["size"]},
        rename=[stats[3], "Flashes Thrown"],
    )
    flash_stats = enemy_flashes.merge(flash_assists, how="outer").fillna(0)
    flash_stats = flash_stats.merge(blind_time, how="outer").fillna(0)
    flash_stats = flash_stats.merge(team_flashes, how="outer").fillna(0)
    flash_stats = flash_stats.merge(flashes_thrown, how="outer").fillna(0)
    flash_stats["EF Per Throw"] = flash_stats["EF"] / flash_stats["Flashes Thrown"]
    flash_stats["EBT Per Enemy"] = flash_stats["EBT"] / flash_stats["EF"]
    flash_stats["FA"] = flash_stats["FA"].astype(int)
    flash_stats.sort_values(by="EF", ascending=False, inplace=True)
    flash_stats.reset_index(drop=True, inplace=True)
    return flash_stats


def calc_bomb_stats(
        bomb_data: pd.DataFrame,
        bomb_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    bomb_filters = bomb_filters or dict()
    team_one = bomb_data["playerTeam"].unique()[0]
    team_two = bomb_data["playerTeam"].unique()[1]
    team_one_plants = filter_group_aggregate(
        bomb_data.loc[(bomb_data["bombAction"] == "plant") & (bomb_data["playerTeam"] == team_one)],
        filters=bomb_filters,
        groupby=["bombSite"],
        aggregate={"bombSite": ["size"]},
        rename=["Bombsite", f"{team_one} Plants"],
    )
    team_two_plants = filter_group_aggregate(
        bomb_data.loc[(bomb_data["bombAction"] == "plant") & (bomb_data["playerTeam"] == team_two)],
        filters=bomb_filters,
        groupby=["bombSite"],
        aggregate={"bombSite": ["size"]},
        rename=["Bombsite", f"{team_two} Plants"],
    )
    team_one_defuses = filter_group_aggregate(
        bomb_data.loc[(bomb_data["bombAction"] == "defuse") & (bomb_data["playerTeam"] == team_one)],
        filters=bomb_filters,
        groupby=["bombSite"],
        aggregate={"bombSite": ["size"]},
        rename=["Bombsite", f"{team_one} Defuses"],
    )
    team_two_defuses = filter_group_aggregate(
        bomb_data.loc[(bomb_data["bombAction"] == "defuse") & (bomb_data["playerTeam"] == team_two)],
        filters=bomb_filters,
        groupby=["bombSite"],
        aggregate={"bombSite": ["size"]},
        rename=["Bombsite", f"{team_two} Defuses"],
    )
    bomb_stats = team_one_plants.merge(team_two_defuses, how="outer").fillna(0)
    bomb_stats[f"{team_two} Defuse %"] = (
            bomb_stats[f"{team_two} Defuses"] / bomb_stats[f"{team_one} Plants"]
    )
    bomb_stats = bomb_stats.merge(team_two_plants, how="outer").fillna(0)
    bomb_stats = bomb_stats.merge(team_one_defuses, how="outer").fillna(0)
    bomb_stats[f"{team_one} Defuse %"] = (
            bomb_stats[f"{team_one} Defuses"] / bomb_stats[f"{team_two} Plants"]
    )
    bomb_stats.loc[2] = [
        "A and B",
        bomb_stats[f"{team_one} Plants"].sum(),
        bomb_stats[f"{team_two} Defuses"].sum(),
        (
                bomb_stats[f"{team_two} Defuses"].sum()
                / bomb_stats[f"{team_one} Plants"].sum()
        ),
        bomb_stats[f"{team_two} Plants"].sum(),
        bomb_stats[f"{team_one} Defuses"].sum(),
        (
                bomb_stats[f"{team_one} Defuses"].sum()
                / bomb_stats[f"{team_two} Plants"].sum()
        ),
    ]
    bomb_stats.fillna(0, inplace=True)
    bomb_stats.iloc[:, [1, 2, 4, 5]] = bomb_stats.iloc[:, [1, 2, 4, 5]].astype(int)
    return bomb_stats


def calc_econ_stats(
        round_data: pd.DataFrame,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    round_filters = round_filters or dict()
    ct_stats = filter_group_aggregate(
        round_data,
        filters=round_filters,
        groupby=["ctTeam"],
        aggregate={"ctStartEqVal": ["mean"], "ctRoundStartMoney": ["mean"], "ctSpend": ["mean"]},
        rename=["Side", "Avg EQ Value", "Avg Cash", "Avg Spend"],
    )
    ct_stats["Side"] = ct_stats["Side"] + " CT"
    ct_buys = filter_group_aggregate(
        round_data,
        filters=round_filters,
        groupby=["ctTeam", "ctBuyType"],
        aggregate={"ctBuyType": ["size"]},
        rename=["Side", "Buy Type", "Counts"],
    )
    ct_buys = ct_buys.pivot(index="Side", columns="Buy Type", values="Counts")
    ct_buys.reset_index(inplace=True)
    ct_buys.rename_axis(None, axis=1, inplace=True)
    ct_buys["Side"] = ct_buys["Side"] + " CT"
    t_stats = filter_group_aggregate(
        round_data,
        filters=round_filters,
        groupby=["tTeam"],
        aggregate={"tStartEqVal": ["mean"], "tRoundStartMoney": ["mean"], "tSpend": ["mean"]},
        rename=["Side", "Avg EQ Value", "Avg Cash", "Avg Spend"],
    )
    t_stats["Side"] = t_stats["Side"] + " T"
    t_buys = filter_group_aggregate(
        round_data,
        filters=round_filters,
        groupby=["tTeam", "tBuyType"],
        aggregate={"tBuyType": ["size"]},
        rename=["Side", "Buy Type", "Counts"],
    )
    t_buys = t_buys.pivot(index="Side", columns="Buy Type", values="Counts")
    t_buys.reset_index(inplace=True)
    t_buys.rename_axis(None, axis=1, inplace=True)
    t_buys["Side"] = t_buys["Side"] + " T"
    econ_buys = ct_buys.append(t_buys)
    econ_stats = ct_stats.append(t_stats)
    econ_stats = econ_buys.merge(econ_stats, how="outer")
    econ_stats.fillna(0, inplace=True)
    econ_stats.iloc[:, 1:] = econ_stats.iloc[:, 1:].astype(int)
    return econ_stats


# Helper function for kill_breakdown()
def calc_weapon_type(weapon: str) -> str:
    if weapon in ["Knife"]:
        return "Melee Kills"
    elif weapon in [
        "CZ-75 Auto",
        "Desert Eagle",
        "Dual Berettas",
        "Five-SeveN",
        "Glock-18",
        "P2000",
        "P250",
        "R8 Revolver",
        "Tec-9",
        "USP-S",
    ]:
        return "Pistol Kills"
    elif weapon in ["MAG-7", "Nova", "Sawed-Off", "XM1014"]:
        return "Shotgun Kills"
    elif weapon in ["MAC-10", "MP5-SD", "MP7", "MP9", "P90", "PP-Bizon", "UMP-45"]:
        return "SMG Kills"
    elif weapon in ["AK-47", "AUG", "FAMAS", "Galil AR", "M4A1-S", "M4A4", "SG 553"]:
        return "Assault Rifle Kills"
    elif weapon in ["M249", "Negev"]:
        return "Machine Gun Kills"
    elif weapon in ["AWP", "G3SG1", "SCAR-20", "SSG 08"]:
        return "Sniper Rifle Kills"
    else:
        return "Utility Kills"


def calc_kill_breakdown(
        kill_data: pd.DataFrame,
        team: bool = False,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    kill_filters = kill_filters or dict()
    stats = ["attackerName", "Player"]
    if team:
        stats = ["attackerTeam", "Team"]
    kill_breakdown = kill_data.loc[
        kill_data["attackerTeam"] != kill_data["victimTeam"]
        ].copy()
    kill_breakdown["Kills Type"] = kill_breakdown.apply(
        lambda row: calc_weapon_type(row["weapon"]), axis=1
    )
    kill_breakdown = filter_group_aggregate(
        kill_breakdown,
        filters=kill_filters,
        groupby=[stats[0], "Kills Type"],
        aggregate={stats[0]: ["size"]},
        rename=[stats[1], "Kills Type", "Kills"],
    )
    kill_breakdown = kill_breakdown.pivot(
        index=stats[1], columns="Kills Type", values="Kills"
    )
    for col in [
        "Melee Kills",
        "Pistol Kills",
        "Shotgun Kills",
        "SMG Kills",
        "Assault Rifle Kills",
        "Machine Gun Kills",
        "Sniper Rifle Kills",
        "Utility Kills",
    ]:
        if not col in kill_breakdown.columns:
            kill_breakdown.insert(0, col, 0)
        kill_breakdown[col].fillna(0, inplace=True)
        kill_breakdown[col] = kill_breakdown[col].astype(int)
    kill_breakdown["Total Kills"] = kill_breakdown.iloc[0:].sum(axis=1)
    kill_breakdown.reset_index(inplace=True)
    kill_breakdown.rename_axis(None, axis=1, inplace=True)
    kill_breakdown = kill_breakdown[
        [
            stats[1],
            "Melee Kills",
            "Pistol Kills",
            "Shotgun Kills",
            "SMG Kills",
            "Assault Rifle Kills",
            "Machine Gun Kills",
            "Sniper Rifle Kills",
            "Utility Kills",
            "Total Kills",
        ]
    ]
    kill_breakdown.sort_values(by="Total Kills", ascending=False, inplace=True)
    kill_breakdown.reset_index(drop=True, inplace=True)
    return kill_breakdown


def calc_util_dmg_breakdown(
        damage_data: pd.DataFrame,
        grenade_data: pd.DataFrame,
        team: bool = False,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        grenade_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    damage_filters = damage_filters or dict()
    grenade_filters = grenade_filters or dict()

    stats = ["attackerName", "throwerName", "Player"] if not team else ["attackerTeam", "throwerTeam", "Team"]

    utils_dms_filter = \
        (damage_data["attackerTeam"] != damage_data["victimTeam"]) & \
        (damage_data["weapon"].isin(["HE Grenade", "Incendiary Grenade", "Molotov"]))
    util_dmg = filter_group_aggregate(
        damage_data.loc[utils_dms_filter],
        filters=damage_filters,
        groupby=[stats[0], "weapon"],
        aggregate={"hpDamageTaken": ["sum"], "hpDamage": ["sum"]},
        rename=[stats[2], "Nade Type", "Given UD", "UD"],
    )

    nades_thrown_filter = grenade_data["grenadeType"].isin(["HE Grenade", "Incendiary Grenade", "Molotov"])
    nades_thrown = filter_group_aggregate(
        grenade_data.loc[nades_thrown_filter],
        filters=grenade_filters,
        groupby=[stats[1], "grenadeType"],
        aggregate={stats[1]: ["size"]},
        rename=[stats[2], "Nade Type", "Nades Thrown"],
    )
    util_dmg_breakdown = util_dmg.merge(
        nades_thrown, how="outer", on=[stats[2], "Nade Type"]
    ).fillna(0)
    util_dmg_breakdown["Given UD Per Nade"] = (
            util_dmg_breakdown["Given UD"] / util_dmg_breakdown["Nades Thrown"]
    )
    util_dmg_breakdown["UD Per Nade"] = (
            util_dmg_breakdown["UD"] / util_dmg_breakdown["Nades Thrown"]
    )
    util_dmg_breakdown.sort_values(
        by=[stats[2], "Given UD"], ascending=[True, False], inplace=True
    )
    util_dmg_breakdown.reset_index(drop=True, inplace=True)
    return util_dmg_breakdown


def calc_player_box_score(
        damage_data: pd.DataFrame,
        flash_data: pd.DataFrame,
        grenade_data: pd.DataFrame,
        kill_data: pd.DataFrame,
        round_data: pd.DataFrame,
        weapon_fire_data: pd.DataFrame,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        flash_filters: Dict[str, Union[List[bool], List[str]]] = None,
        grenade_filters: Dict[str, Union[List[bool], List[str]]] = None,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
        death_filters: Dict[str, Union[List[bool], List[str]]] = None,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
        weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    """Returns a player box score dataframe.

    Args:
       damage_data: A dataframe with damage data.
       flash_data: A dataframe with flash data.
       grenade_data: A dataframe with grenade data.
       kill_data: A dataframe with kill data.
       round_data: A dataframe with round data.
       weapon_fire_data: A dataframe with weapon fire data.
       damage_filters: A dictionary where the keys are the columns of the
           dataframe represented by damage_data to filter the damage data by
           and the values are lists that contain the column filters.
       flash_filters: A dictionary where the keys are the columns of the
           dataframe represented by flash_data to filter the flash data by
           and the values are lists that contain the column filters.
       grenade_filters: A dictionary where the keys are the columns of the
           dataframe represented by grenade_data to filter the grenade data by
           and the values are lists that contain the column filters.
       kill_filters: A dictionary where the keys are the columns of the
           dataframe represented by kill_data to filter the kill data by and
           the values are lists that contain the column filters.
       death_filters: A dictionary where the keys are the columns of the
           dataframe represented by kill_data to filter the death data by and
           the values are lists that contain the column filters.
       round_filters: A dictionary where the keys are the columns of the
           dataframe represented by round_data to filter the round data by and
           the values are lists that contain the column filters.
       weapon_fire_filters: A dictionary where the keys are the columns of the
           dataframe to filter the weapon fire data by and the values are lists
           that contain the column filters.
    """
    damage_filters = damage_filters or dict()
    flash_filters = flash_filters or dict()
    grenade_filters = grenade_filters or dict()
    kill_filters = kill_filters or dict()
    death_filters = death_filters or dict()
    round_filters = round_filters or dict()
    weapon_fire_filters = weapon_fire_filters or dict()

    k_stats = calc_kill_stats(
        damage_data,
        kill_data,
        round_data,
        weapon_fire_data,
        team=False,
        damage_filters=damage_filters,
        kill_filters=kill_filters,
        death_filters=death_filters,
        round_filters=round_filters,
        weapon_fire_filters=weapon_fire_filters,
    )
    k_stats = k_stats[
        ["Player", "K", "D", "A", "FA", "HS%", "ACC%", "HS ACC%", "KDR", "KAST%"]
    ]

    adr_stats = calc_adr(
        damage_data,
        round_data,
        team=False,
        damage_filters=damage_filters,
        round_filters=round_filters)
    adr_stats = adr_stats[["Player", "Norm ADR"]]
    adr_stats.columns = ["Player", "ADR"]

    ud_stats = calc_util_dmg(
        damage_data,
        grenade_data,
        team=False,
        damage_filters=damage_filters,
        grenade_filters=grenade_filters)
    ud_stats = ud_stats[["Player", "UD", "UD Per Nade"]]

    f_stats = calc_flash_stats(
        flash_data,
        grenade_data,
        kill_data,
        team=False,
        flash_filters=flash_filters,
        grenade_filters=grenade_filters,
        kill_filters=kill_filters,
    )
    f_stats = f_stats[["Player", "EF", "EF Per Throw"]]

    rating_stats = calc_rating(
        damage_data,
        kill_data,
        round_data,
        kast_string="KAST",
        flash_assists=True,
        damage_filters=damage_filters,
        death_filters=death_filters,
        kill_filters=kill_filters,
        round_filters=round_filters)

    box_score = k_stats.merge(adr_stats, how="outer").fillna(0)
    box_score = box_score.merge(ud_stats, how="outer").fillna(0)
    box_score = box_score.merge(f_stats, how="outer").fillna(0)
    box_score = box_score.merge(rating_stats, how="outer").fillna(0)
    return box_score


def calc_win_breakdown(
        round_data: pd.DataFrame,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    round_filters = round_filters or dict()

    round_data_copy = round_data.copy()
    round_data_copy.replace("BombDefused", "CT Bomb Defusal Wins", inplace=True)
    round_data_copy.replace("CTWin", "CT T Elim Wins", inplace=True)
    round_data_copy.replace("TargetBombed", "T Bomb Detonation Wins", inplace=True)
    round_data_copy.replace("TargetSaved", "CT Time Expired Wins", inplace=True)
    round_data_copy.replace("TerroristsWin", "T CT Elim Wins", inplace=True)

    win_breakdown_stats = filter_group_aggregate(
        round_data_copy,
        filters=round_filters,
        groupby=["winningTeam", "roundEndReason"],
        aggregate={"roundEndReason": ["size"]},
        rename=["Team", "RoundEndReason", "Count"],
    )

    win_breakdown_stats = win_breakdown_stats \
        .pivot(index="Team", columns="RoundEndReason", values="Count") \
        .fillna(0)

    win_breakdown_stats.reset_index(inplace=True)
    win_breakdown_stats.rename_axis(None, axis=1, inplace=True)
    win_breakdown_stats["Total CT Wins"] = win_breakdown_stats.iloc[0:][
        list(
            set.intersection(
                set(win_breakdown_stats.columns),
                {"CT Bomb Refusal Wins", "CT T Elim Wins", "CT Time Expired Wins"},
            )
        )
    ].sum(axis=1)

    win_breakdown_stats["Total T Wins"] = win_breakdown_stats.iloc[0:][
        list(
            set.intersection(
                set(win_breakdown_stats.columns),
                {"T Bomb Detonation Wins", "T CT Elim Wins"},
            )
        )
    ].sum(axis=1)

    win_breakdown_stats["Total Wins"] = win_breakdown_stats.iloc[0:, 0:-2].sum(axis=1)
    win_breakdown_stats.iloc[:, 1:] = win_breakdown_stats.iloc[:, 1:].astype(int)
    return win_breakdown_stats


def calc_team_box_score(
        damage_data: pd.DataFrame,
        flash_data: pd.DataFrame,
        grenade_data: pd.DataFrame,
        kill_data: pd.DataFrame,
        round_data: pd.DataFrame,
        weapon_fire_data: pd.DataFrame,
        damage_filters: Dict[str, Union[List[bool], List[str]]] = None,
        flash_filters: Dict[str, Union[List[bool], List[str]]] = None,
        grenade_filters: Dict[str, Union[List[bool], List[str]]] = None,
        kill_filters: Dict[str, Union[List[bool], List[str]]] = None,
        death_filters: Dict[str, Union[List[bool], List[str]]] = None,
        round_filters: Dict[str, Union[List[bool], List[str]]] = None,
        weapon_fire_filters: Dict[str, Union[List[bool], List[str]]] = None,
) -> pd.DataFrame:
    damage_filters = damage_filters or dict()
    flash_filters = flash_filters or dict()
    grenade_filters = grenade_filters or dict()
    kill_filters = kill_filters or dict()
    death_filters = death_filters or dict()
    round_filters = round_filters or dict()
    weapon_fire_filters = weapon_fire_filters or dict()

    k_stats = calc_kill_stats(
        damage_data,
        kill_data,
        round_data,
        weapon_fire_data,
        True,
        damage_filters,
        kill_filters,
        death_filters,
        round_filters,
        weapon_fire_filters,
    )
    acc_stats = calc_accuracy(
        damage_data, weapon_fire_data, True, damage_filters, weapon_fire_filters
    )
    adr_stats = calc_adr(damage_data, round_data, True, damage_filters, round_filters)
    ud_stats = calc_util_dmg(
        damage_data, grenade_data, True, damage_filters, grenade_filters
    )
    f_stats = calc_flash_stats(
        flash_data,
        grenade_data,
        kill_data,
        True,
        flash_filters,
        grenade_filters,
        kill_filters,
    )
    e_stats = calc_econ_stats(round_data, round_filters)
    for index in e_stats.index:
        e_stats.iloc[index, 0] = e_stats["Side"].str.rsplit(n=1)[index][0]
        rounds = e_stats.iloc[index, 1:-4].sum()
        e_stats.iloc[index, -3:] = e_stats.iloc[index, -3:] * rounds
    e_stats = e_stats.groupby(["Side"]).sum()
    e_stats.reset_index(inplace=True)
    e_stats.iloc[:, -3:] = (
            e_stats.iloc[:, -3:] / len(filter_df(round_data, round_filters))
    ).astype(int)
    e_stats.rename(columns={"Side": "Team"}, inplace=True)
    box_score = k_stats.merge(acc_stats, how="outer")
    box_score = box_score.merge(adr_stats, how="outer")
    box_score = box_score.merge(ud_stats, how="outer")
    box_score = box_score.merge(f_stats, how="outer")
    box_score = box_score.merge(e_stats, how="outer")
    box_score = box_score.merge(
        calc_win_breakdown(round_data, round_filters), how="outer"
    ).fillna(0)
    box_score.rename(
        columns={
            "Norm ADR": "ADR",
            "Total CT Wins": "CT Wins",
            "Total T Wins": "T Wins",
            "Total Wins": "Score",
        },
        inplace=True,
    )
    score = box_score["Score"]
    ct_wins = box_score["CT Wins"]
    t_wins = box_score["T Wins"]
    box_score.drop(["Score", "CT Wins", "T Wins"], axis=1, inplace=True)
    box_score.insert(1, "Score", score)
    box_score.insert(2, "CT Wins", ct_wins)
    box_score.insert(3, "T Wins", t_wins)
    box_score = box_score.transpose()
    box_score.columns = box_score.iloc[0]
    box_score.drop("Team", inplace=True)
    box_score.rename_axis(None, axis=1, inplace=True)
    box_score = box_score.loc[
                [
                    "Score",
                    "CT Wins",
                    "T Wins",
                    "K",
                    "D",
                    "A",
                    "FA",
                    "+/-",
                    "FK",
                    "HS",
                    "HS%",
                    "Strafe%",
                    "ACC%",
                    "HS ACC%",
                    "ADR",
                    "UD",
                    "Nades Thrown",
                    "UD Per Nade",
                    "EF",
                    "Flashes Thrown",
                    "EF Per Throw",
                    "EBT Per Enemy",
                ],
                :,
                ].append(box_score.iloc[31:, :])
    return box_score
