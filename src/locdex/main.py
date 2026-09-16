import argparse
import sys
import os
from .router import route_task
from .validator import full_validation
from .github_push import ship_change
from .memory import init_db, save_memory, recall_similar
from .rollback import save_checkpoint, restore_latest_checkpoint
from .editor import get_workspace_context
from .telemetry import log_routing_outcome
from .planner import get_metrics_report
from .safety import is_safe_path, is_protected_path  # UPDATED IMPORT

def startup_diagnostic():
    """Runs a pre-flight check on required environment variables."""
    print("\n[System] Running environment diagnostics...")
    
    missing = []
    if not os.environ.get("OPENROUTER_API_KEY"):
        print(" ⚠️  Missing OPENROUTER_API_KEY: Cloud fallback failover is DISABLED.")
        missing.append("cloud")
        
    if not os.environ.get("GITHUB_TOKEN"):
        print(" ⚠️  Missing GITHUB_TOKEN: GitHub PR automation ('ship it') is DISABLED.")
        missing.append("git")
        
    if not missing:
        print(" ✓ All environment configurations detected. Agent is fully armed.")
    else:
        print(" ℹ️  Agent will operate with degraded capabilities until keys are exported.")
    print("-" * 50)

def chat_loop():
    print("Welcome to Locdex Chat (Mode A)")
    print("Type your task, 'ship it' to PR, 'budget' for cost metrics, or 'exit' to quit.")
    
    startup_diagnostic()
    
    db_conn = init_db()
    dummy_thresholds = {}
    
    last_task = "update-code"
    last_diff = ""
    output_file = "generated_code.py" 
    
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ['exit', 'quit']:
                print(get_metrics_report())
                break

            if user_input.lower() in ['budget', 'stats']:
                print(get_metrics_report())
                continue

            if user_input.lower() == 'rollback':
                print(f"[System] Attempting to restore {output_file} to previous state...")
                if restore_latest_checkpoint(output_file):
                    print(f"✓ Successfully rewound {output_file}.")
                else:
                    print(f"x No previous checkpoints found for {output_file}.")
                continue
            
            if user_input.lower() == 'ship it':
                print(f"[System] Running Validation Gate on {output_file}...")
                
                validation = full_validation(".", last_diff, output_file)
                
                if validation.get("all_pass"):
                    print("[System] Validation Passed! Tests ✓ Lint ✓ AI Safety ✓")
                    
                    # ENFORCE PATH SECURITY BEFORE SAVING
                    if not is_safe_path(".", output_file):
                        print(f"[Security Block] Blocked attempt to commit a file outside the workspace: {output_file}")
                        continue

                    if is_protected_path(output_file):
                        print(f"[Security Block] Blocked attempt to commit a protected internal file: {output_file}")
                        continue
                        
                    os.makedirs(os.path.dirname(os.path.abspath(output_file)) or ".", exist_ok=True)
                    if not os.path.exists(output_file):
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(last_diff)
                            
                    save_memory(db_conn, last_task, last_diff, success=True)
                    log_routing_outcome("general_task", "python", "local", success=True, attempts=1)
                    print("[System] Code pattern saved to local memory.")
                    
                    try:
                        pr_url = ship_change(
                            repo_path=".", 
                            changed_files=[output_file], 
                            task_description=last_task
                        )
                        print(f"\n✓ Opened PR: {pr_url}")
                    except Exception as git_err:
                        print(f"\n[git error] Failed to push or create PR: {git_err}")
                else:
                    print(f"[System] Validation Failed. {validation.get('message', '')}")
                    save_memory(db_conn, last_task, last_diff, success=False)
                    log_routing_outcome("general_task", "python", "local", success=False, attempts=1)
                continue
            
            if not user_input.strip():
                continue
                
            print("[System] Reading workspace context...")
            last_task = user_input
            last_diff = "" 
            
            past_examples = recall_similar(db_conn, user_input)
            memory_string = "\n\n".join(past_examples) if past_examples else "None available yet."
            workspace_string = get_workspace_context(".")
            
            system_prompt = (
                f"RELEVANT PAST EXAMPLES:\n{memory_string}\n\n"
                f"WORKSPACE CONTEXT (Current local files):\n{workspace_string}"
            )
            context = {"repo_path": ".", "system_prompt": system_prompt}
            
            print("[Router is evaluating the task...]")
            result = route_task(user_input, "general_task", context, dummy_thresholds)
            
            if result is None:
                result = {}
            elif isinstance(result, str):
                result = {"source": "mock", "result": {"diff": result, "filepath": "generated_code.py"}}
                
            source = result.get("source", "unknown")
            safe_result = result.get("result")
            
            if isinstance(safe_result, str):
                safe_result = {"diff": safe_result, "filepath": "generated_code.py"}
            elif not safe_result:
                safe_result = {}
                
            last_diff = safe_result.get("diff", "No code generated.")
            output_file = safe_result.get("filepath", "generated_code.py")
            
            print(f"[{source} model] ✓ Targeting {output_file}:")
            print(last_diff)
            
            # ENFORCE PATH SECURITY BEFORE GENERATING
            if not is_safe_path(".", output_file):
                print(f"\n[Security Block] Path traversal detected! The LLM attempted to write to: {output_file}")
                print("Write operation aborted to protect the host system.")
                continue

            if is_protected_path(output_file):
                print(f"\n[Security Block] Attempted to modify a protected internal path: {output_file}")
                print("Write operation aborted to prevent repository/CI hijacking.")
                continue
            
            save_checkpoint(output_file)
            
            os.makedirs(os.path.dirname(os.path.abspath(output_file)) or ".", exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(last_diff)
            print(f"(Code saved to {output_file} in your working directory)")
            
        except KeyboardInterrupt:
            print("\nExiting Locdex...")
            print(get_metrics_report())
            break
        except Exception as e:
            print(f"\n[Error] Something went wrong: {e}")

def cli():
    parser = argparse.ArgumentParser(description="Locdex - Local-First AI Coding Agent")
    parser.add_argument("mode", nargs="?", default="chat", help="Command to run (e.g., chat)")
    parser.add_argument("--task", help="One-shot task description")
    
    args = parser.parse_args()

    if args.task:
        print(f"Running one-shot task: {args.task}")
    elif args.mode == "chat":
        chat_loop()
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()