"""
Update Mission Item Tool - Modify specific mission item by sequence number
"""

from typing import Optional, Union
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, field_validator

from .tools import PX4ToolBase
from core.parsing import parse_altitude, parse_distance, parse_radius, parse_coordinates


class UpdateMissionItemInput(BaseModel):
    """Update specific mission item by its sequence number in the mission"""
    
    seq: int = Field(description="Mission item number to update (1=first item, 2=second item, etc.)")
    
    # GPS coordinates - DISCOURAGED, prefer relative positioning
    coordinates: Optional[Union[str, tuple]] = Field(None, description="New GPS coordinates as 'lat,lon' (e.g., '40.7128,-74.0060'). **Avoid using unless user provides exact coordinates.** Prefer distance/heading/reference_frame for more intuitive positioning.")
    mgrs: Optional[str] = Field(None, description="New MGRS coordinate string like '11SMT1234567890'.")
    
    # Relative positioning - PREFERRED method for positioning
    distance: Optional[Union[float, str, tuple]] = Field(None, description="**PREFERRED**: New distance value for relative positioning with optional units (e.g., '2 miles', '1000 meters', '500 ft').")
    heading: Optional[str] = Field(None, description="**PREFERRED**: New compass direction as text.")
    relative_reference_frame: Optional[str] = Field(None, description="**PREFERRED**: New reference point for distance measurement. Use 'origin' when user references 'start', 'takeoff', 'here', etc., 'last_waypoint' if the user references the last waypoint, or 'self' to move the item relative to its current position.")
    
    # Altitude specification
    altitude: Optional[Union[float, str, tuple]] = Field(None, description="New altitude for the specified item with optional units (e.g., '150 feet', '50 meters').")
    
    # Orbit radius (loiter only)
    radius: Optional[Union[float, str, tuple]] = Field(None, description="New radius for orbit/loiter items only with optional units (e.g., '500 feet', '100 meters'). Only works on loiter commands.")
    
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
    
    @field_validator('radius', mode='before')
    @classmethod
    def parse_radius_field(cls, v):
        if v is None:
            return None
        parsed_value, units = parse_radius(v)
        if parsed_value is None:
            return v  # Let Pydantic handle validation error
        return (parsed_value, units)
    
    @field_validator('coordinates', mode='before')
    @classmethod
    def parse_coordinates_field(cls, v):
        if v is None:
            return None
        lat, lon = parse_coordinates(v)
        if lat is None or lon is None:
            return v  # Let Pydantic handle validation error
        return (lat, lon)
    
    # Search parameters
    search_target: Optional[str] = Field(None, description="Target description for AI to search for during this mission item (e.g., 'vehicles', 'people', 'buildings').")
    detection_behavior: Optional[str] = Field(None, description="Detection behavior: 'tag_and_continue' (mark targets and continue mission) or 'detect_and_monitor' (abort mission and circle detected target).")


