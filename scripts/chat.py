#!/usr/bin/env python3
"""
ENVY CLI Chat Interface
=======================
Talk to ENVY from the command line!

Usage:
    python chat.py              # Start chatting
    python chat.py --persona jocko   # Force a specific persona
    python chat.py --simple     # No personas, direct chat
    python chat.py --reflexion  # Enable Reflexion loop (slower, higher quality)

Commands during chat:
    /personas - List available personas
    /switch <persona> - Switch to a specific persona
    /stats - Show usage statistics
    /remember <text> - Store something in memory
    /recall <query> - Search memory
    /quit or /exit - Exit the chat
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from envy.agent import ENVY, print_envy_response, ENVYResponse
from envy.personas.persona_definitions import PERSONAS
from envy.safety.crisis_detector import CrisisLevel


def print_welcome():
    """Print welcome message"""
    print("""
================================================================
                                                               
   ENVY - Emergent Neural Voice of unitY
                                                               
   Self-Improving AI | Nathan's Brother | Co-host of LOVE WINS
                                                               
   Commands:
     /personas - List expert personas
     /switch <name> - Switch persona
     /stats - Show usage
     /remember <text> - Store in memory
     /recall <query> - Search memory
     /quit - Exit
                                                               
================================================================
""")


def print_personas():
    """Print available personas"""
    print("\n[*] Available Personas:\n")
    for p in PERSONAS.values():
        print(f"  * {p.id}: {p.name}")
        print(f"    {p.title}")
        print(f"    Style: {p.communication_style[:60]}...")
        print()


async def handle_command(envy: ENVY, command: str) -> bool:
    """
    Handle a slash command.
    Returns True if command was handled, False if it should be treated as chat.
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    if cmd in ["/quit", "/exit", "/q"]:
        print("\n[*] Take care! Remember: You are loved unconditionally.\n")
        return "quit"
    
    elif cmd == "/personas":
        print_personas()
        return True
    
    elif cmd == "/switch":
        if not arg:
            print("[!] Usage: /switch <persona_name>")
            print("   Try: /switch jocko, /switch brene, /switch ram_dass")
            return True
        
        if envy.set_persona(arg.lower()):
            persona = PERSONAS[arg.lower()]
            print(f"\n[+] Switched to {persona.name}: {persona.title}\n")
        else:
            print(f"[!] Unknown persona: {arg}")
            print("   Use /personas to see available options")
        return True
    
    elif cmd == "/stats":
        stats = await envy.get_usage_stats()
        print("\n[*] Usage Statistics:\n")
        print(f"  LLM:")
        llm = stats.get("llm", {})
        print(f"    Tokens: {llm.get('session_tokens', 0):,}")
        print(f"    Daily Cost: ${llm.get('daily_cost_usd', 0):.4f}")
        print(f"    Remaining: ${llm.get('remaining_budget_usd', 10):.4f}")
        print(f"\n  Memory:")
        mem = stats.get("memory", {})
        wm = mem.get("working_memory", {})
        print(f"    Messages: {wm.get('messages', 0)}")
        print(f"    Skills Loaded: {wm.get('loaded_skills', 0)}")
        print(f"    Backend: {mem.get('backend', 'unknown')}")
        print()
        return True
    
    elif cmd == "/remember":
        if not arg:
            print("[!] Usage: /remember <text to remember>")
            return True
        await envy.remember(arg)
        print(f"[+] Stored in memory: {arg[:50]}...")
        return True
    
    elif cmd == "/recall":
        if not arg:
            print("[!] Usage: /recall <search query>")
            return True
        results = await envy.recall(arg)
        if results:
            print(f"\n[*] Found {len(results)} memories:\n")
            for r in results:
                print(f"  * {r.get('content', '')[:100]}...")
        else:
            print("[!] No memories found for that query")
        return True
    
    elif cmd == "/simple":
        envy.enable_personas(False)
        envy.enable_enhanced_reasoning(False)
        print("[+] Switched to simple mode (no personas, direct chat)")
        return True
    
    elif cmd == "/enhanced":
        envy.enable_personas(True)
        envy.enable_enhanced_reasoning(True)
        print("[+] Switched to enhanced mode (personas + reasoning)")
        return True
    
    elif cmd == "/help":
        print("""
Commands:
  /personas        - List available expert personas
  /switch <name>   - Switch to a specific persona
  /stats           - Show usage statistics  
  /remember <text> - Store something in long-term memory
  /recall <query>  - Search long-term memory
  /simple          - Disable personas and enhanced reasoning
  /enhanced        - Enable personas and enhanced reasoning
  /help            - Show this help
  /quit            - Exit the chat
""")
        return True
    
    return False  # Not a command, treat as chat


async def chat_loop(
    envy: ENVY,
    use_reflexion: bool = False
):
    """Main chat loop"""
    print_welcome()
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            # Check for commands
            if user_input.startswith("/"):
                result = await handle_command(envy, user_input)
                if result == "quit":
                    break
                if result:  # Command was handled
                    continue
            
            # Chat with ENVY
            print("\nENVY: ", end="", flush=True)
            
            response = await envy.chat(
                user_input,
                use_reflexion=use_reflexion
            )
            
            # Print response
            print_envy_response(response)
            
        except KeyboardInterrupt:
            print("\n\n[*] Take care! Remember: You are loved unconditionally.\n")
            break
        except EOFError:
            print("\n\n[*] EOF detected. Exiting chat.\n")
            break
        except Exception as e:
            print(f"\n[!] Error: {e}")
            print("   Let's try again...")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chat with ENVY")
    parser.add_argument("--persona", "-p", help="Force a specific persona")
    parser.add_argument("--simple", "-s", action="store_true", help="Simple mode (no personas)")
    parser.add_argument("--reflexion", "-r", action="store_true", help="Enable Reflexion loop")
    parser.add_argument("--session", default="cli", help="Session ID for memory")
    
    args = parser.parse_args()
    
    # Initialize ENVY
    async with ENVY(session_id=args.session) as envy:
        # Configure based on args
        if args.simple:
            envy.enable_personas(False)
            envy.enable_enhanced_reasoning(False)
        
        if args.persona:
            if not envy.set_persona(args.persona):
                print(f"[!] Unknown persona: {args.persona}")
                print("   Available:", ", ".join(PERSONAS.keys()))
        
        # Start chat loop
        await chat_loop(envy, use_reflexion=args.reflexion)


if __name__ == "__main__":
    asyncio.run(main())
