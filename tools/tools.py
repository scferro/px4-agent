"""
PX4 Mission Planning Tools - Main module
Contains shared functions, schemas, and tool registry
"""

from typing import Dict, Any, Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core import MissionManager


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

# Base class for all mission item tools
class PX4ToolBase(BaseTool):
    """Base class providing shared functionality for all PX4 tools"""
    
    def __init__(self, mission_manager: MissionManager):
        super().__init__()
        self._mission_manager = mission_manager
    
    @property
    def mission_manager(self):
        return self._mission_manager
    
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
        if mission:
            # Save a copy of all mission items
            return [item for item in mission.items]
        return []
    
    def _restore_mission_state(self, saved_state):
        """Restore mission state from saved state"""
        mission = self.mission_manager.get_mission()
        if mission:
            mission.items.clear()
            mission.items.extend(saved_state)
    
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
        
        # Show all available parameters from schema
        for category, params in schema.items():
            display += f"\n[{category}]\n"
            for param in params:
                value = getattr(item, param, None)
                if value is None:
                    display += f"    {param}: {UNSPECIFIED_MARKER}\n"
                else:
                    display += f"    {param}: {value}\n"
        
        return display
    
    def _get_mission_state_summary(self) -> str:
        """Get brief summary of current mission state"""
        mission = self.mission_manager.get_mission()
        if not mission or not mission.items:
            return ""
        
        summary = f"\n\nCURRENT MISSION STATE: {len(mission.items)} items:"
        for i, item in enumerate(mission.items):
            cmd_name = self._get_command_name(getattr(item, 'command_type', 'unknown'))
            item_desc = f"\n  {i+1}. {cmd_name}"
            
            # Add key parameters
            if hasattr(item, 'altitude') and item.altitude is not None:
                alt_units = getattr(item, 'altitude_units', 'units')
                item_desc += f" at {item.altitude} {alt_units}"
            
            if hasattr(item, 'radius') and item.radius is not None:
                radius_units = getattr(item, 'radius_units', 'units')
                item_desc += f" (radius: {item.radius} {radius_units})"
            
            summary += item_desc
        
        return summary
    
    def _build_coordinate_description(self, latitude, longitude, mgrs, distance, heading, distance_units, relative_reference_frame):
        """Build coordinate description for responses"""
        if latitude is not None and longitude is not None:
            return f"lat/long ({latitude:.6f}, {longitude:.6f})"
        elif mgrs is not None:
            return f"MGRS {mgrs}"
        elif distance is not None and heading is not None:
            units_text = f" {distance_units}" if distance_units else ""
            ref_frame = relative_reference_frame or "origin"
            return f"{distance}{units_text} {heading} from {ref_frame}"
        else:
            return "coordinates not specified"

def get_px4_tools(mission_manager: MissionManager) -> list:
    """Get all PX4 mission planning tools"""
    from .add_waypoint_tool import AddWaypointTool
    from .add_takeoff_tool import AddTakeoffTool
    from .add_rtl_tool import AddRTLTool
    from .add_loiter_tool import AddLoiterTool
    from .update_mission_item_tool import UpdateMissionItemTool
    from .delete_mission_item_tool import DeleteMissionItemTool
    
    return [
        AddWaypointTool(mission_manager),
        AddTakeoffTool(mission_manager),
        AddRTLTool(mission_manager),
        AddLoiterTool(mission_manager),
        UpdateMissionItemTool(mission_manager),
        DeleteMissionItemTool(mission_manager),
    ]