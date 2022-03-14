import json
import os.path
import sys
from dataclasses import dataclass
from typing import List, Any, Dict, Optional, Callable, Iterable
from faceit_api.faceit_data import FaceitData


CONFIG_FILE = "faceit.json"


@dataclass
class Stats(object):
    kills: int
    assists: int
    deaths: int
    headshots: float
    mvps: int
    result: int
    triple: int
    quadro: int
    penta: int
    kd: float
    kr: float

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Stats":
        return Stats(
            assists=int(data['Assists']),
            deaths=int(data['Deaths']),
            kills=int(data['Kills']),
            headshots=float(data['Headshots %']),
            triple=int(data['Triple Kills']),
            quadro=int(data['Quadro Kills']),
            penta=int(data['Penta Kills']),
            result=int(data['Result']),
            kd=float(data['K/D Ratio']),
            kr=float(data['K/R Ratio']),
            mvps=int(data['MVPs'])
        )


@dataclass
class MeanStats(object):
    nickname: str
    matches: int
    kills: int
    assists: int
    deaths: int
    headshots: float
    mvps: int
    result: int
    triple: int
    quadro: int
    penta: int
    kd: float
    kr: float



@dataclass
class Player(object):
    player_id: str
    nickname: str
    stats: Dict[str, Stats]
    mean: Optional[Stats]


def analyze_champ(faceit: FaceitData, champ_id: str):
    print(f"---- Analyzing champ={champ_id} ----")
    players = dict()
    champ = faceit.championship_matches(champ_id)
    for match in champ["items"]:
        analyze_match(faceit, match["match_id"], players)
    return players


def analyze_match(faceit: FaceitData, match_id: str, players: Dict[str, Player]):

    match_details = faceit.match_details(match_id)
    # print(match_details)
    teams = match_details["teams"]
    faction1 = teams["faction1"]["name"]
    faction2 = teams["faction2"]["name"]
    url = match_details["faceit_url"].replace("{lang}", "ru")
    print(f"Analyzing match: {match_id} <{faction1} vs {faction2}> url: {url}")

    match_stats = faceit.match_stats(match_id)

    if match_stats is None:
        print(f"Match stats for {match_id} can't be obtained!")
        return dict()

    rounds = match_stats["rounds"]

    assert len(rounds) == 1, "Supported only bo1 tournaments"

    game = rounds[0]

    for team in game["teams"]:
        players_data = team["players"]
        for player_data in players_data:
            player_id = player_data["player_id"]
            nickname = player_data["nickname"]
            player = players.setdefault(player_id, Player(player_id, nickname, dict(), None))

            stats_data = Stats.from_dict(player_data["player_stats"])
            player.stats[match_id] = stats_data


def mean(iterable: Iterable):
    items = list(iterable)
    return sum(items) / len(items)


def calc_stat_by_key(player: Player, func=Callable, key=Callable):
    return func.__call__(key(stats) for stats in player.stats.values())


def calc_mean(player: Player):
    return MeanStats(
        nickname=player.nickname,
        matches=len(player.stats),
        kills=calc_stat_by_key(player, sum, key=lambda it: it.kills),
        assists=calc_stat_by_key(player, sum, key=lambda it: it.assists),
        deaths=calc_stat_by_key(player, sum, key=lambda it: it.deaths),
        headshots=calc_stat_by_key(player, mean, key=lambda it: it.headshots),
        mvps=calc_stat_by_key(player, sum, key=lambda it: it.mvps),
        result=calc_stat_by_key(player, sum, key=lambda it: it.result),
        triple=calc_stat_by_key(player, sum, key=lambda it: it.triple),
        quadro=calc_stat_by_key(player, sum, key=lambda it: it.quadro),
        penta=calc_stat_by_key(player, sum, key=lambda it: it.penta),
        kd=calc_stat_by_key(player, mean, key=lambda it: it.kd),
        kr=calc_stat_by_key(player, mean, key=lambda it: it.kr),
    )


def print_stats(players: Dict[str, Player]):
    for player_id, player in players.items():
        print(f"%38s  %2s %2s %2s  %4s %4s  %4s  %4s %2s  %2s %2s %2s" %
              (
                  f"Statistics for {player.nickname}",
                  "K", "A", "D", "K/D", "K/R", "HS%", "MVPs", "R", "T", "Q", "P"
              )
        )
        for match_id, stats in player.stats.items():
            print(f"%38s  %2d %2d %2d  %4.2f %4.2f  %4.1f  %4d %2d  %2d %2d %2d" % (
                match_id,
                stats.kills,
                stats.assists,
                stats.deaths,
                stats.kd,
                stats.kr,
                stats.headshots,
                stats.mvps,
                stats.result,
                stats.triple,
                stats.quadro,
                stats.penta)
            )


def print_mean(players: Dict[str, Player]):
    print(f"%15s\t%3s\t%3s\t%3s\t%3s\t%4s\t%4s\t%5s\t%4s\t%3s\t%3s\t%3s\t%3s" %
          ("nickname", "M", "K", "A", "D", "K/D", "K/R", "HS%", "MVPs", "R", "T", "Q", "P"))

    stats = [calc_mean(player) for player in players.values()]

    for mean_stats in sorted(stats, key=lambda it: it.matches, reverse=True):
        print(f"%15s\t%3d\t%3d\t%3d\t%3d\t%4.2f\t%4.2f\t%5.1f\t%4d\t%3d\t%3d\t%3d\t%3d" % (
            mean_stats.nickname,
            mean_stats.matches,
            mean_stats.kills,
            mean_stats.assists,
            mean_stats.deaths,
            mean_stats.kd,
            mean_stats.kr,
            mean_stats.headshots,
            mean_stats.mvps,
            mean_stats.result,
            mean_stats.triple,
            mean_stats.quadro,
            mean_stats.penta)
        )


def main(args: List[str]):
    if not os.path.isfile(CONFIG_FILE):
        sys.exit(f"Configuration file {CONFIG_FILE} not found")

    with open(CONFIG_FILE, "rt") as file:
        config_data = json.loads(file.read())

    apikey = config_data["apikey"]

    if len(args) < 2:
        sys.exit("Specify at least one championship id in program arguments")

    faceit = FaceitData(apikey.strip())

    for champ_id in args[1:]:
        players = analyze_champ(faceit, champ_id)

        # print_stats(players)

        print_mean(players)


if __name__ == '__main__':
    main(sys.argv)
