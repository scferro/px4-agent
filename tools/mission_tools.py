"""
PX4 Mission Planning Tools for LangChain
Tools that wrap the mission manager functionality
"""

from typing import Dict, Any, Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json

from core import MissionManager

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

class TakeoffInput(BaseModel):
    """Launch drone from ground to specified flight altitude"""
    
    # GPS coordinates for takeoff location - usually leave None
    latitude: Optional[float] = Field(None, description="Takeoff GPS latitude. Usually leave None to takeoff from current drone position. Only specify if user explicitly mentions takeoff location like 'takeoff from 37.7749, -122.4194'.")
    longitude: Optional[float] = Field(None, description="Takeoff GPS longitude. Usually leave None to takeoff from current drone position. Only specify if user explicitly mentions takeoff location like 'takeoff from 37.7749, -122.4194'.")
    
    # Target altitude - required parameter
    altitude: Optional[float] = Field(None, description="Target takeoff altitude that drone will climb to. Extract from phrases like 'takeoff to 250 feet' (altitude=250), 'launch to 100 meters' (altitude=100), 'take off to 20m' (altitude=20). This sets the flight altitude for the mission.")
    altitude_units: Optional[str] = Field(None, description="Units for takeoff altitude. Extract from user input: 'meters'/'m' or 'feet'/'ft'. Example: 'takeoff to 250 feet' uses 'feet'.")


class RTLInput(BaseModel):
    """Return to launch - automatically fly back to takeoff point and land"""

class UpdateMissionItemInput(BaseModel):
    """Update specific mission item by its sequence number in the mission"""
    
    seq: int = Field(description="Mission item number to update (1=first item, 2=second item, etc.). Extract from user phrases like 'change the second waypoint' (seq=2), 'update item 3' (seq=3), 'modify the first takeoff' (seq=1).")
    altitude: Optional[float] = Field(None, description="New altitude for the specified item. Use when user wants to change altitude like 'change item 2 altitude to 300 feet' (altitude=300), 'update the second waypoint to 100 meters' (altitude=100).")
    altitude_units: Optional[str] = Field(None, description="New altitude units for the update. Extract from user input: 'meters'/'m' or 'feet'/'ft'. Example: 'change item 2 to 300 feet' uses 'feet'.")
    radius: Optional[float] = Field(None, description="New radius for orbit/loiter items only. Use when user wants to change orbit size like 'update item 3 radius to 200 meters' (radius=200), 'change the second orbit to 400 feet' (radius=400). Only works on loiter commands.")
    radius_units: Optional[str] = Field(None, description="New radius units for orbit updates. Extract from user input: 'meters'/'m' or 'feet'/'ft'. Example: 'update radius to 200 meters' uses 'meters'.")

class DeleteMissionItemInput(BaseModel):
    """Delete/remove specific mission item by sequence number"""
    
    seq: int = Field(description="Mission item number to delete (1=first item, 2=second item, etc.). Extract from user phrases like 'delete the second waypoint' (seq=2), 'remove item 3' (seq=3), 'get rid of the first takeoff' (seq=1). Item will be permanently removed and remaining items renumbered.")

# Global mission manager instance to share across all tools
_shared_mission_manager = MissionManager()

# Model Parameter Schemas - Maps command types to ALL parameters the model can return
MODEL_PARAMETER_SCHEMAS = {
    'takeoff': {
        'Location Parameters': ['latitude', 'longitude'],
        'Altitude Parameters': ['altitude', 'altitude_units']
    },
    'waypoint': {
        'GPS Coordinates': ['latitude', 'longitude', 'mgrs'],
        'Relative Positioning': ['distance', 'heading', 'distance_units', 'relative_reference_frame'],
        'Altitude Parameters': ['altitude', 'altitude_units']
    },
    'loiter': {
        'GPS Coordinates': ['latitude', 'longitude', 'mgrs'],
        'Relative Positioning': ['distance', 'heading', 'distance_units', 'relative_reference_frame'],
        'Orbit Parameters': ['radius', 'radius_units'],
        'Altitude Parameters': ['altitude', 'altitude_units']
    },
    'rtl': {}  # No parameters available
}

# Command Type Mapping
COMMAND_TYPE_MAP = {
    # Will be populated with MAV_CMD imports
}

