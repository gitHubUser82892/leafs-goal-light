#
#  sudo systemctl restart webhook_listener.service
#  sudo systemctl status webhook_listener.service
#  sudo systemctl start webhook_listener.service
#  sudo systemctl stop webhook_listener.service
#  sudo systemctl enable webhook_listener.service   To enable a service to start automatically at boot time 
#  sudo systemctl disable webhook_listener.service   To disable from startign at boot time
#  sudo journalctl -u webhook_listener.service   To view the logs for a specific service
#
#  /etc/systemd/system/webhook_listener.service
#  sudo systemctl daemon-reload   After changing the service file
#


from flask import Flask, request, jsonify, send_from_directory
import os
import time
import signal
import subprocess

# Modify the PATH to include the necessary directories
print("PATH:", os.environ["PATH"])
os.environ["PATH"] += os.pathsep + "/usr/bin"

app = Flask(__name__)

# Replace with the name of the process you want to restart
PROCESS_NAME = "python3 /home/rmayor/Projects/leafs_goal_light/goal_tracker.py"

# MP3 directory for leafs goal horn
MP3_DIR = "/home/rmayor/Projects/leafs_goal_light"



#
#  The route for the game start sound
#
@app.route('/files/leafs_game_start.mp3')
def serve_start_mp3():
    mp3_filename = "leafs_game_start.mp3"
    try: 
       file_path = os.path.join(MP3_DIR, mp3_filename)
       print(f"Trying to send file from {file_path}")

       # Check if the file exists in the directory
       if os.path.exists(os.path.join(MP3_DIR, mp3_filename)):
          return send_from_directory(MP3_DIR, mp3_filename)
       else:
          print(f"File not found: {file_path}")
          return "File not found", 404
    except Exception as e:
       print(f"Error sending mp3 file: {e}")
       return "Error serving file", 500


#
# The route for the goal sound
#
@app.route('/files/leafs_goal_horn.mp3')
def serve_horn_mp3():
    mp3_filename = "leafs_goal_horn.mp3"

    try: 
       file_path = os.path.join(MP3_DIR, mp3_filename)
       print(f"Trying to send file from {file_path}")

       # Check if the file exists in the directory
       if os.path.exists(os.path.join(MP3_DIR, mp3_filename)):
          return send_from_directory(MP3_DIR, mp3_filename)
       else:
          print(f"File not found: {mp3_filename}")
          return "File not found", 404
    except Exception as e:
       print(f"Error sending mp3 file: {e}")
       return "Error serving file", 500


#
#  The route to listen for a notification of commits to the git repo
#
@app.route('/webhook/gitcommit', methods=['POST'])
def webhook():
    print("Headers:", request.headers)

    data = request.json  # Get JSON data from the webhook
    print(f"Received webhook data: {data}")

    # Kill the existing process
    kill_process(PROCESS_NAME)

    time.sleep(5)
    # Restart the process
    start_process(PROCESS_NAME)

    return jsonify({"status": "success", "message": f"{PROCESS_NAME} restarted"}), 200


#
#  Kill the existing process
#
def kill_process(process_name):
    try:
        # Get the process ID (PID)
        pid = int(subprocess.check_output(["pgrep", "-f", process_name]))
        os.kill(pid, signal.SIGTERM)  # Send SIGTERM signal to kill the process
        print(f"Killed process {process_name} with PID {pid}")
    except Exception as e:
        print(f"Error killing process {process_name}: {e}")
    time.sleep(1)


#
#  Pull down the latest from git and start the leafs_goal_light application
#
def start_process(process_name):
    try:
        # Pull down refreshes to the code
        print(f"Pulling from git")
        subprocess.Popen(["sudo", "-u", "rmayor", "/usr/bin/git", "-C", "/home/rmayor/Projects/leafs_goal_light", "pull", "https://github.com/gitHubUser82892/leafs-goal-light", "main"])
    except Exception as e:
        print(f"Error pulling from git: {e}")


    print(f"Waiting for git to finish before starting")
    time.sleep(15)

    try:
        # Start the process (modify the command as necessary)
        subprocess.Popen(["python3", "/home/rmayor/Projects/leafs_goal_light/goal_tracker.py"])  # You may need to include the full path
        print(f"Started process {process_name}")
    except Exception as e:
        print(f"Error starting process {process_name}: {e}")
    time.sleep(1)


#
#  Upon startup, kill the existing process, start the webhook_listener and start the goal_tracker app
#
if __name__ == '__main__':
    kill_process(PROCESS_NAME)
    start_process(PROCESS_NAME)
    app.run(host='0.0.0.0', port=5000, debug=True)  # Listen on all interfaces
    

