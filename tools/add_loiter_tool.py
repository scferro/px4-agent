"""
Add Loiter Tool - Create circular orbit/loiter pattern
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class LoiterInput(BaseModel):
    """Create circular orbit/loiter pattern at specified location with defined radius"""
    
    # GPS coordinates for exact orbit center location
    latitude: Optional[float] = Field(None, description="GPS latitude for orbit center in decimal degrees. Use when user provides exact coordinates for orbit location like 'orbit at 37.7749, -122.4194'. Leave None if using relative positioning or orbiting at current location.")
    longitude: Optional[float] = Field(None, description="GPS longitude for orbit center in decimal degrees. Use when user provides exact coordinates for orbit location like 'orbit at 37.7749, -122.4194'. Leave None if using relative positioning or orbiting at current location.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate for orbit center. Use only when user provides MGRS grid coordinates for orbit location.")
    
    # Relative positioning for orbit center - use for "orbit 2 miles north of here"
    distance: Optional[float] = Field(None, description="Distance from reference point to orbit center. Extract number from phrases like 'orbit 2 miles north' (distance=2), 'circle 500 feet east of takeoff' (distance=500), 'loiter 1 km south of current position' (distance=1). Use with heading.")
    heading: Optional[str] = Field(None, description="Direction from reference point to orbit center as text. Use the exact words from user input: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Extract from phrases like 'orbit 2 miles north' (heading='north'), 'circle 500 feet southeast' (heading='southeast'). Use with distance.")
    distance_units: Optional[str] = Field(None, description="Units for distance to orbit center. Extract from user input: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'. Example: 'orbit 2 miles north' uses 'miles'.")
    relative_reference_frame: Optional[str] = Field(None, description="Reference point for measuring distance to orbit center. Use 'origin' (takeoff) unless user specifies: 'from current position'/'from here' (use 'current'), 'from last waypoint' (use 'last_waypoint').")
    
    # Orbit radius - critical parameter often specified by user
    radius: Optional[float] = Field(None, description="Radius of the circular orbit pattern. Extract from phrases like 'with 400 foot radius' (radius=400), 'circle with 50m radius' (radius=50), '200 meter orbit' (radius=200). This determines the size of the circle the drone flies.")
    radius_units: Optional[str] = Field(None, description="Units for orbit radius. Extract from user input: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'. Example: '400 foot radius' uses 'feet'.")
    
    # Optional orbit altitude
    altitude: Optional[float] = Field(None, description="Altitude for the orbit pattern. Only specify if user mentions orbit height like 'orbit at 150 feet altitude'. Leave None if not specified.")
    altitude_units: Optional[str] = Field(None, description="Units for orbit altitude: 'meters'/'m' or 'feet'/'ft'. Example: 'orbit at 150 feet' uses 'feet'.")
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert this loiter in the mission (1=first item, 2=second item, etc.). Use when you want to add the loiter NOT at the end of the mission. Extract from phrases like 'insert orbit at position 2', 'add loiter as first item', 'make this the third command'. Set to 0 or omit to add at the end of the mission.")


class AddLoiterTool(PX4ToolBase):
    name: str = "add_loiter"
    description: str = "Add circular orbit/loiter pattern at specified location. Use when user wants drone to fly in circles, orbit, or loiter. Requires radius specification. Use for commands like 'orbit', 'circle', 'loiter', or when radius is mentioned like 'orbit with 400 foot radius', 'circle 2 miles north with 200m radius'. Creates continuous circular flight pattern."
    args_schema: type = LoiterInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)

    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None, 
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None, 
             radius: Optional[float] = None, radius_units: Optional[str] = None, insert_at: Optional[int] = None) -> str:
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
                radius_units=radius_units,  # Store EXACTLY what model provided
                insert_at=insert_at,
                original_radius=radius,
                original_altitude=altitude,
                altitude_units=altitude_units,  # Store EXACTLY what model provided
                original_latitude=latitude,
                original_longitude=longitude
            )
            
            # Store original heading as text for display
            if heading is not None:
                item.heading = heading
                item.distance = distance
                item.distance_units = distance_units  # Store EXACTLY what model provided
                item.relative_reference_frame = relative_reference_frame  # Store EXACTLY what model provided
            
            # Validate mission after adding loiter
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
            
            # Build response with preserved units
            altitude_msg = f"{altitude} {altitude_units}" if altitude is not None else "not specified"
            radius_msg = f"{radius} {radius_units}" if radius is not None else "not specified"
            
            response = f"Loiter command added to mission: {coord_desc}, Alt={altitude_msg}, Radius={radius_msg}, (Item {item.seq + 1})"
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"