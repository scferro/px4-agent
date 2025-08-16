"""
PX4 Mission State Management
Handles mission creation, validation, and state tracking
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import math

from .constants import MAV_CMD, MAV_FRAME, SAFETY_LIMITS, VALIDATION_RULES, DEFAULTS

@dataclass
class MissionItem:
    """Represents a single mission item"""
    seq: int
    frame: int
    command: int
    current: int = 0
    autocontinue: int = 1
    param1: float = 0.0
    param2: float = 0.0
    param3: float = 0.0
    param4: float = 0.0
    x: float = 0.0  # Final Latitude or local X
    y: float = 0.0  # Final Longitude or local Y
    z: float = 0.0  # Final Altitude or local Z

    # Raw input values
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    mgrs: Optional[str] = None
    distance: Optional[float] = None
    heading: Optional[float] = None
    altitude: Optional[float] = None
    radius: Optional[float] = None
    
    # Unit specifications - store EXACTLY what model provided
    altitude_units: Optional[str] = None
    distance_units: Optional[str] = None
    radius_units: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'seq': self.seq,
            'frame': self.frame,
            'command': self.command,
            'current': self.current,
            'autocontinue': self.autocontinue,
            'param1': self.param1,
            'param2': self.param2,
            'param3': self.param3,
            'param4': self.param4,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'mgrs': self.mgrs,
            'distance': self.distance,
            'heading': self.heading,
            'altitude': self.altitude,
            'radius': self.radius,
            'altitude_units': self.altitude_units,
            'distance_units': self.distance_units,
            'radius_units': self.radius_units,
        }

@dataclass
class Mission:
    """Represents a complete mission"""
    version: int = DEFAULTS.MISSION_VERSION
    items: List[MissionItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def add_item(self, item: MissionItem) -> MissionItem:
        """Add mission item to end of mission"""
        item.seq = len(self.items)
        self.items.append(item)
        self.modified_at = datetime.now()
        return item
    
    def clear_items(self):
        """Remove all mission items"""
        self.items.clear()
        self.modified_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'version': self.version,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }

class MissionManager:
    """Manages single current mission and validation"""
    
    def __init__(self):
        self.current_mission: Optional[Mission] = None
    
    def create_mission(self) -> Mission:
        """Create a new current mission"""
        mission = Mission()
        self.current_mission = mission
        return mission
    
    def get_mission(self) -> Optional[Mission]:
        """Get current mission"""
        return self.current_mission
    
    def clear_mission(self) -> bool:
        """Clear current mission"""
        if self.current_mission:
            self.current_mission = None
            return True
        return False
    
    def has_mission(self) -> bool:
        """Check if current mission exists"""
        return self.current_mission is not None
    
    def add_takeoff(self, lat: float, lon: float, alt: float, 
                   altitude_units: Optional[str] = None, **original_params) -> MissionItem:
        """Add takeoff command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            frame=MAV_FRAME.GLOBAL_RELATIVE_ALT,
            command=MAV_CMD.NAV_TAKEOFF,
            # NO param1, param4, x, y, z - model can't control these
            # Store ONLY what model can provide
            altitude=original_params.get('original_altitude'),
            altitude_units=altitude_units,
            latitude=original_params.get('original_latitude'),
            longitude=original_params.get('original_longitude')
        )
        return mission.add_item(item)
    
    def add_waypoint(self, lat: float, lon: float, alt: float,
                    acceptance_radius: float = DEFAULTS.WAYPOINT_ACCEPTANCE_RADIUS_M,
                    hold_time: float = DEFAULTS.WAYPOINT_HOLD_TIME_S,
                    yaw_angle: float = DEFAULTS.YAW_ANGLE_DEG,
                    altitude_units: Optional[str] = None, **original_params) -> MissionItem:
        """Add waypoint command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            frame=MAV_FRAME.GLOBAL_RELATIVE_ALT,
            command=MAV_CMD.NAV_WAYPOINT,
            # NO param1, param2, param3, param4, x, y, z - model can't control these
            # Store ONLY what model can provide
            altitude=original_params.get('original_altitude'),
            altitude_units=altitude_units,
            latitude=original_params.get('original_latitude'),
            longitude=original_params.get('original_longitude')
        )
        return mission.add_item(item)
    
    
    def add_return_to_launch(self) -> MissionItem:
        """Add return to launch command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            frame=MAV_FRAME.GLOBAL,
            command=MAV_CMD.NAV_RETURN_TO_LAUNCH
            # NO other parameters - RTL has no model-controllable parameters
        )
        return mission.add_item(item)
    
    def add_loiter(self, lat: float, lon: float, alt: float,
                  radius: float, time: float = DEFAULTS.LOITER_TIME_S, 
                  radius_units: Optional[str] = None, **original_params) -> MissionItem:
        """Add loiter command"""
        mission = self._get_current_mission_or_raise()
        
        command = MAV_CMD.NAV_LOITER_TIME if time > 0 else MAV_CMD.NAV_LOITER_UNLIM
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            frame=MAV_FRAME.GLOBAL_RELATIVE_ALT,
            command=command,
            # NO param1, param3, param4, x, y, z - model can't control these
            # Store ONLY what model can provide
            radius=original_params.get('original_radius'),
            radius_units=radius_units,
            altitude=original_params.get('original_altitude'),
            altitude_units=original_params.get('altitude_units'),
            latitude=original_params.get('original_latitude'),
            longitude=original_params.get('original_longitude')
        )
        return mission.add_item(item)
    
    def set_speed(self, speed: float, speed_type: int = 0) -> MissionItem:
        """Add speed change command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=len(mission.items),
            frame=MAV_FRAME.GLOBAL,
            command=MAV_CMD.DO_CHANGE_SPEED,
            param1=speed_type,  # 0=Airspeed, 1=Ground Speed
            param2=speed,
            param3=-1  # Use default throttle
        )
        return mission.add_item(item)
    
    def validate_mission(self) -> Tuple[bool, List[str]]:
        """Validate mission for safety and completeness"""
        mission = self._get_current_mission_or_raise()
        errors = []
        
        if len(mission.items) == 0:
            errors.append("Mission has no items")
            return False, errors
        
        if len(mission.items) > VALIDATION_RULES.MAX_MISSION_ITEMS:
            errors.append(f"Mission exceeds maximum {VALIDATION_RULES.MAX_MISSION_ITEMS} items")
        
        # Check for takeoff
        has_takeoff = any(item.command == MAV_CMD.NAV_TAKEOFF for item in mission.items)
        if VALIDATION_RULES.REQUIRE_TAKEOFF and not has_takeoff:
            errors.append("Mission should start with a takeoff command")
        
        # Check for RTL
        has_rtl = any(item.command == MAV_CMD.NAV_RETURN_TO_LAUNCH for item in mission.items)
        if VALIDATION_RULES.REQUIRE_LANDING_OR_RTL and not has_rtl:
            errors.append("Mission should end with return-to-launch")
        
        # Validate individual items
        for i, item in enumerate(mission.items):
            item_errors = self._validate_mission_item(item, i)
            errors.extend(item_errors)
        
        return len(errors) == 0, errors
    
    def export_mission(self, format: str = 'json') -> str:
        """Export mission in specified format"""
        mission = self._get_current_mission_or_raise()
        
        if format == 'qgc':
            return self._export_qgc_format(mission)
        else:
            return json.dumps(mission.to_dict(), indent=2)
    
    def _get_current_mission_or_raise(self) -> Mission:
        """Get current mission or raise error if not found"""
        if not self.current_mission:
            raise ValueError("No current mission available")
        return self.current_mission
    
    def _validate_mission_item(self, item: MissionItem, index: int) -> List[str]:
        """Validate individual mission item"""
        errors = []
        
        # Check navigation commands for altitude limits
        nav_commands = [MAV_CMD.NAV_WAYPOINT, MAV_CMD.NAV_TAKEOFF, 
                       MAV_CMD.NAV_LOITER_TIME, MAV_CMD.NAV_LOITER_UNLIM]
        
        if item.command in nav_commands:
            if item.z <= 0:
                errors.append(f"Item {index}: Altitude must be positive")
            elif item.z > SAFETY_LIMITS.MAX_ALTITUDE_M:
                errors.append(f"Item {index}: Altitude {item.z}m exceeds limit of {SAFETY_LIMITS.MAX_ALTITUDE_M}m")
            elif item.z < SAFETY_LIMITS.MIN_ALTITUDE_M:
                errors.append(f"Item {index}: Altitude {item.z}m below minimum of {SAFETY_LIMITS.MIN_ALTITUDE_M}m")
        
        # Check loiter radius
        if item.command in [MAV_CMD.NAV_LOITER_TIME, MAV_CMD.NAV_LOITER_UNLIM]:
            radius = item.param3
            if radius < SAFETY_LIMITS.MIN_LOITER_RADIUS_M:
                errors.append(f"Item {index}: Loiter radius {radius}m too small")
            elif radius > SAFETY_LIMITS.MAX_LOITER_RADIUS_M:
                errors.append(f"Item {index}: Loiter radius {radius}m too large")
        
        # Check speed commands
        if item.command == MAV_CMD.DO_CHANGE_SPEED:
            speed = item.param2
            if speed < SAFETY_LIMITS.MIN_SPEED_MS:
                errors.append(f"Item {index}: Speed {speed}m/s too low")
            elif speed > SAFETY_LIMITS.MAX_SPEED_MS:
                errors.append(f"Item {index}: Speed {speed}m/s too high")
        
        return errors
    
    def _export_qgc_format(self, mission: Mission) -> str:
        """Export mission in QGroundControl format"""
        qgc_mission = {
            "fileType": "Plan",
            "geoFence": {"circles": [], "polygons": [], "version": 2},
            "groundStation": "QGroundControl",
            "mission": {
                "cruiseSpeed": 15,
                "firmwareType": 12,  # PX4 Pro
                "hoverSpeed": 5,
                "items": [
                    {
                        "AMSLAltAboveTerrain": None,
                        "Altitude": item.z,
                        "AltitudeMode": 1,
                        "autoContinue": item.autocontinue == 1,
                        "command": item.command,
                        "doJumpId": item.seq + 1,
                        "frame": item.frame,
                        "params": [item.param1, item.param2, item.param3, item.param4, item.x, item.y, item.z],
                        "type": "SimpleItem"
                    }
                    for item in mission.items
                ],
                "plannedHomePosition": [
                    mission.items[0].x, mission.items[0].y, mission.items[0].z
                ] if mission.items else [0, 0, 0],
                "vehicleType": 2,  # Multi-Rotor
                "version": 2
            },
            "rallyPoints": {"points": [], "version": 2},
            "version": 1
        }
        return json.dumps(qgc_mission, indent=2)