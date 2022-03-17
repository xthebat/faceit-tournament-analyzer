from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Union, Dict

import pandas as pd
from awpy import DemoParser

from demo.analytics import calc_player_box_score
from demo.utils import clear_data, clear_rounds


@dataclass
class Statistics:
    rounds: pd.DataFrame
    damages: pd.DataFrame
    kills: pd.DataFrame
    flashes: pd.DataFrame
    weapons_fire: pd.DataFrame
    grenades: pd.DataFrame

    def player_box_score(self):
        return calc_player_box_score(
            self.damages, self.flashes, self.grenades, self.kills, self.rounds, self.weapons_fire)

    def concat(self, other: "Statistics") -> "Statistics":
        return Statistics(
            rounds=pd.concat([self.rounds, other.rounds], ignore_index=True),
            damages=pd.concat([self.damages, other.damages], ignore_index=True),
            kills=pd.concat([self.kills, other.kills], ignore_index=True),
            flashes=pd.concat([self.flashes, other.flashes], ignore_index=True),
            weapons_fire=pd.concat([self.weapons_fire, other.weapons_fire], ignore_index=True),
            grenades=pd.concat([self.grenades, other.grenades], ignore_index=True),
        )


@dataclass
class Demo:
    dem_path: Path
    json_path: Path
    stats: Statistics

    @classmethod
    def analyze(cls, demo_path: Union[Path, str], force: bool = False):
        demo_path = Path(demo_path) if isinstance(demo_path, str) else demo_path

        out_path = demo_path.parent

        json_path = Path(out_path, demo_path.stem).with_suffix(".json")

        demo_parser = DemoParser(
            demofile=str(demo_path),
            log=True,
            # TODO: there is bug in DemoParser.parse_demo() in self.output_file ... lead to ERROR logging
            outpath=str(out_path),
            parse_frames=False,
            trade_time=5,
            buy_style="hltv",
            json_indentation=True
        )

        if force or not json_path.is_file():
            # output results to a dictionary of dataframes.
            df: Dict[str, pd.DataFrame] = demo_parser.parse(return_type="df")
        else:
            # read to also internal state... why
            demo_parser.read_json(str(json_path))
            df: Dict[str, pd.DataFrame] = demo_parser.parse_json_to_df()

        offset, rounds = clear_rounds(df["rounds"])

        stats = Statistics(
            rounds=rounds,
            damages=clear_data(df["damages"], offset, rounds),
            kills=clear_data(df["kills"], offset, rounds),
            flashes=clear_data(df["flashes"], offset, rounds),
            weapons_fire=clear_data(df["weaponFires"], offset, rounds),
            grenades=clear_data(df["grenades"], offset, rounds)
        )

        return Demo(demo_path, json_path, stats)
