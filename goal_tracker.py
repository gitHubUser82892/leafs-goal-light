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
    - sonos: The global Sonos speaker object.
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
import inspect

# Add these after imports, before constants
_debug_indent_level = 0


def debug_print(message, indent_change=0):
    """
    Print a debug message with timestamp and proper indentation based on call stack depth.
    """
    global _debug_indent_level
    
    # Get the caller's frame info to check if it's the main function
    caller_frame = inspect.currentframe().f_back
    func_name = caller_frame.f_code.co_name
    
    # For regular messages (indent_change == 0), add one level of indentation
    # This ensures messages within decorated functions are properly indented
    indent_level = _debug_indent_level
    if indent_change == 0:
        # Don't add extra indent for main function
        if func_name != 'goal_tracker_main':
            indent_level += 1
    elif indent_change == 1:
        _debug_indent_level += 1
        indent_level = _debug_indent_level
    elif indent_change == -1:
        indent_level = _debug_indent_level
        _debug_indent_level = max(0, _debug_indent_level - 1)
    
    # Create indent string based on current level
    indent = "| " * max(0, indent_level) if func_name != 'goal_tracker_main' else ""
    
    # Print message with timestamp in the correct timezone and indentation
    print(f"[{datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}]: {indent}{message}")


def debug_print_error(message, indent_change=0):
    """
    Print an error debug message with timestamp, function name, line number, and proper indentation.
    Similar to debug_print() but includes additional context for error tracking.
    """
    global _debug_indent_level
    
    # Get the caller's frame info
    caller_frame = inspect.currentframe().f_back
    func_name = caller_frame.f_code.co_name
    line_no = caller_frame.f_lineno
    
    # Handle indentation similar to debug_print()
    indent_level = _debug_indent_level
    if indent_change == 0:
        # Don't add extra indent for main function
        if func_name != 'goal_tracker_main':
            indent_level += 1
    elif indent_change == 1:
        _debug_indent_level += 1
        indent_level = _debug_indent_level
    elif indent_change == -1:
        indent_level = _debug_indent_level
        _debug_indent_level = max(0, _debug_indent_level - 1)
    
    # Create indent string based on current level
    indent = "|  " * max(0, indent_level) if func_name != 'goal_tracker_main' else ""
    
    # Print message with timestamp in the correct timezone, function name, line number, and indentation
    print(f"[{datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}] ERROR in {func_name}() line {line_no}: {indent}{message}")


def function_debug_decorator(func):
    """
    Decorator that automatically logs function entry and exit with parameters.
    
    This decorator wraps functions to provide automatic debug logging of:
        - Function entry with all parameters (both positional and keyword)
        - Function exit
    
    The decorator automatically manages indentation levels to show the call stack visually.
    
    Args:
        func: The function to be decorated
    
    Returns:
        wrapper: The wrapped function with added debug logging
    
    Example usage:
        @function_debug_decorator
        def my_function(param1, param2="default"):
            pass
    
    Example output:
        [2024-03-20 10:15:00]: Entering my_function(123, param2=default)
        [2024-03-20 10:15:00]: Exiting my_function()
    """
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        
        # Special case for check_scores function
        if func_name == 'check_scores':
            # Skip the first argument (data) and only format remaining args
            args_str = [str(arg) for arg in args[1:]]
        else:
            # Format all positional arguments
            args_str = [str(arg) for arg in args]
        
        # Format keyword arguments
        kwargs_str = [f"{k}={v}" for k, v in kwargs.items()]
        
        # Combine all arguments
        all_args = args_str + kwargs_str
        params = ", ".join(all_args)
        
        debug_print(f"Entering {func_name}( {params} )", 1)
        result = func(*args, **kwargs)
        debug_print(f"Exiting {func_name}()", -1)
        return result
    return wrapper


# Constants - these should never change
TORONTO_TEAM_ID = 10
HTTP_STATUS_OK = 200
TIMEZONE = 'America/New_York'
DEFAULT_WAIT_TIME = 1*60  # 5 minutes
DEBUGMODE = False
DEFAULT_SOUND_VOLUME = 60
SCORE_CHECK_INTERVAL = 8  # how many seconds between checking the score

# Sonos speaker configurations
SONOS_OFFICE_IP = "192.168.86.29"      # Office:1 Sonos speaker
SONOS_FAMILY_ROOM_IP = "192.168.86.36" # FamilyRoom2 speaker
SONOS_BEAM_IP = "192.168.86.196"       # Family Room Beam Sonos speaker

