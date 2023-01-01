import pandas as pd
import requests
import base64
import json
import time
import random
from datetime import date, datetime
from enum import Enum
from tiebreakers import two_team_div_tiebreaker, two_team_wc_tiebreaker, threeplus_team_div_tiebreaker, threeplus_team_wc_tiebreaker

# TODO:
# - create two-team and three-plus-team tiebreaker functions, which call individual tiebreaker functions
# - diff functions for division and wild card

standings_url = "https://api.mysportsfeeds.com/v2.1/pull/nfl/2022-2023-regular/standings.json"
key = "620395f2-bb1d-4a47-b464-697aec"
division_names = ["AFC East", "AFC North", "AFC West", "AFC South", "NFC East", "NFC North", "NFC West", "NFC South"]
num_epochs = 50000

abbs_to_codes = None
team_info = None # map of team codes to dicts containing abbr, name, division name

class Result(Enum):
    T1WIN = 0
    T1LOSS = 1
    TIE = 2

def wins_from_game(game, is_t1):
    if is_t1:
        if game.result == Result.T1WIN:
            return 1
        elif game.result == Result.T1LOSS:
            return 0
        else:
            return 0.5
    else:
        if game.result == Result.T1WIN:
            return 0
        elif game.result == Result.T1LOSS:
            return 1
        else:
            return 0.5


def get_division_champ(div):
    # division has a list of Team objects
    div.teams.sort()
    # find out how many teams are tied (2-4)
    for i in range(1, len(div.teams)):
        if div.teams[i] != div.teams[0]:
            break
    tied = div.teams[:i]
    if len(tied) == 1: # no ties, return top team
        return div.teams[0]
    if len(tied) == 2: # two teams tied
        # do first 4 tiebreakers, then just coinflip
        tb1 = tiebreaker1(tied[0], tied[1])
        if tb1 != Result.TIE:
            return tied[0] if tb1 == Result.T1WIN else tied[1]
        tb2 = tiebreaker2(tied[0], tied[1])
        if tb2 != Result.TIE:
            return tied[0] if tb2 == Result.T1WIN else tied[1]
        tb3 = tiebreaker3(tied[0], tied[1])
        if tb3 != Result.TIE:
            return tied[0] if tb3 == Result.T1WIN else tied[1]
        tb4 = tiebreaker4(tied[0], tied[1])
        if tb4 != Result.TIE:
            return tied[0] if tb4 == Result.T1WIN else tied[1]
        tb5 = tiebreaker5(tied[0], tied[1])
        return tied[0] if tb5 == Result.T1WIN else tied[1]
    if len(tied) > 2:
        # TODO: handle 3 team+ division ties
        return tied[0]

def get_wildcards(standings, div_champs):
    # TODO: write get wildcards function for a conference
    rem_teams = []
    for d in standings.afc:
        rem_teams.extend(d.teams)
    for d in standings.nfc:
        rem_teams.extend(d.teams)
    rem_teams = list(set(rem_teams).difference(div_champs))
    # Figure out tiebreakers
    rem_teams.sort()
    wildcards = []
    i = 0
    j = 1
    while len(wildcards) < 3:
        while rem_teams[i] == rem_teams[j]:
            j += 1
        if j - i == 1: # If no ties
            wildcards.append(rem_teams[i])
            i = j
            j += 1
        elif j - i == 2: # If two teams tied
            winner = 
        elif j - i > 2: # If three or more teams tied

        else:
            # shouldn't be here

    return
        
def is_team1(game, team1):
    return abbs_to_codes[game.winner] == team1.code

def get_opp(game, team1):
    is_t1 = is_team1(game, team1)
    opp = game.t1code if is_t1 else game.t2code
    return opp
        
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

class Team:
    def __init__(self, name, code, wins, losses, ties, divRank, divName, conf):
        self.name = name
        self.code = code
        self.wins = wins
        self.losses = losses
        self.ties = ties
        self.divRank = divRank
        self.playoff_elo = 0
        self.playoff_seed = 0
        self.divName = divName
        self.conf = conf
        self.games = []
    def add_game(self, game):
        if game.t1code == self.code:
            if game.result == Result.T1WIN:
                self.wins += 1
            elif game.result == Result.T1LOSS:
                self.losses += 1
            else:
                self.ties += 1
        else:
            if game.result == Result.T1WIN:
                self.losses += 1
            elif game.result == Result.T1LOSS:
                self.wins += 1
            else:
                self.ties += 1
    def __repr__(self):
        if self.ties > 0:
            return self.name + " (" + str(self.wins) + "-" + str(self.losses) + "-" + str(self.ties) + ")"
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __str__(self):
        if self.ties > 0:
            return self.name + " (" + str(self.wins) + "-" + str(self.losses) + "-" + str(self.ties) + ")"
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __gt__(self, other):
        return self.wins + 0.5 * self.ties > other.wins + 0.5 * other.ties
    def __eq__(self, other):
        # allows comparison between Team object and int, respresenting a team code
        if isinstance(other, int):
            return self.code == other
        # otherwise compare two Team objects
        return self.wins == other.wins and self.losses == other.losses
    def __hash__(self):
        return hash(self.code)
    def same(self, other):
        return self.name == other.name

