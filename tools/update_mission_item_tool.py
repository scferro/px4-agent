"""
Update Mission Item Tool - Modify specific mission item by sequence number
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class UpdateMissionItemInput(BaseModel):
    """Update specific mission item by its sequence number in the mission"""
    
    seq: int = Field(description="Mission item number to update (1=first item, 2=second item, etc.)")
    
    # GPS coordinates - use when user provides exact lat/lon numbers
    latitude: Optional[float] = Field(None, description="New GPS latitude in decimal degrees.")
    longitude: Optional[float] = Field(None, description="New GPS longitude in decimal degrees.")
    mgrs: Optional[str] = Field(None, description="New MGRS coordinate string like '11SMT1234567890'.")
    
    # Relative positioning - use for directional commands like "move 2 miles north"
    distance: Optional[float] = Field(None, description="New distance value for relative positioning.")
    heading: Optional[str] = Field(None, description="New compass direction as text.")
    distance_units: Optional[str] = Field(None, description="New units for distance parameter: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    relative_reference_frame: Optional[str] = Field(None, description="New reference point for distance measurement. Use 'origin' when user references 'start', 'takeoff', 'here', etc. or 'last_waypoint' if the user references the last waypoint.")")
    
    # Altitude specification
    altitude: Optional[float] = Field(None, description="New altitude for the specified item.")
    altitude_units: Optional[str] = Field(None, description="New altitude units for the update: 'meters'/'m' or 'feet'/'ft'.")
    
    # Orbit radius (loiter only)
    radius: Optional[float] = Field(None, description="New radius for orbit/loiter items only. Only works on loiter commands.")
    radius_units: Optional[str] = Field(None, description="New radius units for orbit updates: 'meters'/'m' or 'feet'/'ft'.")
    
    # Search parameters
    search_target: Optional[str] = Field(None, description="Target description for AI to search for during this mission item (e.g., 'vehicles', 'people', 'buildings').")
    detection_behavior: Optional[str] = Field(None, description="Detection behavior: 'tag_and_continue' (mark targets and continue mission) or 'detect_and_monitor' (abort mission and circle detected target).")


class UpdateMissionItemTool(PX4ToolBase):
    name: str = "update_mission_item"
    description: str = "Update specific mission item by its sequence number. Can update waypoint, loiter, and survey items. Use when user wants to modify a particular item or when you need to correct a mistake. You CANNOT update a mission item TYPE. To change the type, first delete the old item then create a new one of the correct type."
    args_schema: type = UpdateMissionItemInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, seq: int, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None,
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None, 
             radius: Optional[float] = None, radius_units: Optional[str] = None,
             search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> str:
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
                    
                    # Update heading only (for takeoff VTOL transition direction)
                    if heading is not None and distance is None and not response.startswith("Error:"):
                        if supports_heading:
                            item.heading = heading
                            changes_made.append(f"heading to {heading}")
                        else:
                            response = f"Error: Cannot modify heading on item {seq} - {command_type} commands don't support heading"
                    
                    # Update altitude if provided
                    if altitude is not None and not response.startswith("Error:"):
                        if hasattr(item, 'altitude'):
                            item.altitude = altitude
                        if altitude_units and hasattr(item, 'altitude_units'):
                            item.altitude_units = altitude_units
                        changes_made.append(f"altitude to {altitude} {altitude_units or 'meters'}")
                    
                    # Update radius if provided (for loiter and survey items)
                    if radius is not None and not response.startswith("Error:"):
                        if command_type in ['loiter', 'survey']:
                            if hasattr(item, 'radius'):
                                item.radius = radius
                            if radius_units and hasattr(item, 'radius_units'):
                                item.radius_units = radius_units
                            changes_made.append(f"radius to {radius} {radius_units or 'meters'}")
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