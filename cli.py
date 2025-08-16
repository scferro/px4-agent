"""
PX4 Agent Command Line Interface
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import PX4Agent
from core import OutputFormatter
from config import get_settings

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="PX4 Agent - Intelligent drone mission planning with LangChain and Granite 3.3 2B",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Command mode - single action
  px4-agent command "takeoff to 15 meters at coordinates 37.7749, -122.4194"
  
  # Mission mode - new mission  
  px4-agent mission new "Create a survey mission over Golden Gate Park at 50m altitude"
  
  # Mission mode - update existing mission
  px4-agent mission update "Add landing at home coordinates" --mission-file current_mission.json
  
  # Check system status
  px4-agent status
  
  # List available missions (if any cached)
  px4-agent list
        """
    )
    
    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output showing model reasoning and tool details"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="mode", help="Operation mode")
    
    # Command mode
    command_parser = subparsers.add_parser("command", help="Execute single command")
    command_parser.add_argument("input", help="Command to execute")
    
    # Mission mode
    mission_parser = subparsers.add_parser("mission", help="Mission planning mode")
    mission_subparsers = mission_parser.add_subparsers(dest="mission_type", help="Mission type")
    
    # New mission
    new_parser = mission_subparsers.add_parser("new", help="Create new mission (launches interactive chat)")
    new_parser.add_argument("input", nargs="?", help="Optional initial mission description")
    new_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    # Update mission
    update_parser = mission_subparsers.add_parser("update", help="Update existing mission (launches interactive chat)")
    update_parser.add_argument("input", nargs="?", help="Optional initial update description")
    update_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    # Status check
    subparsers.add_parser("status", help="Check system status")
    
    # List missions
    subparsers.add_parser("list", help="List available missions")
    
    return parser

def load_mission_file(file_path: str) -> Dict[str, Any]:
    """Load mission data from JSON file"""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Mission file not found: {file_path}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in mission file: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to load mission file: {str(e)}")

def handle_command_mode(agent: PX4Agent, formatter: OutputFormatter, args) -> int:
    """Handle command mode execution"""
    try:
        result = agent.command_mode(args.input)
        formatter.print_command_result(result)
        return 0 if result["success"] else 1
    except Exception as e:
        formatter.print_error("Command execution failed", str(e))
        return 1

def handle_mission_new(agent: PX4Agent, formatter: OutputFormatter, args) -> int:
    """Handle new mission mode with chat interface"""
    try:
        # Set verbose mode if requested
        verbose = getattr(args, 'verbose', False)
        if verbose:
            agent.verbose = True
        
        # Process initial request if provided
        if args.input:
            result = agent.mission_mode_new(args.input)
            formatter.print_mission_result(result)
            
            if not result["success"]:
                return 1
        else:
            # Create empty mission and show info
            agent.mission_manager.create_mission()
            formatter.print_info("Starting new mission. Enter your first request below.")
        
        # Launch chat interface
        return mission_chat(agent, formatter, is_new_mission=False)
        
    except Exception as e:
        formatter.print_error("Mission creation failed", str(e))
        return 1

def handle_mission_update(agent: PX4Agent, formatter: OutputFormatter, args) -> int:
    """Handle mission update mode with chat interface"""
    try:
        # Set verbose mode if requested
        verbose = getattr(args, 'verbose', False)
        if verbose:
            agent.verbose = True
        
        # Load current mission data from standard file
        mission_file = "current_mission.json"
        if not Path(mission_file).exists():
            formatter.print_error("No current mission found", "Please create a new mission first or ensure current_mission.json exists")
            return 1
            
        mission_data = load_mission_file(mission_file)
        
        # Process initial update if provided
        if args.input:
            result = agent.mission_mode_update(args.input, mission_data)
            formatter.print_mission_result(result)
            
            if not result["success"]:
                return 1
        else:
            formatter.print_info("Mission loaded. Enter your update requests below.")
        
        # Launch chat interface
        return mission_chat(agent, formatter, is_new_mission=False)
        
    except Exception as e:
        formatter.print_error("Mission update failed", str(e))
        return 1

