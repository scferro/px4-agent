"""
Add AI Search Tool - Enable AI-powered target detection and search
"""

from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class AISearchInput(BaseModel):
    """Enable AI-powered target detection and search capabilities"""
    
    # AI Search Parameters
    status: Optional[str] = Field("enabled", description="AI search status: 'enabled' or 'disabled'")
    target: Optional[str] = Field(None, description="Target description for AI to search for")
    behavior: Optional[str] = Field("tag_and_continue", description="Search behavior: 'tag_and_continue' (mark targets and continue mission) or 'detect_and_monitor' (abort mission and circle detected target)")
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert AI search in mission. Set to specific position number or omit to add at end.")


class AddAISearchTool(PX4ToolBase):
    name: str = "add_ai_search"
    description: str = "Add AI-powered target detection and search capabilities to mission. Use when user wants AI to search for specific targets using image recognition. Enable search and set a target BEFORE the mission item where the user want to perform the search e.g. before loiter/survey/waypoint."
    args_schema: type = AISearchInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, status: Optional[str] = "enabled", target: Optional[str] = None, 
             behavior: Optional[str] = "tag_and_continue", insert_at: Optional[int] = None) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Use mission manager method
            item = self.mission_manager.add_ai_search(
                status=status,
                target=target,
                behavior=behavior,
                insert_at=insert_at
            )
            
            # Validate mission after adding AI search
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
            
            # Build response message
            target_msg = f"Target: {target}" if target else "Target: not specified"
            response = f"AI Search added to mission: Status={status}, {target_msg}, Behavior={behavior} (Item {item.seq + 1})"
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"