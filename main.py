import pandas as pd
import random
import time
from datetime import datetime
from tiebreakers import Tiebreakers, Result

standings_url = "https://api.mysportsfeeds.com/v2.1/pull/nfl/2022-2023-regular/standings.json"
key = "620395f2-bb1d-4a47-b464-697aec"
division_names = ["AFC EAST", "AFC NORTH", "AFC WEST", "AFC SOUTH", "NFC EAST", "NFC NORTH", "NFC WEST", "NFC SOUTH"]
num_epochs = 10000
elo_file = "nfl_elo.csv"
info_file = "team_info.csv"

class LeagueInfo:
    def __init__(self, info_file):
        raw_team_info = pd.read_csv(info_file)
        # Turn raw_team_info into map of maps by team_id
        self.team_info = {}
        ids = raw_team_info["ABBR"]
        rest = raw_team_info.drop("ABBR", axis=1)
        for id in ids:
            self.team_info[id] = {}
        for row in range(raw_team_info.shape[0]):
            for col in rest.columns:
                self.team_info[ids[row]][col] = rest.loc[row, col]

class Team:
    def __init__(self, name, abb, wins, losses, ties, divName, conf):
        self.name = name
        self.abb = abb
        self.wins = wins
        self.losses = losses
        self.ties = ties
        self.playoff_elo = 0
        self.playoff_seed = 0
        self.divName = divName
        self.conf = conf
        self.games = []
        self.wlt = 0
    def add_game(self, game):
        if game.t1abb == self.abb:
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
        self.games.append(game)
        self._calc_wlt()
    def _calc_wlt(self):
        self.wlt = (self.wins + 0.5*self.ties) / len(self.games)
    def __repr__(self):
        if self.ties > 0:
            return self.name + " (" + str(self.wins) + "-" + str(self.losses) + "-" + str(self.ties) + ")"
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __str__(self):
        return self.__repr__()
    def __gt__(self, other):
        return self.wlt > other.wlt
    def __eq__(self, other):
        return self.wlt == other.wlt
    def __hash__(self):
        return hash(self.abb)
    def same(self, other):
        return self.abb == other.abb

class Game:
    def __init__(self, t1abb, t2abb, result):
        self.t1abb = t1abb
        self.t2abb = t2abb
        self.result = result
    def __repr__(self):
        if self.result == Result.T1WIN:
            return "(" + self.t1abb + " beat " + self.t2abb + ")"
        if self.result == Result.T1LOSS:
            return "(" + self.t2abb + " beat " + self.t1abb + ")"
        return "(" + self.t1abb + " tied " + self.t2abb + ")"
    def __str__(self):
        return self.__repr__()

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
        return self.__repr__()

class Standings:
    def __init__(self, league_info, past_results):
        self.league_info = league_info
        # create conferences, fill divisions with teams, fill teams with info / games
        # Key it by team abbreviations
        self.teams = {}
        self.afc = {"AFC EAST":[], "AFC NORTH":[], "AFC WEST":[], "AFC SOUTH":[]}
        self.nfc = {"NFC EAST":[], "NFC NORTH":[], "NFC WEST":[], "NFC SOUTH":[]}
        
        # Populate Team dict
        for abb in league_info.team_info:
            name = league_info.team_info[abb]["NAME"]
            wins = 0
            losses = 0
            ties = 0
            divName = league_info.team_info[abb]["DIV"]
            conf = divName.split(" ")[0]
            t = Team(name, abb, wins, losses, ties, divName, conf)
            self.teams[abb] = t

        # Populate AFC and NFC
        for team in self.teams.values():
            if team.conf == "AFC":
                self.afc[team.divName].append(team)
            else:
                self.nfc[team.divName].append(team)

        # Add past game results
        for row in range(past_results.shape[0]):
            t1 = past_results.iloc[row, past_results.columns.get_loc("team1")].upper()
            t2 = past_results.iloc[row, past_results.columns.get_loc("team2")].upper()
            s1 = past_results.iloc[row, past_results.columns.get_loc("score1")]
            s2 = past_results.iloc[row, past_results.columns.get_loc("score2")]
            result = Result.T1WIN if s1 > s2 else Result.T1LOSS if s2 > s1 else Result.TIE
            self.add_result(t1, t2, result)

        # Copy the teams dict to be re-used as template for each epoch
        self.orig_teams = self.teams.copy()
    def add_result(self, t1abbr, t2abbr, result):
        game = Game(t1abbr, t2abbr, result)
        self.teams[t1abbr].add_game(game)
        self.teams[t2abbr].add_game(game)
    def update_elo(self, abb, elo):
        self.teams[abb].playoff_elo = elo
    def reset(self):
        self.teams = self.orig_teams.copy()

    # def __repr__(self):
    #     s = ""
    #     for d in self.afc:
    #         s += str(d) + "\n"
    #     for d in self.nfc:
    #         s += str(d) + "\n"
    #     return s 

