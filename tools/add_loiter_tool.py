"""
Add Loiter Tool - Create circular orbit/loiter pattern
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase
from config.settings import get_agent_settings

# Load agent settings for Field descriptions
_agent_settings = get_agent_settings()

class LoiterInput(BaseModel):
    """Create circular orbit/loiter pattern at specified location with defined radius"""

    # GPS coordinates for exact orbit center location
    latitude: Optional[float] = Field(None, description="GPS latitude for orbit center. Use ONLY when latitude is specified by the user.")
    longitude: Optional[float] = Field(None, description="GPS longitude for orbit center. Use ONLY when longitude is specified by the user.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate for orbit center. Use ONLY when user provides MGRS coordinates.")
    
    # Relative positioning for orbit center - use for "orbit 2 miles north of here"
    distance: Optional[float] = Field(None, description="Distance to orbit center from reference point. Use with heading. Can set to 0.0 to oribt AT the reference frame.")
    heading: Optional[str] = Field(None, description="Direction to orbit center: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Use with distance.")
    distance_units: Optional[str] = Field(None, description="Units for distance: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    relative_reference_frame: Optional[str] = Field(None, description="Reference point for distance: 'origin' (takeoff), 'last_waypoint'. Make an educated guess if using relative positioning. Typically 'last_waypoint' unless user specifies 'origin'.")
    
    # Orbit radius - critical parameter often specified by user
    radius: Optional[float] = Field(None, description=f"Radius of the circular orbit. Put units in radius_units. Default = {_agent_settings['loiter_default_radius']} {_agent_settings['loiter_radius_units']}")
    radius_units: Optional[str] = Field(None, description="Units for orbit radius: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    
    # Optional orbit altitude
    altitude: Optional[float] = Field(None, description=f"Altitude for the orbit pattern. Specify only if user mentions height. Put units in altitude_units. Default = {_agent_settings['loiter_default_altitude']} {_agent_settings['loiter_altitude_units']}")
    altitude_units: Optional[str] = Field(None, description="Units for orbit altitude: 'meters'/'m' or 'feet'/'ft'.")
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert loiter in mission. Set to specific position number or omit to add at end.")
    
    # Search parameters
    search_target: Optional[str] = Field(None, description="Target description for AI to search for during survey (e.g., 'vehicles', 'people', 'buildings'). Do not use if user does not specify.")
    detection_behavior: Optional[str] = Field(None, description="Detection behavior: 'tag_and_continue' (mark targets and continue mission) or 'detect_and_monitor' (abort mission and circle detected target). Use with search_target")
    

class AddLoiterTool(PX4ToolBase):
    name: str = "add_loiter"
    description: str = "Add circular orbit/loiter pattern at specified location. Use when user wants drone to fly in circles, orbit, or loiter. The drone can perform AI searches with its camera while loitering. Use for commands like 'orbit', 'circle', 'loiter', or when radius is mentioned like 'circle 2 miles north with 200m radius'. Specify Lat/Long OR MGRS OR distance/heading/reference. Do not mix location systems."
    args_schema: type = LoiterInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)

    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None, 
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None, 
             radius: Optional[float] = None, radius_units: Optional[str] = None, insert_at: Optional[int] = None,
             search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Build coordinate description following wx-agent pattern
            coord_desc = self._build_coordinate_description(latitude, longitude, mgrs, distance, heading, distance_units, relative_reference_frame)
            
            # For mission manager, use lat/lon if provided, otherwise use 0 (no guessing)
            actual_lat = latitude if latitude is not None else 0.0
            actual_lon = longitude if longitude is not None else 0.0
            actual_alt = altitude if altitude is not None else 0.0
            actual_radius = radius if radius is not None else 50.0  # Default radius
            
            item = self.mission_manager.add_loiter(
                actual_lat, actual_lon, actual_alt, actual_radius,
                radius_units=radius_units,
                insert_at=insert_at,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                altitude_units=altitude_units,
                mgrs=mgrs,
                distance=distance,
                heading=heading,
                distance_units=distance_units,
                relative_reference_frame=relative_reference_frame,
                search_target=search_target,
                detection_behavior=detection_behavior
            )
            
            # Validate mission after adding loiter
            is_valid, validation_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {validation_msg}" + self._get_mission_state_summary()
            
            # Build response with preserved units
            altitude_msg = f"{altitude} {altitude_units}" if altitude is not None else "not specified"
            radius_msg = f"{radius} {radius_units}" if radius is not None else "not specified"
            
            response = f"Loiter command added to mission: {coord_desc}, Alt={altitude_msg}, Radius={radius_msg}, (Item {item.seq + 1})"
            
            # Include auto-fix notifications if any
            if validation_msg:
                response += f". {validation_msg}"
            
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"