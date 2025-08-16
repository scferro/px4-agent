"""
Output formatting and display utilities for PX4 Agent
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

from config import get_settings

class OutputFormatter:
    """Handles formatted output for different modes and verbosity levels"""
    
    def __init__(self, verbose: bool = False):
        self.settings = get_settings()
        self.verbose = verbose
        self.console = Console(
            color_system="auto" if self.settings.output.use_colors else None,
            force_terminal=True
        )
    
    def print_system_status(self, status: Dict[str, Any]):
        """Print system status information"""
        title = "🛸 PX4 Agent System Status"
        
        # Create status table
        table = Table(title="System Components")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        # Ollama status
        ollama_status = "✅ Ready" if status["ollama_ready"] else "❌ Issues"
        ollama_details = "Connected" if status["ollama_ready"] else "; ".join(status["ollama_issues"])
        table.add_row("Ollama", ollama_status, ollama_details)
        
        # Agent status
        agent_status = "✅ Ready" if status["agent_initialized"] else "❌ Not initialized"
        table.add_row("Agent", agent_status, f"{status['tools_loaded']} tools loaded")
        
        # Mission status  
        has_current_mission = status.get("current_mission_exists", False)
        mission_details = "Current mission available" if has_current_mission else "No current mission"
        table.add_row("Missions", "📋 Current", mission_details)
        
        # Current mode
        current_mode = status.get("current_mode", "None")
        table.add_row("Mode", f"⚡ {current_mode}", "Current operation mode")
        
        panel = Panel(table, title=title, border_style="blue")
        self.console.print(panel)
        
        # Show system info in verbose mode
        if self.verbose:
            self._print_system_info(status["system_info"])
    
    def _print_system_info(self, system_info: Dict[str, Any]):
        """Print detailed system information"""
        self.console.print("\n[bold cyan]Detailed System Information[/bold cyan]")
        
        # Model info
        self.console.print(f"Model: {system_info['model_name']}")
        self.console.print(f"Base URL: {system_info['base_url']}")
        self.console.print(f"Temperature: {system_info['temperature']}")
        
        # Available models
        if system_info["available_models"]:
            self.console.print("Available models:", ", ".join(system_info["available_models"]))
    
    def print_command_result(self, result: Dict[str, Any]):
        """Print result from command mode"""
        if result["success"]:
            title = "🎯 Command Executed"
            style = "green"
        else:
            title = "❌ Command Failed"
            style = "red"
        
        # Main result
        panel = Panel(
            result["output"],
            title=title,
            border_style=style
        )
        self.console.print(panel)
        
        # Show intermediate steps in verbose mode
        if self.verbose and result.get("intermediate_steps"):
            self._print_intermediate_steps(result["intermediate_steps"])
        
        # Show error details if failed
        if not result["success"] and result.get("error"):
            self.console.print(f"\n[red]Error Details:[/red] {result['error']}")
    
    def print_mission_result(self, result: Dict[str, Any]):
        """Print result from mission mode"""
        mode_name = "New Mission" if result["mode"] == "mission_new" else "Mission Update"
        
        if result["success"]:
            title = f"🚁 {mode_name} Created"
            style = "green"
        else:
            title = f"❌ {mode_name} Failed"
            style = "red"
        
        # Main result
        panel = Panel(
            result["output"],
            title=title,
            border_style=style
        )
        self.console.print(panel)
        
        # Show mission summary
        if result["success"] and result.get("mission_state"):
            self._print_mission_summary(result["mission_state"])
        
        # Show intermediate steps in verbose mode
        if self.verbose and result.get("intermediate_steps"):
            self._print_intermediate_steps(result["intermediate_steps"])
        
        # Show error details if failed
        if not result["success"] and result.get("error"):
            self.console.print(f"\n[red]Error Details:[/red] {result['error']}")
    
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
        from core.constants import COMMAND_EMOJIS, DISPLAY_CONFIG
        
        # Command type mapping
        from core.constants import MAV_CMD
        command_type_map = {
            MAV_CMD.NAV_TAKEOFF: 'takeoff',
            MAV_CMD.NAV_WAYPOINT: 'waypoint',
            MAV_CMD.NAV_LOITER_UNLIM: 'loiter',
            MAV_CMD.NAV_LOITER_TIME: 'loiter',
            MAV_CMD.NAV_RETURN_TO_LAUNCH: 'rtl'
        }
        
        # Create table
        table = Table(title="DETAILED MISSION DISPLAY")
        table.add_column("Item", style="cyan", width=6)
        table.add_column("Command", style="green", width=20)
        table.add_column("Parameters", style="blue")
        
        for item in items:
            command_type = command_type_map.get(item['command'], 'unknown')
            command_name = self._get_command_display_name(item['command']).replace('🚀 ', '').replace('📍 ', '').replace('🔄 ', '').replace('🏠 ', '')
            
            emoji = COMMAND_EMOJIS.get(command_type, '❓')
            item_num = f"{item['seq'] + 1}"
            command_display = f"{emoji} {command_name.upper()}"
            
            # Build parameters display - same logic as before
            params_display = ""
            
            if command_type == 'rtl':
                params_display = "(No parameters available)"
            else:
                sections = []
                
                # Location Parameters - show if any location info specified
                if (item.get('latitude') is not None or item.get('longitude') is not None or 
                    item.get('mgrs') is not None or item.get('distance') is not None or item.get('heading') is not None):
                    
                    # GPS Coordinates section
                    if (item.get('latitude') is not None or item.get('longitude') is not None or item.get('mgrs') is not None):
                        gps_params = []
                        if item.get('latitude') is not None:
                            gps_params.append(f"latitude: {item['latitude']}")
                        if item.get('longitude') is not None:
                            gps_params.append(f"longitude: {item['longitude']}")
                        if item.get('mgrs') is not None:
                            gps_params.append(f"mgrs: {item['mgrs']}")
                        sections.append(f"GPS Coordinates:\n  " + "\n  ".join(gps_params))
                    
                    # Relative Positioning section
                    if (item.get('distance') is not None or item.get('heading') is not None):
                        rel_params = []
                        if item.get('distance') is not None:
                            rel_params.append(f"distance: {item['distance']}")
                        if item.get('heading') is not None:
                            rel_params.append(f"heading: {item['heading']}")
                        # Show units/reference only if distance/heading specified
                        if item.get('distance') is not None:
                            rel_params.append(f"distance_units: {item.get('distance_units') or 'unspecified'}")
                            rel_params.append(f"distance_reference_frame: {item.get('distance_reference_frame') or 'unspecified'}")
                        sections.append(f"Relative Positioning:\n  " + "\n  ".join(rel_params))
                
                # Orbit Parameters - show if radius specified
                if command_type == 'loiter' and item.get('radius') is not None:
                    orbit_params = [
                        f"radius: {item['radius']}",
                        f"radius_units: {item.get('radius_units') or 'unspecified'}"
                    ]
                    sections.append(f"Orbit Parameters:\n  " + "\n  ".join(orbit_params))
                
                # Altitude Parameters - show if altitude specified
                if item.get('altitude') is not None:
                    alt_params = [
                        f"altitude: {item['altitude']}",
                        f"altitude_units: {item.get('altitude_units') or 'unspecified'}"
                    ]
                    sections.append(f"Altitude Parameters:\n  " + "\n  ".join(alt_params))
                
                if sections:
                    params_display = "\n\n".join(sections)
                else:
                    params_display = "(No parameters specified)"
            
            table.add_row(item_num, command_display, params_display)
        
        return table
    
    def _print_intermediate_steps(self, steps: List[Any]):
        """Print intermediate steps for verbose mode"""
        if not steps:
            return
        
        self.console.print("\n[bold cyan]Execution Steps:[/bold cyan]")
        
        for i, step in enumerate(steps, 1):
            if hasattr(step, '__len__') and len(step) >= 2:
                action, result = step[0], step[1]
                
                # Create tree for step
                tree = Tree(f"[bold]Step {i}[/bold]")
                
                # Add action
                if hasattr(action, 'tool') and hasattr(action, 'tool_input'):
                    tool_branch = tree.add(f"[green]Tool:[/green] {action.tool}")
                    if action.tool_input:
                        tool_branch.add(f"[blue]Input:[/blue] {json.dumps(action.tool_input, indent=2)}")
                
                # Add result
                if result:
                    tree.add(f"[yellow]Result:[/yellow] {str(result)}")
                
                self.console.print(tree)
    
    def _get_command_display_name(self, command_id: int) -> str:
        """Get display name for command"""
        from core.constants import MAV_CMD
        
        command_map = {
            MAV_CMD.NAV_WAYPOINT: "🎯 Waypoint",
            MAV_CMD.NAV_TAKEOFF: "🚀 Takeoff",
            MAV_CMD.NAV_LAND: "🛬 Landing", 
            MAV_CMD.NAV_RETURN_TO_LAUNCH: "🏠 RTL",
            MAV_CMD.NAV_LOITER_TIME: "🔄 Loiter (Timed)",
            MAV_CMD.NAV_LOITER_UNLIM: "🔄 Loiter (Unlimited)",
            MAV_CMD.DO_CHANGE_SPEED: "⚡ Speed Change"
        }
        
        return command_map.get(command_id, f"Command {command_id}")
    
    def print_mission_list(self, missions: List[Dict[str, Any]]):
        """Print list of missions"""
        if not missions:
            self.console.print("[yellow]No current mission available[/yellow]")
            return
        
        # For single current mission approach, just show current mission details
        mission = missions[0] if missions else None
        if not mission:
            self.console.print("[yellow]No current mission available[/yellow]")
            return
            
        table = Table(title="Current Mission")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        item_count = str(mission["total_items"])
        valid = "✅ Valid" if mission["valid"] else "❌ Invalid"
        created = datetime.fromisoformat(mission["created_at"]).strftime("%Y-%m-%d %H:%M")
        
        # Format command counts
        command_summary = []
        for cmd, count in mission["command_counts"].items():
            command_summary.append(f"{cmd}: {count}")
        commands = ", ".join(command_summary) if command_summary else "None"
        
        table.add_row("Items", item_count)
        table.add_row("Status", valid)
        table.add_row("Created", created)
        table.add_row("Commands", commands)
        
        self.console.print(table)
    
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
    
    def print_json(self, data: Dict[str, Any], title: str = "JSON Output"):
        """Print JSON data with syntax highlighting"""
        json_str = json.dumps(data, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        
        panel = Panel(
            syntax,
            title=title,
            border_style="blue"
        )
        self.console.print(panel)