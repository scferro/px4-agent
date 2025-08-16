"""
Add RTL Tool - Return to launch command
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class RTLInput(BaseModel):
    """Return to launch - automatically fly back to takeoff point and land"""
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert this RTL in the mission (1=first item, 2=second item, etc.). Extract from phrases like 'insert RTL at position 5', 'add return to launch as last item'. Leave None to add at the end of the mission.")


class AddRTLTool(PX4ToolBase):
    name: str = "add_rtl"
    description: str = "Add return to launch command to automatically fly back to takeoff point and land. Use when user wants drone to return home, land, or come back. Typically the last command in a mission. Use for commands like 'return to launch', 'RTL', 'come back', 'land at home', 'return home'."
    args_schema: type = RTLInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, insert_at: Optional[int] = None) -> str:
        # Create response
        response = ""

        # Populate response
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            item = self.mission_manager.add_return_to_launch(insert_at=insert_at)
            
            # Validate mission after adding RTL
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
            else:
                response = f"Return to Launch command added to mission (Item {item.seq + 1})"
                response += self._get_mission_state_summary()
            
        except Exception as e:
            response = f"Error: {str(e)}"

        return response