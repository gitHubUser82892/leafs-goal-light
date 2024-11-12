# #
# #
#
# Originally by:  gitHubUser82892 
#
# Stored in github:  https://github.com/gitHubUser82892/leafs-goal-light
#
# TODO
#    - Test auto-crash recovery of the webhook_listener
#    - fix the github commit listener in homeassistant
#    - Use delta_time to figure out how long to sleep
#
#
# Instructions
#    - To use new sound files:  ffmpeg -i file.wav file.mp3
#    - webhook_listener running as systemd service
# #
# #
"""
Goal Tracker for Toronto Maple Leafs
This script tracks the Toronto Maple Leafs' games using the NHL API and triggers actions such as playing sounds on a Sonos speaker and activating a goal light via Home Assistant webhooks.
Modules:
    - requests: For making HTTP requests to the NHL API and Home Assistant webhooks.
    - time: For adding delays between API calls.
    - json: For parsing JSON responses from the NHL API.
    - pytz: For timezone conversions.
    - sys: For redirecting stdout and stderr to a log file.
    - soco: For controlling Sonos speakers.
    - datetime: For handling date and time operations.
Constants:
    - TORONTO_TEAM_ID: The team ID for the Toronto Maple Leafs.
    - HTTP_STATUS_OK: HTTP status code for a successful request.
    - TIMEZONE: The timezone for the game times.
    - SONOS_IP: The IP address of the Sonos speaker.
    - RASPPI_IP: The IP address of the Raspberry Pi running the webserver.
    - SOUND_GAME_START_FILE: The file path for the game start sound.
    - SOUND_GOAL_HORN_FILE: The file path for the goal horn sound.
Global Variables:
    - game_is_live: Boolean indicating if a game is currently live.
    - game_about_to_start: Boolean indicating if a game is about to start.
    - game_in_intermission: Boolean indicating if a game is in intermission.
    - toronto_is_home: Boolean indicating if Toronto is the home team.
    - toronto_score: The current score of the Toronto Maple Leafs.
    - opponent_score: The current score of the opponent team.
    - game_today: Boolean indicating if there is a game today.
Functions:
    - get_opponent_team_name(game, home_team_id): Returns the name of the opponent team.
    - get_apiweb_nhl_data(endpoint): Makes a GET request to the NHL API and returns the JSON response.
    - get_boxscore_data(gameId): Retrieves and parses the boxscore data for a given game ID.
    - get_playbyplay_data(gameId): Retrieves and parses the play-by-play data for a given game ID.
    - current_toronto_game(): Determines if Toronto is playing today and returns the game ID if applicable.
    - activate_goal_light(message): Sends a POST request to the Home Assistant webhook to activate the goal light.
    - notify_game_about_to_start(message): Sends a POST request to the Home Assistant webhook to notify that the game is about to start.
    - check_scores(boxscore_data): Checks the current scores and triggers actions if there has been a recent goal.
    - start_game(): Resets the scores and sets the game as live when it starts.
    - play_sounds(sound_file): Plays a sound on the Sonos speaker.
    - goal_tracker_main(): The main function that runs the goal tracker.
Usage:
    Run the script to start tracking the Toronto Maple Leafs' games. The script will log its output to a specified log file and continuously check for game updates.
"""



import requests
import time
import json
import pytz
import sys
import soco
from datetime import datetime
from datetime import timedelta

# Constants
TORONTO_TEAM_ID = 10
HTTP_STATUS_OK = 200
TIMEZONE = 'US/Eastern'
DEFAULT_WAIT_TIME = 5*60  # 5 minutes

#SONOS_IP = "192.168.86.29"  #  Office:1 Sonos speaker
#SONOS_IP = "192.168.86.196" #  Family Room Beam Sonos speaker
SONOS_IP = "192.168.86.46"  # FamilyRoom2 speaker

RASPPI_IP = "192.168.86.61:5000"  # This is the IP of the Raspberry Pi running the webserver
SOUND_GAME_START_FILE = "/files/leafs_game_start.mp3"  # Webhook to get the file returned from the webserver
SOUND_GOAL_HORN_FILE = "/files/leafs_goal_horn.mp3"  # Webhook to get the file returned from the webserver

