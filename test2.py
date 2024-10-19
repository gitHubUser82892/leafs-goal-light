import soco
import time

# SONOS_IP = "192.168.86.196"  # family room beam speaker
SONOS_IP = "192.168.86.29"  # office speaker
MP3_FILE_URL = "http://192.168.86.61:5000/files/leafs_goal_horn.mp3"

def main():

    sonos = soco.SoCo(SONOS_IP)  

    # Display basic info about the speaker
    print(f"Connected to Sonos Speaker: {sonos.player_name}")
    print(f"Current Volume: {sonos.volume}")
    original_volume = sonos.volume
    sonos.volume = 50
    
    # Play the MP3 file
    print(f"Attempting to play: {MP3_FILE_URL}")
    sonos.play_uri(MP3_FILE_URL)

    # Check the state of the player
    time.sleep(2)  # Give some time for the Sonos speaker to start playing
    current_track = sonos.get_current_track_info()
    state = sonos.get_current_transport_info()["current_transport_state"]

    print(f"Track Info: {current_track}")
    print(f"Current State: {state}")
    
    # Volume control for debugging
    if state == "PLAYING":
        print("Playback started successfully.")
    else:
        print(f"Playback did not start. Current state: {state}")
    
    # Check the playback position every few seconds
    for i in range(5):
        track_position = sonos.get_current_track_info()['position']
        print(f"Track Position after {i+1} seconds: {track_position}")
        time.sleep(1)

    sonos.volume = original_volume



if __name__ == "__main__":
    main()