class Game:
    def __init__(self, t1code, t2code, result):
        self.t1code = t1code
        self.t2code = t2code
        self.result = result

class Division:
    def __init__(self, name):
        # teams is a list of Team objects, empty at init
        self.name = name
        self.teams = []
    def __repr__(self):
        s = self.name + ":\n"
        for t in self.teams:
            s += str(t) + "\n"
        return s
    def __str__(self):
        s = self.name + ":\n"
        for t in self.teams:
            s += str(t) + "\n"
        return s

class Standings:
    def __init__(self, info):
        # create conferences, fill divisions with teams, fill teams with info / games
        self.afc = []
        self.nfc = []
        for d in division_names[:4]:
            self.afc.append(Division(d))
        for d in division_names[4:]:
            self.nfc.append(Division(d))

        for team in info:
            name = team["team"]["city"] + " " + team["team"]["name"]
            code = team["team"]["id"]
            wins = team["stats"]["standings"]["wins"]
            losses = team["stats"]["standings"]["losses"]
            ties = team["stats"]["standings"]["ties"]
            divRank = team["divisionRank"]["rank"]
            divName = team["divisionRank"]["divisionName"]
            divIndex = division_names.index(divName)
            conf = 0 if divIndex < 4 else 1 # conf = 0 if AFC, 1 if NFC
            t = Team(name, code, wins, losses, ties, divRank, divName, conf)
            # add new team object to its division
            if divIndex < 4:
                self.afc[divIndex].teams.append(t)
            else:
                self.nfc[divIndex-4].teams.append(t)
        
    def add_result(self, t1code, t2code, result):
        # search both afc and nfc for winning and losing teams
        game = Game(t1code, t2code, result)
        for d in self.afc:
            for t in d.teams:
                if t.code == t1code:
                    # update winning team
                    t.add_game(game)
                if t.code == t2code:
                    t.add_game(game)
        for d in self.nfc:
            for t in d.teams:
                if t.code == t1code:
                    # update winning team
                    t.add_game(game)
                if t.code == t2code:
                    t.add_game(game)
    def update_elo(self, team, elo):
        for d in self.afc:
            for t in d.teams:
                if abbs_to_codes[team] == t.code:
                    t.playoff_elo = elo
                    return
        for d in self.nfc:
            for t in d.teams:
                if abbs_to_codes[team] == t.code:
                    t.playoff_elo = elo
                    return
    def get_playoff_seedings(self):
        # returns two lists, with 7 playoff seeds in AFC and NFC
        afc_seeds = []
        nfc_seeds = []
        # sort divisions
        for d in self.afc:
            d.teams.sort(reverse=True)
        for d in self.nfc:
            d.teams.sort(reverse=True)
        # add four division champs
        for d in self.afc:
            afc_seeds.append(d.teams[0])
        afc_seeds.sort(reverse=True)
        # add three wild cards
        afc_wild = []
        for d in self.afc:
            afc_wild.extend(d.teams[1:])
        afc_wild.sort(reverse=True)
        afc_seeds.extend(afc_wild[:3])

        # repeat for NFC
        # add four division champs
        for d in self.nfc:
            nfc_seeds.append(d.teams[0])
        nfc_seeds.sort(reverse=True)
        # add three wild cards
        nfc_wild = []
        for d in self.nfc:
            nfc_wild.extend(d.teams[1:])
        nfc_wild.sort(reverse=True)
        nfc_seeds.extend(nfc_wild[:3])

        assert len(afc_seeds) == 7
        assert len(nfc_seeds) == 7
        return afc_seeds, nfc_seeds
    def reset(self, info):
        for team in info:
            code = team["team"]["id"]
            wins = team["stats"]["standings"]["wins"]
            losses = team["stats"]["standings"]["losses"]
            ties = team["stats"]["standings"]["ties"]
            for d in self.afc:
                for t in d.teams:
                    if code == t.code:
                        t.wins = wins
                        t.losses = losses
                        t.ties = ties
            for d in self.nfc:
                for t in d.teams:
                    if code == t.code:
                        t.wins = wins
                        t.losses = losses
                        t.ties = ties

    def __repr__(self):
        s = ""
        for d in self.afc:
            s += str(d) + "\n"
        for d in self.nfc:
            s += str(d) + "\n"
        return s 

