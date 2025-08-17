"""
Move Mission Item Tool - Reposition mission item to different sequence position
"""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class MoveMissionItemInput(BaseModel):
    """Move/reposition specific mission item to a different position in the mission"""
    
    seq: int = Field(description="Current position of mission item to move (1=first item, 2=second item, etc.). Extract from user phrases like 'move the second waypoint' (seq=2), 'reposition item 3' (seq=3).")
    insert_at: int = Field(description="New position where item should be moved (1=first position, 2=second position, etc.). Extract from user phrases like 'move item 2 to position 5' (insert_at=5), 'put the waypoint at the beginning' (insert_at=1).")


class MoveMissionItemTool(PX4ToolBase):
    name: str = "move_mission_item"
    description: str = "Move/reposition specific mission item to a different position in the mission. Use when user wants to reorder mission items by moving one item to a new position. Use for commands like 'move the second waypoint to position 5', 'put item 3 at the beginning', 'reposition the takeoff to be first', 'move the last item to position 2'. All other items automatically shift to accommodate the move."
    args_schema: type = MoveMissionItemInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)
    
    def _run(self, seq: int, insert_at: int) -> str:
        try:
            mission = self.mission_manager.get_mission()
            if not mission or not mission.items:
                return "Error: No mission items to move"
            
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Convert 1-based indexing to 0-based
            zero_based_seq = seq - 1
            zero_based_insert_at = insert_at - 1
            
            # Validate source position
            if seq < 1 or zero_based_seq >= len(mission.items):
                return f"Error: Invalid source position {seq}. Mission has {len(mission.items)} items (1 to {len(mission.items)})"
            
            # Validate destination position (can be 1 to len+1 for append)
            if insert_at < 1 or insert_at > len(mission.items):
                return f"Error: Invalid destination position {insert_at}. Valid positions are 1 to {len(mission.items)}"
            
            # Check if moving to same position (no-op)
            if seq == insert_at:
                return f"Item {seq} is already at position {insert_at}. No change needed." + self._get_mission_state_summary()
            
            # Get item info for confirmation message
            item_to_move = mission.items[zero_based_seq]
            command_name = self._get_command_name(getattr(item_to_move, 'command_type', 'unknown'))
            
            # Remove item from current position
            moved_item = mission.items.pop(zero_based_seq)
            
            # Adjust insertion index if moving item forward (since we removed an item)
            if insert_at > seq:
                adjusted_insert_at = zero_based_insert_at - 1
            else:
                adjusted_insert_at = zero_based_insert_at
            
            # Insert at new position
            mission.items.insert(adjusted_insert_at, moved_item)
            
            # Resequence all items
            for i, item in enumerate(mission.items):
                item.seq = i
            
            # Validate mission after move
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
            
            # Build success response
            response = f"Moved mission item {seq} ({command_name}) to position {insert_at}. Mission reordered successfully."
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"