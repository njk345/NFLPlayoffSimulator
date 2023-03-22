# NFLPlayoffSimulator
Simulator for the rest of the NFL season, inspired by the [NY Times simulator](https://www.nytimes.com/interactive/2022/upshot/nfl-playoff-picture.html) and [538's simulator](https://projects.fivethirtyeight.com/2022-nfl-predictions/).

### Todo
- Make more efficient
    - update_elo
    - add_result
    - wlt
    - add_game
    - tiebreaker4
    - get_opp
    - 
- Implement elo updates after every game using 538 formulas
- Create website using Flask or Django
- Implement different modes
    - simulate rest of current season
    - simulate current season from arbitrary date
    - manually select rest of season results and show tiebreakers / seeds
    - explain tiebreakers for given records

### Conda

Activate env: `conda activate nflsim`

Update requirements: `conda env update --file environment.yaml --prune`

Put any new dependencies under "dependencies" in environment.yaml

