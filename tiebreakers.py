from main import get_opp, is_team1, Result

def two_team_div_tiebreaker(team1, team2):
    pass

def two_team_wc_tiebreaker(team1, team2):
    pass

def threeplus_team_div_tiebreaker(team1, team2):
    pass

def threeplus_team_wc_tiebreaker(team1, team2):
    pass

# Returns T1WIN if team1 wins tiebreaker, T2WIN if team2 wins, TIE if not settled
# Head-to-head record
def tiebreaker1(team1, team2):
    # Head-to-head team record
    t1wins = 0
    t2wins = 0
    for game in team1.games:
        # abbr of opposing team
        opp = get_opp(game, team1)
        if abbs_to_codes[opp] == team2.code:
            # found game against team2
            t1wins += wins_from_game(game, True)
            t2wins += wins_from_game(game, False)
    if t1wins > t2wins:
        return Result.T1WIN
    elif t2wins > t1wins:
        return Result.T2WIN
    return Result.TIE

# In-division record
def tiebreaker2(team1, team2):
    t1wins = 0
    for game in team1.games:
        opp = get_opp(game, team1)
        if team_info[opp]["DIV"] == team_info[team1.code]["DIV"]:
            # teams in same division, count result
            t1wins += wins_from_game(game, is_t1)
    t2wins = 0
    for game in team2.games:
        opp = get_opp(game, team2)
        if team_info[opp]["DIV"] == team_info[team2.code]["DIV"]:
            # teams in same division, count result
            t2wins += wins_from_game(game, is_t1)
    if t1wins > t2wins:
        return Result.T1WIN
    elif t2wins > t1wins:
        return Result.T2WIN
    return Result.TIE

# Record in common opponents
def tiebreaker3(team1, team2):
    # use sets to find common opponents
    # loop through to get total wins each against common opponents
    t1_opps = {}
    for game in team1.games:
        t1_opps.add(get_opp(game, team1))
    t2_opps = {}
    for game in team2.games:
        t2_opps.add(get_opp(game, team2))
    common_opps = t1_opps.intersection(t2_opps)
    t1wins = 0
    for game in team1.games:
        if get_opp(game, team1) in common_opps:
            t1wins += wins_from_game(game, team1)
    t2wins = 0
    for game in team2.games:
        if get_opp(game, team2) in common_opps:
            t2wins += wins_from_game(game, team2)
    if t1wins > t2wins:
        return Result.T1WIN
    elif t2wins > t1wins:
        return Result.T2WIN
    return Result.TIE

# Record in conference
def tiebreaker4(team1, team2):
    t1wins = 0
    for game in team1.games:
        opp = get_opp(game, team1)
        if team_info[opp]["DIV"].startswith(team_info[team1.code]["DIV"]):
            # opponent in same conference
            is_t1 = is_team1(game, team1)
            t1wins += wins_from_game(game, is_t1)
    t2wins = 0
    for game in team2.games:
        opp = get_opp(game, team2)
        if team_info[opp]["DIV"].startswith(team_info[team2.code]["DIV"]):
            # opponent in same conference
            is_t1 = is_team1(game, team2)
            t2wins += wins_from_game(game, is_t1)
    if t1wins > t2wins:
        return Result.T1WIN
    elif t2wins > t1wins:
        return Result.T2WIN
    return Result.TIE

# Coin flip
def tiebreaker5(team1, team2):
    return Result.T1WIN if random.random() < 0.5 else Result.T2WIN