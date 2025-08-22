"""
Measurement Parsing Utilities
Handles parsing of measurements with embedded units from LLM outputs
"""

import re
from typing import Union, Tuple, Optional


# Unit normalization patterns
UNIT_PATTERNS = {
    # Distance/Radius units (most common first for efficiency)
    r'(feet|ft|foot|\')$': 'feet',
    r'(meters?|m)$': 'meters', 
    r'(miles?|mi)$': 'miles',
    r'(kilometers?|km|kms?)$': 'kilometers',
    r'(nautical_?miles?|nm|nmi)$': 'nautical_miles',
}


def parse_measurement(value: Union[str, int, float, None], default_units: str = 'meters') -> Tuple[Optional[float], Optional[str]]:
    """
    Parse measurement string into (float_value, units) tuple.
    
    Args:
        value: Input value - can be number, string with units, or None
        default_units: Units to use when none specified
        
    Returns:
        Tuple of (parsed_number, normalized_units) or (None, None) if invalid
        
    Examples:
        "150.0 feet" -> (150.0, "feet")
        "500 ft" -> (500.0, "feet") 
        "100" -> (100.0, "meters")  # using default
        100.0 -> (100.0, "meters")  # using default
        "2 miles" -> (2.0, "miles")
        None -> (None, None)
        "invalid" -> (None, None)
    """
    if value is None:
        return (None, None)
    
    # Handle numeric inputs (int/float)
    if isinstance(value, (int, float)):
        return (float(value), default_units)
    
    # Handle string inputs
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return (None, None)
        
        # Try to extract number and optional units
        # Regex matches: number (int or float) + optional whitespace + optional units
        match = re.match(r'^(\d+(?:\.\d+)?)\s*(.*)$', value)
        if not match:
            return (None, None)
        
        try:
            number = float(match.group(1))
            unit_text = match.group(2).lower().strip()
            
            # If no unit text, use default
            if not unit_text:
                return (number, default_units)
            
            # Normalize units using patterns
            for pattern, normalized_unit in UNIT_PATTERNS.items():
                if re.search(pattern, unit_text):
                    return (number, normalized_unit)
            
            # If we found unit text but no pattern matched, still return the number with default units
            # This handles cases like "150 xyz" where xyz isn't a recognized unit
            return (number, default_units)
            
        except (ValueError, AttributeError):
            return (None, None)
    
    # For any other type, return None
    return (None, None)


def parse_altitude(value: Union[str, int, float, None]) -> Tuple[Optional[float], Optional[str]]:
    """Parse altitude measurement (defaults to meters)"""
    return parse_measurement(value, default_units='meters')


def parse_distance(value: Union[str, int, float, None]) -> Tuple[Optional[float], Optional[str]]:
    """Parse distance measurement (defaults to meters)"""
    return parse_measurement(value, default_units='meters')


def parse_radius(value: Union[str, int, float, None]) -> Tuple[Optional[float], Optional[str]]:
    """Parse radius measurement (defaults to meters)"""
    return parse_measurement(value, default_units='meters')


# Convenience function for validation in Pydantic models
def create_measurement_validator(default_units: str = 'meters'):
    """Create a Pydantic validator function for measurement fields"""
    def validator(v):
        if v is None:
            return None
        parsed_value, units = parse_measurement(v, default_units)
        if parsed_value is None:
            # Return original value to let Pydantic handle the validation error
            return v
        return (parsed_value, units)
    return validator