"""
PX4 Mission State Management
Handles mission creation, validation, and state tracking
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from config import get_settings

@dataclass
class MissionItem:
    """Represents a single mission item"""
    seq: int
    frame: int = 0
    command: int = 0
    current: int = 0
    
    # Command type for tracking what each mission item is
    command_type: Optional[str] = None

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
            'command_type': self.command_type,
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
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }

class MissionManager:
    """Manages single current mission and validation"""
    
    def __init__(self, mode: str = "mission"):
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
    
    def set_mode(self, mode: str):
        """Set the validation mode"""
        self.mode = mode # "mission" or "command"
    
    def add_takeoff(self, lat: float, lon: float, alt: float, 
                   altitude_units: Optional[str] = None, **original_params) -> MissionItem:
        """Add takeoff command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            command_type='takeoff',  # Track what type of command this is
            # Store ONLY what model can provide
            altitude=original_params.get('original_altitude'),
            altitude_units=altitude_units,
            latitude=original_params.get('original_latitude'),
            longitude=original_params.get('original_longitude')
        )
        return mission.add_item(item)
    
    def add_waypoint(self, lat: float, lon: float, alt: float,
                    altitude_units: Optional[str] = None, **original_params) -> MissionItem:
        """Add waypoint command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            command_type='waypoint',  # Track what type of command this is
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
            command_type='rtl'  # Track what type of command this is
        )
        return mission.add_item(item)
    
    def add_loiter(self, lat: float, lon: float, alt: float,
                  radius: float, radius_units: Optional[str] = None, **original_params) -> MissionItem:
        """Add loiter command"""
        mission = self._get_current_mission_or_raise()
        
        
        item = MissionItem(
            seq=0,  # Will be set by add_item
            command_type='loiter',  # Track what type of command this is
            # Store ONLY what model can provide
            radius=original_params.get('original_radius'),
            radius_units=radius_units,
            altitude=original_params.get('original_altitude'),
            altitude_units=original_params.get('altitude_units'),
            latitude=original_params.get('original_latitude'),
            longitude=original_params.get('original_longitude')
        )
        return mission.add_item(item)
    
    def validate_mission(self) -> Tuple[bool, List[str]]:
        """Validate mission for safety and completeness"""
        mission = self._get_current_mission_or_raise()
        errors = []
        
        if len(mission.items) == 0:
            errors.append("Mission has no items")
            return False, errors
        
        settings = get_settings()
        if len(mission.items) > settings.agent.max_mission_items:
            errors.append(f"Mission exceeds maximum {settings.agent.max_mission_items} items")
        
        # Different validation rules based on mode
        if self.mode == "mission":
            # Strict validation for mission mode (building complete missions)
            has_takeoff = any(getattr(item, 'command_type', None) == 'takeoff' for item in mission.items)
            if settings.agent.require_takeoff and not has_takeoff:
                errors.append("Mission should start with a takeoff command")
            
            # Check takeoff positioning
            if settings.agent.takeoff_must_be_first and has_takeoff:
                if getattr(mission.items[0], 'command_type', None) != 'takeoff':
                    errors.append("Takeoff command is not the first item - takeoff must be the initial command")
            
            # Check for multiple takeoffs/RTLs
            takeoff_count = sum(1 for item in mission.items if getattr(item, 'command_type', None) == 'takeoff')
            rtl_count = sum(1 for item in mission.items if getattr(item, 'command_type', None) == 'rtl')
            
            if settings.agent.single_takeoff_only and takeoff_count > 1:
                errors.append(f"Mission has {takeoff_count} takeoff commands - only one is allowed")
            
            if settings.agent.single_rtl_only and rtl_count > 1:
                errors.append(f"Mission has {rtl_count} RTL commands - only one is allowed")
        
        elif self.mode == "command":            
            # Ensure the "mission" length is 1 or less
            mission_item_count = len(mission.items)
            if mission_item_count > 1:
                errors.append(f"Mission has {mission_item_count} commands - only one is allowed")
        
        # Validate individual items (applies to both modes)
        for i, item in enumerate(mission.items):
            item_errors = self._validate_mission_item(item, i)
            errors.extend(item_errors)
        
        return len(errors) == 0, errors
    
    def _get_current_mission_or_raise(self) -> Mission:
        """Get current mission or raise error if not found"""
        if not self.current_mission:
            raise ValueError("No current mission available")
        return self.current_mission
    
    def _validate_mission_item(self, item: MissionItem, index: int) -> List[str]:
        """Validate individual mission item"""
        errors = []
        
        # Check navigation commands for altitude limits
        nav_command_types = ['waypoint', 'takeoff', 'loiter', 'rtl']
        
        command_type = getattr(item, 'command_type', None)
        if command_type in nav_command_types:
            # Check altitude from the field where it's actually stored
            altitude_value = getattr(item, 'altitude', None)
            if altitude_value is not None and altitude_value <= 0:
                errors.append(f"Item {index}: Altitude must be positive")
        
        
        return errors
    
