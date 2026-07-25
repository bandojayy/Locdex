import argparse
import sys
import os
from .router import route_task
from .validator import full_validation
from .github_push import ship_change
from .memory import init_db, save_memory, recall_similar  # NEW IMPORT

def chat_loop():
    print("Welcome to Locdex Chat (Mode A)")
    print("Type your task, 'ship it' to validate and PR, or 'exit' to quit.")
    
    # Initialize the local memory database
    db_conn = init_db()
    
    dummy_thresholds = {}
    last_task = "update-code"
    last_diff = ""
    output_file = "generated_code.py"
    
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if user_input.lower() == 'ship it':
                print("[System] Running Validation Gate...")
                validation = full_validation(".", last_diff)
                
                if validation.get("all_pass"):
                    print("[System] Validation Passed! Tests ✓ Lint ✓ AI Safety ✓")
                    
                    if not os.path.exists(output_file):
                        with open(output_file, "w") as f:
                            f.write(last_diff)
                            
                    # Save this successful outcome to our local memory database!
                    save_memory(db_conn, last_task, last_diff, success=True)
                    print("[System] Code pattern saved to local memory.")
                    
                    repo_name = "giddy-0x/Locdex"
                    
                    try:
                        pr_url = ship_change(
                            repo_path=".", 
                            changed_files=[output_file], 
                            task_description=last_task, 
                            repo_name=repo_name
                        )
                        print(f"\n✓ Opened PR: {pr_url}")
                    except Exception as git_err:
                        print(f"\n[git error] Failed to push or create PR: {git_err}")
                else:
                    print(f"[System] Validation Failed. {validation.get('message', '')}")
                    # Save the failure to memory so the AI learns what doesn't work
                    save_memory(db_conn, last_task, last_diff, success=False)
                continue
            
            if not user_input.strip():
                continue
                
            print("[Router is evaluating the task...]")
            last_task = user_input
            
            # Retrieve past similar examples to inject into the system prompt
            past_examples = recall_similar(db_conn, user_input)
            memory_string = "\n\n".join(past_examples) if past_examples else "None available yet."
            
            system_prompt = f"RELEVANT PAST EXAMPLES (from this project's history):\n{memory_string}"
            context = {"repo_path": ".", "system_prompt": system_prompt}
            
            category = "general_task" 
            result = route_task(user_input, category, context, dummy_thresholds)
            
            source = result.get("source", "unknown")
            last_diff = result.get("result", {}).get("diff", "No code generated.")
            
            print(f"[{source} model] ✓ Here's the change:")
            print(last_diff)
            
            with open(output_file, "w") as f:
                f.write(last_diff)
            print(f"(Code saved to {output_file} in your working directory)")
            
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
        # One-shot logic remains a stub for v0.1
    elif args.mode == "chat":
        chat_loop()
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()