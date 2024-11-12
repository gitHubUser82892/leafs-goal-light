import requests
import time
import json
import pytz
import sys
import soco
from datetime import datetime
from datetime import timedelta

SONOS_IP = "192.168.86.29"  #  Office:1 Sonos speaker
#SONOS_IP = "192.168.86.196" #  Family Room Beam Sonos speaker
#SONOS_IP = "192.168.86.46"  # FamilyRoom2 speaker

RASPPI_IP = "192.168.86.61:5000"  # This is the IP of the Raspberry Pi running the webserver
SOUND_GAME_START_FILE = "/files/leafs_game_start.mp3"  # Webhook to get the file returned from the webserver
SOUND_GOAL_HORN_FILE = "/files/leafs_goal_horn.mp3"  # Webhook to get the file returned from the webserver

#
# Play sounds on a Sonos speaker
#
def play_sounds(sound_files):
    try:
        sonos = soco.SoCo(SONOS_IP)

        # Display basic info about the speaker
        print(f"Connected to Sonos Speaker: {sonos.player_name}")
        print(f"Current Volume: {sonos.volume}")
        original_volume = sonos.volume
        sonos.volume = 15

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




def goal_tracker_main():
    global game_is_live # Use the global variable
    global game_about_to_start
    global toronto_is_home 
    global game_today
    global wait_time

    game_is_live = False
    game_about_to_start = False
    toronto_is_home = False
    game_today = False 
    roster = {}

    debug_mode = True
    if (debug_mode == True):
        print(f"Debug mode is on \n")
        #play_sound(SOUND_GAME_START_FILE)
        #play_sound(SOUND_GOAL_HORN_FILE)
        play_sounds([
            "/roster/GoalScoredBy.mp3",
            "/roster/Knies.mp3",
            "/roster/Assist.mp3",
            "/roster/Marner.mp3",
            "/roster/Nylander.mp3"
        ])
        return # For now, just play the start sound and exit
    


if __name__ == "__main__":



    print(f"***************************************************************************************")
    print(f"*\n* Starting sound testing at {datetime.now()}\n*")
    print(f"***************************************************************************************\n")

    goal_tracker_main()