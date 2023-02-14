# CHAT FUCKING GPT WROTE THIS !!!!
class Game:
    def __init__(self, opponent, result):
        self.opponent = opponent
        self.result = result

class Team:
    def __init__(self, name):
        self.name = name
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.games = []

    def add_result(self, result, opponent):
        self.games.append((opponent, result))
        if result == "W":
            self.wins += 1
        elif result == "L":
            self.losses += 1
        elif result == "T":
            self.ties += 1

    def record(self):
        return f"{self.wins}-{self.losses}-{self.ties}"

    def win_loss_tie_percentage(self):
        total_games = self.wins + self.losses + self.ties
        return (self.wins + 0.5 * self.ties) / total_games * 100

    def __repr__(self):
        return f"{self.name}: {self.record()}"

    def __lt__(self, other):
        if isinstance(other, Team):
            return self.win_loss_tie_percentage() < other.win_loss_tie_percentage()
        return False

class Division:
    def __init__(self, name):
        self.name = name
        self.teams = []

    def add_team(self, team):
        self.teams.append(team)

    def sort_teams(self):
        self.teams.sort(reverse=True)

    def winner(self):
        self.sort_teams()
        return self.teams[0]

    def __repr__(self):
        return f"Division {self.name}: {self.teams}"

class Conference:
    def __init__(self, name):
        self.name = name
        self.divisions = []

    def add_division(self, division):
        self.divisions.append(division)

    def playoff_seeds(self):
        playoff_teams = []
        for division in self.divisions:
            playoff_teams.append(division.winner())
        all_teams = []
        for division in self.divisions:
            all_teams.extend(division.teams)
        all_teams = sorted(all_teams, reverse=True)
        for team in playoff_teams:
            all_teams.remove(team)
        playoff_teams.extend(all_teams[:3])
        return playoff_teams[:7]
