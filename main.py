import pandas as pd
import requests
import base64
import json
import random
from datetime import datetime, timedelta
from tiebreakers import Tiebreakers, Result

standings_url = "https://api.mysportsfeeds.com/v2.1/pull/nfl/2022-2023-regular/standings.json"
key = "620395f2-bb1d-4a47-b464-697aec"
division_names = ["AFC EAST", "AFC NORTH", "AFC WEST", "AFC SOUTH", "NFC EAST", "NFC NORTH", "NFC WEST", "NFC SOUTH"]
num_epochs = 1000
elo_file = "nfl_elo_22-23.csv"
info_file = "team_info.csv"

class LeagueInfo:
    def __init__(self, info_file):
        raw_team_info = pd.read_csv(info_file)
        # Create map of team abbreviations to team codes
        self.abbs_to_codes = dict(zip(raw_team_info["ABBR"].to_list(), raw_team_info["CODE"].to_list()))
        # Turn raw_team_info into map of maps by team_id
        self.team_info = {}
        ids = raw_team_info["CODE"]
        rest = raw_team_info.drop("CODE", axis=1)
        for id in ids:
            self.team_info[id] = {}
        for row in range(raw_team_info.shape[0]):
            for col in rest.columns:
                self.team_info[ids[row]][col] = rest.loc[row, col]

class Team:
    def __init__(self, name, code, wins, losses, ties, divName, conf):
        self.name = name
        self.code = code
        self.wins = wins
        self.losses = losses
        self.ties = ties
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
        self.games.append(game)
    def wlt(self):
        return (self.wins + 0.5*self.ties) / len(self.games)
    def __repr__(self):
        if self.ties > 0:
            return self.name + " (" + str(self.wins) + "-" + str(self.losses) + "-" + str(self.ties) + ")"
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __str__(self):
        if self.ties > 0:
            return self.name + " (" + str(self.wins) + "-" + str(self.losses) + "-" + str(self.ties) + ")"
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __gt__(self, other):
        return self.wlt() > other.wlt()
    def __eq__(self, other):
        # allows comparison between Team object and int, respresenting a team code
        if isinstance(other, int):
            return self.code == other
        return self.wlt() == other.wlt()
    def __hash__(self):
        return hash(self.code)
    def same(self, other):
        return self.name == other.name

class Game:
    def __init__(self, t1code, t2code, result):
        self.t1code = t1code
        self.t2code = t2code
        self.result = result
    # def __repr__(self):
    #     if self.result == Result.T1WIN:
    #         return "(" + team_info[self.t1code]["ABBR"] + " beat " + team_info[self.t2code]["ABBR"] + ")"
    #     if self.result == Result.T1LOSS:
    #         return "(" + team_info[self.t2code]["ABBR"] + " beat " + team_info[self.t1code]["ABBR"] + ")"
    #     return "(" + team_info[self.t1code]["ABBR"] + " tied " + team_info[self.t2code]["ABBR"] + ")"
    # def __str__(self):
    #     if self.result == Result.T1WIN:
    #         return "(" + team_info[self.t1code]["ABBR"] + " beat " + team_info[self.t2code]["ABBR"] + ")"
    #     if self.result == Result.T1LOSS:
    #         return "(" + team_info[self.t2code]["ABBR"] + " beat " + team_info[self.t1code]["ABBR"] + ")"
    #     return "(" + team_info[self.t1code]["ABBR"] + " tied " + team_info[self.t2code]["ABBR"] + ")"

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
    def __init__(self, league_info, past_results):
        self.league_info = league_info
        # create conferences, fill divisions with teams, fill teams with info / games
        self.afc = []
        self.nfc = []
        for d in division_names[:4]:
            self.afc.append(Division(d))
        for d in division_names[4:]:
            self.nfc.append(Division(d))

        for code in league_info.team_info:
            name = league_info.team_info[code]["NAME"]
            wins = 0
            losses = 0
            ties = 0
            divName = league_info.team_info[code]["DIV"]
            conf = divName.split(" ")[0]
            t = Team(name, code, wins, losses, ties, divName, conf)
            divIndex = division_names.index(divName)
            # add new team object to its division
            if divIndex < 4:
                self.afc[divIndex].teams.append(t)
            else:
                self.nfc[divIndex-4].teams.append(t)

        # Add past game results
        for row in range(past_results.shape[0]):
            t1 = league_info.abbs_to_codes[past_results.iloc[row, past_results.columns.get_loc("team1")]]
            t2 = league_info.abbs_to_codes[past_results.iloc[row, past_results.columns.get_loc("team2")]]
            s1 = past_results.iloc[row, past_results.columns.get_loc("score1")]
            s2 = past_results.iloc[row, past_results.columns.get_loc("score2")]
            result = Result.T1WIN if s1 > s2 else Result.T1LOSS if s2 > s1 else Result.TIE
            self.add_result(t1, t2, result)
        
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
                if self.league_info.abbs_to_codes[team] == t.code:
                    t.playoff_elo = elo
                    return
        for d in self.nfc:
            for t in d.teams:
                if self.league_info.abbs_to_codes[team] == t.code:
                    t.playoff_elo = elo
                    return
    def reset(self, team_info):
        # # TODO: Fix this to get wins, losses, ties from 538 data
        # for code in team_info:
        #     wins = team_info["stats"]["standings"]["wins"]
        #     losses = team["stats"]["standings"]["losses"]
        #     ties = team["stats"]["standings"]["ties"]
        #     for d in self.afc:
        #         for t in d.teams:
        #             if code == t.code:
        #                 t.wins = wins
        #                 t.losses = losses
        #                 t.ties = ties
        #     for d in self.nfc:
        #         for t in d.teams:
        #             if code == t.code:
        #                 t.wins = wins
        #                 t.losses = losses
        #                 t.ties = ties
        return

    def __repr__(self):
        s = ""
        for d in self.afc:
            s += str(d) + "\n"
        for d in self.nfc:
            s += str(d) + "\n"
        return s 

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

