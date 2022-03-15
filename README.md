# faceit-tournament-analyzer

### description

Simple script to gather players statistics for whole championship using faceit-api and awpy 

### before run
1. Get your faceit application key: https://developers.faceit.com/

2. Put it into JSON with name e.g. `faceit.json` in current directory and follow format:
```json
{
  "apikey": "<key>",
  "demos_dir": "<path to directory to store .dem files and json cache files>"
}
```

3. Get git submodule

```shell
git submodule update --init --recursive
```
4. Run like:

```shell
faceit-tournament-analyzer.py --config faceit.json <championship_id1> <championship_id2>
```