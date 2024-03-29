import random
from enum import Enum

class Result(Enum):
    T1WIN = 0
    T1LOSS = 1
    TIE = 2

class Tiebreakers:
    def __init__(self, team_info):
        self.team_info = team_info

    def wins_from_game(self, game, team):
        if self.is_team1(game, team):
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

    def is_team1(self, game, team):
        return team.abb == game.t1abb

    def find_team(self, teams, team):
        for i in range(len(teams)):
            if teams[i].same(team):
                return i

    def get_opp(self, game, team):
        return game.t2abb if self.is_team1(game, team) else game.t1abb

    # div is a list of Teams
    def get_division_champ(self, div):
        div.sort(reverse=True)
        # find out how many teams are tied (2-4)
        i = 1
        while i < len(div):
            if div[i] != div[0]:
                break
            i += 1
        tied = div[:i]
        if len(tied) == 1: # no ties, return top team
            return div[0]
        if len(tied) == 2: # two teams tied
            return self.two_team_div_tiebreaker(tied[0], tied[1])
        if len(tied) > 2:
            return self.threeplus_team_div_tiebreaker(tied)

    def get_wildcards(self, standings, is_afc, div_champs):
        rem_teams = []
        if is_afc:
            for d in standings.afc.values():
                rem_teams.extend(d)
        else:
            for d in standings.nfc.values():
                rem_teams.extend(d)
        rem_teams = list(set(rem_teams).difference(div_champs))
        # Figure out tiebreakers
        rem_teams.sort(reverse=True)
        wildcards = []
        i = 0
        # Fill the wildcards one at a time
        while len(wildcards) < 3:
            i = 0
            while i < len(rem_teams) and rem_teams[0] == rem_teams[i]:
                i += 1
            if i == 1: # If no ties, add first team and continue
                wildcards.append(rem_teams[0])
                rem_teams.pop(0)
            elif i == 2: # If two teams tied, run two-team tiebreaker
                # Determine if from same division or not
                if rem_teams[0].divName == rem_teams[1].divName:
                    winner = self.two_team_div_tiebreaker(rem_teams[0], rem_teams[1])
                else:
                    winner = self.two_team_wc_tiebreaker(rem_teams[0], rem_teams[1])
                if winner.same(rem_teams[0]): # T1 WON
                    wildcards.append(rem_teams[0])
                    rem_teams = rem_teams[1:]
                else: # T2 WON
                    wildcards.append(rem_teams[1])
                    rem_teams.pop(1)
            elif i > 2: # If three or more teams tied
                # Group tied teams by division
                # Find winner of each division using div tiebreakers
                # Finally, compare winner of each division using wc tiebreakers
                # Come up with a single winner of the 3+ team tie (NFL words this so confusingly!)
                tied = rem_teams[:i]
                div_sets = {}
                for team in tied:
                    if team.divName in div_sets:
                        div_sets[team.divName].append(team)
                    else:
                        div_sets[team.divName] = [team]
                div_winners = []
                for div in div_sets.keys():
                    if len(div_sets[div]) == 1:
                        div_winners.append(div_sets[div][0])
                    elif len(div_sets[div]) == 2:
                        div_winners.append(self.two_team_div_tiebreaker(div_sets[div][0], div_sets[div][1]))
                    else:
                        div_winners.append(self.threeplus_team_div_tiebreaker(div_sets[div]))
                if len(div_winners) == 1:
                    winner = div_winners[0]
                elif len(div_winners) == 2:
                    winner = self.two_team_wc_tiebreaker(div_winners[0], div_winners[1])
                else:
                    winner = self.threeplus_team_wc_tiebreaker(div_winners)
                wildcards.append(winner)
                # find winner's original index in rem_teams and remove
                for t in range(len(rem_teams)):
                    if winner.same(rem_teams[t]):
                        break
                rem_teams.pop(t)
            else:
                # shouldn't be here
                raise RuntimeError()
        return wildcards

    def get_playoff_seeds(self, standings):
        # returns two lists, with 7 playoff seeds in AFC and NFC
        # get division champs
        afc_champs = []
        for d in standings.afc.values():
            champ = self.get_division_champ(d)
            afc_champs.append(champ)
        nfc_champs = []
        for d in standings.nfc.values():
            champ = self.get_division_champ(d)
            nfc_champs.append(champ)
        assert len(afc_champs) == 4
        assert len(nfc_champs) == 4

        # sort division champs into 1-4 seeds
        seed1a = self.threeplus_team_wc_tiebreaker(afc_champs)
        afc_champs.pop(self.find_team(afc_champs, seed1a))
        seed2a = self.threeplus_team_wc_tiebreaker(afc_champs)
        afc_champs.pop(self.find_team(afc_champs, seed2a))
        seed3a = self.two_team_wc_tiebreaker(afc_champs[0], afc_champs[1])
        afc_champs.pop(self.find_team(afc_champs, seed3a))
        seed4a = afc_champs[0]
        
        afc_seeds = [seed1a, seed2a, seed3a, seed4a]

        seed1n = self.threeplus_team_wc_tiebreaker(nfc_champs)
        nfc_champs.pop(self.find_team(nfc_champs, seed1n))
        seed2n = self.threeplus_team_wc_tiebreaker(nfc_champs)
        nfc_champs.pop(self.find_team(nfc_champs, seed2n))
        seed3n = self.two_team_wc_tiebreaker(nfc_champs[0], nfc_champs[1])
        nfc_champs.pop(self.find_team(nfc_champs, seed3n))
        seed4n = nfc_champs[0]
        
        nfc_seeds = [seed1n, seed2n, seed3n, seed4n]
        # get wildcard teams
        afc_seeds.extend(self.get_wildcards(standings, True, afc_seeds))
        nfc_seeds.extend(self.get_wildcards(standings, False, nfc_seeds))

        assert len(afc_seeds) == 7
        assert len(nfc_seeds) == 7
        return afc_seeds, nfc_seeds

    # Takes in two team objects and returns the winner after divisional tiebreakers
    # 1. Head-to-head
    # 2. Divisional record
    # 3. Common games
    # 4. Conference record
    # 5. Coin flip
    def two_team_div_tiebreaker(self, team1, team2):
        # the div / wc tiebreakers return a single Team
        if team1 > team2:
            return team1
        elif team2 > team1:
            return team2
        tb1 = self.tiebreaker1(team1, team2)
        if len(tb1) == 1:
            return tb1[0]
        tb2 = self.tiebreaker2(team1, team2)
        if len(tb2) == 1:
            return tb2[0]
        tb3 = self.tiebreaker3(team1, team2, False)
        if len(tb3) == 1:
            return tb3[0]
        tb4 = self.tiebreaker4(team1, team2)
        if len(tb4) == 1:
            return tb4[0]
        tb5 = self.tiebreaker5(team1, team2)
        return tb5[0]

    # Takes in two Team objects and returns the winner after wild card tiebreakers
    # 1. Head-to-head
    # 2. Conference record
    # 3. Common games (minimum of 4)
    # 4. Coin flip
    def two_team_wc_tiebreaker(self, team1, team2):
        if team1 > team2:
            return team1
        elif team2 > team1:
            return team2
        tb1 = self.tiebreaker1(team1, team2)
        if len(tb1) == 1:
            return tb1[0]
        tb2 = self.tiebreaker4(team1, team2)
        if len(tb2) == 1:
            return tb2[0]
        tb3 = self.tiebreaker3(team1, team2, True)
        if len(tb3) == 1:
            return tb3[0]
        tb4 = self.tiebreaker5(team1, team2)
        return tb4[0]

    # Takes in a list of three or more Team objects and returns the winner (1) after divisional tiebreakers
    def threeplus_team_div_tiebreaker(self, teams):    
        # check for if one team has better WLT than others, just like two-way tiebreakers    
        teams.sort(reverse=True)
        # find out how many teams are tied (2-4)
        for i in range(1, len(teams)):
            if teams[i] != teams[0]:
                break
        left = teams[:i]
        if len(left) == 1:
            return left[0]
        if len(left) == 2:
            # restart at 2 team tiebreaker
            return self.two_team_div_tiebreaker(left[0], left[1])
        tiebreakers = [self.tiebreaker6, self.tiebreaker7, self.tiebreaker8, self.tiebreaker9, self.tiebreaker10]
        start_len = len(left)
        for i in range(len(tiebreakers)):
            left = tiebreakers[i](left) if i != 2 else tiebreakers[i](left, False)
            if len(left) == 1:
                # return only team left
                return left[0]
            if len(left) == 2:
                # restart at 2 team tiebreaker
                return self.two_team_div_tiebreaker(left[0], left[1])
            if len(left) < start_len and len(left) >= 3:
                # one team was eliminated, restart at 3 team tiebreaker
                return self.threeplus_team_div_tiebreaker(left) 
            # otherwise, no teams eliminated, proceed with 3 team tiebreakers
        return None

    # Takes in a list of three or more Team objects and returns the winner (1) after wild card tiebreakers
    def threeplus_team_wc_tiebreaker(self, teams):
        # check for if one team has better WLT than others, just like two-way tiebreakers    
        teams.sort(reverse=True)
        # find out how many teams are tied (2-4)
        for i in range(1, len(teams)):
            if teams[i] != teams[0]:
                break
        left = teams[:i]
        if len(left) == 1:
            return left[0]
        if len(left) == 2:
            # restart at 2 team tiebreaker
            return self.two_team_wc_tiebreaker(left[0], left[1])
        tiebreakers = [self.tiebreaker11, self.tiebreaker9, self.tiebreaker8, self.tiebreaker10]
        start_len = len(left)
        for i in range(len(tiebreakers)):
            left = tiebreakers[i](left) if i != 2 else tiebreakers[i](left, True)
            if len(left) == 1:
                return left[0]
            if len(left) == 2:
                # restart at 2 team tiebreaker
                return self.two_team_wc_tiebreaker(left[0], left[1])
            if len(left) < start_len and len(left) >= 3:
                # one team was eliminated, restart at 3 team tiebreaker
                return self.threeplus_team_wc_tiebreaker(left) 
            # otherwise, no teams eliminated, proceed with 3 team tiebreakers
        return None

    # Each tiebreaker returns the list of teams who remain after applied
    # I.e. if 1 team left returns [team1] --> winner, if 2 left returns [team1, team2] --> still tied
    # -------------------------------------------------------------

    # Head-to-head record
    def tiebreaker1(self, team1, team2):
        # Head-to-head team record
        t1wins = 0
        t2wins = 0
        for game in team1.games:
            # abbr of opposing team
            opp = self.get_opp(game, team1)
            if opp == team2.abb:
                # found game against team2
                t1wins += self.wins_from_game(game, team1)
                t2wins += self.wins_from_game(game, team2)
        if t1wins > t2wins:
            return [team1]
        elif t2wins > t1wins:
            return [team2]
        return [team1, team2]

    # In-division record
    def tiebreaker2(self, team1, team2):
        t1wins = 0
        for game in team1.games:
            opp = self.get_opp(game, team1)
            if self.team_info[opp]["DIV"] == team1.divName:
                # teams in same division, count result
                t1wins += self.wins_from_game(game, team1)
        t2wins = 0
        for game in team2.games:
            opp = self.get_opp(game, team2)
            if self.team_info[opp]["DIV"] == team2.divName:
                # teams in same division, count result
                t2wins += self.wins_from_game(game, team2)
        if t1wins > t2wins:
            return [team1]
        elif t2wins > t1wins:
            return [team2]
        return [team1, team2]

    # Record in common opponents
    def tiebreaker3(self, team1, team2, minimum):
        # use sets to find common opponents
        # loop through to get total wins each against common opponents
        t1_opps = set()
        for game in team1.games:
            t1_opps.add(self.get_opp(game, team1))
        t2_opps = set()
        for game in team2.games:
            t2_opps.add(self.get_opp(game, team2))
        common_opps = t1_opps.intersection(t2_opps)
        if minimum and len(common_opps) < 4:
            return [team1, team2]
        t1wins = 0
        for game in team1.games:
            if self.get_opp(game, team1) in common_opps:
                t1wins += self.wins_from_game(game, team1)
        t2wins = 0
        for game in team2.games:
            if self.get_opp(game, team2) in common_opps:
                t2wins += self.wins_from_game(game, team2)
        if t1wins > t2wins:
            return [team1]
        elif t2wins > t1wins:
            return [team2]
        return [team1, team2]

    # Record in conference
    def tiebreaker4(self, team1, team2):
        t1wins = 0
        for game in team1.games:
            opp = self.get_opp(game, team1)
            if self.team_info[opp]["DIV"].startswith(team1.conf):
                # opponent in same conference
                t1wins += self.wins_from_game(game, team1)
        t2wins = 0
        for game in team2.games:
            opp = self.get_opp(game, team2)
            if self.team_info[opp]["DIV"].startswith(team2.conf):
                # opponent in same conference
                t2wins += self.wins_from_game(game, team2)
        if t1wins > t2wins:
            return [team1]
        elif t2wins > t1wins:
            return [team2]
        return [team1, team2]

    # Coin flip
    def tiebreaker5(self, team1, team2):
        return [random.choice([team1, team2])]

    # 3+ team head-to-head
    # returns array of the teams remaining after tiebreaker
    def tiebreaker6(self, teams):
        # For each team, tally record against games against other teams
        abbs = set()
        for t in teams:
            abbs.add(t.abb)
        records = []
        for t in teams:
            tot_wins = 0
            for g in t.games:
                opp = self.get_opp(g, t)
                if opp in abbs:
                    tot_wins += self.wins_from_game(g, t)
            records.append((tot_wins, t))
        records = sorted(records, key=lambda x: x[0], reverse=True)
        # figure out how many teams remained tied
        i = 1
        while i < len(records) and records[i][0] == records[0][0]:
            i += 1
        tied = records[:i]
        return [team[1] for team in tied]
        
    # 3+ team in-division
    def tiebreaker7(self, teams):
        records = []
        for t in teams:
            tot_wins = 0
            for g in t.games:
                opp = self.get_opp(g, t)
                if self.team_info[opp]["DIV"] == t.divName: # game is in-division
                    tot_wins += self.wins_from_game(g, t)
            records.append((tot_wins, t))
        records = sorted(records, key=lambda x: x[0], reverse=True)
        # figure out how many teams remained tied
        i = 1
        while i < len(records) and records[i][0] == records[0][0]:
            i += 1
        tied = records[:i]
        return [team[1] for team in tied]

    # 3+ team common-games
    def tiebreaker8(self, teams, minimum):
        opps = [] # list of sets, each containing a team's opponents
        for t in teams:
            t_opps = set()
            for game in t.games:
                t_opps.add(self.get_opp(game, t))
            opps.append(t_opps)
        common_opps = opps[0]
        for i in range(1, len(opps)):
            common_opps = common_opps.intersection(opps[i])
        if minimum and len(common_opps) < 4:
            return teams
        
        records = []
        for t in teams:
            tot_wins = 0
            for g in t.games:
                if self.get_opp(g, t) in common_opps:
                    tot_wins += self.wins_from_game(g, t)
            records.append((tot_wins, t))
        records = sorted(records, key=lambda x: x[0], reverse=True)
        # figure out how many teams remained tied
        i = 1
        while i < len(records) and records[i][0] == records[0][0]:
            i += 1
        tied = records[:i]
        return [team[1] for team in tied]

    # 3+ team in-conference
    def tiebreaker9(self, teams):
        records = []
        for t in teams:
            tot_wins = 0
            for g in t.games:
                opp = self.get_opp(g, t)
                if self.team_info[opp]["DIV"][:3] == t.conf: # game is in-conference
                    tot_wins += self.wins_from_game(g, t)
            records.append((tot_wins, t))
        records = sorted(records, key=lambda x: x[0], reverse=True)
        # figure out how many teams remained tied
        i = 1
        while i < len(records) and records[i][0] == records[0][0]:
            i += 1
        tied = records[:i]
        return [team[1] for team in tied]

    # 3+ team coin toss
    def tiebreaker10(self, teams):
        return [random.choice(teams)]

    # 3+ team head-to-head sweep
    def tiebreaker11(self, teams):
        # If one team defeated all others, they win tiebreaker
        # If one team lost to all others, they are eliminated from tiebreaker
        team_set = set([t.abb for t in teams])
        sweep_loser = -1 # index of team that lost to all teams, if any
        for i, t in list(enumerate(teams)):
            wins = set()
            losses = set()
            for g in t.games:
                opp = self.get_opp(g, t)
                w = self.wins_from_game(g, t)
                if w == 1:
                    wins.add(opp)
                elif w == 0:
                    losses.add(opp)
            team_set_others = team_set.copy()
            team_set_others.remove(t.abb)
            if wins.intersection(team_set_others) == team_set_others:
                # this team beat all other teams
                return [t]
            if losses.intersection(team_set_others) == team_set_others:
                # this team lost to all other teams
                sweep_loser = i
        if sweep_loser != -1: # if one team lost to all others, remove it
            teams.pop(sweep_loser)
        return teams