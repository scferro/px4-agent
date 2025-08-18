"""
PX4 Agent Command Line Interface
Simplified to support only mission and command chat modes
"""

import sys
import argparse
from typing import Dict, Any
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import PX4Agent
from cli import OutputFormatter
from config import get_settings

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="PX4 Agent - Intelligent drone mission planning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mission mode - interactive mission building
  px4-agent mission
  
  # Command mode - single commands with reset
  px4-agent command
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
    
    # Mission mode - interactive chat
    mission_parser = subparsers.add_parser("mission", help="Mission planning chat mode")
    
    # Command mode - interactive chat with reset
    command_parser = subparsers.add_parser("command", help="Command chat mode (resets after each response)")
    
    return parser

def mission_chat(agent: PX4Agent, formatter: OutputFormatter) -> int:
    """Interactive chat interface for mission building"""
    formatter.print_info("🚁 Mission Chat Mode - Interactive mission building")
    formatter.print_info("Commands: 'quit' to exit, 'show' to review mission")
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
            elif user_input.lower() in ['show', 'review']:
                # Show mission for review
                mission = agent.mission_manager.get_mission()
                if mission and mission.items:
                    formatter.print_info(f"Current mission has {len(mission.items)} items:")
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
            result = agent.mission_mode(user_input)
            
            # Show result
            if result["success"]:
                agent_response = result.get("output", "").strip()
                if agent_response:
                    print(f"🤖 Agent: {agent_response}")
                else:
                    print("✅ Request completed")
                
                # Show mission summary
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

def command_chat(agent: PX4Agent, formatter: OutputFormatter) -> int:
    """Interactive chat interface for single commands with reset"""
    formatter.print_info("⚡ Command Chat Mode - Single commands with reset")
    formatter.print_info("Commands: 'quit' to exit")
    formatter.print_warning("Note: Mission and chat history reset after each command")
    print()
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("Command> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                formatter.print_info("Goodbye!")
                break
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                formatter.print_info("Goodbye!")
                break
            elif not user_input:
                continue
            
            # Process command request
            result = agent.command_mode(user_input)
            
            # Show result
            if result["success"]:
                agent_response = result.get("output", "").strip()
                if agent_response:
                    print(f"🤖 Agent: {agent_response}")
                else:
                    print("✅ Command completed")
                
                # Show mission summary if mission was created
                if result.get("mission_state"):
                    print("\n📋 Mission Created:")
                    formatter._print_mission_summary(result["mission_state"])
            else:
                formatter.print_error("Command failed", result.get("error", "Unknown error"))
            
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
    if args.mode == "mission":
        return mission_chat(agent, formatter)
    elif args.mode == "command":
        return command_chat(agent, formatter)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())