def get_last_elos(standings, past_results):
    # get elo's from last week of past_results
    last_date = past_results[past_results.playoff.isna()].tail(1).dateObject.iloc[0]
    last_date_minus1 = last_date - pd.Timedelta(days=1)
    last_week = past_results[(past_results.dateObject == last_date) | (past_results.dateObject == last_date_minus1)]
    for index, row in last_week.iterrows():
        team1 = row.team1
        team2 = row.team2
        code1 = standings.league_info.abbs_to_codes[team1]
        code2 = standings.league_info.abbs_to_codes[team2]
        prob = row.elo_prob1 # prob that team1 wins
        standings.update_elo(team1, row.elo1_pre)
        standings.update_elo(team2, row.elo2_pre)

# Sims a specific year in history, loading in all regular season results and simulating the playoffs
# def sim_season(year):
#     elo = pd.read_csv("nfl_elo.csv")
#     raw_team_info = pd.read_csv("team_info.csv")

#     elo = elo[elo["playoff"].isna()]
#     elo["dateObject"] = elo["date"].apply((lambda x: datetime.strptime(x, "%Y-%m-%d")))
#     past_results = elo[elo["dateObject"] < start_date]
#     rem_games = elo[elo["dateObject"] >= start_date]

#     encoded_auth = "Basic " + base64.b64encode('{}:{}'.format(key,"MYSPORTSFEEDS").encode('utf-8')).decode('ascii')
#     r = requests.get(standings_url, headers={"Authorization": encoded_auth})
#     info = r.json()["teams"]

#     # Create map of team abbreviations to team codes
#     abbs_to_codes = dict(zip(raw_team_info["ABBR"].to_list(), raw_team_info["CODE"].to_list()))
#     # Turn raw_team_info into map of maps by team_id
#     team_info = {}
#     ids = raw_team_info["CODE"]
#     rest = raw_team_info.drop("CODE", axis=1)
#     for id in ids:
#         team_info[id] = {}
#     for row in range(raw_team_info.shape[0]):
#         for col in rest.columns:
#             team_info[ids[row]][col] = rest.loc[row, col]
    
#     tiebreakers = Tiebreakers(abbs_to_codes, team_info)

#     # 1. Standings contain info from API for already-played games
#     # 2. Get remaining game info from elo rankings CSV
#     # 3. Simulate remaining games acc. to elo rankings
#     # 4. Get playoff seedings
#     # 5. Simulate playoffs and get Super Bowl champion
#     # 6. Repeat many times to get probabilities of playoffs and super bowl

#     results = PlayoffResults()

#     for i in range(num_epochs):
#         if i % 100 == 0:
#             print(str(i) + "/" + str(num_epochs))
#         # First load standings at current week --> each team wins and losses, organized by division / conferences
#         standings = Standings(info, past_results)
#         # Sim remaining games
#         for index, row in rem_games.iterrows():
#             team1 = row.team1
#             team2 = row.team2
#             code1 = abbs_to_codes[team1]
#             code2 = abbs_to_codes[team2]
#             prob = row.elo_prob1 # prob that team1 wins
#             standings.update_elo(team1, row.elo1_pre)
#             standings.update_elo(team2, row.elo2_pre)
#             rand = random.random()
#             result = Result.T1WIN if rand <= prob else Result.T1LOSS
#             standings.add_result(code1, code2, result)

