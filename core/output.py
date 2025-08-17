"""
Output formatting and display utilities for PX4 Agent
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree


class OutputFormatter:
    """Handles formatted output for different modes and verbosity levels"""

    COMMAND_DISPLAY = {
        'takeoff': "🚀 Takeoff",
        'waypoint': "📍 Waypoint",
        'loiter': "🔄 Loiter",
        'rtl': "🏠 RTL",
        'survey': "🗺️ Survey",
        'ai_search': "🔍 AI Search"
    }
    
    UNSPECIFIED_MARKER = "unspecified"
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.console = Console(
            color_system="auto",  # Always use colors
            force_terminal=True
        )
    
    def _print_mission_summary(self, mission_state: Dict[str, Any]):
        """Print mission summary with exhaustive parameter display"""
        self.console.print(f"\n[bold cyan]Current Mission Summary[/bold cyan]")
        
        items = mission_state.get("items", [])
        if not items:
            self.console.print("[yellow]No mission items[/yellow]")
            return
        
        # Use exhaustive parameter display in table format
        table = self._get_exhaustive_parameter_display(items)
        self.console.print(table)
        
    def _get_exhaustive_parameter_display(self, items: List[Dict[str, Any]]):
        """Generate smart parameter display in table format - only show relevant parameters"""
        
        # Create table
        table = Table(title="DETAILED MISSION DISPLAY")
        table.add_column("Item", style="cyan", width=6)
        table.add_column("Command", style="green", width=20)
        table.add_column("Parameters", style="blue")
        
        for item in items:
            command_type = item.get('command_type', 'unknown')
            item_num = f"{item['seq'] + 1}"
            command_display = self.COMMAND_DISPLAY.get(command_type, f"Unknown {command_type}")
            
            # Build parameters display - same logic as before
            params_display = ""
            
            # All command types use the same parameter display logic
            sections = []
            
            # Location Parameters - show if any location info specified
            if (item.get('latitude') is not None or item.get('longitude') is not None or 
                item.get('mgrs') is not None or item.get('distance') is not None or item.get('relative_reference_frame') is not None):
                
                # Lat/Long
                if (item.get('latitude') is not None or item.get('longitude') is not None):
                        gps_params = []
                        if item.get('latitude') is not None:
                            gps_params.append(f"latitude: {item['latitude']}")
                        else:
                            gps_params.append(f"latitude: {self.UNSPECIFIED_MARKER}")
                        if item.get('longitude') is not None:
                            gps_params.append(f"longitude: {item['longitude']}")
                        else:
                            gps_params.append(f"longitude: {self.UNSPECIFIED_MARKER}")
                        sections.append(f"Lat/Long Coordinates:\n  " + "\n  ".join(gps_params))
                    
                # MGRS
                if (item.get('mgrs') is not None):
                        mgrs_params = []
                        mgrs_params.append(f"mgrs: {item['mgrs']}")
                        sections.append(f"MGRS Coordinates:\n  " + "\n  ".join(mgrs_params))
                    
                # Relative Positioning section
                if (item.get('distance') is not None or item.get('heading') is not None or item.get('relative_reference_frame') is not None):
                        rel_params = []
                        if item.get('distance') is not None:
                            rel_params.append(f"distance: {item['distance']}")
                        else:
                            rel_params.append(f"distance: {self.UNSPECIFIED_MARKER}")
                        if item.get('heading') is not None:
                            rel_params.append(f"heading: {item['heading']}")
                        else:
                            rel_params.append(f"heading: {self.UNSPECIFIED_MARKER}")
                        if item.get('relative_reference_frame') is not None:
                            rel_params.append(f"relative_reference_frame: {item.get('relative_reference_frame')}")
                        else:
                            rel_params.append(f"relative_reference_frame: {self.UNSPECIFIED_MARKER}")                            
                        sections.append(f"Relative Positioning:\n  " + "\n  ".join(rel_params))
            
            # Radius Parameters - show if radius specified (for loiter and survey)
            if (command_type == 'loiter' or command_type == 'survey') and item.get('radius') is not None:
                radius_params = [
                    f"radius: {item['radius']}",
                    f"radius_units: {item.get('radius_units') or self.UNSPECIFIED_MARKER}"
                ]
                if command_type == 'loiter':
                    sections.append(f"Orbit Parameters:\n  " + "\n  ".join(radius_params))
                elif command_type == 'survey':
                    sections.append(f"Survey Area:\n  " + "\n  ".join(radius_params))
            
            # Altitude Parameters - show if altitude specified
            if item.get('altitude') is not None:
                alt_params = [
                    f"altitude: {item['altitude']}",
                    f"altitude_units: {item.get('altitude_units') or self.UNSPECIFIED_MARKER}"
                ]
                sections.append(f"Altitude Parameters:\n  " + "\n  ".join(alt_params))
            
            # AI Search Parameters - show if any AI search parameters specified
            if command_type == 'ai_search' and (item.get('status') is not None or item.get('target') is not None or item.get('behavior') is not None):
                ai_params = [
                    f"status: {item.get('status') or self.UNSPECIFIED_MARKER}",
                    f"target: {item.get('target') or self.UNSPECIFIED_MARKER}",
                    f"behavior: {item.get('behavior') or self.UNSPECIFIED_MARKER}"
                ]
                sections.append(f"AI Search Parameters:\n  " + "\n  ".join(ai_params))
            
            if sections:
                params_display = "\n\n".join(sections)
            else:
                params_display = "(No parameters specified)"
            
            table.add_row(item_num, command_display, params_display)
        
        return table
    
    def print_error(self, message: str, details: Optional[str] = None):
        """Print error message"""
        panel = Panel(
            message,
            title="❌ Error",
            border_style="red"
        )
        self.console.print(panel)
        
        if details and self.verbose:
            self.console.print(f"\n[red]Details:[/red] {details}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"[yellow]⚠️  Warning:[/yellow] {message}")
    
    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"[blue]ℹ️  Info:[/blue] {message}")
    
    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"[green]✅ Success:[/green] {message}")
    
