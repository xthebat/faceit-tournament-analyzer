import json
from dataclasses import dataclass
from typing import Any

import requests
from requests import Response


FACEIT_API_URL = "https://api.faceit.com"

STATS_V1_ENDPOINT = "stats/v1"
USERS_V1_ENDPOINT = "users/v1"
MATCH_V2_ENDPOINT = "match/v2"

_GET_REQUEST = "GET"


@dataclass
class FaceitApiRequestError(Exception):
    response: Response


class FaceitApi(object):

    def __init__(self, base_url: str = FACEIT_API_URL):
        self._base_url = base_url

    def _request(self, request: str, endpoint: str, url: str):
        headers = {'accept': 'application/json'}
        api = f"{self._base_url}/{endpoint}/{url}"
        response: Response = requests.request(request, url=api, headers=headers)
        if response.status_code != 200:
            raise FaceitApiRequestError(response)
        content = response.content.decode('utf-8')
        result = json.loads(content)
        return result["payload"] if "payload" in result else result

    def _get_request(self, endpoint: str, url: str):
        return self._request(_GET_REQUEST, endpoint, url)

    def _stats_v1_request(self, url: str):
        return self._get_request(STATS_V1_ENDPOINT, url)

    def _users_v1_request(self, url: str):
        return self._get_request(USERS_V1_ENDPOINT, url)

    def _match_v2_request(self, url: str):
        return self._get_request(MATCH_V2_ENDPOINT, url)

    def player_matches_stats(self, player_id: str, game: str, page: int = 0, size: int = 0):
        return self._stats_v1_request(f"stats/time/users/{player_id}/games/{game}?page={page}&size={size}")

    def player_details_by_name(self, nickname: str):
        return self._users_v1_request(f"nicknames/{nickname}")

    def player_details_by_id(self, player_id: str):
        return self._users_v1_request(f"users/{player_id}")

    def match_details(self, match_id: str):
        return self._match_v2_request(f"match/{match_id}")

    def championship_matches(self, championship_id: str):
        return self._match_v2_request(f"match?entityId={championship_id}&entityType=championship")