# Global variables
game_is_live = False
game_about_to_start = False
toronto_is_home = False
toronto_score = 0
opponent_score = 0
game_today = False
wait_time = 0  # Time to wait before checking the game again
roster = {}  # Dictionary to store the roster data



#
# Home Assistant Webook URL with private key
#
# I'm ok with this being in the code, as it's a webhook that is only accessible from my local network
HA_WEBHOOK_URL_ACTIVATE_GOAL_LIGHT = "http://homeassistant.local:8123/api/webhook/-kh7S2pAv4MiS1H2ghDvpxTND"
HA_WEBHOOK_URL_NOTIFY_GAME_ABOUT_TO_START = "http://homeassistant.local:8123/api/webhook/nhl_game_about_to_start-q2NblABPRjzDLhwSNeH2dlpD"


#
# This is the direct call to the public NHL API
#
def get_apiweb_nhl_data(endpoint):
    base_url = "https://api-web.nhle.com/"
    url = f"{base_url}{endpoint}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve data from NHL API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        return None


    
#
# POST to webhook to drive the HomeAssistant automation to turn on goal light
#
def activate_goal_light(message):
    payload = {"text": message}
    try:
        response = requests.post(HA_WEBHOOK_URL_ACTIVATE_GOAL_LIGHT, json=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        print("Successfully sent POST request to webhook")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send POST request to webhook: {e}")


#
# POST to webhook to drive the HomeAssistant automation to send notification that the game is about to start
#
def notify_game_about_to_start(message):
    payload = {"message": message}
    try:
        response = requests.post(HA_WEBHOOK_URL_NOTIFY_GAME_ABOUT_TO_START, json=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        print("Successfully sent POST request to webhook")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send POST request to webhook: {e}")



#
#  Play sounds based on the list of input files
#
# Example of how to call play_sounds
# play_sounds([
#     "/roster/GoalScoredBy.mp3",
#     "/roster/Knies.mp3",
#     "/roster/Assist.mp3",
#     "/roster/Marner.mp3",
#     "/roster/Nylander.mp3"
# ])
def play_sounds(sound_files):
    try:
        sonos = soco.SoCo(SONOS_IP)

        # Display basic info about the speaker
        print(f"Connected to Sonos Speaker: {sonos.player_name}")
        print(f"Current Volume: {sonos.volume}")
        original_volume = sonos.volume
        sonos.volume = 50

        for sound_file in sound_files:
            # Play the MP3 file
            MP3_FILE_URL = f"http://{RASPPI_IP}{sound_file}"
            print(f"Attempting to play: {MP3_FILE_URL}")
            sonos.play_uri(MP3_FILE_URL)

            # Check the state of the player
            #current_track = sonos.get_current_track_info()
            state = sonos.get_current_transport_info()["current_transport_state"]

            #print(f"Track Info: {current_track}")
            print(f"Current State: {state}")

            # Volume control for debugging
            if state == "PLAYING":
                print("Playback started successfully.")
            else:
                print(f"Playback did not start. Current state: {state}")

            # Check the playback position every few seconds
            while state == "PLAYING" or state == "TRANSITIONING":
                #track_position = sonos.get_current_track_info()['position']
                #print(f"Track Position: {track_position}")
                time.sleep(0.05)
                state = sonos.get_current_transport_info()["current_transport_state"]
                print(f"Current State: {state}")

        sonos.volume = original_volume

    except soco.exceptions.SoCoException as e:
        print(f"Sonos error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")



#
# Pull the boxscore data from the API and do some parsing
#
def get_boxscore_data(gameId):
    global game_is_live
    
    endpoint = "v1/gamecenter/" + str(gameId) + "/boxscore"
    print(f"== Boxscore data: " + endpoint + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    data = get_apiweb_nhl_data(endpoint)
    if data:
        
        game_state = data.get('gameState')
        if game_state != 'LIVE':
            # mark the game as ended
            print(f"Game is no longer live\n")
            game_is_live = False

            # If we want to do something when the game ends, we can do it here

        return data
    else:
        print("Failed to retrieve data")



#
# Pull the play-by-play data from the API and do some parsing
#
def get_play_by_play_data(gameId):
    global game_is_live
    
    endpoint = "v1/gamecenter/" + str(gameId) + "/play-by-play"
    print(f"== Play-by-play data: " + endpoint + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    data = get_apiweb_nhl_data(endpoint)
    if data:
        
        game_state = data.get('gameState')
        if game_state != 'LIVE':
            # mark the game as ended
            print(f"Game is no longer live\n")
            game_is_live = False

            # If we want to do something when the game ends, we can do it here

        return data
    else:
        print("Failed to retrieve data")


#
#  Get the goal scorer and assists data from the play-by-play API for the most recent Toronto goal.  Return the list of names
#
def get_goal_scorer(data):
    try:
        events = data.get('plays', [])
        
        for event in reversed(events):
            if event.get('typeCode') == 505:  # Goal event
                scoring_team_id = event.get('details', {}).get('eventOwnerTeamId')
                if scoring_team_id == TORONTO_TEAM_ID:
                    scoring_player_id = event.get('details', {}).get('scoringPlayerId')
                    assist1_player_id = event.get('details', {}).get('assist1PlayerId')
                    assist2_player_id = event.get('details', {}).get('assist2PlayerId')
                    
                    return {
                        'scoringPlayerID': scoring_player_id,
                        'assist1PlayerID': assist1_player_id,
                        'assist2PlayerID': assist2_player_id
                    }
    except KeyError as e:
        print(f"Key error while parsing data: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return None


#
# Check the current scores to see if there has been a recent goal
#
def check_scores(data):
    global toronto_score
    global opponent_score
    global toronto_is_home
    home_team_score = 0
    away_team_score = 0
    toronto_goal = False

    try:
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
                print(f"Away Team (Toronto) Score: {away_team_score}")
        else:
            print("Away Team Score not found")
        print("\n")


        if toronto_is_home:
            if home_team_score > toronto_score:
                print(f"TORONTO GOAL!\n")
                toronto_goal = True
            if away_team_score > opponent_score:
                print(f"OPPONENT GOAL\n")
                
            toronto_score = home_team_score  # Update the scores.  It's possible they decreased if the goal was disallowed
            opponent_score = away_team_score
        else:
            if away_team_score > toronto_score:
                print(f"TORONTO GOAL!\n")
                toronto_goal = True
            if home_team_score > opponent_score:
                print(f"OPPONENT GOAL\n")

            toronto_score = away_team_score
            opponent_score = home_team_score
        
        # If there was a goal, then activate the goal light and play the goal horn
        if toronto_goal:
            activate_goal_light("TORONTO GOAL!")
            play_sounds(SOUND_GOAL_HORN_FILE)
            goal_scorer_info = get_goal_scorer(data)
            if goal_scorer_info:
                print(f"Scoring Player ID: {goal_scorer_info['scoringPlayerID']}")
                print(f"Assist 1 Player ID: {goal_scorer_info['assist1PlayerID']}")
                print(f"Assist 2 Player ID: {goal_scorer_info['assist2PlayerID']}")

                sounds_to_play = ["/roster/GoalScoredBy.mp3"]
                if goal_scorer_info['scoringPlayerID'] in roster:
                    sounds_to_play.append(f"/roster/{roster[goal_scorer_info['scoringPlayerID']]}.mp3")
                
                if goal_scorer_info['assist1PlayerID'] in roster:
                    sounds_to_play.append("/roster/Assist.mp3")
                    sounds_to_play.append(f"/roster/{roster[goal_scorer_info['assist1PlayerID']]}.mp3")
                
                if goal_scorer_info['assist2PlayerID'] in roster:
                    sounds_to_play.append(f"/roster/{roster[goal_scorer_info['assist2PlayerID']]}.mp3")
                
                play_sounds(sounds_to_play)

    except KeyError as e:
        print(f"Key error while checking scores: {e}")
    except Exception as e:
        print(f"Unexpected error while checking scores: {e}")

    return


#
# Get the roster data for the Toronto Maple Leafs
#
def get_toronto_roster():
    endpoint = "v1/roster/TOR/20242025"
    data = get_apiweb_nhl_data(endpoint)
    
    if data:
        roster = {}
        
        # Process forwards
        forwards = data.get('forwards', [])
        for player in forwards:
            player_id = player.get('id')
            last_name = player.get('lastName', {}).get('default', '')
            roster[player_id] = last_name
        
        # Process defensemen
        defensemen = data.get('defensemen', [])
        for player in defensemen:
            player_id = player.get('id')
            last_name = player.get('lastName', {}).get('default', '')
            roster[player_id] = last_name
        
        # Process goalies
        goalies = data.get('goalies', [])
        for player in goalies:
            player_id = player.get('id')
            last_name = player.get('lastName', {}).get('default', '')
            roster[player_id] = last_name
        
        return roster
    else:
        print(f"Failed to retrieve roster data\n")
    
    return None


#
# Return the gameId if Toronto is playing now or determine if it's about to start
#
def current_toronto_game():
    global game_is_live  # Use the global variable
    global toronto_is_home
    global game_today
    global game_about_to_start
    global wait_time

    today_date = f"{datetime.now().strftime('%Y-%m-%d')}"
    endpoint = "v1/schedule/" + today_date

    print(f"== Find next game: " + endpoint + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    data = get_apiweb_nhl_data(endpoint)
    if data:
        try:
            for game_week in data.get('gameWeek', []):
                game_date = game_week.get('date')
                if game_date == today_date:
                    for game in game_week.get('games', []):
                        away_team_id = game.get('awayTeam', {}).get('id')
                        home_team_id = game.get('homeTeam', {}).get('id')
                    
                        if away_team_id == TORONTO_TEAM_ID or home_team_id == TORONTO_TEAM_ID: 
                            game_today = True

                            # Toronto is playing today.  Get the gameId and start time
                            gameId = game.get('id')
                            print(f"Toronto is playing today with gameId: {gameId}")

                            # Get the opponent team name
                            if home_team_id == TORONTO_TEAM_ID:  
                                opponent_team_name = game.get('awayTeam', {}).get('placeName', {}).get('default')
                                toronto_is_home = True
                                print(f"Toronto is the home team and playing against {opponent_team_name}")
                            else:
                                toronto_is_home = False
                                opponent_team_name = game.get('homeTeam', {}).get('placeName', {}).get('default')
                                print(f"Toronto is the away team and playing against {opponent_team_name}")

                            # Calculations on the start time and delta from the current time
                            startTimeUTC = game.get('startTimeUTC')
                            start_time = datetime.strptime(startTimeUTC, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc).astimezone(pytz.timezone(TIMEZONE))
                            current_time = datetime.now(pytz.timezone('US/Eastern'))
                            time_delta = (start_time - current_time)

                            print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"Start time:   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"Time until game starts:   {str(time_delta).split('.')[0]}")

                            # Check if the game is live or about to start or will be later in the day
                            gameState = game.get('gameState')
                            if gameState == 'LIVE':  # Check if the game is live
                                print(f"Game is LIVE!")
                                if not game_is_live:  # If the game wasn't already live, then set it as started
                                    start_game()
                                return gameId
                            elif gameState == 'OFF' or time_delta < timedelta(hours=-1):  # If the game already happened today
                                print(f"Toronto played earlier today")
                                game_today = False   # Don't check again until tomorrow
                                game_is_live = False
                                game_about_to_start = False 
                                return None
                            elif time_delta < timedelta(minutes=5) and time_delta > timedelta(minutes=0) and not game_about_to_start:  # If it's not started, but it will within 5 minutes
                                print(f"Game is about to start!  Starting in {str(time_delta).split('.')[0]}")
                                game_about_to_start = True
                                notify_game_about_to_start("Game about to start!")
                                return gameId
                            elif game_about_to_start:
                                return gameId
                            elif time_delta > timedelta(minutes=5):
                                # If it's not live or about to start, then it's later in the day
                                print(f"Game is starting later today {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                game_about_to_start = False

                                if time_delta > timedelta(hours=1):
                                    rounded_time_delta = timedelta(hours=time_delta.seconds // 3600)
                                    wait_time = rounded_time_delta.total_seconds()
                                    print(f"Rounded wait time to the nearest hour: {rounded_time_delta}")
                                else:
                                    wait_time = 5 * 60
                                    print(f"Wait time set to 5 minutes")
                                return None
                            else:
                                print(f"This is an edge case to watch for...")
                                return None

                    print(f"No Toronto games today")
                    return None
                else:
                    print(f"No games today")
                    return None
        except KeyError as e:
            print(f"Key error while parsing schedule data: {e}")
        except Exception as e:
            print(f"Unexpected error while parsing schedule data: {e}")
    else:
        print("Failed to retrieve data")
    return None



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

    print(f"Game has started!\n")
    play_sounds(SOUND_GAME_START_FILE)



#
# Main function
#
def goal_tracker_main():
    global game_is_live # Use the global variable
    global game_about_to_start
    global toronto_is_home 
    global game_today
    global wait_time
    global roster

    game_is_live = False
    game_about_to_start = False
    toronto_is_home = False
    game_today = False 
    wait_time = DEFAULT_WAIT_TIME

    debug_mode = False
    if (debug_mode == True):
        print(f"Debug mode is on\n")
        play_sounds(SOUND_GAME_START_FILE)
        time.sleep(5)
        activate_goal_light(1)
        play_sounds(SOUND_GOAL_HORN_FILE)
        return # For now, just play the start sound and exit


    # Start by getting the roster data and parsing it so we just have the player id and name
    print(f"Retrieving roster data...")
    roster = get_toronto_roster()
    if roster:
        print(f"Roster data retrieved successfully")
    time.sleep(10)  # Pause for 10 seconds to avoid hitting the API too quickly


    # Main loop
    while (True):  # Keep checking for games
     
        # Makes a call to the NHL API to get the game schedule.  
        # Should run this only a few times a day, and then start calling boxscore within 5 minutes of start time
        gameId = current_toronto_game()

        # Use this for debugging to force a specific game to be found
        #gameId = "2024010006"
        #start_game()
        #toronto_is_home = True


        # Debugging of the goal scorer API
        # game_id = '2024010006'  # Replace with the actual game ID
        # goal_scorer_info = get_goal_scorer(game_id)
        # if goal_scorer_info:
        #     print(f"Scoring Player ID: {goal_scorer_info['scoringPlayerID']}")
        #     print(f"Assist 1 Player ID: {goal_scorer_info['assist1PlayerID']}")
        #     print(f"Assist 2 Player ID: {goal_scorer_info['assist2PlayerID']}")
        

        if game_today == True:
            if (game_about_to_start == True):
                print(f"Game about to start!  Waiting 20 seconds...\n")
                time.sleep(20)  # Check every 20 seconds if the game is about to start
            else: 
                hours, remainder = divmod(wait_time, 3600)
                minutes, _ = divmod(remainder, 60)
                next_check_time = datetime.now(pytz.timezone('US/Eastern')) + timedelta(seconds=wait_time)
                print(f"No active game. Waiting {int(hours)} hours and {int(minutes)} minutes... until {next_check_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                time.sleep(wait_time) 
                wait_time = DEFAULT_WAIT_TIME  # Set the wait time to 5 minutes for next time
        else:
            print(f"Pausing for 8 hours as there is no game today\n")
            time.sleep(60*60*8)  # Pause for 8 hours if there's no game today

        # Main loop to execute during a live game
        while (game_is_live == True):
            #boxscore_data = get_boxscore_data(gameId)  # Retrive the current boxscore data from the API
            #check_scores(boxscore_data)  # Check the scores for new goals
            playbyplay_data = get_play_by_play_data(gameId)  # Retrive the current play-by-play data from the API
            check_scores(playbyplay_data)  # Check the scores for new goals
            time.sleep(10) # Check scores every 10 seconds
        

    


if __name__ == "__main__":

    # direct output to a log file
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Open a file for logging and set sys.stdout to the file
    log_file = open('/home/rmayor/Projects/leafs_goal_light/output.log', 'a')
    # Redirect stdout to the file
    sys.stdout = log_file
    # Reconfigure stdout for immediate flushing
    sys.stdout.reconfigure(line_buffering=True)

    # Redirect stderr to the file
    sys.stderr = log_file
    # Reconfigure stderr for immediate flushing
    sys.stderr.reconfigure(line_buffering=True)

    print(f"***************************************************************************************")
    print(f"*\n* Starting goal tracker at {datetime.now()}\n*")
    print(f"***************************************************************************************\n")

    goal_tracker_main()

