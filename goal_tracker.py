#
# Originally by:  gitHubUser82892 
#
# # These are the header comments.  
# Change from external nabu casa to local so I don't reveal my external URL and webhook
# Testing a change
# #


import requests
import logging
import time
import json
import pytz
from datetime import datetime

# Configure logging
logging.basicConfig(filename='output.log', level=logging.INFO, format='%(message)s')

# Global variables
game_is_live = False
game_about_to_start = False
game_in_intermission = False
toronto_is_home = False
toronto_score = 0
opponent_score = 0

# Home Assistant Webook URL
HA_WEBHOOK_URL = "http://homeassistant.local:8123/api/webhook/-kh7S2pAv4MiS1H2ghDvpxTND"


#
#
#
def get_apiweb_nhl_data(endpoint):
    base_url = "https://api-web.nhle.com/"
    url = f"{base_url}{endpoint}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

#
#
#
def get_boxscore_data(gameId):
    global game_is_live
    global game_in_intermission
    
    endpoint = "v1/gamecenter/" + str(gameId) + "/boxscore"
    print(f"== Boxscore data: " + endpoint + f" {datetime.now()}")
    data = get_apiweb_nhl_data(endpoint)
    if data:
        #print(data, "\n")
        
        game_state = data.get('gameState')
        if game_state != 'LIVE':
            # mark the game as ended
            game_is_live = False

        # Use this to optimize the refresh times, but would need to check in more frequently as it ends
        #intermission = data.get('clock','inIntermission')
        #if intermission == 'true':
        #    game_in_intermission = True
        #else:
        #    game_in_intermission = False


        home_team = data.get('homeTeam', {})
        away_team = data.get('awayTeam', {})

        home_team_score = home_team.get('score')
        away_team_score = away_team.get('score')

        if home_team_score is not None:
            if toronto_is_home == True:
                print(f"Home Team (Toronto) Score: {home_team_score}")
            else:
                print(f"Home Team (Opponent) Score: {home_team_score}")
        else:
            print("Home Team Score not found")

        if away_team_score is not None:
            if toronto_is_home == True:
                print(f"Away Team (Opponent) Score: {away_team_score}")
            else:
                print(f"Home Team (Toronto) Score: {away_team_score}")
        else:
            print("Away Team Score not found")
        print("\n")

        return data
    else:
        print("Failed to retrieve data")

#
#
#
def get_playbyplay_data(gameId):
    endpoint = "v1/gamecenter/" + str(gameId) + "/play-by-play"
    print(f"== Play by Play data: " + endpoint + f" {datetime.now()}")
    data = get_apiweb_nhl_data(endpoint)
    if data:
        #print(data, "\n")

        home_team = data.get('homeTeam', {})
        away_team = data.get('awayTeam', {})

        home_team_score = home_team.get('score')
        away_team_score = away_team.get('score')

        if home_team_score is not None:
            print(f"Home Team Score: {home_team_score}")
        else:
            print("Home Team Score not found")

        if away_team_score is not None:
            print(f"Away Team Score: {away_team_score}")
        else:
            print("Away Team Score not found")
        print("\n")
        return data
    else:
        print("Failed to retrieve data")


#
# # Return the gameId if Toronto is playing now
#
def current_toronto_game():
    global game_is_live  # Use the global variable
    global toronto_is_home

    today_date = f"{datetime.now().strftime('%Y-%m-%d')}"
    endpoint = "v1/schedule/" + today_date

    print(f"== Find next game: " + endpoint + f" {datetime.now()}\n")

    data = get_apiweb_nhl_data(endpoint)
    if data:
        for game_week in data.get('gameWeek', []):
            game_date = game_week.get('date')
            if game_date == today_date:
                for game in game_week.get('games', []):
                    away_team_id = game.get('awayTeam', {}).get('id')
                    home_team_id = game.get('homeTeam', {}).get('id')
                    
                    # print(json.dumps(game, indent=4))

                    if away_team_id == 10 or home_team_id == 10:
                        gameId=(game.get('id'))
                        startTimeUTC = game.get('startTimeUTC')

                        # Parse startTimeUTC to datetime object
                        start_time = datetime.strptime(startTimeUTC, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
                        current_time = datetime.now(pytz.UTC)

                    
                        
                        print(f"Toronto is playing today with gameId: {gameId} starting at {start_time}")

                        gameState = game.get('gameState')
                        if gameState == 'LIVE':
                            print(f"Game is LIVE!")
                            if game_is_live == False:
                                    start_game()
                                    if home_team_id == 10:
                                        toronto_is_home = True
                                    else:
                                        toronto_is_home = False
                            return gameId
                        else:
                            print(f"Game is starting at {start_time}")
                            return None

                # if we exit the for loop, then no Toronto games were found today
                print(f"No Toronto games today")
                game_is_live = False
                return None
            else:
                print(f"No games today")
                game_is_live = False
                return None
    else:
         game_is_live = False
         print("Failed to retrieve data")
    return None                   
    

#
# POST to webhook
#
def post_to_webhook(message):
    payload = {"text": message}
    try:
        response = requests.post(HA_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print("Successfully sent POST request to webhook")
        else:
            print(f"Failed to send POST request to webhook: {response.status_code}")
    except Exception as e:
        print(f"Error sending POST request to webhook: {e}")



#
# Check the current scores to see if there has been a recent goal
#
def check_scores(boxscore_data, playbyplay_data):
    global toronto_score
    global opponent_score
    global toronto_is_home

    # check the boxscore data
    home_team = boxscore_data.get('homeTeam', {})
    away_team = boxscore_data.get('awayTeam', {})

    home_team_score = home_team.get('score')
    away_team_score = away_team.get('score')

    if toronto_is_home == True:
        if home_team_score > toronto_score:
            print(f"Boxscore: TORONTO GOAL!\n")
            toronto_score = home_team_score
            post_to_webhook(1)
        if away_team_score > opponent_score:
            print(f"Boxscore: OPPONENT GOAL\n")
            opponent_score = away_team_score
    else:
        if away_team_score > toronto_score:
            print(f"Boxscore: TORONTO GOAL!\n")
            post_to_webhook(1)
            toronto_score = away_team_score
        if home_team_score > opponent_score:
            print(f"Boxscore: OPPONENT GOAL\n")
            opponent_score = home_team_score

    # check the play by play data
    # Do I need to?  Is it any different speed than the play by play data?


    return


#
# Reset the scores for a game when it starts
#
def start_game():
    global game_is_live
    global game_about_to_start
    global toronto_score
    global opponent_score

    game_is_live = True
    game_about_to_start = False
    toronto_score = 0
    opponent_score = 0



def goal_tracker_main():
    global game_is_live  # Use the global variable
    global toronto_is_home 

    while (True):     # Check every 5 minutes
     
        # Should run this only a few times a day, and then start calling boxscore within 5 minutes of start time
        gameId = current_toronto_game()

        # Use this to force a specific game to be found
        #gameId = "2024010006"
        #start_game()
        #toronto_is_home = True
        


        while (game_is_live == True or game_about_to_start == True):
            #    for _ in range(1):
                    boxscore_data = get_boxscore_data(gameId)
                    playbyplay_data = get_playbyplay_data(gameId)
                    check_scores(boxscore_data, playbyplay_data)
                    time.sleep(15)
        
        print(f"No active game\n")

        time.sleep(2*60)
    

    print("\nEND\n")



if __name__ == "__main__":
    goal_tracker_main()

