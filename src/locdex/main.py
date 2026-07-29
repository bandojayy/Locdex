import argparse
import sys
import os
from .router import route_task
from .validator import full_validation
from .github_push import ship_change
from .memory import init_db, save_memory, recall_similar
from .rollback import save_checkpoint, restore_latest_checkpoint
from .editor import get_workspace_context  # NEW IMPORT

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

            # --- ROLLBACK INTERCEPT ---
            if user_input.lower() == 'rollback':
                print(f"[System] Attempting to restore {output_file} to previous state...")
                if restore_latest_checkpoint(output_file):
                    print(f"✓ Successfully rewound {output_file}.")
                else:
                    print(f"x No previous checkpoints found for {output_file}.")
                continue
            # -----------------------------
            
            if user_input.lower() == 'ship it':
                print("[System] Running Validation Gate...")
                validation = full_validation(".", last_diff)
                
                if validation.get("all_pass"):
                    print("[System] Validation Passed! Tests ✓ Lint ✓ AI Safety ✓")
                    
                    if not os.path.exists(output_file):
                        with open(output_file, "w") as f:
                            f.write(last_diff)
                            
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
                    save_memory(db_conn, last_task, last_diff, success=False)
                continue
            
            if not user_input.strip():
                continue
                
            print("[System] Reading workspace context...")
            last_task = user_input
            
            # --- CONTEXT ASSEMBLY ---
            past_examples = recall_similar(db_conn, user_input)
            memory_string = "\n\n".join(past_examples) if past_examples else "None available yet."
            
            # Fetch current local files to give the LLM project awareness
            workspace_string = get_workspace_context(".")
            
            system_prompt = (
                f"RELEVANT PAST EXAMPLES:\n{memory_string}\n\n"
                f"WORKSPACE CONTEXT (Current local files):\n{workspace_string}"
            )
            context = {"repo_path": ".", "system_prompt": system_prompt}
            # ------------------------
            
            category = "general_task" 
            print("[Router is evaluating the task...]")
            
            # --- ROUTE TASK ---
            result = route_task(user_input, category, context, dummy_thresholds)
            
            # --- BULLETPROOF SAFETY CHECKS ---
            if result is None:
                result = {}
            elif isinstance(result, str):
                result = {"source": "mock", "result": {"diff": result}}
                
            source = result.get("source", "unknown")
            safe_result = result.get("result")
            
            if isinstance(safe_result, str):
                safe_result = {"diff": safe_result}
            elif not safe_result:
                safe_result = {}
                
            last_diff = safe_result.get("diff", "No code generated.")
            # ---------------------------------
            
            print(f"[{source} model] ✓ Here's the change:")
            print(last_diff)
            
            save_checkpoint(output_file)
            
            with open(output_file, "w", encoding="utf-8") as f:
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
    elif args.mode == "chat":
        chat_loop()
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()