class PX4ToolsMixin:
    """Mixin class providing mission manager access"""
    
    @property
    def mission_manager(self):
        return _shared_mission_manager
    
    def _get_command_name(self, command_type: str) -> str:
        """Get human-readable command name from type"""
        command_map = {
            'takeoff': "Takeoff",
            'waypoint': "Waypoint",
            'loiter': "Loiter",
            'rtl': "Return to Launch"
        }
        return command_map.get(command_type, f"Unknown {command_type}")
    
    def _validate_mission_after_action(self) -> tuple[bool, str]:
        """Validate mission after action is performed - allows rollback if invalid"""
        mission = self.mission_manager.get_mission()
        if not mission:
            return True, ""
        
        # Use the comprehensive mission validation from MissionManager with mode-specific rules
        is_valid, error_list = self.mission_manager.validate_mission()
        
        if not is_valid:
            # Return first error as primary message
            primary_error = error_list[0] if error_list else "Mission validation failed"
            return False, primary_error
        
        return True, ""
    
    def _save_mission_state(self):
        """Save current mission state for rollback"""
        mission = self.mission_manager.get_mission()
        if not mission:
            return None
        
        # Create a deep copy of mission items
        import copy
        return copy.deepcopy(mission.items)
    
    def _restore_mission_state(self, saved_items):
        """Restore mission to previous state"""
        mission = self.mission_manager.get_mission()
        if mission and saved_items is not None:
            mission.items = saved_items
            # Resequence items
            for i, item in enumerate(mission.items):
                item.seq = i
    
    def _get_detailed_parameter_display(self, item) -> str:
        """Show ALL model-available parameters for this mission item"""
        COMMAND_EMOJIS = {
            'takeoff': "🚀",
            'waypoint': "📍", 
            'loiter': "🔄",
            'rtl': "🏠"
        }
        UNSPECIFIED_MARKER = "unspecified"
        
        command_type = getattr(item, 'command_type', 'unknown')
        command_name = self._get_command_name(command_type)
        schema = MODEL_PARAMETER_SCHEMAS.get(command_type, {})
        
        emoji = COMMAND_EMOJIS.get(command_type, '❓')
        display = f"{emoji} {command_name.upper()} (Item {item.seq + 1})\n"
        
        if not schema:
            display += "  (No parameters available for this command type)\n"
            return display
        
        for category, params in schema.items():
            display += f"  {category}:\n"
            for param in params:
                value = getattr(item, param, None)
                if value is None:
                    display += f"    {param}: {UNSPECIFIED_MARKER}\n"
                else:
                    display += f"    {param}: {value}\n"
            display += "\n"
        
        return display
    
    def _convert_heading_to_degrees(self, heading: Optional[str]) -> Optional[float]:
        """Convert text direction to degrees"""
        if heading is None:
            return None
        
        direction_map = {
            'north': 0.0,
            'northeast': 45.0,
            'east': 90.0,
            'southeast': 135.0,
            'south': 180.0,
            'southwest': 225.0,
            'west': 270.0,
            'northwest': 315.0,
            # Common abbreviations
            'n': 0.0,
            'ne': 45.0,
            'e': 90.0,
            'se': 135.0,
            's': 180.0,
            'sw': 225.0,
            'w': 270.0,
            'nw': 315.0
        }
        
        return direction_map.get(heading.lower())
    
    def _get_mission_state_summary(self) -> str:
        """Get current mission state summary for tool responses - MODEL CONTEXT ONLY"""
        mission = self.mission_manager.get_mission()
        if not mission or not mission.items:
            return "\n\nCURRENT MISSION STATE: Empty mission - no items yet."
        
        summary = f"\n\nCURRENT MISSION STATE: {len(mission.items)} items:"
        for i, item in enumerate(mission.items):
            cmd_name = self._get_command_name(getattr(item, 'command_type', 'unknown'))
            item_desc = f"\n  {i+1}. {cmd_name}"
            
            # ONLY show coordinates if actually specified by model
            if hasattr(item, 'latitude') and item.latitude is not None and hasattr(item, 'longitude') and item.longitude is not None:
                item_desc += f" at ({item.latitude:.6f}, {item.longitude:.6f})"
            elif hasattr(item, 'mgrs') and item.mgrs:
                item_desc += f" at MGRS {item.mgrs}"
            # Show distance/heading info if any positioning specified - make missing parts clear
            distance_specified = hasattr(item, 'distance') and item.distance is not None
            heading_specified = hasattr(item, 'heading') and item.heading is not None
            distance_units_specified = hasattr(item, 'distance_units') and item.distance_units
            reference_specified = hasattr(item, 'relative_reference_frame') and item.relative_reference_frame
            
            if distance_specified or heading_specified or distance_units_specified or reference_specified:
                position_parts = []
                
                if distance_specified or distance_units_specified:
                    if distance_specified and distance_units_specified:
                        distance_str = f"{item.distance}{item.distance_units}"
                    elif distance_specified and not distance_units_specified:
                        distance_str = f"{item.distance} (units missing)"
                    elif not distance_specified and distance_units_specified:
                        distance_str = f"(not specified) {item.distance_units}"
                    position_parts.append(distance_str)
                
                if heading_specified:
                    heading_display = item.heading if isinstance(item.heading, str) else f"{item.heading}°"
                    position_parts.append(heading_display)
                elif distance_specified:  # If distance but no heading
                    position_parts.append("(direction missing)")
                
                if reference_specified:
                    ref_str = f" from {item.relative_reference_frame}"
                elif distance_specified or heading_specified:
                    ref_str = " from (reference missing)"
                else:
                    ref_str = ""
                
                if position_parts:
                    item_desc += f" at {' '.join(position_parts)}{ref_str}"
            
            # Show altitude info if either value or units specified - make missing parts clear
            altitude_specified = hasattr(item, 'altitude') and item.altitude is not None
            altitude_units_specified = hasattr(item, 'altitude_units') and item.altitude_units
            
            if altitude_specified or altitude_units_specified:
                if altitude_specified and altitude_units_specified:
                    altitude_str = f"{item.altitude}{item.altitude_units}"
                elif altitude_specified and not altitude_units_specified:
                    altitude_str = f"{item.altitude} (units missing)"
                elif not altitude_specified and altitude_units_specified:
                    altitude_str = f"(not specified) {item.altitude_units}"
                item_desc += f", alt: {altitude_str}"
            
            # Show radius info if either value or units specified - make missing parts clear
            radius_specified = hasattr(item, 'radius') and item.radius is not None
            radius_units_specified = hasattr(item, 'radius_units') and item.radius_units
            
            if radius_specified or radius_units_specified:
                if radius_specified and radius_units_specified:
                    radius_str = f"{item.radius}{item.radius_units}"
                elif radius_specified and not radius_units_specified:
                    radius_str = f"{item.radius} (units missing)"
                elif not radius_specified and radius_units_specified:
                    radius_str = f"(not specified) {item.radius_units}"
                item_desc += f", radius: {radius_str}"
            
            # NO MAVLink parameters - only show what model can specify
            
            summary += item_desc
        
        return summary
    
    def _build_coordinate_description(self, latitude, longitude, mgrs, distance, heading, distance_units, relative_reference_frame):
        """Build coordinate description following wx-agent pattern"""
        if latitude is not None and longitude is not None:
            return f"lat/long ({latitude:.6f}, {longitude:.6f})"
        elif mgrs is not None:
            return f"MGRS {mgrs}"
        elif distance is not None and heading is not None:
            ref_desc = {"origin": "takeoff", "current": "current position", "last_waypoint": "last waypoint"}.get(relative_reference_frame, "takeoff")
            return f"{distance} {distance_units} {heading} from {ref_desc}"
        else:
            return "coordinates not specified"

