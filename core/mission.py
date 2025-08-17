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
    heading: Optional[str] = None  # Text direction like 'north', 'east', etc.
    altitude: Optional[float] = None
    radius: Optional[float] = None
    
    # Unit specifications and reference frame - store EXACTLY what model provided
    altitude_units: Optional[str] = None
    distance_units: Optional[str] = None
    radius_units: Optional[str] = None
    relative_reference_frame: Optional[str] = None
    
    # AI Search parameters
    status: Optional[str] = None
    target: Optional[str] = None
    behavior: Optional[str] = None
    
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
            'relative_reference_frame': self.relative_reference_frame,
            'status': self.status,
            'target': self.target,
            'behavior': self.behavior,
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
        self.mode = mode
    
    def insert_item_at(self, item: MissionItem, position: Optional[int] = None) -> MissionItem:
        """Insert mission item at specific position or append to end"""
        mission = self._get_current_mission_or_raise()
        
        if position is None or position <= 0:
            # Append to end (default behavior)
            item.seq = len(mission.items)
            mission.items.append(item)
        else:
            # Insert at specific position (1-based)
            insert_index = position - 1  # Convert to 0-based index
            
            if insert_index > len(mission.items):
                # If position is beyond current length, append to end
                item.seq = len(mission.items)
                mission.items.append(item)
            else:
                # Insert at specified position
                item.seq = insert_index
                mission.items.insert(insert_index, item)
                
                # Resequence all items after insertion
                for i, mission_item in enumerate(mission.items):
                    mission_item.seq = i
        
        mission.modified_at = datetime.now()
        return item
    
    def add_takeoff(self, lat: float, lon: float, alt: float, 
                   altitude_units: Optional[str] = None, 
                   latitude: Optional[float] = None, longitude: Optional[float] = None, 
                   altitude: Optional[float] = None, mgrs: Optional[str] = None) -> MissionItem:
        """Add takeoff command - always goes at the beginning"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='takeoff',  # Track what type of command this is
            # Store model parameters directly
            altitude=altitude,
            altitude_units=altitude_units,
            latitude=latitude,
            longitude=longitude,
            mgrs=mgrs
        )
        return self.insert_item_at(item, 1)  # Always insert at position 1 (first)
    
    def add_waypoint(self, lat: float, lon: float, alt: float,
                    altitude_units: Optional[str] = None, insert_at: Optional[int] = None, 
                    latitude: Optional[float] = None, longitude: Optional[float] = None, 
                    altitude: Optional[float] = None, mgrs: Optional[str] = None,
                    distance: Optional[float] = None, heading: Optional[str] = None,
                    distance_units: Optional[str] = None, relative_reference_frame: Optional[str] = None) -> MissionItem:
        """Add waypoint command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='waypoint',  # Track what type of command this is
            # Store model parameters directly
            altitude=altitude,
            altitude_units=altitude_units,
            latitude=latitude,
            longitude=longitude,
            mgrs=mgrs,
            distance=distance,
            heading=heading,
            distance_units=distance_units,
            relative_reference_frame=relative_reference_frame
        )
        return self.insert_item_at(item, insert_at)
    
    
    def add_return_to_launch(self, altitude: Optional[float] = None, 
                            altitude_units: Optional[str] = None) -> MissionItem:
        """Add return to launch command - always goes at the end"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='rtl',  # Track what type of command this is
            altitude=altitude,
            altitude_units=altitude_units
        )
        return self.insert_item_at(item, None)  # None = add at end
    
    def add_loiter(self, lat: float, lon: float, alt: float,
                  radius: float, radius_units: Optional[str] = None, insert_at: Optional[int] = None,
                  latitude: Optional[float] = None, longitude: Optional[float] = None, 
                  altitude: Optional[float] = None, altitude_units: Optional[str] = None,
                  mgrs: Optional[str] = None, distance: Optional[float] = None, 
                  heading: Optional[str] = None, distance_units: Optional[str] = None,
                  relative_reference_frame: Optional[str] = None) -> MissionItem:
        """Add loiter command"""
        mission = self._get_current_mission_or_raise()
        
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='loiter',  # Track what type of command this is
            # Store model parameters directly
            radius=radius,
            radius_units=radius_units,
            altitude=altitude,
            altitude_units=altitude_units,
            latitude=latitude,
            longitude=longitude,
            mgrs=mgrs,
            distance=distance,
            heading=heading,
            distance_units=distance_units,
            relative_reference_frame=relative_reference_frame
        )
        return self.insert_item_at(item, insert_at)
    
    def add_survey(self, mode: str, center_lat: float, center_lon: float, 
                  radius: Optional[float] = None, corners: Optional[List[Dict]] = None,
                  altitude: float = 100.0, radius_units: Optional[str] = None, 
                  altitude_units: Optional[str] = None, insert_at: Optional[int] = None,
                  center_latitude: Optional[float] = None, center_longitude: Optional[float] = None,
                  survey_radius: Optional[float] = None, survey_altitude: Optional[float] = None,
                  center_mgrs: Optional[str] = None, center_distance: Optional[float] = None,
                  center_heading: Optional[str] = None, center_distance_units: Optional[str] = None,
                  center_relative_reference_frame: Optional[str] = None) -> MissionItem:
        """Add survey command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='survey',  # Track what type of command this is
            # Store model parameters directly
            radius=survey_radius,
            radius_units=radius_units,
            altitude=survey_altitude,
            altitude_units=altitude_units,
            latitude=center_latitude,
            longitude=center_longitude,
            mgrs=center_mgrs,
            distance=center_distance,
            heading=center_heading,
            distance_units=center_distance_units,
            relative_reference_frame=center_relative_reference_frame
        )
        
        # Store survey-specific data as attributes
        item.survey_mode = mode
        item.corners = corners
        
        return self.insert_item_at(item, insert_at)
    
    def add_ai_search(self, status: Optional[str] = None, target: Optional[str] = None,
                     behavior: Optional[str] = None, insert_at: Optional[int] = None) -> MissionItem:
        """Add AI search command"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='ai_search',  # Track what type of command this is
            status=status,
            target=target,
            behavior=behavior
        )
        return self.insert_item_at(item, insert_at)
    
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
            has_rtl = any(getattr(item, 'command_type', None) == 'rtl' for item in mission.items)
            
            # Check takeoff positioning
            if settings.agent.takeoff_must_be_first and has_takeoff:
                if getattr(mission.items[0], 'command_type', None) != 'takeoff':
                    errors.append("Takeoff command is not the first item - takeoff must be the initial command")

            # Check RTL positioning
            if settings.agent.rtl_must_be_last and has_rtl:
                if getattr(mission.items[-1], 'command_type', None) != 'rtl':
                    errors.append("RTL command is not the last item - RTL must be at the last command")
            
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
    
    def get_mission_state_summary(self) -> str:
        """Get brief summary of current mission state in XML format"""
        mission = self.get_mission()
        summary = f"\n\n<mission_state>\n<total_items>{len(mission.items)}</total_items>"

        if mission and mission.items:
            for i, item in enumerate(mission.items):
                command_type = getattr(item, 'command_type', 'unknown')
                
                summary += f"\n<item_{i+1}>"
                summary += f"\n  <type>{command_type}</type>"
                
                # Add key parameters
                if (hasattr(item, 'altitude') and item.altitude is not None) or (hasattr(item, 'altitude_units') and item.altitude_units is not None):
                    altitude_val = item.altitude if item.altitude is not None else "(altitude)"
                    alt_units = item.altitude_units if item.altitude_units is not None else "(altitude_units)"
                    summary += f"\n  <altitude>{altitude_val} {alt_units}</altitude>"
                
                # Show radius if either radius or radius_units is specified
                if (hasattr(item, 'radius') and item.radius is not None) or (hasattr(item, 'radius_units') and item.radius_units is not None):
                    radius_val = item.radius if item.radius is not None else "(radius)"
                    radius_units = item.radius_units if item.radius_units is not None else "(radius_units)"
                    summary += f"\n  <radius>{radius_val} {radius_units}</radius>"
                
                # Add position info if available
                if (hasattr(item, 'latitude') and item.latitude is not None) or (hasattr(item, 'longitude') and item.longitude is not None):
                    lat_val = f"{item.latitude:.6f}" if item.latitude is not None else "(latitude)"
                    lon_val = f"{item.longitude:.6f}" if item.longitude is not None else "(longitude)"
                    summary += f"\n  <position>lat/lon ({lat_val}, {lon_val})</position>"
                elif hasattr(item, 'mgrs') and item.mgrs is not None:
                    summary += f"\n  <position>MGRS {item.mgrs}</position>"
                elif (hasattr(item, 'distance') and item.distance is not None) or (hasattr(item, 'heading') and item.heading is not None) or (hasattr(item, 'distance_units') and item.distance_units is not None) or (hasattr(item, 'relative_reference_frame') and item.relative_reference_frame is not None):
                    distance = item.distance if item.distance is not None else "(distance)"
                    dist_units = item.distance_units if item.distance_units is not None else "(distance_units)"
                    heading = item.heading if item.heading is not None else "(heading)"
                    ref_frame = item.relative_reference_frame if item.relative_reference_frame is not None else "(relative_reference_frame)"
                    summary += f"\n  <position>{distance} {dist_units} {heading} from {ref_frame}</position>"
                
                # Show AI search parameters if any are specified
                if command_type == 'ai_search' and ((hasattr(item, 'status') and item.status is not None) or (hasattr(item, 'target') and item.target is not None) or (hasattr(item, 'behavior') and item.behavior is not None)):
                    status = item.status if item.status is not None else "(status)"
                    target = item.target if item.target is not None else "(target)"
                    behavior = item.behavior if item.behavior is not None else "(behavior)"
                    summary += f"\n  <ai_search>status={status}, target={target}, behavior={behavior}</ai_search>"
            
                summary += f"\n</item_{i+1}>"
        
        summary += "\n</mission_state>"
        return summary
    
