"""
PX4 Agent HTTP CLI Client
Simple CLI client that communicates with the Flask server via HTTP
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import requests
from typing import Dict, Any, Optional
import json

from cli import OutputFormatter


class PX4AgentClient:
    """HTTP client for PX4Agent server"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def check_server_status(self) -> bool:
        """Check if server is running and agent is initialized"""
        try:
            response = self.session.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                return status.get('agent_initialized', False)
            return False
        except requests.RequestException:
            return False
    
    def mission_mode_request(self, user_input: str) -> Dict[str, Any]:
        """Send mission mode request to server"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/mission",
                json={"user_input": user_input},
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return {
                    "success": False,
                    "mode": "mission",
                    "input": user_input,
                    "error": error_data.get("error", f"HTTP {response.status_code}"),
                    "output": error_data.get("output", f"Server error: {response.status_code}")
                }
                
        except requests.RequestException as e:
            return {
                "success": False,
                "mode": "mission",
                "input": user_input,
                "error": str(e),
                "output": f"Connection failed: {str(e)}"
            }
    
    def command_mode_request(self, user_input: str) -> Dict[str, Any]:
        """Send command mode request to server"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/command",
                json={"user_input": user_input},
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return {
                    "success": False,
                    "mode": "command",
                    "input": user_input,
                    "error": error_data.get("error", f"HTTP {response.status_code}"),
                    "output": error_data.get("output", f"Server error: {response.status_code}")
                }
                
        except requests.RequestException as e:
            return {
                "success": False,
                "mode": "command",
                "input": user_input,
                "error": str(e),
                "output": f"Connection failed: {str(e)}"
            }
    
    def show_mission(self) -> Dict[str, Any]:
        """Get mission for review (like CLI 'show' command)"""
        try:
            response = self.session.post(f"{self.base_url}/api/mission/show", timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "output": "Failed to retrieve mission"
                }
                
        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "output": f"Connection failed: {str(e)}"
            }


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="PX4 Agent HTTP Client - Intelligent drone mission planning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mission mode - interactive mission building
  px4-agent-client mission
  
  # Command mode - single commands with reset
  px4-agent-client command
        """
    )
    
    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output showing model reasoning and tool details"
    )
    
    parser.add_argument(
        "--server", "-s",
        type=str,
        default="http://127.0.0.1:5000",
        help="PX4Agent server URL (default: http://127.0.0.1:5000)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="mode", help="Operation mode")
    
    # Mission mode - interactive chat
    mission_parser = subparsers.add_parser("mission", help="Mission planning chat mode")
    
    # Command mode - interactive chat with reset
    command_parser = subparsers.add_parser("command", help="Command chat mode (resets after each response)")
    
    return parser


def mission_chat(client: PX4AgentClient, formatter: OutputFormatter) -> int:
    """Interactive chat interface for mission building"""
    formatter.print_info("🚁 Mission Chat Mode - Interactive mission building")
    formatter.print_info("Commands: 'quit' to exit, 'show' to review mission")
    formatter.print_info(f"Connected to: {client.base_url}")
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
                result = client.show_mission()
                if result["success"]:
                    if result.get("mission_state"):
                        formatter.print_info(f"Current mission has items:")
                        formatter._print_mission_summary(result["mission_state"])
                    else:
                        formatter.print_warning("Mission is empty")
                else:
                    formatter.print_error("Failed to show mission", result.get("error", "Unknown error"))
                continue
            elif not user_input:
                continue
            
            # Process mission request
            result = client.mission_mode_request(user_input)
            
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


def command_chat(client: PX4AgentClient, formatter: OutputFormatter) -> int:
    """Interactive chat interface for single commands with reset"""
    formatter.print_info("⚡ Command Chat Mode - Single commands with reset")
    formatter.print_info("Commands: 'quit' to exit")
    formatter.print_warning("Note: Mission and chat history reset after each command")
    formatter.print_info(f"Connected to: {client.base_url}")
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
            result = client.command_mode_request(user_input)
            
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
    
    # Initialize components
    try:
        client = PX4AgentClient(base_url=args.server, verbose=args.verbose)
        formatter = OutputFormatter(verbose=args.verbose)
    except Exception as e:
        print(f"Client initialization failed: {e}", file=sys.stderr)
        return 1
    
    # Check server connection
    formatter.print_info(f"Connecting to PX4Agent server at {client.base_url}...")
    if not client.check_server_status():
        formatter.print_error("Server connection failed", 
                             f"Cannot connect to PX4Agent server at {client.base_url}\n"
                             "Make sure the server is running with: python server.py")
        return 1
    
    formatter.print_info("✅ Connected to PX4Agent server")
    
    # Handle different modes
    if args.mode == "mission":
        return mission_chat(client, formatter)
    elif args.mode == "command":
        return command_chat(client, formatter)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())