class AddWaypointTool(PX4ToolsMixin, BaseTool):
    name: str = "add_waypoint"
    description: str = "Add waypoint for drone navigation to specific location. Use when user wants drone to fly to a location using either exact GPS coordinates (like '37.7749, -122.4194') or relative directions (like '2 miles north', '500 feet east'). Creates flight path point where drone flies to location and continues to next mission item."
    args_schema: type = WaypointInput
    
    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None, 
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Work with current mission
            
            # Build coordinate description following wx-agent pattern
            coord_desc = self._build_coordinate_description(latitude, longitude, mgrs, distance, heading, distance_units, relative_reference_frame)
            
            # For mission manager, use lat/lon if provided, otherwise use defaults
            actual_lat = latitude if latitude is not None else 40.7128
            actual_lon = longitude if longitude is not None else -74.0060
            actual_alt = altitude if altitude is not None else 0.0
            
            # Convert text heading to degrees for mission manager
            heading_degrees = self._convert_heading_to_degrees(heading)
            
            # Use mission manager method
            item = self.mission_manager.add_waypoint(
                actual_lat, actual_lon, actual_alt, 
                altitude_units=altitude_units,  # Store EXACTLY what model provided
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
            actual_seq = item.seq
            
            # Validate mission after adding waypoint
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Error: {error_msg}"
            
            # Build response message with preserved units
            altitude_msg = f"{altitude} {altitude_units}" if altitude is not None else "not specified"
            response = f"Waypoint added to mission: {coord_desc}, Alt={altitude_msg} (Item {actual_seq + 1})"
            response += self._get_mission_state_summary()
            return response
        except Exception as e:
            return f"Error: {str(e)}"

class AddLoiterTool(PX4ToolsMixin, BaseTool):
    name: str = "add_loiter"
    description: str = "Add circular orbit/loiter pattern at specified location. Use when user wants drone to fly in circles, orbit, or loiter. Requires radius specification. Use for commands like 'orbit', 'circle', 'loiter', or when radius is mentioned like 'orbit with 400 foot radius', 'circle 2 miles north with 200m radius'. Creates continuous circular flight pattern."
    args_schema: type = LoiterInput

    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, mgrs: Optional[str] = None, 
             distance: Optional[float] = None, heading: Optional[str] = None, distance_units: Optional[str] = None, 
             relative_reference_frame: Optional[str] = None, altitude: Optional[float] = None, altitude_units: Optional[str] = None, 
             radius: Optional[float] = None, radius_units: Optional[str] = None) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()

            # Work with current mission
            
            # Build coordinate description following wx-agent pattern
            coord_desc = self._build_coordinate_description(latitude, longitude, mgrs, distance, heading, distance_units, relative_reference_frame)
            
            # For mission manager, use lat/lon if provided, otherwise use 0 (no guessing)
            actual_lat = latitude if latitude is not None else 0.0
            actual_lon = longitude if longitude is not None else 0.0
            actual_alt = altitude if altitude is not None else 0.0
            actual_radius = radius if radius is not None else 50.0  # Default radius
            
            # Convert text heading to degrees for mission manager
            heading_degrees = self._convert_heading_to_degrees(heading)
            
            item = self.mission_manager.add_loiter(
                actual_lat, actual_lon, actual_alt, actual_radius,
                radius_units=radius_units,  # Store EXACTLY what model provided
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
                return f"Error: {error_msg}"
            
            # Build response with preserved units
            altitude_msg = f"{altitude} {altitude_units}" if altitude is not None else "not specified"
            radius_msg = f"{radius} {radius_units}" if radius is not None else "not specified"
            
            response = f"Loiter command added to mission: {coord_desc}, Alt={altitude_msg}, Radius={radius_msg}, (Item {item.seq + 1})"
            response += self._get_mission_state_summary()
            return response
        except Exception as e:
            return f"Error: {str(e)}"

class AddTakeoffTool(PX4ToolsMixin, BaseTool):
    name: str = "add_takeoff"
    description: str = "Add takeoff command to launch drone from ground to flight altitude. Use when user wants drone to take off, launch, or lift off. Typically the first command in any mission. Use for commands like 'takeoff', 'launch', 'lift off', especially when altitude is specified like 'takeoff to 200 feet', 'launch to 100 meters'."
    args_schema: type = TakeoffInput
    
    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, 
             altitude: Optional[float] = None, altitude_units: Optional[str] = None) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Build coordinate description - for takeoff, usually just use altitude
            coord_desc = ""
            if latitude is not None and longitude is not None:
                coord_desc = f" from lat/long ({latitude:.6f}, {longitude:.6f})"
            else:
                coord_desc = ""
            
            # For mission manager, use lat/lon if provided, otherwise use 0 (no guessing)
            actual_lat = latitude if latitude is not None else 0.0
            actual_lon = longitude if longitude is not None else 0.0
            actual_alt = altitude if altitude is not None else 10.0  # Default takeoff altitude
            
            item = self.mission_manager.add_takeoff(
                actual_lat, actual_lon, actual_alt, 
                altitude_units=altitude_units,  # Store EXACTLY what model provided
                original_altitude=altitude,
                original_latitude=latitude,
                original_longitude=longitude
            )
            
            # Validate mission after adding takeoff
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Error: {error_msg}"
            
            # Build response message with preserved units
            altitude_msg = f" to {altitude} {altitude_units}" if altitude is not None else " to default altitude"
            response = f"Takeoff command added to mission{coord_desc}{altitude_msg} (Item {item.seq + 1})"
            response += self._get_mission_state_summary()
            return response
        except Exception as e:
            return f"Error: {str(e)}"


