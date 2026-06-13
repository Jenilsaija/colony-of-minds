#!/usr/bin/env python3
"""
Interactive CLI Operator Shell for Colony of Minds.
Implements a premium command-line assistant using standard libraries and ANSI formatting.
"""

import sys
import os
import cmd
import time
import json
from pathlib import Path
from typing import Optional

# Ensure package directories are in sys.path if run directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from colony_ai.run_colony import run_pipeline, get_process_memory_mb
from colony_ai.colony.config import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_PATH, DEFAULT_OLLAMA_API_URL
from colony_ai.memory.memory_store import MemoryStore

# ANSI Styling Helper Constants
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_GRAY = "\033[90m"

BANNER = f"""
{C_CYAN}{C_BOLD}┌────────────────────────────────────────────────────────┐
│             COLONY OF MINDS - PERSONAL OPERATOR        │
│    Low-resource micro-agent composition framework      │
└────────────────────────────────────────────────────────┘{C_RESET}
Type {C_CYAN}/help{C_RESET} to view commands. Type {C_CYAN}/exit{C_RESET} to quit.
"""

class ColonyCliShell(cmd.Cmd):
    intro = BANNER
    prompt = f"\n{C_CYAN}{C_BOLD}colony >{C_RESET} "
    
    def __init__(self):
        super().__init__()
        self.memory_store = MemoryStore()
        
        # Local settings state
        self.atma_mode = "model" if DEFAULT_OLLAMA_MODEL else "template"
        self.model_name = DEFAULT_OLLAMA_MODEL
        self.ollama_path = DEFAULT_OLLAMA_PATH
        self.ollama_api_url = DEFAULT_OLLAMA_API_URL
        self.safety_level = "high"
        self.verbose = False
        
        # Local metrics state
        self.queries_count = 0
        self.total_latency_ms = 0.0
        self.max_ram_mb = 0.0
        
    def preloop(self):
        # Update terminal title if possible
        if sys.platform.startswith("win"):
            os.system("title Colony of Minds AI Shell")
            
    def default(self, line: str):
        """Processes standard queries that do not start with a slash command."""
        query = line.strip()
        if not query:
            return
            
        # Catch accidental leading slashes or show error for invalid commands
        if query.startswith("/"):
            print(f"{C_RED}Unknown command: {query}. Type /help for assistance.{C_RESET}")
            return
            
        self.queries_count += 1
        print(f"\n{C_GRAY}[*] Thinking...{C_RESET}")
        
        t0 = time.time()
        try:
            # Prepare configuration overrides
            model = self.model_name if self.atma_mode == "model" else ""
            
            # Execute pipeline
            answer = run_pipeline(
                query=query,
                verbose=self.verbose,
                model_name=model,
                ollama_path=self.ollama_path,
                ollama_api_url=self.ollama_api_url
            )
            
            latency = (time.time() - t0) * 1000
            self.total_latency_ms += latency
            
            current_ram = get_process_memory_mb()
            if current_ram > self.max_ram_mb:
                self.max_ram_mb = current_ram
                
            # Formatted Output
            print(f"\n{C_GREEN}{C_BOLD}Response:{C_RESET}\n{answer}")
            print(f"\n{C_GRAY}─── Latency: {latency:.1f}ms | RAM: {current_ram:.1f}MB ───{C_RESET}")
            
        except KeyboardInterrupt:
            print(f"\n{C_YELLOW}[!] Query execution aborted by user.{C_RESET}")
        except Exception as e:
            print(f"\n{C_RED}[!] Error executing query: {e}{C_RESET}")

    def emptyline(self):
        # Prevent repeating the last command on empty enter key
        pass

    # Command: /exit
    def do_exit(self, arg):
        """Exit the shell. Usage: /exit"""
        print(f"{C_CYAN}Goodbye!{C_RESET}")
        return True
    
    def do_quit(self, arg):
        """Exit the shell. Usage: /quit"""
        return self.do_exit(arg)

    # Command: /clear
    def do_clear(self, arg):
        """Clear the screen. Usage: /clear"""
        os.system("cls" if os.name == "nt" else "clear")
        print(self.intro)

    # Command: /settings
    def do_settings(self, arg):
        """View or configure settings.
Usage:
  /settings                    - View active settings
  /settings atma <mode>        - Set Atma mode to 'model' or 'template'
  /settings model <name>       - Set Ollama model name (e.g. qwen2.5:0.5b)
  /settings api_url <value>    - Set Ollama HTTP API URL (e.g. http://localhost:11434)
  /settings safety <level>     - Set Safety Gate level to 'high', 'medium', or 'low'
  /settings verbose <on/off>   - Toggle detailed pipeline logs
"""
        args = arg.strip().split()
        if not args:
            # Display current settings
            print(f"\n{C_CYAN}{C_BOLD}=== Colony Settings ==={C_RESET}")
            print(f"  {C_BOLD}Atma Mode:{C_RESET}    {self.atma_mode}")
            print(f"  {C_BOLD}Model Name:{C_RESET}   {self.model_name or '<none>'}")
            print(f"  {C_BOLD}Ollama Path:{C_RESET}  {self.ollama_path}")
            print(f"  {C_BOLD}Ollama API URL:{C_RESET} {self.ollama_api_url}")
            print(f"  {C_BOLD}Safety Level:{C_RESET} {self.safety_level}")
            print(f"  {C_BOLD}Verbose:{C_RESET}      {'ON' if self.verbose else 'OFF'}")
            print(f"  {C_BOLD}Database:{C_RESET}     {self.memory_store.db_path}")
            return

        cmd_name = args[0].lower()
        if len(args) < 2:
            print(f"{C_RED}Missing setting value. Usage: /settings {cmd_name} <value>{C_RESET}")
            return
            
        value = args[1].lower()
        
        if cmd_name == "atma":
            if value in ["model", "template"]:
                self.atma_mode = value
                print(f"{C_GREEN}Atma mode updated to: {self.atma_mode}{C_RESET}")
            else:
                print(C_RED + "Invalid Atma mode. Choose 'model' or 'template'." + C_RESET)
                
        elif cmd_name == "model":
            self.model_name = args[1]
            print(f"{C_GREEN}Ollama model name set to: {self.model_name}{C_RESET}")
            
        elif cmd_name == "api_url":
            self.ollama_api_url = args[1]
            print(f"{C_GREEN}Ollama API URL set to: {self.ollama_api_url}{C_RESET}")
            
        elif cmd_name == "safety":
            if value in ["high", "medium", "low"]:
                self.safety_level = value
                # Dynamically set threshold if relevant
                threshold = 0.7 if value == "high" else (0.5 if value == "medium" else 0.2)
                os.environ["COLONY_CONFIDENCE_THRESHOLD"] = str(threshold)
                print(f"{C_GREEN}Safety level set to: {self.safety_level} (confidence threshold: {threshold}){C_RESET}")
            else:
                print(C_RED + "Invalid safety level. Choose 'high', 'medium', or 'low'." + C_RESET)
                
        elif cmd_name == "verbose":
            if value in ["on", "true", "yes", "1"]:
                self.verbose = True
                print(f"{C_GREEN}Verbose logging: ON{C_RESET}")
            elif value in ["off", "false", "no", "0"]:
                self.verbose = False
                print(f"{C_GREEN}Verbose logging: OFF{C_RESET}")
            else:
                print(C_RED + "Invalid toggle. Choose 'on' or 'off'." + C_RESET)
        else:
            print(f"{C_RED}Unknown setting category: {cmd_name}{C_RESET}")

    # Command: /stats
    def do_stats(self, arg):
        """Print current session statistics. Usage: /stats"""
        avg_latency = self.total_latency_ms / self.queries_count if self.queries_count > 0 else 0.0
        print(f"\n{C_CYAN}{C_BOLD}=== Session Performance Statistics ==={C_RESET}")
        print(f"  {C_BOLD}Queries Processed:{C_RESET} {self.queries_count}")
        print(f"  {C_BOLD}Average Latency:{C_RESET}   {avg_latency:.1f} ms")
        print(f"  {C_BOLD}Peak memory RSS:{C_RESET}   {self.max_ram_mb:.1f} MB (Target: <150MB)")
        print(f"  {C_BOLD}Ollama Synthesis:{C_RESET}  {'Enabled' if self.atma_mode == 'model' else 'Disabled'}")

    # Command: /history
    def do_history(self, arg):
        """View recent interactions from memory. Usage: /history [limit]"""
        limit = 10
        if arg.strip().isdigit():
            limit = int(arg.strip())
            
        history = self.memory_store.get_history(limit)
        if not history:
            print(f"{C_YELLOW}No history entries found in memory store.{C_RESET}")
            return
            
        print(f"\n{C_CYAN}{C_BOLD}=== Recent Interaction History ({len(history)}) ==={C_RESET}")
        for idx, item in enumerate(history, 1):
            time_str = item["timestamp"][:19].replace("T", " ")
            op_str = ", ".join(item["routed_operators"])
            ver_str = f"{C_GREEN}VERIFIED{C_RESET}" if item["verified"] else f"{C_RED}REJECTED{C_RESET}"
            
            print(f"\n{C_CYAN}{idx}. [{time_str}] {ver_str} (Ops: {op_str}){C_RESET}")
            print(f"   {C_BOLD}Query:{C_RESET} {item['query']}")
            print(f"   {C_BOLD}Answer:{C_RESET} {item['response']}")

    # Override standard Cmd methods for custom slash-style commands parsing
    def onecmd(self, line: str) -> bool:
        cmd_line = line.strip()
        if cmd_line.startswith("/"):
            # Translate "/cmd args" into standard Cmd format "cmd args"
            parts = cmd_line[1:].split(maxsplit=1)
            cmd_name = parts[0]
            cmd_arg = parts[1] if len(parts) > 1 else ""
            
            # Check if method exists
            method_name = f"do_{cmd_name}"
            if hasattr(self, method_name):
                return getattr(self, method_name)(cmd_arg)
            else:
                print(f"{C_RED}Unknown command: /{cmd_name}. Type /help for details.{C_RESET}")
                return False
        
        # Standard input query
        return super().onecmd(line)

    def do_help(self, arg):
        """Shows help details. Usage: /help"""
        print(f"\n{C_CYAN}{C_BOLD}=== Available Commands ==={C_RESET}")
        print(f"  {C_CYAN}/settings{C_RESET} [atma|model|api_url|safety|verbose] [val] - Manage configuration")
        print(f"  {C_CYAN}/stats{C_RESET}                                      - View performance diagnostics")
        print(f"  {C_CYAN}/history{C_RESET} [limit]                             - Display database interaction logs")
        print(f"  {C_CYAN}/clear{C_RESET}                                      - Clear the terminal screen")
        print(f"  {C_CYAN}/exit{C_RESET} or {C_CYAN}/quit{C_RESET}                          - Terminate shell session")
        print(f"\n{C_CYAN}Simply type any query (e.g. 'calculate 45 * 123') to prompt the operator.{C_RESET}")

def main():
    try:
        shell = ColonyCliShell()
        shell.cmdloop()
    except KeyboardInterrupt:
        print(f"\n{C_CYAN}Goodbye!{C_RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
