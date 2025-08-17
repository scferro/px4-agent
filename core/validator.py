"""
PX4 Mission Validation
Handles mission validation logic and safety checks
"""

from typing import List, Tuple, Optional
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
        
        # NEW: Add missing commands if enabled
        if self.settings.agent.auto_add_missing_takeoff:
            takeoff_fixes = self._ensure_takeoff_exists(mission)
            fixes.extend(takeoff_fixes)
        
        if self.settings.agent.auto_add_missing_rtl:
            rtl_fixes = self._ensure_rtl_exists(mission)
            fixes.extend(rtl_fixes)
        
        # NEW: Complete missing parameters
        if self.settings.agent.auto_complete_parameters:
            param_fixes = self._complete_missing_parameters(mission)
            fixes.extend(param_fixes)
        
        # Check for multiple takeoffs/RTLs (after auto-addition)
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
    
    def _ensure_takeoff_exists(self, mission: Mission) -> List[str]:
        """Add takeoff command if missing"""
        fixes = []
        has_takeoff = any(getattr(item, 'command_type', None) == 'takeoff' for item in mission.items)
        
        if not has_takeoff:
            takeoff = MissionItem(
                seq=0,
                command_type='takeoff',
                altitude=self.settings.agent.takeoff_default_altitude,
                altitude_units=self.settings.agent.takeoff_altitude_units,
                latitude=self.settings.agent.takeoff_default_latitude,
                longitude=self.settings.agent.takeoff_default_longitude
            )
            mission.items.insert(0, takeoff)
            self._resequence_items(mission)
            fixes.append(f"Auto-added takeoff: {takeoff.altitude} {takeoff.altitude_units}")
        
        return fixes

    def _ensure_rtl_exists(self, mission: Mission) -> List[str]:
        """Add RTL command if missing"""
        fixes = []
        has_rtl = any(getattr(item, 'command_type', None) == 'rtl' for item in mission.items)
        
        if not has_rtl:
            # Use takeoff altitude if configured and available
            rtl_altitude = (self._get_takeoff_altitude(mission) 
                           if self.settings.agent.rtl_use_takeoff_altitude 
                           else self.settings.agent.rtl_default_altitude)
            
            rtl = MissionItem(
                seq=len(mission.items),
                command_type='rtl',
                altitude=rtl_altitude,
                altitude_units=self.settings.agent.rtl_altitude_units
            )
            mission.items.append(rtl)
            fixes.append(f"Auto-added RTL: {rtl.altitude} {rtl.altitude_units}")
        
        return fixes

    def _complete_missing_parameters(self, mission: Mission) -> List[str]:
        """Complete missing parameters using command-specific defaults and smart strategies"""
        fixes = []
        
        for i, item in enumerate(mission.items):
            command_type = getattr(item, 'command_type', None)
            if not command_type:
                continue
            
            # Complete altitude for all navigation commands
            if hasattr(item, 'altitude'):
                altitude_fixes = self._complete_altitude(item, command_type, mission, i)
                fixes.extend(altitude_fixes)
            
            # Complete altitude_units
            if hasattr(item, 'altitude_units') and item.altitude_units is None:
                item.altitude_units = getattr(self.settings.agent, f"{command_type}_altitude_units")
                fixes.append(f"Set altitude units: {item.altitude_units}")
            
            # Complete radius for loiter/survey
            if command_type in ['loiter', 'survey'] and hasattr(item, 'radius'):
                radius_fixes = self._complete_radius(item, command_type)
                fixes.extend(radius_fixes)
            
            # Complete radius_units for loiter/survey
            if command_type in ['loiter', 'survey'] and hasattr(item, 'radius_units') and item.radius_units is None:
                item.radius_units = getattr(self.settings.agent, f"{command_type}_radius_units")
                fixes.append(f"Set radius units: {item.radius_units}")
            
            # Complete coordinates for loiter/survey if missing
            if command_type in ['loiter', 'survey']:
                coord_fixes = self._complete_coordinates(item, command_type, mission, i)
                fixes.extend(coord_fixes)
            
            # Complete distance_units for relative positioning
            if hasattr(item, 'distance_units') and item.distance_units is None and hasattr(item, 'distance') and item.distance is not None:
                item.distance_units = self.settings.agent.default_distance_units
                fixes.append(f"Set distance units: {item.distance_units}")
            
            # Complete search parameters if not specified
            if hasattr(item, 'search_target') and item.search_target is None:
                item.search_target = self.settings.agent.default_search_target
            
            if hasattr(item, 'detection_behavior') and item.detection_behavior is None and item.search_target:
                item.detection_behavior = self.settings.agent.default_detection_behavior
                fixes.append(f"Set detection behavior: {item.detection_behavior}")
        
        return fixes

    def _complete_altitude(self, item: MissionItem, command_type: str, mission: Mission, index: int) -> List[str]:
        """Complete altitude with smart defaulting per command type"""
        fixes = []
        
        # Get configured min/max for this command type
        min_alt = getattr(self.settings.agent, f"{command_type}_min_altitude")
        max_alt = getattr(self.settings.agent, f"{command_type}_max_altitude")
        
        # Apply global constraints
        min_alt = max(min_alt, self.settings.agent.global_min_altitude)
        max_alt = min(max_alt, self.settings.agent.global_max_altitude)
        
        if item.altitude is None:
            # Smart defaulting based on command type and configuration
            if command_type == "waypoint" and self.settings.agent.waypoint_use_previous_altitude:
                prev_alt = self._get_previous_altitude(mission, index)
                if prev_alt:
                    item.altitude = prev_alt
                    fixes.append(f"Set altitude from previous item: {item.altitude} meters")
                else:
                    item.altitude = self.settings.agent.waypoint_default_altitude
                    fixes.append(f"Set default altitude: {item.altitude} meters")
            
            elif command_type == "loiter" and self.settings.agent.loiter_use_previous_altitude:
                prev_alt = self._get_previous_altitude(mission, index)
                if prev_alt:
                    item.altitude = prev_alt
                    fixes.append(f"Set loiter altitude from previous item: {item.altitude} meters")
                else:
                    item.altitude = self.settings.agent.loiter_default_altitude
                    fixes.append(f"Set default loiter altitude: {item.altitude} meters")
            
            elif command_type == "survey" and self.settings.agent.survey_use_previous_altitude:
                prev_alt = self._get_previous_altitude(mission, index)
                if prev_alt:
                    item.altitude = prev_alt
                    fixes.append(f"Set survey altitude from previous item: {item.altitude} meters")
                else:
                    item.altitude = self.settings.agent.survey_default_altitude
                    fixes.append(f"Set default survey altitude: {item.altitude} meters")
            
            elif command_type == "rtl" and self.settings.agent.rtl_use_takeoff_altitude:
                takeoff_alt = self._get_takeoff_altitude(mission)
                if takeoff_alt:
                    item.altitude = takeoff_alt
                    fixes.append(f"Set RTL altitude from takeoff: {item.altitude} meters")
                else:
                    item.altitude = self.settings.agent.rtl_default_altitude
                    fixes.append(f"Set default RTL altitude: {item.altitude} meters")
            
            else:
                # Use command-specific default
                item.altitude = getattr(self.settings.agent, f"{command_type}_default_altitude")
                fixes.append(f"Set default {command_type} altitude: {item.altitude} meters")
        
        # Clamp to min/max constraints
        if item.altitude < min_alt:
            item.altitude = min_alt
            fixes.append(f"Clamped {command_type} altitude to minimum: {item.altitude} meters")
        elif item.altitude > max_alt:
            item.altitude = max_alt
            fixes.append(f"Clamped {command_type} altitude to maximum: {item.altitude} meters")
        
        return fixes

    def _complete_radius(self, item: MissionItem, command_type: str) -> List[str]:
        """Complete radius with defaults and clamping"""
        fixes = []
        
        # Get configured min/max for this command type
        min_radius = getattr(self.settings.agent, f"{command_type}_min_radius")
        max_radius = getattr(self.settings.agent, f"{command_type}_max_radius")
        
        # Apply global constraints
        min_radius = max(min_radius, self.settings.agent.global_min_radius)
        max_radius = min(max_radius, self.settings.agent.global_max_radius)
        
        if item.radius is None:
            item.radius = getattr(self.settings.agent, f"{command_type}_default_radius")
            fixes.append(f"Set default {command_type} radius: {item.radius} meters")
        
        # Clamp to min/max
        if item.radius < min_radius:
            item.radius = min_radius
            fixes.append(f"Clamped {command_type} radius to minimum: {item.radius} meters")
        elif item.radius > max_radius:
            item.radius = max_radius
            fixes.append(f"Clamped {command_type} radius to maximum: {item.radius} meters")
        
        return fixes

    def _complete_coordinates(self, item: MissionItem, command_type: str, mission: Mission, index: int) -> List[str]:
        """Complete missing coordinates for loiter/survey using smart defaults"""
        fixes = []
        
        # Check if coordinates are missing
        has_lat_lon = (hasattr(item, 'latitude') and item.latitude is not None and 
                       hasattr(item, 'longitude') and item.longitude is not None)
        has_mgrs = hasattr(item, 'mgrs') and item.mgrs is not None
        has_relative = (hasattr(item, 'distance') and item.distance is not None and
                       hasattr(item, 'heading') and item.heading is not None)
        
        if not (has_lat_lon or has_mgrs or has_relative):
            # Use smart location defaulting if configured
            use_last_waypoint = getattr(self.settings.agent, f"{command_type}_use_last_waypoint_location", False)
            
            if use_last_waypoint:
                last_coords = self._get_last_waypoint_coordinates(mission, index)
                if last_coords:
                    item.latitude, item.longitude = last_coords
                    fixes.append(f"Set {command_type} location from last waypoint: {item.latitude:.6f}, {item.longitude:.6f}")
                else:
                    # Fallback to defaults
                    item.latitude = getattr(self.settings.agent, f"{command_type}_default_latitude")
                    item.longitude = getattr(self.settings.agent, f"{command_type}_default_longitude")
                    fixes.append(f"Set default {command_type} location: {item.latitude}, {item.longitude}")
            else:
                # Use configured defaults
                item.latitude = getattr(self.settings.agent, f"{command_type}_default_latitude")
                item.longitude = getattr(self.settings.agent, f"{command_type}_default_longitude")
                fixes.append(f"Set default {command_type} location: {item.latitude}, {item.longitude}")
        
        return fixes

    def _get_previous_altitude(self, mission: Mission, current_index: int) -> Optional[float]:
        """Find altitude from previous navigation command"""
        for i in range(current_index - 1, -1, -1):
            prev_item = mission.items[i]
            if (hasattr(prev_item, 'altitude') and prev_item.altitude is not None and
                getattr(prev_item, 'command_type', None) in ['waypoint', 'takeoff', 'loiter', 'survey']):
                return prev_item.altitude
        return None

    def _get_takeoff_altitude(self, mission: Mission) -> Optional[float]:
        """Find altitude from takeoff command"""
        for item in mission.items:
            if (getattr(item, 'command_type', None) == 'takeoff' and 
                hasattr(item, 'altitude') and item.altitude is not None):
                return item.altitude
        return None

    def _get_last_waypoint_coordinates(self, mission: Mission, current_index: int) -> Optional[Tuple[float, float]]:
        """Find coordinates from last waypoint or navigation command"""
        for i in range(current_index - 1, -1, -1):
            prev_item = mission.items[i]
            if (getattr(prev_item, 'command_type', None) in ['waypoint', 'takeoff', 'loiter', 'survey'] and
                hasattr(prev_item, 'latitude') and prev_item.latitude is not None and
                hasattr(prev_item, 'longitude') and prev_item.longitude is not None):
                return (prev_item.latitude, prev_item.longitude)
        return None

    def _resequence_items(self, mission: Mission):
        """Update sequence numbers after insertion/modification"""
        for i, item in enumerate(mission.items):
            item.seq = i