class AddRTLTool(PX4ToolsMixin, BaseTool):
    name: str = "add_return_to_launch"
    description: str = "Add return to launch command for automatic return and landing. Use when user wants drone to automatically fly back to takeoff point and land. Typically the last command in a mission. Use for commands like 'RTL', 'return to launch', 'go home', 'return home', 'come back'."
    args_schema: type = RTLInput
    
    def _run(self) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Work with current mission
            item = self.mission_manager.add_return_to_launch()
            
            # Validate mission after adding RTL
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Error: {error_msg}"
            
            response = f"Return to Launch command added to mission (Item {item.seq + 1})"
            response += self._get_mission_state_summary()
            return response
        except Exception as e:
            return f"Error: {str(e)}"

class UpdateMissionItemTool(PX4ToolsMixin, BaseTool):
    name: str = "update_mission_item"
    description: str = "Update specific mission item by its sequence number. Use when user wants to modify a particular item by specifying its position in the mission. Use for commands like 'change the second waypoint altitude to 300 feet', 'update item 1 radius to 200 meters', 'modify the third command altitude'."
    args_schema: type = UpdateMissionItemInput
    
    def _run(self, seq: int, altitude: Optional[float] = None, altitude_units: Optional[str] = None,
             radius: Optional[float] = None, radius_units: Optional[str] = None) -> str:
        try:
            mission = self.mission_manager.get_mission()
            if not mission or not mission.items:
                return "Error: No mission items to update"
            
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Convert 1-based indexing to 0-based
            zero_based_seq = seq - 1
            if seq < 1 or zero_based_seq >= len(mission.items):
                return f"Error: Invalid sequence number {seq}. Mission has {len(mission.items)} items (1 to {len(mission.items)})"
            
            item = mission.items[zero_based_seq]
            changes_made = []
            
            # Update altitude if provided
            if altitude is not None:
                item.z = altitude
                if hasattr(item, 'altitude'):
                    item.altitude = altitude
                if altitude_units and hasattr(item, 'altitude_units'):
                    item.altitude_units = altitude_units
                changes_made.append(f"altitude to {altitude} {altitude_units or 'meters'}")
            
            # Update radius if provided (only for loiter items)
            if radius is not None:
                if hasattr(item, 'radius') or item.command == 17:  # MAV_CMD.NAV_LOITER_UNLIM
                    item.param3 = radius  # Radius is stored in param3 for loiter
                    if hasattr(item, 'radius'):
                        item.radius = radius
                    if radius_units and hasattr(item, 'radius_units'):
                        item.radius_units = radius_units
                    changes_made.append(f"radius to {radius} {radius_units or 'meters'}")
                else:
                    return f"Error: Cannot modify radius on item {seq} - not a loiter/orbit command"
            
            if not changes_made:
                return "No changes specified - provide altitude, radius, or other parameters to modify"
            
            # Validate mission after modifications
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Error: {error_msg}"
            
            changes_str = ", ".join(changes_made)
            response = f"Updated mission item {seq}: {changes_str}"
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"

