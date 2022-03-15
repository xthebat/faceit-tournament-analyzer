import argparse
import json
import os.path
import sys
from pathlib import Path
from typing import List, Optional

from demo.base import Demo, Statistics
from faceit.faceit import Faceit


def analyze_championship(faceit: Faceit, championship: str, demos_dir: Path, args: argparse.Namespace):
    matches = faceit.championship_matches(championship)

    played_matches = list(filter(lambda it: it.demo_url is not None, matches))

    stats: Optional[Statistics] = None
    for match in played_matches:
        dem_path = faceit.download_demo(match, demos_dir, args.force_download)
        demo = Demo.analyze(dem_path, args.force_analyze)
        if args.match_stats:
            print(demo.stats.player_box_score().to_string())
        stats = stats.concat(demo.stats) if stats is not None else demo.stats

    print(stats.player_box_score().to_string())


def main(argv: List[str]):
    parser = argparse.ArgumentParser(prog="faceit-tournament-analyzer", description='Facet tournament analyzer')
    parser.add_argument('--force_analyze', action="store_true", help="Force to re-analyze demo")
    parser.add_argument('--force_download', action="store_true", help="Force to re-download demo")
    parser.add_argument('--match_stats', action="store_true", help="Print each match statistics")
    parser.add_argument('-c', '--config', required=True, type=str, help="Path to config. file")
    parser.add_argument('championships', type=str, nargs='+', help="Identifier of championships to analyze")
    args = parser.parse_args(argv[1:])

    print(args)

    if not os.path.isfile(args.config):
        sys.exit(f"Configuration file {args.config} not found")

    with open(args.config, "rt") as file:
        config_data = json.loads(file.read())

    apikey = config_data["apikey"]
    demos_dir = Path(config_data["demos_dir"])

    demos_dir.mkdir(exist_ok=True)

    if len(args.championships) == 0:
        sys.exit("Specify at least one championship id in program arguments")

    faceit = Faceit(apikey)
    for championship in args.championships:
        analyze_championship(faceit, championship, demos_dir, args)


if __name__ == '__main__':
    main(sys.argv)
