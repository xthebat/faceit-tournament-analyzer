import json
import time
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterable, Union, List, Dict
from urllib.request import Request, urlopen

import requests

from faceit_api.faceit_data import FaceitData
from utils.functions import dict_get_or_default
from utils.logging import logger

log = logger()


@dataclass
class Player:
    player_id: str
    nickname: str
    level: Optional[int]

    @classmethod
    def from_data(cls, data: dict) -> "Player":
        skill = int(data["skill_level"]) if "skill_level" in data else None
        return Player(data["player_id"], data["nickname"], skill)

    def __hash__(self):
        return hash(self.player_id)

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.player_id == other.player_id


@dataclass
class Team:
    name: str
    players: Optional[List[Player]]

    @classmethod
    def from_data(cls, data: dict, name_column: str, players_column: Optional[str]) -> "Team":
        players = None if players_column is None \
            else [Player.from_data(player_data) for player_data in data[players_column]]
        return Team(data[name_column], players)


def _get_winner(data: dict, team_a: Team, team_b: Team):
    return team_a if data["results"]["winner"] == "faction1" else team_b


@dataclass
class Game:
    team_a: Team
    team_b: Team
    match_id: str
    winner: Team
    mode: str
    date: datetime

    @classmethod
    def from_data(cls, data: dict) -> "Game":
        teams_data = data["teams"]
        team_a = Team.from_data(teams_data["faction1"], "nickname", "players")
        team_b = Team.from_data(teams_data["faction2"], "nickname", "players")
        winner = _get_winner(data, team_a, team_b)
        date = datetime.fromtimestamp(data['started_at'])
        return Game(
            match_id=data["match_id"],
            team_a=team_a,
            team_b=team_b,
            winner=winner,
            mode=data["game_mode"],
            date=date
        )

    def is_player_win(self, player: Player):
        return any(player == it for it in self.winner.players)

    def __hash__(self):
        return hash(self.match_id)

    def __eq__(self, other):
        if not isinstance(other, Match):
            return False
        return self.match_id == other.match_id


@dataclass
class Statistic:
    name: str
    team: str
    map_name: str
    rounds: int
    elo: Optional[int]
    mode: str
    date: datetime

    @classmethod
    def from_data(cls, data: dict) -> "Statistic":
        return Statistic(
            name=data["nickname"],
            team=data["i5"],
            map_name=data["i1"],
            rounds=dict_get_or_default(data, "i12", None, convert=int),
            elo=dict_get_or_default(data, "elo", None, convert=int),
            mode=data["gameMode"],
            date=dict_get_or_default(data, "date", None, convert=lambda it: datetime.fromtimestamp(it // 1000))
        )


@dataclass
class Match:
    team_a: Team
    team_b: Team
    map: str
    faceit_url: str
    demo_url: Optional[str]
    match_id: str
    winner: Team
    date: Optional[datetime]
    calculate_elo: bool
    is_played: bool

    @classmethod
    def from_data(cls, data: dict) -> "Match":
        is_played = "demo_url" in data
        teams_data = data["teams"]
        team_a = Team.from_data(teams_data["faction1"], "name", "roster" if is_played else None)
        team_b = Team.from_data(teams_data["faction2"], "name", "roster" if is_played else None)
        winner = _get_winner(data, team_a, team_b)
        date = datetime.fromtimestamp(data['started_at']) if is_played else None
        return Match(
            match_id=data["match_id"],
            faceit_url=data["faceit_url"].replace("{lang}", "en"),
            team_a=team_a,
            team_b=team_b,
            demo_url=data["demo_url"][0] if is_played else None,
            map=data["voting"]["map"]["pick"][0] if is_played else None,
            winner=winner,
            calculate_elo=data["calculate_elo"],
            date=date,
            is_played=is_played
        )

    def __hash__(self):
        return hash(self.match_id)

    def __eq__(self, other):
        if not isinstance(other, Match):
            return False
        return self.match_id == other.match_id


_FACEIT_STATS_URL = "https://api.faceit.com/stats/v1"


def _get_player_matches_stats(faceit: FaceitData, player_id: str, game: str, page: int = 0, size: int = 0):
    api_url = f"{_FACEIT_STATS_URL}/stats/time/users/{player_id}/games/{game}?page={page}&size={size}"
    headers = {'accept': 'application/json'}
    res = requests.get(api_url, headers=headers)
    return json.loads(res.content.decode('utf-8')) if res.status_code == 200 else None


class Faceit(object):

    def __init__(self, apikey: str):
        #
        self.apikey = apikey
        self.client = FaceitData(apikey)

    def championship_matches(self, champ_id) -> Iterable[Match]:
        data = self.client.championship_matches(champ_id)
        return [Match.from_data(item) for item in data["items"]]

    def match(self, match_id: str) -> Match:
        data = self.client.match_details(match_id)
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

        player_details = self.client.player_details(nickname)
        if player_details is None:
            return None
        return Player.from_data(player_details)

    def player_games_v1(self, player_id: str, count: Optional[int] = None) -> Iterable[Game]:
        index = 0
        position = 0
        while True:
            log.info(f"Requesting player {player_id} matches from {position}")
            matches = self.client.player_matches(player_id, "csgo", starting_item_position=position)
            if matches is None or len(matches["items"]) == 0:
                break
            for item in matches["items"]:
                index += 1
                yield Game.from_data(item)
                if count is not None and index >= count:
                    return
            time.sleep(0.1)
            position += 20

    def player_games_v2(self, player_id: str, count: Optional[int] = None):
        log.info(f"Request player {player_id} statistics history")

        index = 0
        page = 0

        player = Player.from_data(self.client.player_id_details(player_id))

        while True:
            log.info(f"Requesting player {player_id}/{player.nickname} matches for page {page}")
            matches = _get_player_matches_stats(self.client, player_id, "csgo", page)
            if matches is None or len(matches) == 0:
                break
            for item in matches:
                index += 1
                yield Statistic.from_data(item)
                if count is not None and index >= count:
                    return
            page += 1
