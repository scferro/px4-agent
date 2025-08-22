"""
PX4 Mission Manager
Manages single current mission and validation
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from config import get_settings
from core.mission import Mission, MissionItem
from core.validator import MissionValidator


class MissionManager:
    """Manages single current mission and validation"""
    
    def __init__(self, mode: str = "mission"):
        self.current_mission: Optional[Mission] = None
        self.mode = mode
        self.validator = MissionValidator(get_settings())
    
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
                   altitude: Optional[float] = None, mgrs: Optional[str] = None,
                   heading: Optional[str] = None,
                   search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> MissionItem:
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
            mgrs=mgrs,
            heading=heading,
            search_target=search_target,
            detection_behavior=detection_behavior
        )
        return self.insert_item_at(item, 1)  # Always insert at position 1 (first)
    
    def add_waypoint(self, lat: float, lon: float, alt: float,
                    altitude_units: Optional[str] = None, insert_at: Optional[int] = None, 
                    latitude: Optional[float] = None, longitude: Optional[float] = None, 
                    altitude: Optional[float] = None, mgrs: Optional[str] = None,
                    distance: Optional[float] = None, heading: Optional[str] = None,
                    distance_units: Optional[str] = None, relative_reference_frame: Optional[str] = None,
                    search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> MissionItem:
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
            relative_reference_frame=relative_reference_frame,
            search_target=search_target,
            detection_behavior=detection_behavior
        )
        return self.insert_item_at(item, insert_at)
    
    
    def add_return_to_launch(self, altitude: Optional[float] = None, 
                            altitude_units: Optional[str] = None,
                            search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> MissionItem:
        """Add return to launch command - always goes at the end"""
        mission = self._get_current_mission_or_raise()
        
        item = MissionItem(
            seq=0,  # Will be set by insert_item_at
            command_type='rtl',  # Track what type of command this is
            altitude=altitude,
            altitude_units=altitude_units,
            search_target=search_target,
            detection_behavior=detection_behavior
        )
        return self.insert_item_at(item, None)  # None = add at end
    
    def add_loiter(self, lat: float, lon: float, alt: float,
                  radius: float, radius_units: Optional[str] = None, insert_at: Optional[int] = None,
                  latitude: Optional[float] = None, longitude: Optional[float] = None, 
                  altitude: Optional[float] = None, altitude_units: Optional[str] = None,
                  mgrs: Optional[str] = None, distance: Optional[float] = None, 
                  heading: Optional[str] = None, distance_units: Optional[str] = None,
                  relative_reference_frame: Optional[str] = None,
                  search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> MissionItem:
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
            relative_reference_frame=relative_reference_frame,
            search_target=search_target,
            detection_behavior=detection_behavior
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
                  center_relative_reference_frame: Optional[str] = None,
                  search_target: Optional[str] = None, detection_behavior: Optional[str] = None) -> MissionItem:
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
            relative_reference_frame=center_relative_reference_frame,
            search_target=search_target,
            detection_behavior=detection_behavior
        )
        
        # Store survey-specific data as attributes
        item.survey_mode = mode
        item.corners = corners
        
        return self.insert_item_at(item, insert_at)
    
    
    def validate_mission(self) -> Tuple[bool, List[str]]:
        """Validate mission for safety and completeness"""
        mission = self._get_current_mission_or_raise()
        is_valid, errors, fixes_applied = self.validator.validate_mission(mission, self.mode)
        
        # Combine errors and fixes for reporting
        all_messages = errors.copy()
        if fixes_applied:
            all_messages.extend([f"Auto-fix: {fix}" for fix in fixes_applied])
        
        return is_valid, all_messages
    
    def _get_current_mission_or_raise(self) -> Mission:
        """Get current mission or raise error if not found"""
        if not self.current_mission:
            raise ValueError("No current mission available")
        return self.current_mission
    
    
    def get_mission_state_summary(self) -> str:
        """Get brief summary of current mission state in XML format"""
        mission = self.get_mission()
        summary = f"\n\n<mission_state>\n<total_items>{len(mission.items)}</total_items>"

        if mission and mission.items:
            # Use converted coordinates for display to model
            try:
                from config.settings import get_current_takeoff_settings
                takeoff_settings = get_current_takeoff_settings()
                converted_mission = mission.to_dict(convert_to_absolute=True)
                items_to_display = [type('obj', (object,), item_dict) for item_dict in converted_mission['items']]
            except Exception:
                # Fallback to original mission if conversion fails
                items_to_display = mission.items
            
            for i, item in enumerate(items_to_display):
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
                
                # Add position info - prioritize absolute coordinates from conversion
                if (hasattr(item, 'latitude') and item.latitude is not None) and (hasattr(item, 'longitude') and item.longitude is not None):
                    lat_val = f"{item.latitude:.6f}"
                    lon_val = f"{item.longitude:.6f}"
                    summary += f"\n  <position>lat/lon ({lat_val}, {lon_val})</position>"
                elif hasattr(item, 'mgrs') and item.mgrs is not None:
                    summary += f"\n  <position>MGRS {item.mgrs}</position>"
                elif (hasattr(item, 'distance') and item.distance is not None) or (hasattr(item, 'heading') and item.heading is not None and item.command_type != 'takeoff') or (hasattr(item, 'distance_units') and item.distance_units is not None) or (hasattr(item, 'relative_reference_frame') and item.relative_reference_frame is not None):
                    distance = item.distance if item.distance is not None else "(distance)"
                    dist_units = item.distance_units if item.distance_units is not None else "(distance_units)"
                    heading = item.heading if item.heading is not None else "(heading)"
                    ref_frame = item.relative_reference_frame if item.relative_reference_frame is not None else "(relative_reference_frame)"
                    summary += f"\n  <position>{distance} {dist_units} {heading} from {ref_frame}</position>"
                
                # Always show heading for takeoff commands (VTOL transition direction)
                if item.command_type == 'takeoff' and hasattr(item, 'heading') and item.heading is not None:
                    summary += f"\n  <heading>{item.heading}</heading>"
                
                # Show search parameters if any are specified (for all command types)
                if ((hasattr(item, 'search_target') and item.search_target is not None) or (hasattr(item, 'detection_behavior') and item.detection_behavior is not None)):
                    search_target = item.search_target if item.search_target is not None else "(search_target)"
                    detection_behavior = item.detection_behavior if item.detection_behavior is not None else "(detection_behavior)"
                    summary += f"\n  <search>target={search_target}, behavior={detection_behavior}</search>"
            
                summary += f"\n</item_{i+1}>"
        
        summary += "\n</mission_state>"
        return summary