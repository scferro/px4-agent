"""
Add Waypoint Tool - Navigate drone to specific location
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class WaypointInput(BaseModel):
    """Navigate drone to specific location using GPS coordinates OR relative positioning"""
    
    # GPS coordinates - use when user provides exact lat/lon numbers
    latitude: Optional[float] = Field(None, description="GPS latitude in decimal degrees. Use ONLY when user provides exact coordinates like 'fly to 37.7749, -122.4194' or 'waypoint at 40.7128, -74.0060'. Do NOT use for relative directions like 'north', 'east', 'west', 'south' - use distance/heading instead.")
    longitude: Optional[float] = Field(None, description="GPS longitude in decimal degrees. Use ONLY when user provides exact coordinates like 'fly to 37.7749, -122.4194' or 'waypoint at 40.7128, -74.0060'. Do NOT use for relative directions like 'north', 'east', 'west', 'south' - use distance/heading instead.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate string like '11SMT1234567890'. Use only when user explicitly provides MGRS grid coordinates.")
    
    # Relative positioning - use for directional commands like "2 miles north"
    distance: Optional[float] = Field(None, description="Distance value for relative positioning. Extract the number from phrases like '2 miles north' (distance=2), '500 feet east' (distance=500), '1.5 kilometers south' (distance=1.5). Always use with heading parameter.")
    heading: Optional[str] = Field(None, description="Compass direction as text. Use the exact words from user input: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Extract directly from phrases like '2 miles north' (heading='north'), '500 feet southeast' (heading='southeast'). Always use with distance parameter.")
    distance_units: Optional[str] = Field(None, description="Units for the distance parameter. Extract from user input: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km', 'nautical_miles'/'nm'. Example: '500 feet east' uses 'feet'.")
    relative_reference_frame: Optional[str] = Field(None, description="Where to measure distance from. Use 'origin' (takeoff point) unless user specifies: 'from current position' (use 'current'), 'from last waypoint' (use 'last_waypoint'), or 'from here' (use 'current').")
    
    # Altitude specification
    altitude: Optional[float] = Field(None, description="Flight altitude for this waypoint. Only specify if user mentions altitude like 'fly at 200 feet' or 'waypoint at 100 meters altitude'. Leave None if not specified.")
    altitude_units: Optional[str] = Field(None, description="Units for altitude. Extract from user input: 'meters'/'m' or 'feet'/'ft'. Example: 'fly at 200 feet' uses 'feet'.")
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert this waypoint in the mission (1=first item, 2=second item, etc.). Extract from phrases like 'insert waypoint at position 3', 'add as first item', 'make this the second command'. Leave None to add at the end of the mission.")


class AddWaypointTool(PX4ToolBase):
    name: str = "add_waypoint"
    description: str = "Add waypoint for drone navigation to specific location. Use when user wants drone to fly to a location using either exact GPS coordinates (like '37.7749, -122.4194') or relative directions (like '2 miles north', '500 feet east'). Creates flight path point where drone flies to location and continues to next mission item."
    args_schema: type = WaypointInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None, 
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None,
             insert_at: Optional[int] = None) -> str:
        # Create response
        response = ""

        # Populate response
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Build coordinate description following wx-agent pattern
            coord_desc = self._build_coordinate_description(latitude, longitude, mgrs, distance, heading, distance_units, relative_reference_frame)
            
            # For mission manager, use lat/lon if provided, otherwise use defaults
            actual_lat = latitude if latitude is not None else 40.7128
            actual_lon = longitude if longitude is not None else -74.0060
            actual_alt = altitude if altitude is not None else 0.0
            
            # Use mission manager method
            item = self.mission_manager.add_waypoint(
                actual_lat, actual_lon, actual_alt, 
                altitude_units=altitude_units,  # Store EXACTLY what model provided
                insert_at=insert_at,
                original_altitude=altitude,
                original_latitude=latitude,
                original_longitude=longitude
            )
            
            # Store original heading as text for display
            if heading is not None:
                item.heading = heading
                item.distance = distance
                item.distance_units = distance_units  # Store EXACTLY what model provided
                item.relative_reference_frame = relative_reference_frame  # Store EXACTLY what model provided
            
            # Validate mission after adding waypoint
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
            else:
                # Build response message with preserved units
                altitude_msg = f"{altitude} {altitude_units}" if altitude is not None else "not specified"
                response = f"Waypoint added to mission: {coord_desc}, Alt={altitude_msg} (Item {item.seq + 1})"
                response += self._get_mission_state_summary()
            
        except Exception as e:
            response = f"Error: {str(e)}"

        return response