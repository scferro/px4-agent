"""
Add Waypoint Tool - Navigate drone to specific location
"""

from typing import Optional, Union
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, field_validator

from .tools import PX4ToolBase
from config.settings import get_agent_settings
from core.parsing import parse_altitude, parse_distance

# Load agent settings for Field descriptions
_agent_settings = get_agent_settings()


class WaypointInput(BaseModel):
    """Navigate drone to specific location using GPS coordinates OR relative positioning"""
    
    # GPS coordinates - use when user provides exact lat/lon numbers
    latitude: Optional[float] = Field(None, description="GPS latitude in decimal degrees. Use when user provides exact coordinates. Use ONLY when latitude is specified.")
    longitude: Optional[float] = Field(None, description="GPS longitude in decimal degrees. Use when user provides exact coordinates. Use ONLY when longitude is specified.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate string. Use ONLY when MGRS coordinate is specified.")
    
    # Relative positioning - use for directional commands like "2 miles north"
    distance: Optional[Union[float, str, tuple]] = Field(None, description="Distance value for relative positioning with optional units (e.g., '2 miles', '1000 meters', '500 ft'). Always use with heading parameter. Can set to 0.0 to fly over the reference frame.")
    heading: Optional[str] = Field(None, description="Compass direction: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Always use with distance parameter.")
    relative_reference_frame: Optional[str] = Field(None, description="Reference point for distance: 'origin' (takeoff), 'last_waypoint'. You MUST pick one, make an educated guess if using relative positioning. Use 'origin' when user references 'start', 'takeoff', 'here', etc. Otherwise assume last_waypoint.")
    
    # Altitude specification
    altitude: Optional[Union[float, str, tuple]] = Field(None, description=f"Flight altitude for this waypoint with optional units (e.g., '150 feet', '50 meters'). Specify only if user mentions altitude. Default = {_agent_settings['waypoint_default_altitude']} {_agent_settings['waypoint_altitude_units']}")
    
    @field_validator('distance', mode='before')
    @classmethod
    def parse_distance_field(cls, v):
        if v is None:
            return None
        parsed_value, units = parse_distance(v)
        if parsed_value is None:
            return v  # Let Pydantic handle validation error
        return (parsed_value, units)
    
    @field_validator('altitude', mode='before')
    @classmethod
    def parse_altitude_field(cls, v):
        if v is None:
            return None
        parsed_value, units = parse_altitude(v)
        if parsed_value is None:
            return v  # Let Pydantic handle validation error
        return (parsed_value, units)
        
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert waypoint in mission. Set to specific position number or omit to add at end.")
    
    # Search parameters
    search_target: Optional[str] = Field(None, description="Target description for AI to search for during survey (e.g., 'vehicles', 'people', 'buildings'). Do not use if user does not specify.")
    detection_behavior: Optional[str] = Field(None, description="Detection behavior: 'tag_and_continue' (mark targets and continue mission) or 'detect_and_monitor' (abort mission and circle detected target). Use with search_target")


class AddWaypointTool(PX4ToolBase):
    name: str = "add_waypoint"
    description: str = "Add waypoint for drone navigation to specific location. Use when user wants drone to fly to a location using exact GPS coordinates or relative directions. Creates flight path point where drone flies to location, flies THROUGH it, then continues to the next mission item. The drone can perform AI searches with its camera while passing through a waypoint. Specify Lat/Long OR MGRS OR distance/heading/reference. Do not mix location systems."
    args_schema: type = WaypointInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None, 
             distance: Optional[Union[float, tuple]] = None, heading: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[Union[float, tuple]] = None,
             insert_at: Optional[int] = None, search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> str:
        # Create response
        response = ""

        # Populate response
        try:
            # Parse measurement tuples from validators
            if isinstance(distance, tuple):
                distance_value, distance_units = distance
            else:
                distance_value, distance_units = distance, 'meters'
            
            if isinstance(altitude, tuple):
                altitude_value, altitude_units = altitude
            else:
                altitude_value, altitude_units = altitude, 'meters'
            
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Build coordinate description following wx-agent pattern
            coord_desc = self._build_coordinate_description(latitude, longitude, mgrs, distance_value, heading, distance_units, relative_reference_frame)
            
            # For mission manager, use lat/lon if provided, otherwise use defaults
            actual_lat = latitude if latitude is not None else 40.7128
            actual_lon = longitude if longitude is not None else -74.0060
            actual_alt = altitude_value if altitude_value is not None else 0.0
            
            # Use mission manager method
            item = self.mission_manager.add_waypoint(
                actual_lat, actual_lon, actual_alt, 
                altitude_units=altitude_units,
                insert_at=insert_at,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude_value,
                mgrs=mgrs,
                distance=distance_value,
                heading=heading,
                distance_units=distance_units,
                relative_reference_frame=relative_reference_frame,
                search_target=search_target,
                detection_behavior=detection_behavior
            )
            
            # Validate mission after adding waypoint
            is_valid, validation_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {validation_msg}" + self._get_mission_state_summary()
            else:
                # Build response message with preserved units
                altitude_msg = f"{altitude_value} {altitude_units}" if altitude_value is not None else "not specified"
                response = f"Waypoint added to mission: {coord_desc}, Alt={altitude_msg} (Item {item.seq + 1})"
                
                # Include auto-fix notifications if any
                if validation_msg:
                    response += f". {validation_msg}"
                
                response += self._get_mission_state_summary()
            
        except Exception as e:
            response = f"Error: {str(e)}"

        return response