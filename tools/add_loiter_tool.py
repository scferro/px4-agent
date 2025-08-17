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
    latitude: Optional[float] = Field(None, description="GPS latitude for orbit center in decimal degrees. Use ONLY when latitude is specified by the user.")
    longitude: Optional[float] = Field(None, description="GPS longitude for orbit center in decimal degrees. Use ONLY when longitude is specified by the user.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate for orbit center. Use ONLY when user provides MGRS coordinates.")
    
    # Relative positioning for orbit center - use for "orbit 2 miles north of here"
    distance: Optional[float] = Field(None, description="Distance to orbit center from reference point. Use with heading.")
    heading: Optional[str] = Field(None, description="Direction to orbit center: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Use with distance.")
    distance_units: Optional[str] = Field(None, description="Units for distance: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    relative_reference_frame: Optional[str] = Field(None, description="Reference point for distance: 'origin' (takeoff), 'last_waypoint'. If no location is specified, set to 'lasr_waypoint' and leave other fields blank.")
    
    # Orbit radius - critical parameter often specified by user
    radius: Optional[float] = Field(None, description="Radius of the circular orbit pattern. Determines size of the circle.")
    radius_units: Optional[str] = Field(None, description="Units for orbit radius: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    
    # Optional orbit altitude
    altitude: Optional[float] = Field(None, description="Altitude for the orbit pattern. Specify only if user mentions height.")
    altitude_units: Optional[str] = Field(None, description="Units for orbit altitude: 'meters'/'m' or 'feet'/'ft'.")
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert loiter in mission. Set to specific position number or omit to add at end.")


class AddLoiterTool(PX4ToolBase):
    name: str = "add_loiter"
    description: str = "Add circular orbit/loiter pattern at specified location. Use when user wants drone to fly in circles, orbit, or loiter. Requires radius specification. Use for commands like 'orbit', 'circle', 'loiter', or when radius is mentioned like 'orbit with 400 foot radius', 'circle 2 miles north with 200m radius'. Creates continuous circular flight pattern. Specify Lat/Long OR MGRS OR distance/heading/reference. Do not mix location systems."
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
                relative_reference_frame=relative_reference_frame
            )
            
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