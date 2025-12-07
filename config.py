"""
Shared Configuration File
=========================

Configuration constants used by both goal_tracker.py and webhook_listener.py.
This is the single source of truth for IP addresses and other shared settings.
"""

# Sonos speaker IP addresses
# Update these if your Sonos speakers get new DHCP addresses
SONOS_OFFICE_IP = "192.168.86.29"      # Office:1 Sonos speaker
SONOS_FAMILY_ROOM_IP = "192.168.70.100" # FamilyRoom2 speaker
SONOS_BEAM_IP = "192.168.70.101"       # Family Room Beam Sonos speaker

# List of all Sonos IPs for easy iteration
SONOS_SPEAKER_IPS = [
    SONOS_OFFICE_IP,
    SONOS_FAMILY_ROOM_IP,
    SONOS_BEAM_IP,
]