class PlayoffResults:
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
    # TODO: Make this more sophisticated using 538 methodology
    # Update ELO's after every game, make adjustments
    elo_diff = team1.playoff_elo - team2.playoff_elo
    prob1 = 1 / (10 ** (-elo_diff / 400) + 1)
    return team1 if random.random() <= prob1 else team2

def update_row_elo(standings, team1, team2, elo1_pre, elo2_pre):
    standings.update_elo(team1, elo1_pre)
    standings.update_elo(team2, elo2_pre)

def get_last_elos(standings, past_results):
    # get elo's from last week of past_results
    last_date = past_results[past_results.playoff.isna()].tail(1).dateObject.iloc[0]
    last_date_minus1 = last_date - pd.Timedelta(days=1)
    last_week = past_results[(past_results.dateObject == last_date) | (past_results.dateObject == last_date_minus1)]

    for row in range(last_week.shape[0]):
        team1 = last_week.iloc[row, last_week.columns.get_loc("team1")]
        team2 = last_week.iloc[row, last_week.columns.get_loc("team2")]
        standings.update_elo(team1, last_week.iloc[row, last_week.columns.get_loc("elo1_pre")])
        standings.update_elo(team2, last_week.iloc[row, last_week.columns.get_loc("elo2_pre")])
    # last_week.apply(lambda row: update_row_elo(standings, row.team1, row.team2, row.elo1_pre, row.elo2_pre), axis=1)

def sim_reg_game(standings, team1, team2, elo_prob1, elo_pre1, elo_pre2):
    rand = random.random() # TODO: maybe generate rands vectorized at start?
    result = Result.T1WIN if rand <= elo_prob1 else Result.T1LOSS
    standings.update_elo(team1, elo_pre1)
    standings.update_elo(team2, elo_pre2)
    standings.add_result(team1, team2, result)

if __name__ == "__main__":
    time0 = time.time()
    league_info = LeagueInfo(info_file)
    season = datetime(year=2022, month=9, day=1)

    # start_date = datetime.now() # use today's date to stay current
    start_date = datetime.strptime("9-1-2022", "%m-%d-%Y")
    elo = pd.read_csv(elo_file)
    elo = elo[elo["playoff"].isna()]
    elo["dateObject"] = elo["date"].apply((lambda x: datetime.strptime(x, "%Y-%m-%d")))
    past_results = elo[(elo["dateObject"] < start_date) & (elo["dateObject"] >= season)]
    rem_games = elo[elo["dateObject"] >= start_date]

    # encoded_auth = "Basic " + base64.b64encode('{}:{}'.format(key,"MYSPORTSFEEDS").encode('utf-8')).decode('ascii')
    # r = requests.get(standings_url, headers={"Authorization": encoded_auth})
    # info = r.json()["teams"]
    
    tiebreakers = Tiebreakers(league_info.team_info)

    # 1. Standings contain info from API for already-played games
    # 2. Get remaining game info from elo rankings CSV
    # 3. Simulate remaining games acc. to elo rankings
    # 4. Get playoff seedings
    # 5. Simulate playoffs and get Super Bowl champion
    # 6. Repeat many times to get probabilities of playoffs and super bowl

    results = PlayoffResults()
    standings = Standings(league_info, past_results)

    for i in range(num_epochs):
        if i % 100 == 0:
            print(str(i) + "/" + str(num_epochs))

        # for each row, updates elo's, gathers probs and team abbrevations,
        # sims the game, and logs the result - how to vectorize?

        # TODO: this is the bottleneck
        # Getting: team1, team2, elo_prob1, elo1_pre, elo2_pre
        # # Sim remaining games
        # for index, row in rem_games.iterrows():
        #     team1 = row.team1
        #     team2 = row.team2
        #     prob = row.elo_prob1 # prob that team1 wins
        #     standings.update_elo(team1, row.elo1_pre)
        #     standings.update_elo(team2, row.elo2_pre)
        #     rand = random.random()
        #     result = Result.T1WIN if rand <= prob else Result.T1LOSS
        #     standings.add_result(team1, team2, result)
        rem_games.apply(lambda row: sim_reg_game(standings, row.team1, row.team2, row.elo_prob1, row.elo1_pre, row.elo2_pre), axis=1)

        if rem_games.empty:
            get_last_elos(standings, past_results)

        # if i % 100 == 0:
        #     print(standings)
        # Determine seedings
        # TODO: look into tiebreaker efficiency a bit (maybe no improvement)
        afc_seeds, nfc_seeds = tiebreakers.get_playoff_seeds(standings)
        # print(afc_seeds)
        # print(nfc_seeds)
        for ind, team in enumerate(afc_seeds):
            team.playoff_seed = ind + 1

        for ind, team in enumerate(nfc_seeds):
            team.playoff_seed = ind + 1

        # TODO: This is all pretty fast
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

        standings.reset()
    
    print(results)
    time1 = time.time()
    print("Total Time: " + str(round(time1 - time0, 1)) + "s")
    
    