# Configuration - these can be changed at runtime


# Get local IP dynamically
import socket
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

RASPPI_IP = f"{get_local_ip()}:5000"  # Dynamic IP of this machine

SOUND_GAME_START_FILE = "/files/leafs_game_start.mp3"  # Webhook to get the file returned from the webserver
SOUND_GOAL_HORN_FILE = "/files/leafs_goal_horn.mp3"  # Webhook to get the file returned from the webserver
SOUND_BOO_FILE = "/files/Boo.mp3"  # Webhook to get the file returned from the webserver


# Global variables
game_is_live = False
game_about_to_start = False
toronto_is_home = False
toronto_score = 0
opponent_score = 0
game_today = False
wait_time = 0  # Time to wait before checking the game again
roster = {}  # Dictionary to store the roster data
most_recent_goal_event_id = 0  # the eventId of the most recent Toronto goal event
sonos = None # Sonos speaker object
active_sonos_ip = SONOS_FAMILY_ROOM_IP  # Default speaker, can be changed
opponent_is_senators = False


#
# Home Assistant Webook URL with private key
#
# I'm ok with this being in the code, as it's a webhook that is only accessible from my local network
HA_WEBHOOK_URL_ACTIVATE_GOAL_LIGHT = "http://homeassistant.local:8123/api/webhook/-kh7S2pAv4MiS1H2ghDvpxTND"
HA_WEBHOOK_URL_NOTIFY_GAME_ABOUT_TO_START = "http://homeassistant.local:8123/api/webhook/nhl_game_about_to_start-q2NblABPRjzDLhwSNeH2dlpD"


#
# This is the direct call to the public NHL API
#
@function_debug_decorator
def get_apiweb_nhl_data(endpoint):
    base_url = "https://api-web.nhle.com/"
    url = f"{base_url}{endpoint}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        debug_print_error(f"Failed to retrieve data from NHL API: {e}")
        return None
    except json.JSONDecodeError as e:
        debug_print_error(f"Failed to parse JSON response: {e}")
        return None


    
