"""
Webhook Listener Service
========================

Flask application that serves MP3 files and manages the goal_tracker process.
"""

from flask import Flask, send_from_directory
import os
import time
import signal
import subprocess
from goal_tracker import activate_goal_light, play_sounds

app = Flask(__name__)

# Process and directory configuration
PROCESS_NAME = "python3 /app/goal_tracker.py"
MP3_DIR = "/app"
ROSTER_SOUNDS_DIR = "/app/roster_sounds"
LEAGUE_SOUNDS_DIR = "/app/league_sounds"


@app.route('/files/<filename>')
def serve_mp3(filename):
    """Serve MP3 files from the main directory"""
    try:
        file_path = os.path.join(MP3_DIR, filename)
        print(f"Serving file: {file_path}")
        
        if os.path.exists(file_path):
            return send_from_directory(MP3_DIR, filename)
        else:
            print(f"File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"Error sending mp3 file: {e}")
        return "Error serving file", 500


@app.route('/roster/<filename>')
def serve_roster_mp3(filename):
    """Serve MP3 files from the roster directory"""
    try:
        file_path = os.path.join(ROSTER_SOUNDS_DIR, filename)
        print(f"Serving file: {file_path}")
        
        if os.path.exists(file_path):
            return send_from_directory(ROSTER_SOUNDS_DIR, filename)
        else:
            print(f"File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"Error sending mp3 file: {e}")
        return "Error serving file", 500


@app.route('/league/<filename>')
def serve_league_mp3(filename):
    """Serve MP3 files from the league directory"""
    try:
        file_path = os.path.join(LEAGUE_SOUNDS_DIR, filename)
        print(f"Serving file: {file_path}")
        
        if os.path.exists(file_path):
            return send_from_directory(LEAGUE_SOUNDS_DIR, filename)
        else:
            print(f"File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"Error sending mp3 file: {e}")
        return "Error serving file", 500


@app.route('/webhook/lightandsound', methods=['POST'])
def lightandsound():
    """Manually trigger the goal light and sound"""
    print("Manually playing the light and sound")
    try:
        activate_goal_light(1)
        play_sounds("/files/leafs_goal_horn.mp3")
        return "Success", 200
    except Exception as e:
        print(f"Error triggering light and sound: {e}")
        return "Error", 500


def kill_process(process_name):
    """Kill existing goal_tracker process"""
    try:
        pid = int(subprocess.check_output(["pgrep", "-f", process_name]))
        os.kill(pid, signal.SIGTERM)
        print(f"Killed process {process_name} with PID {pid}")
    except subprocess.CalledProcessError:
        print(f"No existing process found for {process_name}")
    except Exception as e:
        print(f"Error killing process {process_name}: {e}")
    time.sleep(1)


def start_process(process_name):
    """Start the goal_tracker process"""
    try:
        subprocess.Popen(["python3", "/app/goal_tracker.py"])
        print(f"Started process {process_name}")
    except Exception as e:
        print(f"Error starting process {process_name}: {e}")
    time.sleep(1)


if __name__ == '__main__':
    # Start goal_tracker on startup
    kill_process(PROCESS_NAME)
    start_process(PROCESS_NAME)
    
    # Start Flask server (disable debug in production)
    app.run(host='0.0.0.0', port=5000, debug=False)
