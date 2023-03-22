import unittest

from tiebreakers import *
from main import *

elo_file = ""

# Test a specific year, grabbing actual standings and playoff seeds
# and comparing to my tiebreaker simulation's playoff seeds
class TestTiebreakers(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.leagueInfo = LeagueInfo("team_info.csv")
        self.tiebreakers = Tiebreakers(self.leagueInfo.abbs_to_codes, self.leagueInfo.team_info)
        # set up standings (team_info, past_results)
        # team_info initialize here
        # past_results load here for specific year
        
    def test_getplayoffseeds(self):
        # manually check these years against wikipedia
        for year in range(2002, 2023):
            start_date = datetime.now() # use today's date to stay current
            elo = pd.read_csv("nfl_elo.csv")
            elo = elo[elo["playoff"].isna()]
            elo["dateObject"] = elo["date"].apply((lambda x: datetime.strptime(x, "%Y-%m-%d")))
            elo = elo[elo["season"] == year]
            past_results = elo[elo["dateObject"] < start_date]
            # print(past_results)
            rem_games = elo[elo["dateObject"] >= start_date]
            self.assertTrue(rem_games.empty)
            
            standings = Standings(self.leagueInfo, past_results)
            get_last_elos(standings, past_results)

            my_output = self.tiebreakers.get_playoff_seeds(standings)
            my_afc = str(my_output[0])
            my_nfc = str(my_output[1])

            print("Year: ", str(year))
            print(my_afc)
            print(my_nfc)
            print()
        

if __name__ == '__main__':
    unittest.main()