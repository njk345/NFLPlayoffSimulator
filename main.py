import pandas as pd
import requests
import base64
import json
import time
import random
from datetime import date

class Team:
    def __init__(self, name, code, wins, losses, ties, divRank):
        self.name = name
        self.code = code
        self.wins = wins
        self.losses = losses
        self.ties = ties
        self.divRank = divRank
        self.playoff_elo = 0
        self.playoff_seed = 0
    def __repr__(self):
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __str__(self):
        return self.name + " (" + str(self.wins) + "-" + str(self.losses) + ")"
    def __gt__(self, other):
        return self.wins > other.wins
    def __eq__(self, other):
        return self.wins == other.wins
    def __lt__(self, other):
        return self.wins < other.wins
    def same(self, other):
        return self.name == other.name

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
    def __init__(self, abbs_to_codes):
        # afc and nfc are lists of Division objects (4 in each)
        self.afc = []
        self.nfc = []
        self.abbs_to_codes = abbs_to_codes
    def add_result(self, winner, loser):
        # search both afc and nfc for winning and losing teams
        for d in self.afc:
            for t in d.teams:
                if self.abbs_to_codes[winner] == t.code:
                    # update winning team
                    t.wins += 1
                if self.abbs_to_codes[loser] == t.code:
                    t.losses += 1
        for d in self.nfc:
            for t in d.teams:
                if self.abbs_to_codes[winner] == t.code:
                    # update winning team
                    t.wins += 1
                if self.abbs_to_codes[loser] == t.code:
                    t.losses += 1
    def update_elo(self, team, elo):
        for d in self.afc:
            for t in d.teams:
                if self.abbs_to_codes[team] == t.code:
                    t.playoff_elo = elo
                    return
        for d in self.nfc:
            for t in d.teams:
                if self.abbs_to_codes[team] == t.code:
                    t.playoff_elo = elo
                    return
    def get_playoff_seedings(self):
        # returns two lists, with 7 playoff seeds in AFC and NFC
        afc_seeds = []
        nfc_seeds = []
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
            out += t[0] + ": " + "{:.2%}".format(win_pct) + "\n"
        return out


def convert_date(str):
    str_split = str.split("-")     
    year = int(str_split[0])
    month = int(str_split[1])
    day = int(str_split[2])
    return date(year, month, day)   

def sim_game(team1, team2):
    elo_diff = team1.playoff_elo - team2.playoff_elo
    prob1 = 1 / (10 ** (-elo_diff / 400) + 1)
    return team1 if random.random() <= prob1 else team2

division_names = ["AFC East", "AFC North", "AFC West", "AFC South", "NFC East", "NFC North", "NFC West", "NFC South"]

if __name__ == "__main__":
    elo = pd.read_csv("nfl_elo_latest.csv")
    team_codes = pd.read_csv("team_codes.csv")
    standings_url = "https://api.mysportsfeeds.com/v2.1/pull/nfl/current/standings.json"
    key = "5a534df5-28a6-44d2-be37-ba3dce"

    encoded_auth = "Basic " + base64.b64encode('{}:{}'.format(key,"MYSPORTSFEEDS").encode('utf-8')).decode('ascii')
    r = requests.get(standings_url, headers={"Authorization": encoded_auth})
    info = r.json()["teams"]

    # Create map of team abbreviations to team codes
    abbs_to_codes = dict(zip(team_codes["team"].to_list(), team_codes["code"].to_list()))

    # First load standings at current week --> each team wins and losses, organized by division / conferences
    # (eventually add tiebreaker info)
    standings = Standings(abbs_to_codes)
    for d in division_names[:4]:
        standings.afc.append(Division(d))
    for d in division_names[4:]:
        standings.nfc.append(Division(d))

    for team in info:
        name = team["team"]["city"] + " " + team["team"]["name"]
        code = team["team"]["id"]
        wins = team["stats"]["standings"]["wins"]
        losses = team["stats"]["standings"]["losses"]
        ties = team["stats"]["standings"]["ties"]
        divRank = team["divisionRank"]["rank"]
        divName = team["divisionRank"]["divisionName"]
        t = Team(name, code, wins, losses, ties, divRank)
        divIndex = division_names.index(divName)
        # add new team object to its division
        if divIndex < 4:
            standings.afc[divIndex].teams.append(t)
        else:
            standings.nfc[divIndex-4].teams.append(t)

    #print(elo)

    elo["dateObject"] = elo["date"].apply(convert_date)

    start_date = date.today() # use today's date to stay current
    #print(start_date)

    #print(standings)

    num_epochs = 50000

    results = Results()

    for i in range(num_epochs):
        if i % 100 == 0:
            print(str(i) + "/" + str(num_epochs))
        sub_elo = elo[elo["dateObject"] >= start_date]
        for index, row in sub_elo.iterrows():
            team1 = row.team1
            team2 = row.team2
            prob = row.elo_prob1 # prob that team1 wins
            standings.update_elo(team1, row.elo1_pre)
            standings.update_elo(team2, row.elo2_pre)
            rand = random.random()
            if rand <= prob: # team 1 wins
                standings.add_result(team1, team2)
                #print("Winner: " + team1 + ", Loser: " + team2)
            else: # team 2 wins
                standings.add_result(team2, team1)
                #print("Winner: " + team2 + ", Loser: " + team1)
            

        #print(standings)
        afc_seeds, nfc_seeds = standings.get_playoff_seedings()
        #print(afc_seeds)
        #print(nfc_seeds)
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
    