def handle_status(agent: PX4Agent, formatter: OutputFormatter) -> int:
    """Handle status check"""
    try:
        status = agent.check_system_status()
        formatter.print_system_status(status)
        return 0 if status["ollama_ready"] and status["agent_initialized"] else 1
    except Exception as e:
        formatter.print_error("Status check failed", str(e))
        return 1

def handle_list_missions(agent: PX4Agent, formatter: OutputFormatter) -> int:
    """Handle mission listing"""
    try:
        missions = agent.list_missions()
        formatter.print_mission_list(missions)
        return 0
    except Exception as e:
        formatter.print_error("Failed to list missions", str(e))
        return 1

def mission_chat(agent: PX4Agent, formatter: OutputFormatter, is_new_mission: bool = True) -> int:
    """Interactive chat interface for mission building"""
    formatter.print_info("🚁 Mission Chat Mode - Interactive mission building")
    formatter.print_info("Commands: 'quit' to exit, 'status' for mission summary, 'show' to review mission")
    print()
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("Mission> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                formatter.print_info("Goodbye!")
                break
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                formatter.print_info("Goodbye!")
                break
            elif user_input.lower() in ['status', 'summary']:
                missions = agent.list_missions()
                formatter.print_mission_list(missions)
                continue
            elif user_input.lower() in ['show', 'review']:
                # Show mission for approval without interactive prompt
                mission = agent.mission_manager.get_mission()
                if mission and mission.items:
                    formatter.print_info(f"Current mission has {len(mission.items)} items:")
                    # Create a mock result for display
                    result = {
                        "success": True,
                        "mode": "mission_chat",
                        "input": user_input,
                        "output": f"Mission review: {len(mission.items)} items",
                        "mission_state": mission.to_dict()
                    }
                    formatter._print_mission_summary(result["mission_state"])
                else:
                    formatter.print_warning("Mission is empty")
                continue
            elif not user_input:
                continue
            
            # Process mission request
            result = agent.mission_mode_new(user_input)
            is_new_mission = False  # After first request, we're in continuation mode
            
            # Show result
            if result["success"]:
                # Show the agent's actual response (not just success)
                agent_response = result.get("output", "").strip()
                if agent_response:
                    print(f"🤖 Agent: {agent_response}")
                else:
                    print("✅ Request completed")
                
                # In verbose mode, show all details. In normal mode, just show mission summary.
                if formatter.verbose:
                    # Verbose: Show everything including tool calls, intermediate steps, etc.
                    if result.get("intermediate_steps"):
                        formatter._print_intermediate_steps(result["intermediate_steps"])
                
                # Always show mission summary (this is the key info user needs)
                if result.get("mission_state"):
                    print("\n📋 Updated Mission:")
                    formatter._print_mission_summary(result["mission_state"])
            else:
                formatter.print_error("Request failed", result.get("error", "Unknown error"))
            
            print()  # Add spacing
            
    except Exception as e:
        formatter.print_error("Chat session failed", str(e))
        return 1
    
    return 0

def main() -> int:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Load configuration if specified
    if args.config:
        try:
            from config import reload_settings
            reload_settings(args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1
    
    # Initialize components
    try:
        agent = PX4Agent(verbose=args.verbose)
        formatter = OutputFormatter(verbose=args.verbose)
    except Exception as e:
        print(f"Initialization failed: {e}", file=sys.stderr)
        return 1
    
    # Handle different modes
    if args.mode == "command":
        return handle_command_mode(agent, formatter, args)
    
    elif args.mode == "mission":
        if args.mission_type == "new":
            return handle_mission_new(agent, formatter, args)
        elif args.mission_type == "update":
            return handle_mission_update(agent, formatter, args)
        else:
            parser.print_help()
            return 1
    
    elif args.mode == "status":
        return handle_status(agent, formatter)
    
    elif args.mode == "list":
        return handle_list_missions(agent, formatter)
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())