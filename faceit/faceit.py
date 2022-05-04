import time
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterable, Union, List, Dict
from urllib.request import Request, urlopen

from faceit.api import FaceitApi, FaceitApiRequestError
from utils.functions import dict_get_or_default, read_json, write_json
from utils.logging import logger

log = logger()


@dataclass
class Player:
    player_id: str
    nickname: str
    level: Optional[int]
    elo: Optional[int]

    @classmethod
    def from_details(cls, data: dict) -> "Player":
        level = data["games"]["csgo"]["skill_level"]
        elo = data["games"]["csgo"]["faceit_elo"]
        return Player(data["id"], data["nickname"], level, elo)

    @classmethod
    def from_roster(cls, data: dict) -> "Player":
        return Player(data["id"], data["nickname"], data.get("gameSkillLevel", None), data.get("elo", None))

    def __hash__(self):
        return hash(self.player_id)

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.player_id == other.player_id


@dataclass
class Team:
    name: str
    players: Optional[List[Player]] = None

    @classmethod
    def from_faction(cls, data: dict) -> "Team":
        players = [Player.from_roster(it) for it in data["roster"]] if "roster" in data else None
        return Team(data["name"], players)

    def has_player(self, player: Union[Player, str]):
        player_id = player.player_id if isinstance(player, Player) else player
        return any(it.player_id == player_id for it in self)

    def __iter__(self):
        return self.players.__iter__()


def _get_winner(data: dict, team_a: Team, team_b: Team):
    return team_a if data["results"][0]["winner"] == "faction1" else team_b


@dataclass
class StatisticInfo:
    rounds: int
    date: datetime

    elo: Optional[int]
    kills: int
    assists: int
    deaths: int
    mvps: int
    headshots: int

    @classmethod
    def from_data(cls, data: dict):
        return StatisticInfo(
            rounds=data["i12"],
            date=datetime.fromtimestamp(data["date"] // 1000),
            elo=dict_get_or_default(data, "elo", None, int),
            kills=int(data["i6"]),
            assists=int(data["i7"]),
            deaths=int(data["i8"]),
            mvps=int(data["i10"]),
            headshots=int(data["i13"]),
        )


@dataclass
class Statistic:
    match_id: str
    nickname: str
    team_name: str
    map_name: str
    mode: str
    info: Optional[StatisticInfo]

    @classmethod
    def from_data(cls, data: dict) -> "Statistic":
        return Statistic(
            match_id=data["matchId"],
            nickname=data["nickname"],
            team_name=data["i5"],
            map_name=data["i1"],
            mode=data["gameMode"],
            info=StatisticInfo.from_data(data)
        )

    def has_elo(self):
        return self.info.elo is not None


@dataclass
class Match:
    teams: List[Team]
    map: str
    demo_url: Optional[str]
    match_id: str
    winner: Team
    date: Optional[datetime]
    calculate_elo: bool
    is_played: bool

    @classmethod
    def from_data(cls, data: dict) -> "Match":
        is_played = "demoURLs" in data
        teams_data = data["teams"]
        team1 = Team.from_faction(teams_data["faction1"])
        team2 = Team.from_faction(teams_data["faction2"])
        winner = _get_winner(data, team1, team2)
        date = datetime.strptime(data['startedAt'], "%Y-%m-%dT%H:%M:%SZ") if is_played else None
        return Match(
            match_id=data["id"],
            teams=[team1, team2],
            demo_url=data["demoURLs"][0] if is_played else None,
            map=data["voting"]["map"]["pick"][0] if "voting" in data else None,
            winner=winner,
            calculate_elo=data["calculateElo"],
            date=date,
            is_played=is_played)

    def __hash__(self):
        return hash(self.match_id)

    def __eq__(self, other):
        if not isinstance(other, Match):
            return False
        return self.match_id == other.match_id

    def get_players_team(self, player: Union[Player, str]):
        return next(it for it in self.teams if it.has_player(player))


class Faceit(object):

    def __init__(self):
        self._api = FaceitApi()
        self._cache_path = Path("_faceit_cache_")
        self._cache_path.mkdir(exist_ok=True)

    def championship_matches(self, championship_id) -> Iterable[Match]:
        matches_data = self._api.championship_matches(championship_id)
        return [Match.from_data(item) for item in matches_data]

    def match(self, match_id: str, force: bool = False) -> Match:
        match_cache_path = self._cache_path / Path(match_id).with_suffix(".json")
        if not force and match_cache_path.is_file():
            data = read_json(match_cache_path)
        else:
            data = self._api.match_details(match_id)
            write_json(match_cache_path, data)
        return Match.from_data(data)

    def download_demo(self, match: Union[Match, str], directory: Path, force: bool = False):
        log.info(f"Download demo for {match} into {directory}")

        if isinstance(match, Match):
            demo_url = match.demo_url
        elif isinstance(match, str):
            demo_url = self.match(match).demo_url
        else:
            raise TypeError(f"Only Match or str supported as input type for match but got {type(match)}")

        url_path = Path(match.demo_url)

        demo_path = directory / url_path.name.rstrip(".gz")
        if not force and demo_path.is_file():
            return demo_path

        request = Request(demo_url, headers={'User-Agent': 'Mozilla/5.0'})

        with urlopen(request) as input_file:
            compressed = input_file.read()

            data = zlib.decompress(compressed, 15 + 32)

            with open(demo_path, "wb") as output_file:
                output_file.write(data)

        return demo_path

    def download_all_demos(self, matches: Iterable[Match], directory: Path, force: bool = False) -> Dict[Match, Path]:
        return {match: self.download_demo(match, directory, force) for match in matches}

    def player(self, nickname: str) -> Optional[Player]:
        log.info(f"Request player {nickname} details")

        try:
            player_details = self._api.player_details_by_name(nickname)
        except FaceitApiRequestError as error:
            log.error(f"Can't get player for nickname '{nickname}' due to {error}")
            return None
        else:
            return Player.from_details(player_details)

    def matches_stats(self, player: Union[Player, str], count: Optional[int] = None) -> Iterable[Statistic]:
        log.info(f"Request {player} statistics history")

        player_id = player.player_id if isinstance(player, Player) else player

        index = 0
        page = 0

        while True:
            log.debug(f"Requesting player {player} matches for page {page}")
            matches = self._api.player_matches_stats(player_id, "csgo", page)
            if not matches:
                break
            for item in matches:
                index += 1
                yield Statistic.from_data(item)
                if count is not None and index >= count:
                    return
            page += 1
