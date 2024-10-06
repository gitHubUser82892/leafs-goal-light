#
# Originally by:  gitHubUser82892 
#
# # These are the header comments.  
# Change from external nabu casa to local so I don't reveal my external URL and webhook
#
# Stored in github:  https://github.com/gitHubUser82892/leafs-goal-light
#
# #


import requests
import time
import json
import pytz
from datetime import datetime

# Global variables
game_is_live = False
game_about_to_start = False
game_in_intermission = False
toronto_is_home = False
toronto_score = 0
opponent_score = 0
game_today = False

#
# Home Assistant Webook URL with private key
#
# I'm ok with this being in the code, as it's a webhook that is only accessible from my local network
HA_WEBHOOK_URL = "http://homeassistant.local:8123/api/webhook/-kh7S2pAv4MiS1H2ghDvpxTND"


#
# This is the direct call to the NHL API
#
def get_apiweb_nhl_data(endpoint):
    base_url = "https://api-web.nhle.com/"
    url = f"{base_url}{endpoint}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve data from NHL API: {response.status_code}")
        return None


#
# Pull the boxscore data from the API and do some parsing
#
def get_boxscore_data(gameId):
    global game_is_live
    global game_in_intermission
    
    endpoint = "v1/gamecenter/" + str(gameId) + "/boxscore"
    print(f"== Boxscore data: " + endpoint + f" {datetime.now()}")
    data = get_apiweb_nhl_data(endpoint)
    if data:
        
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


        # Parse the score data from the data set
        home_team = data.get('homeTeam', {})
        away_team = data.get('awayTeam', {})
        home_team_score = home_team.get('score')
        away_team_score = away_team.get('score')

        # Print the current scores
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
# Main function to get the play by play data and determine the current score from the API
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
# Return the gameId if Toronto is playing now or determine if it's about to start
#
def current_toronto_game():
    global game_is_live  # Use the global variable
    global toronto_is_home
    global game_today
    global game_about_to_start

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
                
                    if away_team_id == 10 or home_team_id == 10:  # Toronto is team id 10
                        print(f"Toronto is playing today with gameId: {gameId} starting at {start_time}")
                        game_today = True

                        # Toronto is playing today.  Get the gameId and start time
                        gameId=(game.get('id'))
                        startTimeUTC = game.get('startTimeUTC')

                        # Parse startTimeUTC to datetime object
                        start_time = datetime.strptime(startTimeUTC, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
                        current_time = datetime.now(pytz.UTC)
                        
                        # Check if the game is live or about to start or will be later in the day
                        gameState = game.get('gameState')
                        if gameState == 'LIVE':  # Check if the game is live
                            print(f"Game is LIVE!")
                            if game_is_live == False:  # If the game wasn't already live, then set it as started
                                    start_game()
                                    if home_team_id == 10:
                                        toronto_is_home = True
                                    else:
                                        toronto_is_home = False
                            return gameId
                        elif (start_time - current_time).total_seconds() < 300:  # If it's not started, but it will within 5 minutes
                            print(f"Game is about to start!")
                            game_about_to_start = True
                            return gameId
                        else:  # If it's not live or about to start, then it's later in the day
                            print(f"Game is starting at {start_time}")
                            game_about_to_start = False
                            return None

                # if we exit the for loop, then no Toronto games were found today
                print(f"No Toronto games today")
                game_is_live = False
                game_today = False
                game_about_to_start = False
                return None
            else:  # There are no games today at all
                print(f"No games today")
                game_is_live = False
                game_today = False
                game_about_to_start = False
                return None
    else:
         game_is_live = False
         game_today = False
         game_about_to_start = False
         print("Failed to retrieve data")
    return None                   
    

#
# POST to webhook to drive the HomeAssistant automation
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


#
# Main function
#
def goal_tracker_main():
    global game_is_live  # Use the global variable
    global toronto_is_home 
    global game_today

    while (True):  # Keep checking for games
     
        # Makes a call to the NHL API to get the game schedule.  
        # Should run this only a few times a day, and then start calling boxscore within 5 minutes of start time
        gameId = current_toronto_game()

        # Use this for debugging to force a specific game to be found
        #gameId = "2024010006"
        #start_game()
        #toronto_is_home = True
        
        if game_today == False:
            print(f"Pausing for 8 hours as there is no game today\n")
            time.sleep(60*60*8)  # Pause for 8 hours if there's no game today

        while (game_is_live == True or game_about_to_start == True):
                    boxscore_data = get_boxscore_data(gameId)  # Retrive the current boxscore data and scores
                    # playbyplay_data = get_playbyplay_data(gameId)   # Not using this now, as boxscore seems to be just as up to date
                    check_scores(boxscore_data, playbyplay_data)  # Check the scores for new goals
                    time.sleep(15) # Check scores every 15 seconds
        
        print(f"No active game\n")

        time.sleep(2*60)  # Check every 2 minutes if the game has started or it's about to start
    

    print("\nEND\n")


if __name__ == "__main__":
    goal_tracker_main()

