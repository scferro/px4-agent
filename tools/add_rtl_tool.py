"""
Add RTL Tool - Return to launch command
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase
from config.settings import get_agent_settings

# Load agent settings for Field descriptions
_agent_settings = get_agent_settings()


class RTLInput(BaseModel):
    """Return to launch - automatically fly back to takeoff point and land"""
    
    # Optional altitude specification
    altitude: Optional[float] = Field(None, description=f"Landing altitude for RTL. Specify only if user mentions specific landing height. Default = {_agent_settings['rtl_default_altitude']} {_agent_settings['rtl_altitude_units']}")
    altitude_units: Optional[str] = Field(None, description="Units for landing altitude: 'meters'/'m' or 'feet'/'ft'.")


class AddRTLTool(PX4ToolBase):
    name: str = "add_rtl"
    description: str = "Add return to launch command to automatically fly back to takeoff point and land. Always inserted as the LAST mission item. Use when the drone should return home, land, or come back."
    args_schema: type = RTLInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, altitude: Optional[float] = None, altitude_units: Optional[str] = None) -> str:
        # Create response
        response = ""

        # Populate response
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            item = self.mission_manager.add_return_to_launch(
                altitude=altitude,
                altitude_units=altitude_units
            )
            
            # Validate mission after adding RTL
            is_valid, validation_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {validation_msg}" + self._get_mission_state_summary()
            else:
                altitude_msg = f" at {altitude} {altitude_units}" if altitude is not None else ""
                response = f"Return to Launch command added to mission{altitude_msg} (Item {item.seq + 1})"
                
                # Include auto-fix notifications if any
                if validation_msg:
                    response += f". {validation_msg}"
                
                response += self._get_mission_state_summary()
            
        except Exception as e:
            response = f"Error: {str(e)}"

        return response