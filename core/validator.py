"""
PX4 Mission Validation
Handles mission validation logic and safety checks
"""

from typing import List, Tuple
from config.settings import PX4AgentSettings
from core.mission import Mission, MissionItem


class MissionValidator:
    """Handles mission validation logic and safety checks"""
    
    def __init__(self, settings: PX4AgentSettings):
        self.settings = settings
    
    def validate_mission(self, mission: Mission, mode: str) -> Tuple[bool, List[str], List[str]]:
        """Validate mission for safety and completeness"""
        errors = []
        fixes_applied = []
        
        if len(mission.items) == 0:
            errors.append("Mission has no items")
            return False, errors, fixes_applied
        
        if len(mission.items) > self.settings.agent.max_mission_items:
            errors.append(f"Mission exceeds maximum {self.settings.agent.max_mission_items} items")
        
        # Different validation rules based on mode
        if mode == "mission":
            # Validate mission mode rules (with auto-fix integration)
            mode_errors, mode_fixes = self._validate_mission_mode_rules(mission)
            errors.extend(mode_errors)
            fixes_applied.extend(mode_fixes)
            
        elif mode == "command":            
            # Ensure the "mission" length is 1 or less
            mission_item_count = len(mission.items)
            if mission_item_count > 1:
                errors.append(f"Mission has {mission_item_count} commands - only one is allowed")
        
        # Validate individual items (applies to both modes)
        for i, item in enumerate(mission.items):
            item_errors = self.validate_mission_item(item, i)
            errors.extend(item_errors)
        
        return len(errors) == 0, errors, fixes_applied
    
    def validate_mission_item(self, item: MissionItem, index: int) -> List[str]:
        """Validate individual mission item"""
        errors = []
        
        # Check navigation commands for altitude limits
        nav_command_types = ['waypoint', 'takeoff', 'loiter', 'rtl']
        
        command_type = getattr(item, 'command_type', None)
        if command_type in nav_command_types:
            # Check altitude from the field where it's actually stored
            altitude_value = getattr(item, 'altitude', None)
            if altitude_value is not None and altitude_value <= 0:
                errors.append(f"Item {index}: Altitude must be positive")
                        
        return errors
    
    def _validate_mission_mode_rules(self, mission: Mission) -> Tuple[List[str], List[str]]:
        """Validate mission mode specific rules with optional auto-fix"""
        errors = []
        fixes = []
        
        has_takeoff = any(getattr(item, 'command_type', None) == 'takeoff' for item in mission.items)
        has_rtl = any(getattr(item, 'command_type', None) == 'rtl' for item in mission.items)
        
        # Check takeoff positioning - auto-fix or error
        if self.settings.agent.takeoff_must_be_first and has_takeoff:
            if getattr(mission.items[0], 'command_type', None) != 'takeoff':
                if self.settings.agent.auto_fix_positioning:
                    self._move_takeoff_to_start(mission)
                    fixes.append("Moved takeoff command to the beginning of mission")
                else:
                    errors.append("Takeoff command is not the first item - takeoff must be the initial command")

        # Check RTL positioning - auto-fix or error
        if self.settings.agent.rtl_must_be_last and has_rtl:
            if getattr(mission.items[-1], 'command_type', None) != 'rtl':
                if self.settings.agent.auto_fix_positioning:
                    self._move_rtl_to_end(mission)
                    fixes.append("Moved RTL command to the end of mission")
                else:
                    errors.append("RTL command is not the last item - RTL must be at the last command")
        
        # Check for multiple takeoffs/RTLs
        takeoff_count = sum(1 for item in mission.items if getattr(item, 'command_type', None) == 'takeoff')
        rtl_count = sum(1 for item in mission.items if getattr(item, 'command_type', None) == 'rtl')
        
        if self.settings.agent.single_takeoff_only and takeoff_count > 1:
            errors.append(f"Mission has {takeoff_count} takeoff commands - only one is allowed")
        
        if self.settings.agent.single_rtl_only and rtl_count > 1:
            errors.append(f"Mission has {rtl_count} RTL commands - only one is allowed")
        
        return errors, fixes
    
    def _move_takeoff_to_start(self, mission: Mission):
        """Move takeoff items to the beginning of mission"""
        takeoff_items = []
        other_items = []
        
        for item in mission.items:
            if getattr(item, 'command_type', None) == 'takeoff':
                takeoff_items.append(item)
            else:
                other_items.append(item)
        
        # Use mission's built-in methods for clean reordering
        mission.clear_items()
        
        # Add back in correct order: takeoffs first, then others
        for item in takeoff_items + other_items:
            mission.add_item(item)
    
    def _move_rtl_to_end(self, mission: Mission):
        """Move RTL items to the end of mission"""
        rtl_items = []
        other_items = []
        
        for item in mission.items:
            if getattr(item, 'command_type', None) == 'rtl':
                rtl_items.append(item)
            else:
                other_items.append(item)
        
        # Use mission's built-in methods for clean reordering
        mission.clear_items()
        
        # Add back in correct order: others first, then RTLs
        for item in other_items + rtl_items:
            mission.add_item(item)