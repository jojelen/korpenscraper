import time
import os
import json
import argparse

from selenium import webdriver

parser = argparse.ArgumentParser(description="Script to scrape korpen's website for match data")

parser.add_argument("-u", dest="user", type=str, help="Username", default=None)
parser.add_argument("-p", dest="password", type=str, help="Password", default=None)
parser.add_argument(
    "-f",
    dest="failuresfile",
    type=str,
    help="File to save failure ids",
    default="failures.json",
)
parser.add_argument(
    "-m",
    dest="matchesfile",
    type=str,
    help="File to store json data of matches",
    default="matches.json",
)
parser.add_argument(
    "-i", dest="maxmatchid", type=int, help="Max match id", default=4000
)
parser.add_argument(
    "-j", dest="minmatchid", type=int, help="Min match id", default=1
)


def openKorpen():
    browser = webdriver.Firefox()
    browser.get("http://korpenmalmoidrottsforening.zoezi.se")

    member_button = browser.find_element_by_xpath(
        "/html/body/div/div[2]/div/div/div/button[2]"
    )
    member_button.click()
    time.sleep(3)

    return browser


def login(browser, user, password):
    login_button = browser.find_element_by_xpath(
        "/html/body/div[2]/div[1]/aside/div[1]/div/ul/li[9]/a"
    )
    login_button.click()
    time.sleep(3)

    browser.find_element_by_xpath(
        "/html/body/div[4]/div/div/div[2]/div[2]/div/div/fieldset/div[1]/form/div[1]/div/input"
    ).send_keys(user)
    browser.find_element_by_xpath(
        "/html/body/div[4]/div/div/div[2]/div[2]/div/div/fieldset/div[1]/form/div[2]/div/input"
    ).send_keys(password)

    browser.find_element_by_xpath(
        "/html/body/div[4]/div/div/div[2]/div[2]/div/div/fieldset/div[1]/form/div[4]/button"
    ).click()
    time.sleep(1)


def tryFindElement(browser, xpath, num_tries):
    try_nr = 1
    while True:
        time.sleep(1)
        try:
            el = browser.find_element_by_xpath(xpath)
            return el
        except Exception as e:
            if try_nr < num_tries:
                print("Trying again...")
                try_nr += 1
            else:
                raise e


def isValidPlayerName(name):
    return False if name.find(":") >= 0 else True


def getPlayers(browser):
    browser.find_element_by_xpath(
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[4]/div/div/ul/li[1]/a/tab-heading"
    ).click()
    members = tryFindElement(
        browser,
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[4]/div/div/div/div[2]/div[1]",
        3,
    )

    players = [[], []]

    for i in range(0, 2):
        members = browser.find_element_by_xpath(
            "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[4]/div/div/div/div[2]/div[{}]".format(
                i + 1
            )
        )
        members = members.text.split("\n")
        for member in members:
            if not isValidPlayerName(member):
                continue
            if not member[0].isdigit():
                continue

            member = member.lstrip("0123456789")
            if member != "":
                players[i].append(member)

    return players


def getMatchInfo(browser):

    header = tryFindElement(
        browser, "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[1]", 4
    ).text

    info = browser.find_element_by_xpath(
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]"
    ).text
    date = browser.find_element_by_xpath(
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[1]/div/a/strong"
    ).text
    location = browser.find_element_by_xpath(
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[1]/div/span"
    ).text
    scores = browser.find_element_by_xpath(
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[2]/div[2]/div[2]/div/h1"
    ).text.split("-", 1)
    scores = list(map(int, scores))
    container = browser.find_element_by_xpath(
        "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[4]/div/div"
    )

    teams = [
        browser.find_element_by_xpath(
            "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[2]/div[2]/div[1]/table/tbody/tr/td[2]/h1"
        ).text,
        browser.find_element_by_xpath(
            "/html/body/div[2]/div[2]/section/div/teamsportmatch/div/div/div[2]/div[2]/div[2]/div[3]/table/tbody/tr/td[1]/h1"
        ).text,
    ]
    ng_bindings = container.find_elements_by_class_name("ng-binding")

    goals = [[], []]
    yellows = [[], []]
    reds = [[], []]
    for i, el in enumerate(ng_bindings):
        if el.text == "HÄNDELSER":
            middle_line = el.location["x"]

        team_idx = lambda el: 0 if el.location["x"] < middle_line else 1

        if el.text == "Mål":
            goals[team_idx(el)].append(ng_bindings[i + 1].text)
        elif el.text == "Gult Kort":
            yellows[team_idx(el)].append(ng_bindings[i + 1].text)
        elif el.text == "Rött Kort":
            reds[team_idx(el)].append(ng_bindings[i + 1].text)

    players = getPlayers(browser)

    return {
        "header": header,
        "date": date,
        "location": location,
        "teams": teams,
        "players": players,
        "scores": scores,
        "goals": goals,
        "yellows": yellows,
        "reds": reds,
    }


def processMatch(browser, idx):
    browser.get(
        "https://korpenmalmoidrottsforening.zoezi.se/member#/match/{}?workoutId=undefined".format(
            idx
        )
    )

    info = getMatchInfo(browser)
    info["id"] = idx

    return info


def getMatchIdxs(file_path):
    if not os.path.isfile(file_path):
        return set()

    saved_matches = set()
    with open(file_path, "r") as f:
        for line in f.readlines():
            data = json.loads(line)
            saved_matches.add(data["id"])

    return saved_matches


def exportMatchInfo(info, file_path):
    with open(file_path, "a+") as f:
        json.dump(info, f)
        f.write("\n")


def exportFailure(file_path, idx, e):
    with open(file_path, "a+") as f:
        json.dump({"id": idx, "except": "{}".format(e)}, f)
        f.write("\n")


def scrapeAllMatches(browser, args):
    skip_matches = set()
    skip_matches.update(getMatchIdxs(args.matchesfile))
    skip_matches.update(getMatchIdxs(args.failuresfile))

    for i in range(args.minmatchid, args.maxmatchid):
        if i not in skip_matches:
            print("Scraping match nr ", i)
            try:
                info = processMatch(browser, i)
            except Exception as e:
                print("Failed match scraping: ", e)
                exportFailure(args.failuresfile, i, e)
                continue

            # print(info)

            exportMatchInfo(info, args.matchesfile)
            print("Scraping successful!")
        else:
            print("Skipping match nr {}".format(i))


def main(args):
    browser = openKorpen()

    if args.user and args.password:
        login(browser, args.user, args.password)

    scrapeAllMatches(browser, args)


if __name__ == "__main__":
    args = parser.parse_args()

    main(args)