class Results:
    def __init__(self):
        self.teams_to_sbs = dict()
        self.epochs = 0
    def add_result(self, sb_winner):
        if sb_winner.name not in self.teams_to_sbs:
            self.teams_to_sbs[sb_winner.name] = 1
        else:
            self.teams_to_sbs[sb_winner.name] += 1
        self.epochs += 1
    def __repr__(self):
        out = ""
        sorted_teams = sorted(self.teams_to_sbs.items(), key=lambda x: x[1], reverse=True)
        for t in sorted_teams:
            win_pct = t[1] / self.epochs
            out += t[0] + ": " + "{:.2%}".format(win_pct) + " (" + str(t[1]) + " SB wins)\n"
        return out  

def sim_game(team1, team2):
    # simulates a game result using elo ratings
    # doesn't allow ties
    elo_diff = team1.playoff_elo - team2.playoff_elo
    prob1 = 1 / (10 ** (-elo_diff / 400) + 1)
    return team1 if random.random() <= prob1 else team2

if __name__ == "__main__":
    elo = pd.read_csv("nfl_elo_latest.csv")
    raw_team_info = pd.read_csv("team_info.csv")

    encoded_auth = "Basic " + base64.b64encode('{}:{}'.format(key,"MYSPORTSFEEDS").encode('utf-8')).decode('ascii')
    r = requests.get(standings_url, headers={"Authorization": encoded_auth})
    info = r.json()["teams"]

    # Create map of team abbreviations to team codes
    abbs_to_codes = dict(zip(raw_team_info["ABBR"].to_list(), raw_team_info["CODE"].to_list()))

    # First load standings at current week --> each team wins and losses, organized by division / conferences
    standings = Standings(info)

    # 1. Standings contain info from API for already-played games
    # 2. Get remaining game info from elo rankings CSV
    # 3. Simulate remaining games acc. to elo rankings
    # 4. Get playoff seedings
    # 5. Simulate playoffs and get Super Bowl champion
    # 6. Repeat many times to get probabilities of playoffs and super bowl

    elo["dateObject"] = elo["date"].apply((lambda x: datetime.strptime(x, "%Y-%m-%d")))

    start_date = datetime.now() # use today's date to stay current

    rem_games = elo[elo["dateObject"] >= start_date]

    results = Results()

    for i in range(num_epochs):
        if i % 100 == 0:
            print(str(i) + "/" + str(num_epochs))
        sub_elo = elo[elo["dateObject"] >= start_date]
        # Sim remaining games
        for index, row in rem_games.iterrows():
            team1 = row.team1
            team2 = row.team2
            code1 = abbs_to_codes[team1]
            code2 = abbs_to_codes[team2]
            prob = row.elo_prob1 # prob that team1 wins
            standings.update_elo(team1, row.elo1_pre)
            standings.update_elo(team2, row.elo2_pre)
            rand = random.random()
            if rand <= prob: # team 1 wins
                standings.add_result(code1, code2, Result.T1WIN)
                #print("Winner: " + team1 + ", Loser: " + team2)
            else: # team 2 wins
                standings.add_result(code1, code2, Result.T1LOSS)
                #print("Winner: " + team2 + ", Loser: " + team1)
            
        # Determine seedings
        afc_seeds, nfc_seeds = standings.get_playoff_seedings()
        for ind, team in enumerate(afc_seeds):
            team.playoff_seed = ind + 1

        for ind, team in enumerate(nfc_seeds):
            team.playoff_seed = ind + 1

        # sim the playoffs
        # WILD CARD ROUND
        awc1 = sim_game(afc_seeds[1], afc_seeds[6])
        awc2 = sim_game(afc_seeds[2], afc_seeds[5])
        awc3 = sim_game(afc_seeds[3], afc_seeds[4])
        nwc1 = sim_game(nfc_seeds[1], nfc_seeds[6])
        nwc2 = sim_game(nfc_seeds[2], nfc_seeds[5])
        nwc3 = sim_game(nfc_seeds[3], nfc_seeds[4])

        # DIVISIONAL ROUND
        # reseed with sorting
        afc_rem = [awc1, awc2, awc3]
        afc_rem = sorted(afc_rem, key=lambda x: x.playoff_seed)
        nfc_rem = [nwc1, nwc2, nwc3]
        nfc_rem = sorted(nfc_rem, key=lambda x: x.playoff_seed)

        adv1 = sim_game(afc_seeds[0], afc_rem[2])
        adv2 = sim_game(afc_rem[0], afc_rem[1])
        ndv1 = sim_game(nfc_seeds[0], nfc_rem[2])
        ndv2 = sim_game(nfc_rem[0], nfc_rem[1])

        # CONFERENCE ROUND
        acf = sim_game(adv1, adv2)
        ncf = sim_game(ndv1, ndv2)
        
        # SUPER BOWL
        sb = sim_game(acf, ncf)
        #print("Super bowl champ: " + str(sb))

        # log result
        results.add_result(sb)

        # reset standings
        standings.reset(info)
    
    print(results)
    
    