class UpdateMissionItemTool(PX4ToolBase):
    name: str = "update_mission_item"
    description: str = "Update specific mission item by its sequence number. Can update waypoint, loiter, and survey items. Use when user wants to modify a particular item or when you need to correct a mistake. You CANNOT update a mission item TYPE. To change the type, first delete the old item then create a new one of the correct type."
    args_schema: type = UpdateMissionItemInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, seq: int, coordinates: Optional[Union[str, tuple]] = None, mgrs: Optional[str] = None,
             distance: Optional[Union[float, tuple]] = None, heading: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[Union[float, tuple]] = None, 
             radius: Optional[Union[float, tuple]] = None,
             search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> str:
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
            
            if isinstance(radius, tuple):
                radius_value, radius_units = radius
            else:
                radius_value, radius_units = radius, 'meters'
            
            # Parse coordinates from validator
            if isinstance(coordinates, tuple):
                latitude, longitude = coordinates
            else:
                latitude, longitude = None, None
            
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
                    
                    # Check if this item supports position updates (waypoint, loiter, survey) or heading (takeoff)
                    command_type = getattr(item, 'command_type', None)
                    supports_position = command_type in ['waypoint', 'loiter', 'survey']
                    supports_heading = command_type in ['takeoff', 'waypoint', 'loiter', 'survey']
                    
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
                    if distance_value is not None and heading is not None and not response.startswith("Error:"):
                        if supports_position:
                            # Handle 'self' reference frame specially
                            if relative_reference_frame == 'self':
                                # Validate that item has existing coordinates for self-reference
                                if not (hasattr(item, 'latitude') and item.latitude is not None and 
                                       hasattr(item, 'longitude') and item.longitude is not None):
                                    response = f"Error: Cannot use 'self' reference for item {seq} - item must have existing coordinates first"
                                else:
                                    # For 'self' reference, we keep both absolute and relative coordinates
                                    # The absolute coordinates serve as the reference point
                                    item.distance = distance_value
                                    item.heading = heading
                                    if distance_units and hasattr(item, 'distance_units'):
                                        item.distance_units = distance_units
                                    if hasattr(item, 'relative_reference_frame'):
                                        item.relative_reference_frame = relative_reference_frame
                                    # Do NOT clear latitude/longitude for 'self' reference
                                    # Clear MGRS though
                                    if hasattr(item, 'mgrs'): item.mgrs = None
                                    
                                    units_text = f" {distance_units}" if distance_units else ""
                                    changes_made.append(f"position to {distance_value}{units_text} {heading} from current location")
                            else:
                                # Standard relative positioning - clear absolute coordinates
                                item.distance = distance_value
                                item.heading = heading
                                if distance_units and hasattr(item, 'distance_units'):
                                    item.distance_units = distance_units
                                if relative_reference_frame and hasattr(item, 'relative_reference_frame'):
                                    item.relative_reference_frame = relative_reference_frame
                                # Clear GPS/MGRS when setting relative positioning (except for 'self')
                                if hasattr(item, 'latitude'): item.latitude = None
                                if hasattr(item, 'longitude'): item.longitude = None
                                if hasattr(item, 'mgrs'): item.mgrs = None
                                
                                units_text = f" {distance_units}" if distance_units else ""
                                ref_frame = relative_reference_frame or "origin"
                                changes_made.append(f"position to {distance_value}{units_text} {heading} from {ref_frame}")
                        else:
                            response = f"Error: Cannot modify relative position on item {seq} - {command_type} commands don't support positioning"
                    
                    # Update heading only (for takeoff VTOL transition direction)
                    if heading is not None and distance is None and not response.startswith("Error:"):
                        if supports_heading:
                            item.heading = heading
                            changes_made.append(f"heading to {heading}")
                        else:
                            response = f"Error: Cannot modify heading on item {seq} - {command_type} commands don't support heading"
                    
                    # Update altitude if provided
                    if altitude_value is not None and not response.startswith("Error:"):
                        if hasattr(item, 'altitude'):
                            item.altitude = altitude_value
                        if altitude_units and hasattr(item, 'altitude_units'):
                            item.altitude_units = altitude_units
                        changes_made.append(f"altitude to {altitude_value} {altitude_units or 'meters'}")
                    
                    # Update radius if provided (for loiter and survey items)
                    if radius_value is not None and not response.startswith("Error:"):
                        if command_type in ['loiter', 'survey']:
                            if hasattr(item, 'radius'):
                                item.radius = radius_value
                            if radius_units and hasattr(item, 'radius_units'):
                                item.radius_units = radius_units
                            changes_made.append(f"radius to {radius_value} {radius_units or 'meters'}")
                        else:
                            response = f"Error: Cannot modify radius on item {seq} - not a loiter/survey command"
                    
                    # Update search parameters if provided
                    if search_target is not None and not response.startswith("Error:"):
                        if hasattr(item, 'search_target'):
                            item.search_target = search_target
                        changes_made.append(f"search_target to {search_target}")
                    
                    if detection_behavior is not None and not response.startswith("Error:"):
                        if hasattr(item, 'detection_behavior'):
                            item.detection_behavior = detection_behavior
                        changes_made.append(f"detection_behavior to {detection_behavior}")
                    
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