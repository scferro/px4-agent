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
    latitude: Optional[float] = Field(None, description="GPS latitude in decimal degrees. Use when user provides exact coordinates. Do NOT use for relative directions - use distance/heading instead. Use ONLY when latitude is specified.")
    longitude: Optional[float] = Field(None, description="GPS longitude in decimal degrees. Use when user provides exact coordinates. Do NOT use for relative directions - use distance/heading instead. Use ONLY when longitude is specified.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate string. Use when user provides MGRS grid coordinates. Use ONLY when MGRS coordinate is specified.")
    
    # Relative positioning - use for directional commands like "2 miles north"
    distance: Optional[float] = Field(None, description="Distance value for relative positioning. Always use with heading parameter.")
    heading: Optional[str] = Field(None, description="Compass direction: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Always use with distance parameter.")
    distance_units: Optional[str] = Field(None, description="Units for distance: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km', 'nautical_miles'/'nm'.")
    relative_reference_frame: Optional[str] = Field(None, description="Reference point for distance: 'origin' (takeoff), 'current', 'last_waypoint'. If unclear, bias toward 'last_waypoint'.")
    
    # Altitude specification
    altitude: Optional[float] = Field(None, description="Flight altitude for this waypoint. Specify only if user mentions altitude.")
    altitude_units: Optional[str] = Field(None, description="Units for altitude: 'meters'/'m' or 'feet'/'ft'.")
        
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert waypoint in mission. Set to specific position number or omit to add at end.")


class AddWaypointTool(PX4ToolBase):
    name: str = "add_waypoint"
    description: str = "Add waypoint for drone navigation to specific location. Use when user wants drone to fly to a location using exact GPS coordinates or relative directions. Creates flight path point where drone flies to location, flies THROUGH it, then continues to the next mission item. Specify Lat/Long OR MGRS OR distance/heading/reference. Do not mix location systems."
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
                altitude_units=altitude_units,
                insert_at=insert_at,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                mgrs=mgrs,
                distance=distance,
                heading=heading,
                distance_units=distance_units,
                relative_reference_frame=relative_reference_frame
            )
            
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