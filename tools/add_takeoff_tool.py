"""
Add Takeoff Tool - Launch drone from ground to flight altitude
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase
from config.settings import get_agent_settings

# Load agent settings for Field descriptions
_agent_settings = get_agent_settings()


class TakeoffInput(BaseModel):
    """Launch drone from ground to specified flight altitude"""
    
    # GPS coordinates for takeoff location - usually leave None
    latitude: Optional[float] = Field(None, description="Takeoff GPS latitude. Usually leave None to takeoff from current drone position. Use ONLY when latitude is specified.")
    longitude: Optional[float] = Field(None, description="Takeoff GPS longitude. Usually leave None to takeoff from current drone position. Use ONLY when longitude is specified.")
    mgrs: Optional[str] = Field(None, description="MGRS coordinate string. Use when user provides MGRS grid coordinates for takeoff location.")
    
    # Target altitude - required parameter
    altitude: Optional[float] = Field(None, description=f"Target takeoff altitude that drone will climb to. Extract from phrases like 'takeoff to 250 feet', 'launch to 100 meters'. This sets the flight altitude for the mission. DO NOT include unless directly specified by the user. Default = {_agent_settings['takeoff_default_altitude']} {_agent_settings['takeoff_altitude_units']}")
    altitude_units: Optional[str] = Field(None, description="Units for takeoff altitude. Extract from user input: 'meters'/'m' or 'feet'/'ft'.")
    
    # VTOL transition heading
    heading: Optional[str] = Field(None, description="Direction VTOL will point during transition to forward flight: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Typically into the wind. Use ONLY when direction is specified.")


class AddTakeoffTool(PX4ToolBase):
    name: str = "add_takeoff"
    description: str = "Add takeoff command to launch drone from ground to flight altitude. Always inserted as the FIRST mission item. Use when user wants drone to take off, launch, or lift off. Use for commands like 'takeoff', 'launch', 'lift off', especially when altitude is specified like 'takeoff to 200 feet', 'launch to 100 meters'."
    args_schema: type = TakeoffInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, latitude: Optional[float] = None, longitude: Optional[float] = None, 
             altitude: Optional[float] = None, altitude_units: Optional[str] = None,
             mgrs: Optional[str] = None, heading: Optional[str] = None) -> str:
        # Create response
        response = ""

        # Populate response
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Build coordinate description - for takeoff, usually just use altitude
            coord_desc = ""
            if latitude is not None and longitude is not None:
                coord_desc = f" from lat/long ({latitude:.6f}, {longitude:.6f})"
            elif mgrs is not None:
                coord_desc = f" from MGRS {mgrs}"
            else:
                coord_desc = ""
            
            # For mission manager, use lat/lon if provided, otherwise use 0 (no guessing)
            actual_lat = latitude if latitude is not None else 0.0
            actual_lon = longitude if longitude is not None else 0.0
            actual_alt = altitude if altitude is not None else 10.0  # Default takeoff altitude
            
            item = self.mission_manager.add_takeoff(
                actual_lat, actual_lon, actual_alt, 
                altitude_units=altitude_units,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                mgrs=mgrs,
                heading=heading
            )
            
            # Validate mission after adding takeoff
            is_valid, validation_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {validation_msg}" + self._get_mission_state_summary()
            else:
                # Build response message with preserved units
                altitude_msg = f"{altitude} {altitude_units}" if altitude is not None else "default altitude"
                heading_msg = f", Heading={heading}" if heading is not None else ""
                response = f"Takeoff command added to mission{coord_desc}, Alt={altitude_msg}{heading_msg} (Item {item.seq + 1})"
                
                # Include auto-fix notifications if any
                if validation_msg:
                    response += f". {validation_msg}"
                
                response += self._get_mission_state_summary()
            
        except Exception as e:
            response = f"Error: {str(e)}"

        return response