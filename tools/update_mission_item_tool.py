"""
Update Mission Item Tool - Modify specific mission item by sequence number
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class UpdateMissionItemInput(BaseModel):
    """Update specific mission item by its sequence number in the mission"""
    
    seq: int = Field(description="Mission item number to update (1=first item, 2=second item, etc.). Extract from user phrases like 'change the second waypoint' (seq=2), 'update item 3' (seq=3), 'modify the first takeoff' (seq=1).")
    
    # GPS coordinates - use when user provides exact lat/lon numbers
    latitude: Optional[float] = Field(None, description="New GPS latitude in decimal degrees. Use when user wants to change location like 'move item 2 to 37.7749, -122.4194' (latitude=37.7749). Updates exact GPS position.")
    longitude: Optional[float] = Field(None, description="New GPS longitude in decimal degrees. Use when user wants to change location like 'move item 2 to 37.7749, -122.4194' (longitude=-122.4194). Updates exact GPS position.")
    mgrs: Optional[str] = Field(None, description="New MGRS coordinate string like '11SMT1234567890'. Use when user provides MGRS coordinates for repositioning like 'change item 1 to MGRS 11SMT1234567890'.")
    
    # Relative positioning - use for directional commands like "move 2 miles north"
    distance: Optional[float] = Field(None, description="New distance value for relative positioning. Use when user wants to reposition relative to reference like 'move item 2 to 500 feet east' (distance=500), 'change waypoint 1 to 2 miles north' (distance=2).")
    heading: Optional[str] = Field(None, description="New compass direction as text. Use exact words: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Extract from phrases like 'move item 2 to 500 feet east' (heading='east').")
    distance_units: Optional[str] = Field(None, description="New units for distance parameter. Extract from user input: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'. Example: 'move to 500 feet east' uses 'feet'.")
    relative_reference_frame: Optional[str] = Field(None, description="New reference point for distance measurement. Use 'origin' (takeoff point) unless user specifies: 'from current position' (use 'current'), 'from last waypoint' (use 'last_waypoint').")
    
    # Altitude specification
    altitude: Optional[float] = Field(None, description="New altitude for the specified item. Use when user wants to change altitude like 'change item 2 altitude to 300 feet' (altitude=300), 'update the second waypoint to 100 meters' (altitude=100).")
    altitude_units: Optional[str] = Field(None, description="New altitude units for the update. Extract from user input: 'meters'/'m' or 'feet'/'ft'. Example: 'change item 2 to 300 feet' uses 'feet'.")
    
    # Orbit radius (loiter only)
    radius: Optional[float] = Field(None, description="New radius for orbit/loiter items only. Use when user wants to change orbit size like 'update item 3 radius to 200 meters' (radius=200), 'change the second orbit to 400 feet' (radius=400). Only works on loiter commands.")
    radius_units: Optional[str] = Field(None, description="New radius units for orbit updates. Extract from user input: 'meters'/'m' or 'feet'/'ft'. Example: 'update radius to 200 meters' uses 'meters'.")


class UpdateMissionItemTool(PX4ToolBase):
    name: str = "update_mission_item"
    description: str = "Update specific mission item by its sequence number. Use when user wants to modify a particular item by specifying its position in the mission. Can update position (GPS coordinates, relative positioning), altitude, and radius. Use for commands like 'change the second waypoint altitude to 300 feet', 'move item 1 to 2 miles north', 'update waypoint 3 to 37.7749, -122.4194', 'change the second orbit radius to 200 meters'. You CANNOT update a mission item TYPE. To change the type, first delete the old item then create a new one of the correct type."
    args_schema: type = UpdateMissionItemInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, seq: int, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None,
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None, 
             radius: Optional[float] = None, radius_units: Optional[str] = None) -> str:
        # Create response
        response = ""

        # Populate response
        try:
            mission = self.mission_manager.get_mission()
            if not mission or not mission.items:
                response = "Error: No mission items to update"
            else:
                # Save current mission state for potential rollback
                saved_state = self._save_mission_state()
                
                # Convert 1-based indexing to 0-based
                zero_based_seq = seq - 1
                if seq < 1 or zero_based_seq >= len(mission.items):
                    response = f"Error: Invalid sequence number {seq}. Mission has {len(mission.items)} items (1 to {len(mission.items)})"
                else:
                    item = mission.items[zero_based_seq]
                    changes_made = []
                    
                    # Check if this item supports position updates (waypoint or loiter)
                    command_type = getattr(item, 'command_type', None)
                    supports_position = command_type in ['waypoint', 'loiter']
                    
                    # Update GPS coordinates if provided
                    if latitude is not None and longitude is not None:
                        if supports_position:
                            item.latitude = latitude
                            item.longitude = longitude
                            # Clear relative positioning when setting GPS coordinates
                            if hasattr(item, 'distance'): item.distance = None
                            if hasattr(item, 'heading'): item.heading = None
                            changes_made.append(f"position to lat/long ({latitude:.6f}, {longitude:.6f})")
                        else:
                            response = f"Error: Cannot modify GPS coordinates on item {seq} - {command_type} commands don't support positioning"
                    
                    # Update MGRS coordinate if provided
                    if mgrs is not None and not response.startswith("Error:"):
                        if supports_position:
                            item.mgrs = mgrs
                            # Clear other positioning when setting MGRS
                            if hasattr(item, 'latitude'): item.latitude = None
                            if hasattr(item, 'longitude'): item.longitude = None
                            if hasattr(item, 'distance'): item.distance = None
                            if hasattr(item, 'heading'): item.heading = None
                            changes_made.append(f"position to MGRS {mgrs}")
                        else:
                            response = f"Error: Cannot modify MGRS coordinates on item {seq} - {command_type} commands don't support positioning"
                    
                    # Update relative positioning if provided
                    if distance is not None and heading is not None and not response.startswith("Error:"):
                        if supports_position:
                            item.distance = distance
                            item.heading = heading
                            if distance_units and hasattr(item, 'distance_units'):
                                item.distance_units = distance_units
                            if relative_reference_frame and hasattr(item, 'relative_reference_frame'):
                                item.relative_reference_frame = relative_reference_frame
                            # Clear GPS/MGRS when setting relative positioning
                            if hasattr(item, 'latitude'): item.latitude = None
                            if hasattr(item, 'longitude'): item.longitude = None
                            if hasattr(item, 'mgrs'): item.mgrs = None
                            
                            units_text = f" {distance_units}" if distance_units else ""
                            ref_frame = relative_reference_frame or "origin"
                            changes_made.append(f"position to {distance}{units_text} {heading} from {ref_frame}")
                        else:
                            response = f"Error: Cannot modify relative position on item {seq} - {command_type} commands don't support positioning"
                    
                    # Update altitude if provided
                    if altitude is not None and not response.startswith("Error:"):
                        if hasattr(item, 'altitude'):
                            item.altitude = altitude
                        if altitude_units and hasattr(item, 'altitude_units'):
                            item.altitude_units = altitude_units
                        changes_made.append(f"altitude to {altitude} {altitude_units or 'meters'}")
                    
                    # Update radius if provided (only for loiter items)
                    if radius is not None and not response.startswith("Error:"):
                        if command_type == 'loiter':
                            if hasattr(item, 'radius'):
                                item.radius = radius
                            if radius_units and hasattr(item, 'radius_units'):
                                item.radius_units = radius_units
                            changes_made.append(f"radius to {radius} {radius_units or 'meters'}")
                        else:
                            response = f"Error: Cannot modify radius on item {seq} - not a loiter/orbit command"
                    
                    # Check if we have a successful update
                    if not response.startswith("Error:"):
                        if not changes_made:
                            response = "No changes specified - provide position (lat/long, MGRS, or distance/heading), altitude, radius, or other parameters to modify"
                        else:
                            # Validate mission after modifications
                            is_valid, error_msg = self._validate_mission_after_action()
                            if not is_valid:
                                # Rollback the action
                                self._restore_mission_state(saved_state)
                                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
                            else:
                                changes_str = ", ".join(changes_made)
                                response = f"Updated mission item {seq}: {changes_str}"
                                response += self._get_mission_state_summary()
            
        except Exception as e:
            response = f"Error: {str(e)}"

        return response