"""
PX4 Mission Planning Constants
Based on MAVLink protocol and PX4 autopilot system
"""

# MAVLink Command IDs (MAV_CMD)
class MAV_CMD:
    """MAVLink command constants for mission items"""
    NAV_WAYPOINT = 16
    NAV_LOITER_UNLIM = 17
    NAV_LOITER_TURNS = 18
    NAV_LOITER_TIME = 19
    NAV_RETURN_TO_LAUNCH = 20
    NAV_LAND = 21
    NAV_TAKEOFF = 22
    DO_CHANGE_SPEED = 178
    DO_SET_HOME = 179
    DO_SET_ROI = 201

# MAVLink Frame Types
class MAV_FRAME:
    """Coordinate frame reference constants"""
    GLOBAL = 0
    LOCAL_NED = 1
    MISSION = 2
    GLOBAL_RELATIVE_ALT = 3
    LOCAL_ENU = 4
    GLOBAL_INT = 5
    GLOBAL_RELATIVE_ALT_INT = 6
    LOCAL_OFFSET_NED = 7
    BODY_NED = 8
    BODY_OFFSET_NED = 9
    GLOBAL_TERRAIN_ALT = 10
    GLOBAL_TERRAIN_ALT_INT = 11

# Speed Types
class SPEED_TYPE:
    """Speed control types"""
    AIRSPEED = 0
    GROUND_SPEED = 1

# Safety Constants
class SAFETY_LIMITS:
    """Safety constraints for mission planning"""
    MAX_ALTITUDE_M = 120  # FAA recreational limit
    MIN_ALTITUDE_M = 1    # Minimum safe altitude
    MAX_WAYPOINT_DISTANCE_M = 10000  # Maximum distance between waypoints
    MIN_LOITER_RADIUS_M = 5  # Minimum loiter radius
    MAX_LOITER_RADIUS_M = 1000  # Maximum loiter radius
    MAX_SPEED_MS = 25  # Maximum speed in m/s
    MIN_SPEED_MS = 1   # Minimum speed in m/s

# Mission Validation
class VALIDATION_RULES:
    """Mission validation rules and requirements"""
    REQUIRE_TAKEOFF = True
    REQUIRE_LANDING_OR_RTL = True
    MAX_MISSION_ITEMS = 100
    MIN_MISSION_ITEMS = 1
    # Strict enforcement rules
    SINGLE_TAKEOFF_ONLY = True
    SINGLE_RTL_ONLY = True
    TAKEOFF_MUST_BE_FIRST = True
    RTL_MUST_BE_LAST = True

# Export Formats
class EXPORT_FORMAT:
    """Supported mission export formats"""
    JSON = "json"
    QGC = "qgc"  # QGroundControl format
    MAVLINK = "mavlink"

# Display Configuration
class DISPLAY_CONFIG:
    """Display formatting configuration"""
    UNSPECIFIED_MARKER = "unspecified"
    SHOW_ITEM_NUMBERS = True
    UPPERCASE_COMMANDS = True

# Command Emojis for Display
COMMAND_EMOJIS = {
    'takeoff': "🚀",
    'waypoint': "📍", 
    'loiter': "🔄",
    'rtl': "🏠"
}

# Default Values
class DEFAULTS:
    """Default parameter values"""
    TAKEOFF_PITCH_DEG = 15
    WAYPOINT_ACCEPTANCE_RADIUS_M = 0
    WAYPOINT_HOLD_TIME_S = 0
    LOITER_TIME_S = 0  # 0 = unlimited
    YAW_ANGLE_DEG = float('nan')  # Use current yaw
    MISSION_VERSION = 1