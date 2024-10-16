#
# Originally by:  gitHubUser82892 
#
# # These are the header comments.  
# Change from external nabu casa to local so I don't reveal my external URL and webhook
#
# Stored in github:  https://github.com/gitHubUser82892/leafs-goal-light
#
# TODO
#    - Get the sound working through this script
#    - Set the sound volume
#    - Test both the start and goal sounds
#    - Play to the right speaker
#    - Move the webhook_listener into github
#    - Fix all the paths for the webhook_listener
#    - Test auto-crash recovery
#
# try to push all the way through the pipeline.  11:53
# #


import requests
import time
import json
import pytz
import sys
from datetime import datetime

# Global variables
game_is_live = False
game_about_to_start = False
game_in_intermission = False
toronto_is_home = False
toronto_score = 0
opponent_score = 0
game_today = False

SONOS_IP = "192.168.86.250"  #  Office:1 Sonos speaker
#SONOS_IP = "192.168.86.196" #  Family Room Beam Sonos speaker
RASPPI_IP = "192.168.86.61:5000"  # This is the IP of the Raspberry Pi running the webserver
SOUND_GAME_START_FILE = "/files/leafs_game_start.mp3"  # Webhook to get the file returned from the webserver
SOUND_GOAL_HORN_FILE = "/files/leafs_goal_horn.mp3"  # Webhook to get the file returned from the webserver

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
                        game_today = True

                        # Toronto is playing today.  Get the gameId and start time
                        gameId = (game.get('id'))
                        startTimeUTC = game.get('startTimeUTC')

                        # Parse startTimeUTC to datetime object
                        start_time = datetime.strptime(startTimeUTC, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern'))
                        current_time = datetime.now(pytz.timezone('US/Eastern')).replace(tzinfo=pytz.timezone('US/Eastern'))
                        
                        print(f"Toronto is playing today with gameId: {gameId} starting at {start_time}")

                        # convert away_team_id to the name of the team
                        # in the json, this is awayTeam.placeName.default
                        opponent_team_name = game.get('awayTeam', {}).get('placeName', {}).get('default')
                        if home_team_id == 10:  
                            print(f"Toronto is the home team and playing against {opponent_team_name}")
                        else:
                            print(f"Toronto is the away team and playing against {opponent_team_name}")


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
                        elif ((start_time - current_time).total_seconds() < 300) & ((start_time - current_time).total_seconds() > 0):  # If it's not started, but it will within 5 minutes
                            print(f"Game is about to start!")
                            game_about_to_start = True
                            return gameId
                        elif (start_time - current_time) < 0:
                            print(f"Toronto played earlier today")
                            game_today = False
                            game_is_live = False
                            game_about_to_start = False 
                            return None
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
def check_scores(boxscore_data):
    global toronto_score
    global opponent_score
    global toronto_is_home
    home_team_score = 0
    away_team_score = 0

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
            play_sound(SOUND_GOAL_HORN_FILE)
        if away_team_score > opponent_score:
            print(f"Boxscore: OPPONENT GOAL\n")
            opponent_score = away_team_score
    else:
        if away_team_score > toronto_score:
            print(f"Boxscore: TORONTO GOAL!\n")
            post_to_webhook(1)
            play_sound(SOUND_GOAL_HORN_FILE)
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

    play_sound(SOUND_GAME_START_FILE)



#
# Play the goal horn sound
#
# TODO: How do I set the volume?
def play_sound(sound_file):
    # Prepare the HTTP request
    url = f"http://{SONOS_IP}:1400/MediaRenderer/AVTransport/Control"
    
    headers = {
        "Content-Type": "audio/mpeg",  # Change to audio/mpeg for MP3
        "SOAPACTION": '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"',
    }
    
    # The payload for the request
    payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                 s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
            <SetAVTransportURI xmlns="urn:schemas-upnp-org:service:AVTransport:1">
                <InstanceID>0</InstanceID>
                <CurrentURI>http://{RASPPI_IP}{sound_file}</CurrentURI>  # Update to use MP3_FILE
                <CurrentURIMetaData></CurrentURIMetaData>
            </SetAVTransportURI>
        </s:Body>
    </s:Envelope>"""

    # Send the request to the Sonos speaker
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        print("Audio sent to Sonos speaker.")
    else:
        print("Error:", response.text)






#
# Main function
#
def goal_tracker_main():
    global game_is_live # Use the global variable
    global game_about_to_start
    global toronto_is_home 
    global game_today

    game_is_live = False
    game_about_to_start = False
    toronto_is_home = False
    game_today = False 

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

        while (game_is_live == True):
                    boxscore_data = get_boxscore_data(gameId)  # Retrive the current boxscore data and scores
                    # playbyplay_data = get_playbyplay_data(gameId)   # Not using this now, as boxscore seems to be just as up to date
                    check_scores(boxscore_data)  # Check the scores for new goals
                    time.sleep(12) # Check scores every 12 seconds
        
        print(f"No active game\n")

        if (game_about_to_start == True):
            time.sleep(30)  # Check every 30 seconds if the game is about to start
        else: 
            time.sleep(5*60)  # 5 minute delay before checking 
    


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

    print(f"***************************************************************************")
    print(f"*\n* Starting goal tracker at 1218 {datetime.now()}\n*\n")

    goal_tracker_main()