class DeleteMissionItemTool(PX4ToolsMixin, BaseTool):
    name: str = "delete_mission_item"
    description: str = "Delete specific mission item by its sequence number. Use when user wants to remove a particular item from the mission by specifying its position. Use for commands like 'delete the second waypoint', 'remove item 1', 'get rid of that takeoff'. Item is permanently removed and remaining items are renumbered. IF YOU GET STUCK, DELETE LOGS UNTIL YOU ARE IN A PLACE YOU CAN CONTINUE FROM."
    args_schema: type = DeleteMissionItemInput
    
    def _run(self, seq: int) -> str:
        try:
            mission = self.mission_manager.get_mission()
            if not mission or not mission.items:
                return "Error: No mission items to delete"
            
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Convert 1-based indexing to 0-based
            zero_based_seq = seq - 1
            if seq < 1 or zero_based_seq >= len(mission.items):
                return f"Error: Invalid sequence number {seq}. Mission has {len(mission.items)} items (1 to {len(mission.items)})"
            
            # Get item info before deletion for confirmation message
            item_to_delete = mission.items[zero_based_seq]
            command_name = _get_command_name(item_to_delete.command)
            
            # Remove the item from the mission
            del mission.items[zero_based_seq]
            
            # Resequence remaining items
            for i, item in enumerate(mission.items):
                item.seq = i
            
            # Validate mission after deletion
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Error: {error_msg}"
            
            response = f"Deleted mission item {seq} ({command_name}). Mission now has {len(mission.items)} items."
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"

# Note: Detailed mission display removed from model tools - this should be user-facing only

def get_px4_tools() -> list:
    """Get all PX4 mission planning tools"""
    return [
        AddWaypointTool(),
        AddTakeoffTool(),
        AddRTLTool(),
        AddLoiterTool(),
        UpdateMissionItemTool(),
        DeleteMissionItemTool(),
    ]