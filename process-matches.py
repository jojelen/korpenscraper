import os
import json
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description="Script to parse match data")

parser.add_argument("-t", dest="team", type=str, help="Team name", default="Fobåll FA")
parser.add_argument(
    "-m",
    dest="matchesfile",
    type=str,
    help="json data of matches",
    default="matches.json",
)


class Team:
    def __init__(self, team_name):
        self.name = team_name
        self.players = pd.DataFrame(
            {"name": [], "matches": [], "goals": [], "yellows": [], "reds": []}
        )
        self.players.set_index("name", inplace=True)
        self.stats = pd.DataFrame(
            {
                "team": [],
                "matches": [],
                "won": [],
                "drawn": [],
                "lost": [],
                "goals": [],
                "rec": [],
            }
        )
        self.stats.set_index("team", inplace=True)
        self.stats.loc[self.name] = {
            "matches": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals": 0,
            "rec": 0,
        }

    def isValidPlayerName(self, name):
        if name.find(":") >= 0:
            return False
        if name == self.name:
            return False
        if name == "Tilldela tröjnummer":
            return False

        return True

    def getIdx(self, game_info):
        if self.name == game_info["teams"][0]:
            return 0, 1
        elif self.name == game_info["teams"][1]:
            return 1, 0

        return -1, -1

    def createPlayer(self, name):
        print("Adding ", name)
        self.players.loc[name] = {"matches": 0, "goals": 0, "yellows": 0, "reds": 0}

    def addPlayerInfo(self, idx, game_info, col):
        players = game_info[col][idx]
        for player in players:
            if player not in self.players.index:
                print("Not in players: ", player)
                player = "unknown"
                if player not in self.players.index:
                    self.createPlayer("unknown")

            self.players.loc[player][col] += 1

    def addGame(self, game_info):
        team_idx, opp_idx = self.getIdx(game_info)
        if team_idx == -1:
            return

        players_present = game_info["players"][team_idx]
        for player in players_present:
            if not self.isValidPlayerName(player):
                continue

            if player not in self.players.index:
                self.createPlayer(player)

            self.players.loc[player].matches += 1

        self.addPlayerInfo(team_idx, game_info, "goals")
        self.addPlayerInfo(team_idx, game_info, "yellows")
        self.addPlayerInfo(team_idx, game_info, "reds")

        scores = game_info["scores"]
        if scores[team_idx] > scores[opp_idx]:
            self.stats.loc[self.name]["won"] += 1
        elif scores[team_idx] < scores[opp_idx]:
            self.stats.loc[self.name]["lost"] += 1
        else:
            self.stats.loc[self.name]["drawn"] += 1

        self.stats.loc[self.name]["goals"] += scores[team_idx]
        self.stats.loc[self.name]["rec"] += scores[opp_idx]
        self.stats.loc[self.name]["matches"] += 1

    def printStats(self):
        # Cast data.
        self.players = self.players.astype(int).sort_index()
        self.stats = self.stats.astype(int)

        # Augment data.
        self.players["goals/match"] = self.players["goals"] / self.players["matches"]
        self.stats["score"] = self.stats["goals"] - self.stats["rec"]
        self.stats["goals/match"] = self.stats["goals"] / self.stats["matches"]


        print(self.stats)
        print(self.players)


def getMatches(file_path):
    data = []
    with open(file_path, "r") as f:
        for line in f.readlines():
            data.append(json.loads(line))

    return data


def main(args):
    data = getMatches(args.matchesfile)

    team = Team(args.team)

    for game in data:
        team.addGame(game)

    team.printStats()


if __name__ == "__main__":
    args = parser.parse_args()

    main(args)