#
# POST to webhook to drive the HomeAssistant automation to turn on goal light
#
@function_debug_decorator
def activate_goal_light(message):
    payload = {"text": message}
    debug_print(f"Sending POST request with payload: {payload}")
    try:
        response = requests.post(HA_WEBHOOK_URL_ACTIVATE_GOAL_LIGHT, json=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        debug_print("Successfully sent POST request to webhook")
    except requests.exceptions.RequestException as e:
        debug_print_error(f"Failed to send POST request to webhook: {e}")


#
# POST to webhook to drive the HomeAssistant automation to send notification that the game is about to start
#
@function_debug_decorator
def notify_game_about_to_start(message):
    payload = {"message": message}
    try:
        response = requests.post(HA_WEBHOOK_URL_NOTIFY_GAME_ABOUT_TO_START, json=payload)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        debug_print(f"Notify game about to start: Successfully sent POST request to webhook")
    except requests.exceptions.RequestException as e:
        debug_print_error(f"Notify game about to start: Failed to send POST request to webhook: {e}")



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
@function_debug_decorator
def play_sounds(sound_files):
    global sonos, active_sonos_ip  # Add active_sonos_ip to global declaration

    if sonos is None:
        debug_print("No connection to Sonos speaker. Attempting to reconnect...")
        try:
            sonos = soco.SoCo(active_sonos_ip)
            debug_print(f"Reconnected to Sonos Speaker: {sonos.player_name}")
        except Exception as e:
            debug_print_error(f"Failed to reconnect to Sonos speaker: {e}")
            return  # Exit the function if we can't connect
    else:
        debug_print(f"Already connected to Sonos Speaker: {sonos.player_name}")
    
    if isinstance(sound_files, str):
        sound_files = [sound_files]  # this ensures that sound_files is always a list
    try:
        #print(f"Connecting to Sonos Speaker: {SONOS_IP}")
        #sonos = soco.SoCo(SONOS_IP)
        #print(f"Connected to Sonos Speaker: {sonos.player_name}")

        original_volume = sonos.volume

        # Check the current time
        current_time = datetime.now(pytz.timezone(TIMEZONE))
        if current_time.hour >= 23 or current_time.hour < 8:
            sonos.volume = 0
        elif DEBUGMODE:
            sonos.volume = 15
        else:
            sonos.volume = DEFAULT_SOUND_VOLUME
        
        # Display basic info about the speaker

        debug_print(f"Original Volume: {original_volume}  New Volume: {sonos.volume}")

        for sound_file in sound_files:
            sound_file = sound_file.replace(" ", "_")  # Replace spaces with underscores.  All files in the directory have underscores

            # Play the MP3 file
            MP3_FILE_URL = f"http://{RASPPI_IP}{sound_file}"
            debug_print(f"Attempting to play: {MP3_FILE_URL}")
            try:
                sonos.play_uri(MP3_FILE_URL)
            except soco.exceptions.SoCoException as e:
                debug_print_error(f"Failed to play sound {MP3_FILE_URL} on Sonos: {e}")

            # Check the state of the player
            #current_track = sonos.get_current_track_info()
            state = sonos.get_current_transport_info()["current_transport_state"]

            #print(f"Track Info: {current_track}")
            debug_print(f"Current State: {state}")

            # Check the playback position every few seconds
            while state == "PLAYING" or state == "TRANSITIONING":
                #track_position = sonos.get_current_track_info()['position']
                #print(f"Track Position: {track_position}")
                time.sleep(0.02)
                state = sonos.get_current_transport_info()["current_transport_state"]
                debug_print(f"Current State: {state}")
            debug_print(f"Current State: {state}")

        sonos.volume = original_volume

    except soco.exceptions.SoCoException as e:
        debug_print_error(f"Sonos error: {e}")
    except Exception as e:
        debug_print_error(f"Unexpected error: {e}")

    debug_print(f"play_sounds() completed")



#
# Pull the boxscore data from the API and do some parsing
#
# TODO:  Keeping this for now, but it's not being used.  Play-by-play data is more useful
#
@function_debug_decorator
def get_boxscore_data(gameId):
    global game_is_live
    
    endpoint = "v1/gamecenter/" + str(gameId) + "/boxscore"
    debug_print(f"Boxscore data: {endpoint}")
    data = get_apiweb_nhl_data(endpoint)
    if data:
        
        game_state = data.get('gameState')
        if game_state != 'LIVE':
            # mark the game as ended
            debug_print(f"Game is no longer live\n")
            game_is_live = False

            # If we want to do something when the game ends, we can do it here

        return data
    else:
        debug_print_error("Failed to retrieve data")



#
# Pull the play-by-play data from the API and do some parsing
#
@function_debug_decorator
def get_play_by_play_data(gameId, debug=False):
    global game_is_live
    debug_file="/Users/rmayor/Documents/Projects/NHL API/play-by-play-debug.json"
    
    if debug:
        debug_print(f"Debug mode: Reading play-by-play data from {debug_file}")
        try:
            with open(debug_file, 'r') as file:
                data = json.load(file)
                return data
        except Exception as e:
            debug_print_error(f"Failed to read debug file: {e}")
            return None
    else:
        endpoint = "v1/gamecenter/" + str(gameId) + "/play-by-play"
        debug_print(f"Play-by-play data: {endpoint}")
        data = get_apiweb_nhl_data(endpoint)
        if data:
            game_state = data.get('gameState')
            if game_state == 'OFF':  # should I count CRIT as live?
                # mark the game as ended
                debug_print(f"Game is no longer live.  gameState: {game_state}\n")  
                game_is_live = False

                # If we want to do something when the game ends, we can do it here

            return data
        else:
            debug_print_error("Failed to retrieve data")
            return None


#
#  Get the goal scorer and assists data from the play-by-play API for the most recent Toronto goal.  Return the list of names
#
#  Need to ensure that the event we've found is the most recent goal event and not the same as the last one we found.
#  Use the sortOrder field in the event, but also store and check against the last goal we successfully found.
#
#  
#  The event data populates over time, so we need to wait for the data to be populated before we can get the goal scorer info.
#  There are potentially multiple pieces of data in the event that come in over time, so need to check that it's all available.
#  Once the goal scorere info is available, we can play the sounds.  Note that if the goal scorer info is there, but the assit
#  info is not, we can still play the goal scorer info.  It's possible there was no assist, so just proceed at that point to 
#  play the sounds.
#
#  There is a potential issue where a second goal is scored before the data is populated for the first goal.  In this case, we
#  might have a problem.  
#
@function_debug_decorator
def get_goal_scorer(gameId, debug=False):
    global most_recent_goal_event_id
    retry_count = -1
    error_count = 0  # Use this so we don't retry forever and get stuck
    assist1_player_id = 0
    assist2_player_id = 0

    debug_print(f"Starting goal scorer search for game {gameId}")
    try:
        while True:
            restart_while_loop = False
            debug_print(f"get_goal_scorer: Refreshing play-by-play events")

            retry_count += 1
            if retry_count > 35:  # Try for about 3 minutes
                debug_print(f"Failed to find goal_scorer info too many times.  Exiting get_goal_scorer()")
                return None

            time.sleep(5)  # Check every 5 seconds
            data = get_play_by_play_data(gameId, debug)
            if not data:
                debug_print(f"Failed to retrieve play-by-play data while trying to get_goal_scorer().  Pausing for 5 seconds and retrying...")
                error_count += 1
                if error_count > 5:
                    debug_print(f"Failed to retrieve play-by-play data too many times.  Exiting get_goal_scorer()")
                    return None
                continue

            events = data.get('plays', [])

            debug_print(f"Searching events for goal scorer info")
            
            # Sort events based on sortOrder field
            events.sort(key=lambda x: x.get('sortOrder', 0), reverse=True)
            
            for event in events:
                debug_print(f"- Event: {event.get('eventId')} sortOrder: {event.get('sortOrder')}")
                    
                if event.get('typeCode') == 505:  # Goal event
                    debug_print(f"   Goal event found.  TypeCode: {event.get('typeCode')}")

                    scoring_team_id = event.get('details', {}).get('eventOwnerTeamId')
                    if scoring_team_id == None:
                        debug_print(f"   Found the goal event, but there are no details or not eventOwnerTeamId yet.  Wait for data to populate and retry...")
                        restart_while_loop = True
                        break  # Break out of the for loop and retry the while loop

                    if scoring_team_id == TORONTO_TEAM_ID:
                        if most_recent_goal_event_id == event.get('eventId'):
                            debug_print(f"   Found the goal event, but it's the same as the most recent goal event.  Wait for data to populate and retry...")
                            restart_while_loop = True
                            break

                        scoring_player_id = event.get('details', {}).get('scoringPlayerId')
                        if scoring_player_id:  # Check if scoringPlayerId is populated
                            debug_print(f"   Found the right goal event with a scoringPlayerId.  ScoringPlayerId: {scoring_player_id}")

                            assist1_player_id = event.get('details', {}).get('assist1PlayerId')
                            assist2_player_id = event.get('details', {}).get('assist2PlayerId')
                            
                            most_recent_goal_event_id = event.get('eventId')

                            return {
                                'scoringPlayerID': scoring_player_id,
                                'assist1PlayerID': assist1_player_id,
                                'assist2PlayerID': assist2_player_id
                            }
                        else:
                            debug_print(f"   Found the goal event, but there is no scoringPlayerId yet.  Wait for data to populate and retry...")
                            restart_while_loop = True
                            break  # Break out of the for loop and retry the while loop
            if restart_while_loop:
                continue  # Restart the while loop

    except KeyError as e:
        debug_print_error(f"Key error while parsing data: {e}")
    except Exception as e:
        debug_print_error(f"An unexpected error occurred: {e}")
    
    return None



#
# Check the current scores to see if there has been a recent goal
#
@function_debug_decorator
def check_scores(data, gameId):
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
                debug_print(f"Home Team (Toronto) Score:  {home_team_score}")
            else:
                debug_print(f"Home Team (Opponent) Score: {home_team_score}")
        else:
            debug_print_error("Home Team Score not found")

        if away_team_score is not None:
            if toronto_is_home == True:
                debug_print(f"Away Team (Opponent) Score: {away_team_score}")
            else:
                debug_print(f"Away Team (Toronto) Score:  {away_team_score}")
        else:
            debug_print_error("Away Team Score not found")

        # Check for a goal
        if toronto_is_home:
            if home_team_score > toronto_score:
                debug_print(f"*** TORONTO GOAL!")
                toronto_goal = True
            if away_team_score > opponent_score:
                debug_print(f"*** OPPONENT GOAL")
                play_sounds(SOUND_BOO_FILE)
                if opponent_is_senators:
                    sounds_to_play = ["/roster/BradySucks.mp3"]
                    play_sounds(sounds_to_play)
                
            toronto_score = home_team_score  # Update the scores.  It's possible they decreased if the goal was disallowed
            opponent_score = away_team_score
        else:
            if away_team_score > toronto_score:
                debug_print(f"*** TORONTO GOAL!")
                toronto_goal = True
            if home_team_score > opponent_score:
                debug_print(f"*** OPPONENT GOAL")
                play_sounds(SOUND_BOO_FILE)
                if opponent_is_senators:
                    sounds_to_play = ["/roster/BradySucks.mp3"]
                    play_sounds(sounds_to_play)

            toronto_score = away_team_score
            opponent_score = home_team_score
        
        # If there was a goal, then activate the goal light, play the goal horn, and play the scorer and assist names
        if toronto_goal:
            activate_goal_light("TORONTO GOAL!")
            play_sounds(SOUND_GOAL_HORN_FILE)

            goal_scorer_info = get_goal_scorer(gameId, False)  # This will loop until it finds the goal scorer info
            if goal_scorer_info:
                debug_print(f"   Scoring Player ID: {goal_scorer_info['scoringPlayerID']}")
                debug_print(f"   Assist 1 Player ID: {goal_scorer_info['assist1PlayerID']}")
                debug_print(f"   Assist 2 Player ID: {goal_scorer_info['assist2PlayerID']}")

                sounds_to_play = ["/roster/GoalScoredBy.mp3"]
                if goal_scorer_info['scoringPlayerID'] in roster:
                    sounds_to_play.append(f"/roster/{roster[goal_scorer_info['scoringPlayerID']]}.mp3")
                
                if goal_scorer_info['assist1PlayerID'] in roster:
                    sounds_to_play.append("/roster/Assist.mp3")
                    sounds_to_play.append(f"/roster/{roster[goal_scorer_info['assist1PlayerID']]}.mp3")
                
                if goal_scorer_info['assist2PlayerID'] in roster:
                    sounds_to_play.append(f"/roster/{roster[goal_scorer_info['assist2PlayerID']]}.mp3")
                
                play_sounds(sounds_to_play)
            else:
                debug_print_error(f"Failed to retrieve goal scorer information.\n")


    except KeyError as e:
        debug_print_error(f"Key error while checking scores: {e}")
    except Exception as e:
        debug_print_error(f"Unexpected error while checking scores: {e}")

    return


#
# Get the roster data for the Toronto Maple Leafs
#
@function_debug_decorator
def get_toronto_roster():
    debug_print(f"Retrieving roster data...")
    roster = {}
    endpoint = "v1/roster/TOR/20252026"

    try:
        data = get_apiweb_nhl_data(endpoint)
        
        if data:           
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
            
            debug_print(f"Roster data retrieved successfully")
            return roster
        else:
            debug_print_error(f"Failed to retrieve roster data\n")
    
    except KeyError as e:
        debug_print_error(f"Key error while parsing roster data: {e}")
    except Exception as e:
        debug_print_error(f"An unexpected error occurred while retrieving roster data: {e}")
    
    return None


#
# Return the gameId if Toronto is playing now or determine if it's about to start
#
#
# The possible states are:
#   - The start time is in the future
#   - The start time is in the past AND the gameState is OFF
#       - The game is about to start
#       - The game has finished
#   - The start time is in the past AND the gameState is LIVE
#
#  There are other gameStates:  OFF, CRIT, FUT... what else?
#  	•	FUT: Future – The game is scheduled for a future date and has not started yet.
#	•	PRE: Pre-Game – The game is about to start, with pre-game activities underway.
#	•	LIVE: Live – The game is currently in progress.
#	•	OFF: Off – The game has concluded.
#	•	PST: Postponed – The game has been postponed to a later date.
#	•	CAN: Canceled – The game has been canceled and will not be played.#
#
@function_debug_decorator
def current_toronto_game():
    global game_is_live  # Use the global variable
    global toronto_is_home
    global game_today
    global game_about_to_start
    global wait_time
    global opponent_is_senators

    today_date = f"{datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')}"
    endpoint = "v1/schedule/" + today_date

    debug_print(f"Checking schedule for {today_date}")

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
                            debug_print(f"Toronto is playing today with gameId: {gameId}")

                            # Get the opponent team name
                            if home_team_id == TORONTO_TEAM_ID:  
                                toronto_is_home = True
                                opponent_city_name = game.get('awayTeam', {}).get('placeName', {}).get('default')
                                opponent_team_name = game.get('awayTeam', {}).get('commonName', {}).get('default')
                                debug_print(f"Toronto Maple Leafs are the home team and playing against the {opponent_city_name} {opponent_team_name}")
                            else:
                                toronto_is_home = False
                                opponent_city_name = game.get('homeTeam', {}).get('placeName', {}).get('default')
                                opponent_team_name = game.get('homeTeam', {}).get('commonName', {}).get('default')
                                debug_print(f"Toronto Maple Leafs are the away team and playing against the {opponent_city_name} {opponent_team_name}")

                            # If the opponent_team_name is "Senators" then set opponent_is_senators to be True
                            if opponent_team_name == "Senators":
                                opponent_is_senators = True
                                debug_print("Opponent is the Senators!")
                            else:
                                opponent_is_senators = False

                            # Calculations on the start time and delta from the current time
                            startTimeUTC = game.get('startTimeUTC')
                            start_time = datetime.strptime(startTimeUTC, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc).astimezone(pytz.timezone(TIMEZONE))
                            current_time = datetime.now(pytz.timezone(TIMEZONE))
                            time_delta = (start_time - current_time)

                            debug_print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            debug_print(f"Start time:   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            debug_print(f"Time until game starts:   {str(time_delta).split('.')[0]}")
 
                            # 
                            #  Logic to determine the state of the game
                            #
                            gameState = game.get('gameState')
                            debug_print(f"Game State: {gameState}")
                            if gameState == 'PRE':  # Another scenario for the game about to start.  Use same logic as below
                                debug_print(f"PRE  Game is about to start!  Starting in {str(time_delta).split('.')[0]}")
                                if not game_about_to_start:
                                    do_game_about_to_start(opponent_team_name)
                                return gameId
                            elif gameState == 'FUT':  # Another scenario for the game in the future.  Use same logic as below
                                debug_print(f"FUT. Game will start in the future at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                game_about_to_start = False
                                if time_delta > timedelta(hours=1): # If it's more than an hour in the future, then wait hours
                                    rounded_time_delta = timedelta(hours=time_delta.seconds // 3600)
                                    wait_time = rounded_time_delta.total_seconds()
                                    debug_print(f"Rounded wait time to the nearest hour: {rounded_time_delta}")
                                else:
                                    wait_time = 5 * 60  # If it's less than an hour in the future, then recheck in 5 minutes
                                    debug_print(f"Wait time set to 5 minutes")
                                return None   
                            elif time_delta > timedelta(minutes=0):  # Start time is in the future
                                debug_print(f"Game will start in the future at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                game_about_to_start = False
                                if time_delta > timedelta(hours=1): # If it's more than an hour in the future, then wait hours
                                    rounded_time_delta = timedelta(hours=time_delta.seconds // 3600)
                                    wait_time = rounded_time_delta.total_seconds()
                                    debug_print(f"Rounded wait time to the nearest hour: {rounded_time_delta}")
                                else:
                                    wait_time = 5 * 60  # If it's less than an hour in the future, then recheck in 5 minutes
                                    debug_print(f"Wait time set to 5 minutes")
                                return None                            
                            elif time_delta < timedelta(hours=-1) and gameState != 'LIVE':   # Start time at least an hour ago 
                                debug_print(f"!LIVE  Game started at least an hour ago and is not live. GameState: {gameState}")
                                game_today = False  # Don't check again until tomorrow
                                game_is_live = False
                                game_about_to_start = False
                                return None
                            elif time_delta < timedelta(minutes=0) and gameState != 'LIVE':   # Start time in the past and game is OFF
                                debug_print(f"!LIVE  Game is about to start!  Start time in the past and not live.  Starting in {str(time_delta).split('.')[0]}")
                                if not game_about_to_start:
                                    do_game_about_to_start(opponent_team_name)
                                return gameId
                            elif gameState == 'LIVE':  # Check if the game is live
                                debug_print(f"Game is LIVE!")
                                if not game_is_live:  # If the game wasn't already live, then set it as started
                                    start_game(opponent_team_name)
                                return gameId
                            elif gameState == 'PST':
                                debug_print(f"Game has been postponed.  Treat like no game today.  gameState: {gameState}")
                                return None
                            elif gameState == 'CAN':
                                debug_print(f"Game has been cancelled.  Treat like no game today.  gameState: {gameState}")
                            else:
                                debug_print(f"Game is in an unknown state.  gameState: {gameState}")
                                return None

                    debug_print(f"No Toronto games today")
                    game_today = False
                    game_about_to_start = False
                    game_is_live = False
                    return None
                else:
                    debug_print(f"No games today")
                    game_today = False
                    game_about_to_start = False
                    game_is_live = False
                    return None
        except KeyError as e:
            debug_print_error(f"Key error while parsing schedule data: {e}")
            game_today = False
            game_about_to_start = False
            game_is_live = False
        except Exception as e:
            debug_print_error(f"Unexpected error while parsing schedule data: {e}")
            game_today = False
            game_about_to_start = False
            game_is_live = False
    else:
        debug_print_error("Failed to retrieve data")
        game_today = False
        game_about_to_start = False
        game_is_live = False
    return None



#
#  Game is about to start
#
@function_debug_decorator
def do_game_about_to_start(opponent_team_name):
    global game_about_to_start

    try:
        game_about_to_start = True
        debug_print(f"Game is about to start!\n")

        notify_game_about_to_start("Game about to start!")

        sounds_to_play = ["/league/About_to_start.mp3"]
        if toronto_is_home:
            sounds_to_play.append(f"/league/{opponent_team_name}.mp3")
            sounds_to_play.append(f"/league/Versus.mp3")
            sounds_to_play.append(f"/league/Maple_Leafs.mp3") 
        else:
            sounds_to_play.append(f"/league/Maple_Leafs.mp3") 
            sounds_to_play.append(f"/league/Versus.mp3")
            sounds_to_play.append(f"/league/{opponent_team_name}.mp3")
            
        play_sounds(sounds_to_play)
    except Exception as e:
        debug_print_error(f"An error occurred in game_about_to_start: {e}")



#
# Reset the scores for a game when it starts
#
@function_debug_decorator
def start_game(opponent_team_name):
    global game_is_live
    global game_about_to_start
    global toronto_score
    global opponent_score
    global toronto_is_home
    global most_recent_goal_event_id

    try:
        game_is_live = True
        toronto_score = 0
        opponent_score = 0
        most_recent_goal_event_id = 0

        debug_print(f"Game has started!\n")

        if game_about_to_start:  # if we already knew the game was about to start then this is a cold start so play the sounds
            sounds_to_play = ["/league/Started.mp3"]
            if toronto_is_home:
                sounds_to_play.append(f"/league/{opponent_team_name}.mp3")
                sounds_to_play.append(f"/league/Versus.mp3")
                sounds_to_play.append(f"/league/Maple_Leafs.mp3") 
            else:
                sounds_to_play.append(f"/league/Maple_Leafs.mp3") 
                sounds_to_play.append(f"/league/Versus.mp3")
                sounds_to_play.append(f"/league/{opponent_team_name}.mp3")

            play_sounds(sounds_to_play)
            game_about_to_start = False

    except Exception as e:
        debug_print_error(f"An error occurred in start_game: {e}")



#
# Main function
#
@function_debug_decorator
def goal_tracker_main():
    global game_is_live # Use the global variable
    global game_about_to_start
    global toronto_is_home 
    global game_today
    global wait_time
    global roster
    global sonos

    game_is_live = False
    game_about_to_start = False
    toronto_is_home = False
    game_today = False 
    wait_time = DEFAULT_WAIT_TIME
    active_sonos_ip = SONOS_FAMILY_ROOM_IP
    debug_mode = DEBUGMODE

    debug_print(f"")
    debug_print(f"***************************************************************************************")
    debug_print(f"*** Starting goal tracker                                                           ***")
    debug_print(f"***************************************************************************************")
    debug_print(f"")

    # Start by getting the roster data with retry logic
    max_retries = 3
    retry_count = 0
    roster = None
    
    while roster is None and retry_count < max_retries:
        try:
            roster = get_toronto_roster()
            if roster:
                debug_print(f"Successfully retrieved roster data with {len(roster)} players")
            else:
                debug_print_error("get_toronto_roster() returned None")
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                wait_time = 30 * retry_count  # Increase wait time with each retry
                debug_print_error(f"Failed to get roster (attempt {retry_count}/{max_retries}): {e}")
                debug_print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                debug_print_error(f"Failed to get roster after {max_retries} attempts. Initializing empty roster.")
                roster = {}  # Initialize empty roster so the rest of the program can continue
    
    time.sleep(10)  # Pause for 10 seconds to avoid hitting the API too quickly


    # Connect to the Sonos speaker
    try:
        if (debug_mode == True):
            debug_print(f"== Debug mode is on\n")
            active_sonos_ip = SONOS_BEAM_IP

        debug_print(f"Connecting to Sonos Speaker: {active_sonos_ip}")
        sonos = soco.SoCo(active_sonos_ip)  # Assign to the global variable
        debug_print(f"Connected to Sonos Speaker: {sonos.player_name}")

    except soco.exceptions.SoCoException as e:
        debug_print_error(f"Sonos error: {e}")
    except Exception as e:
        debug_print_error(f"Unexpected error connecting to Sonos Speaker: {e}")


    if (debug_mode == True):
        #play_sounds(SOUND_GAME_START_FILE)
        #time.sleep(5)

        gameId = "2024010006"
        toronto_is_home = True
        opponent_team_name = "Canadiens"
        debug_print(f"Starting game for {opponent_team_name}")
        start_game(opponent_team_name)
        time.sleep(10)


        goal_scorer_info = get_goal_scorer(gameId, debug_mode)
        if goal_scorer_info:
            debug_print(f"   Scoring Player ID: {goal_scorer_info['scoringPlayerID']}")
            debug_print(f"   Assist 1 Player ID: {goal_scorer_info['assist1PlayerID']}")
            debug_print(f"   Assist 2 Player ID: {goal_scorer_info['assist2PlayerID']}")

        return # For now, just play the start sound and exit#activate_goal_light(1)
        #play_sounds(SOUND_GOAL_HORN_FILE)


    # Main loop
    while (True):  # Keep checking for games
     
        # Makes a call to the NHL API to get the game schedule.  
        # Should run this only a few times a day, and then start calling boxscore within 5 minutes of start time
        gameId = current_toronto_game()

        if game_today == True:
            # FIX: Add defensive check to prevent infinite loop
            if gameId is None:
                debug_print("WARNING: game_today is True but gameId is None. Resetting flags.")
                game_today = False
                game_about_to_start = False
                game_is_live = False
                continue

            if (game_is_live == True):
                debug_print(f"Game has already started\n")
            elif (game_about_to_start == True):
                debug_print(f"Game about to start!  Waiting 20 seconds...\n")
                time.sleep(20)  # Check every 20 seconds if the game is about to start
            else: 
                # Round down to the nearest hour and wait until then to check the game again
                hours, remainder = divmod(wait_time, 3600)
                minutes, _ = divmod(remainder, 60)
                next_check_time = datetime.now(pytz.timezone(TIMEZONE)) + timedelta(seconds=wait_time)
                debug_print(f"No active game. Waiting {int(hours)} hours and {int(minutes)} minutes... until {next_check_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                time.sleep(wait_time) 
                wait_time = DEFAULT_WAIT_TIME  # reset the wait time to 5 minutes for next time
        else:
            debug_print(f"Pausing for 8 hours as there is no game today\n")
            time.sleep(60*60*8)  # Pause for 8 hours if there's no game today

        # Main loop to execute during a live game
        while (game_is_live == True):
            try:
                #boxscore_data = get_boxscore_data(gameId)  # Retrieve the current boxscore data from the API
                #check_scores(boxscore_data)  # Check the scores for new goals
                playbyplay_data = get_play_by_play_data(gameId, False)  # Retrieve the current play-by-play data from the API
                check_scores(playbyplay_data, gameId)  # Check the scores for new goals
                time.sleep(SCORE_CHECK_INTERVAL)  # Check scores every few seconds
            except Exception as e:
                debug_print_error(f"An error occurred during the game loop: {e}\nPausing for 30 seconds before retrying...\n")
                time.sleep(30)  # Wait for 30 seconds before retrying
        

    


if __name__ == "__main__":

    # direct output to a log file
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    #if DEBUGMODE:
    #    log_file = sys.stdout
    #else:
        # Open a file for logging and set sys.stdout to the file (write mode to start fresh each time)
    log_file = open('/app/output.log', 'w')
        # Redirect stdout to the file
    sys.stdout = log_file

    # Reconfigure stdout for immediate flushing
    sys.stdout.reconfigure(line_buffering=True)

    # Redirect stderr to the file
    sys.stderr = log_file
    # Reconfigure stderr for immediate flushing
    sys.stderr.reconfigure(line_buffering=True)

    debug_print(f"Checking that the network is accessible during start up...")
    
    # Wait for network to be available
    max_retries = 30  # Try for up to 5 minutes
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Try to connect to Google's DNS to check basic connectivity
            response = requests.get("https://8.8.8.8", timeout=5)
            if response.status_code == 200:
                debug_print(f"Network is accessible")
                break
        except requests.RequestException:
            retry_count += 1
            if retry_count < max_retries:
                debug_print_error(f"Network not yet accessible (attempt {retry_count}/{max_retries}). Waiting 10 seconds...")
                time.sleep(10)
            else:
                debug_print_error(f"Network still not accessible after {max_retries} attempts. Continuing anyway...")
    


    goal_tracker_main()

