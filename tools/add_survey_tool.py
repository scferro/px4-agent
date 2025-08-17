"""
Add Survey Tool - Create systematic survey patterns for area coverage
"""

from typing import Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .tools import PX4ToolBase


class SurveyInput(BaseModel):
    """Create survey pattern over specified area using center+radius OR corner points"""
    
    # ===== CENTER + RADIUS SURVEY =====
    # Center location (use same positioning options as waypoints)
    center_latitude: Optional[float] = Field(None, description="GPS latitude for survey center in decimal degrees. Use ONLY when center latitude is specified by the user.")
    center_longitude: Optional[float] = Field(None, description="GPS longitude for survey center in decimal degrees. Use ONLY when center longitude is specified by the user.")
    center_mgrs: Optional[str] = Field(None, description="MGRS coordinate for survey center. Use ONLY when user provides MGRS coordinates.")
    
    # Relative positioning for center - use for "survey 2 miles north of here"
    center_distance: Optional[float] = Field(None, description="Distance to survey center from reference point. Use with center_heading.")
    center_heading: Optional[str] = Field(None, description="Direction to survey center: 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'. Use with center_distance.")
    center_distance_units: Optional[str] = Field(None, description="Units for center distance: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    center_relative_reference_frame: Optional[str] = Field(None, description="Reference point for center distance: 'origin' (takeoff), 'current', 'last_waypoint'. If no location is specified, set to 'lasr_waypoint' and leave other fields blank.")
    
    # Survey area size (for center+radius mode)
    survey_radius: Optional[float] = Field(None, description="Radius of circular survey area. Use with survey_radius_units.")
    survey_radius_units: Optional[str] = Field(None, description="Units for survey radius: 'meters'/'m', 'feet'/'ft', 'miles'/'mi', 'kilometers'/'km'.")
    
    # ===== CORNER POINTS SURVEY =====
    # Corner points defining survey boundary (up to 4 corners for rectangular area)
    corner1_lat: Optional[float] = Field(None, description="Latitude of first corner point in decimal degrees.")
    corner1_lon: Optional[float] = Field(None, description="Longitude of first corner point in decimal degrees.")
    corner1_mgrs: Optional[str] = Field(None, description="MGRS coordinate for first corner point.")
    corner2_lat: Optional[float] = Field(None, description="Latitude of second corner point in decimal degrees.")
    corner2_lon: Optional[float] = Field(None, description="Longitude of second corner point in decimal degrees.")
    corner2_mgrs: Optional[str] = Field(None, description="MGRS coordinate for second corner point.")
    corner3_lat: Optional[float] = Field(None, description="Latitude of third corner point. Optional for triangular areas.")
    corner3_lon: Optional[float] = Field(None, description="Longitude of third corner point. Optional for triangular areas.")
    corner3_mgrs: Optional[str] = Field(None, description="MGRS coordinate for third corner point. Optional for triangular areas.")
    corner4_lat: Optional[float] = Field(None, description="Latitude of fourth corner point. Use for rectangular areas.")
    corner4_lon: Optional[float] = Field(None, description="Longitude of fourth corner point. Use for rectangular areas.")
    corner4_mgrs: Optional[str] = Field(None, description="MGRS coordinate for fourth corner point. Use for rectangular areas.")
    
    # ===== SURVEY PARAMETERS =====
    # Survey flight parameters
    survey_altitude: Optional[float] = Field(None, description="Flight altitude for the survey pattern.")
    survey_altitude_units: Optional[str] = Field(None, description="Units for survey altitude: 'meters'/'m' or 'feet'/'ft'.")
    
    # Insertion position
    insert_at: Optional[int] = Field(None, description="Position to insert survey in mission. Set to specific position number or omit to add at end.")


class AddSurveyTool(PX4ToolBase):
    name: str = "add_survey"
    description: str = "Create systematic survey pattern for area coverage. Two modes: CENTER+RADIUS (specify center point and radius) or CORNER POINTS (define polygon boundary). Use for survey commands like 'survey 1km radius around this point' or 'survey the area bounded by these corners'. Specify Lat/Long OR MGRS OR distance/heading/reference. Do not mix location systems."
    args_schema: type = SurveyInput
    
    def __init__(self, mission_manager):
        super().__init__(mission_manager)

    def _run(self, center_latitude: Optional[float] = None, center_longitude: Optional[float] = None, center_mgrs: Optional[str] = None,
             center_distance: Optional[float] = None, center_heading: Optional[str] = None, center_distance_units: Optional[str] = None,
             center_relative_reference_frame: Optional[str] = None, survey_radius: Optional[float] = None, survey_radius_units: Optional[str] = None,
             corner1_lat: Optional[float] = None, corner1_lon: Optional[float] = None, corner1_mgrs: Optional[str] = None,
             corner2_lat: Optional[float] = None, corner2_lon: Optional[float] = None, corner2_mgrs: Optional[str] = None,
             corner3_lat: Optional[float] = None, corner3_lon: Optional[float] = None, corner3_mgrs: Optional[str] = None,
             corner4_lat: Optional[float] = None, corner4_lon: Optional[float] = None, corner4_mgrs: Optional[str] = None,
             survey_altitude: Optional[float] = None, survey_altitude_units: Optional[str] = None,
             insert_at: Optional[int] = None) -> str:
        try:
            # Save current mission state for potential rollback
            saved_state = self._save_mission_state()
            
            # Build corner points list from individual parameters
            corner_points = []
            if corner1_lat is not None or corner1_mgrs is not None:
                corner_points.append({'lat': corner1_lat, 'lon': corner1_lon, 'mgrs': corner1_mgrs})
            if corner2_lat is not None or corner2_mgrs is not None:
                corner_points.append({'lat': corner2_lat, 'lon': corner2_lon, 'mgrs': corner2_mgrs})
            if corner3_lat is not None or corner3_mgrs is not None:
                corner_points.append({'lat': corner3_lat, 'lon': corner3_lon, 'mgrs': corner3_mgrs})
            if corner4_lat is not None or corner4_mgrs is not None:
                corner_points.append({'lat': corner4_lat, 'lon': corner4_lon, 'mgrs': corner4_mgrs})
            
            # Determine survey mode
            if corner_points and len(corner_points) > 0:
                # Corner points mode
                survey_mode = "polygon"
                area_desc = f"polygon with {len(corner_points)} corners"
            elif center_latitude is not None or center_distance is not None:
                # Center-based mode
                if survey_radius is not None:
                    survey_mode = "circular"
                    area_desc = f"circular area (radius: {survey_radius} {survey_radius_units or 'meters'})"
                else:
                    return "Planning Error: Survey area size not specified. Provide radius for center-based survey" + self._get_mission_state_summary()
            else:
                return "Planning Error: Survey area not defined. Provide center coordinates OR corner points" + self._get_mission_state_summary()
            
            # Build coordinate description for center (if applicable)
            if survey_mode != "polygon":
                center_desc = self._build_coordinate_description(center_latitude, center_longitude, center_mgrs, 
                                                               center_distance, center_heading, center_distance_units, 
                                                               center_relative_reference_frame)
            else:
                center_desc = "defined by corner points"
            
            # Set defaults
            altitude = survey_altitude or 100.0
            altitude_units = survey_altitude_units or "meters"
            
            # Create a survey mission item
            item = self.mission_manager.add_survey(
                mode=survey_mode,
                center_lat=center_latitude or 0.0,
                center_lon=center_longitude or 0.0,
                radius=survey_radius or 0.0,
                corners=corner_points,
                altitude=altitude,
                radius_units=survey_radius_units,
                altitude_units=altitude_units,
                insert_at=insert_at,
                center_latitude=center_latitude,
                center_longitude=center_longitude,
                survey_radius=survey_radius,
                survey_altitude=survey_altitude,
                center_mgrs=center_mgrs,
                center_distance=center_distance,
                center_heading=center_heading,
                center_distance_units=center_distance_units,
                center_relative_reference_frame=center_relative_reference_frame
            )
            
            # Validate mission after adding survey
            is_valid, error_msg = self._validate_mission_after_action()
            if not is_valid:
                # Rollback the action
                self._restore_mission_state(saved_state)
                return f"Planning Error: {error_msg}" + self._get_mission_state_summary()
            
            # Build response with preserved units
            response = f"Survey pattern created for {area_desc} at {center_desc}, Alt={altitude} {altitude_units} (Item {item.seq + 1})"
            response += self._get_mission_state_summary()
            return response
            
        except Exception as e:
            response = f"Error: {str(e)}"
            
        return response