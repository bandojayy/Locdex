import argparse
import sys
from .router import route_task

def chat_loop():
    print("Welcome to Locdex Chat (Mode A)")
    print("Type your task, 'ship it' to validate and PR, or 'exit' to quit.")
    
    # Empty stubs for features we will build in later milestones
    dummy_thresholds = {}
    context = {"repo_path": "."}
    
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            
            # The trigger for Mode B
            if user_input.lower() == 'ship it':
                print("[System] The Validation Gate and PR pipeline will trigger here in the next milestone.")
                continue
            
            if not user_input.strip():
                continue
                
            print("[Router is evaluating the task...]")
            
            # For v0.1, we assign a generic category. Telemetry will improve this later.
            category = "general_task" 
            
            result = route_task(user_input, category, context, dummy_thresholds)
            
            source = result.get("source", "unknown")
            diff = result.get("result", {}).get("diff", "No code generated or an error occurred.")
            
            print(f"[{source} model] ✓ Here's the change:")
            print(diff)
            
        except KeyboardInterrupt:
            print("\nExiting Locdex...")
            break
        except Exception as e:
            print(f"\n[Error] Something went wrong: {e}")

def cli():
    parser = argparse.ArgumentParser(description="Locdex - Local-First AI Coding Agent")
    parser.add_argument("mode", nargs="?", default="chat", help="Command to run (e.g., chat)")
    parser.add_argument("--task", help="One-shot task description")
    parser.add_argument("--ship", action="store_true", help="Trigger full validation and PR pipeline")
    
    args = parser.parse_args()

    if args.task:
        print(f"Running one-shot task: {args.task}")
        dummy_thresholds = {}
        context = {"repo_path": "."}
        
        result = route_task(args.task, "general_task", context, dummy_thresholds)
        diff = result.get("result", {}).get("diff", "")
        print(f"\n{diff}")
        
        if args.ship:
             print("\n[System] The Validation Gate and PR pipeline will trigger here in the next milestone.")
    elif args.mode == "chat":
        chat_loop()
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()