#         if rem_games.empty:
#             get_last_elos(standings, past_results)

#         # Determine seedings
#         afc_seeds, nfc_seeds = tiebreakers.get_playoff_seeds(standings)
#         # print(afc_seeds)
#         # print(nfc_seeds)
#         for ind, team in enumerate(afc_seeds):
#             team.playoff_seed = ind + 1

#         for ind, team in enumerate(nfc_seeds):
#             team.playoff_seed = ind + 1

#         # sim the playoffs
#         # WILD CARD ROUND
#         awc1 = sim_game(afc_seeds[1], afc_seeds[6])
#         awc2 = sim_game(afc_seeds[2], afc_seeds[5])
#         awc3 = sim_game(afc_seeds[3], afc_seeds[4])
#         nwc1 = sim_game(nfc_seeds[1], nfc_seeds[6])
#         nwc2 = sim_game(nfc_seeds[2], nfc_seeds[5])
#         nwc3 = sim_game(nfc_seeds[3], nfc_seeds[4])

#         # DIVISIONAL ROUND
#         # reseed with sorting
#         afc_rem = [awc1, awc2, awc3]
#         afc_rem = sorted(afc_rem, key=lambda x: x.playoff_seed)
#         nfc_rem = [nwc1, nwc2, nwc3]
#         nfc_rem = sorted(nfc_rem, key=lambda x: x.playoff_seed)

#         adv1 = sim_game(afc_seeds[0], afc_rem[2])
#         adv2 = sim_game(afc_rem[0], afc_rem[1])
#         ndv1 = sim_game(nfc_seeds[0], nfc_rem[2])
#         ndv2 = sim_game(nfc_rem[0], nfc_rem[1])

#         # CONFERENCE ROUND
#         acf = sim_game(adv1, adv2)
#         ncf = sim_game(ndv1, ndv2)
        
#         # SUPER BOWL
#         sb = sim_game(acf, ncf)

if __name__ == "__main__":
    league_info = LeagueInfo(info_file)

    start_date = datetime.now() # use today's date to stay current
    elo = pd.read_csv(elo_file)
    elo = elo[elo["playoff"].isna()]
    elo["dateObject"] = elo["date"].apply((lambda x: datetime.strptime(x, "%Y-%m-%d")))
    past_results = elo[elo["dateObject"] < start_date]
    rem_games = elo[elo["dateObject"] >= start_date]

    # encoded_auth = "Basic " + base64.b64encode('{}:{}'.format(key,"MYSPORTSFEEDS").encode('utf-8')).decode('ascii')
    # r = requests.get(standings_url, headers={"Authorization": encoded_auth})
    # info = r.json()["teams"]
    
    tiebreakers = Tiebreakers(league_info.abbs_to_codes, league_info.team_info)

    # 1. Standings contain info from API for already-played games
    # 2. Get remaining game info from elo rankings CSV
    # 3. Simulate remaining games acc. to elo rankings
    # 4. Get playoff seedings
    # 5. Simulate playoffs and get Super Bowl champion
    # 6. Repeat many times to get probabilities of playoffs and super bowl

    results = PlayoffResults()

    for i in range(num_epochs):
        if i % 100 == 0:
            print(str(i) + "/" + str(num_epochs))
        # First load standings at current week --> each team wins and losses, organized by division / conferences
        standings = Standings(league_info, past_results)
        # Sim remaining games
        for index, row in rem_games.iterrows():
            team1 = row.team1
            team2 = row.team2
            code1 = league_info.abbs_to_codes[team1]
            code2 = league_info.abbs_to_codes[team2]
            prob = row.elo_prob1 # prob that team1 wins
            standings.update_elo(team1, row.elo1_pre)
            standings.update_elo(team2, row.elo2_pre)
            rand = random.random()
            result = Result.T1WIN if rand <= prob else Result.T1LOSS
            standings.add_result(code1, code2, result)

        if rem_games.empty:
            get_last_elos(standings, past_results)

        # Determine seedings
        afc_seeds, nfc_seeds = tiebreakers.get_playoff_seeds(standings)
        # print(afc_seeds)
        # print(nfc_seeds)
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
    
    print(results)
    
    