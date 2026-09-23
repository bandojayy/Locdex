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
from .safety import is_safe_path, is_protected_path, check_ast_security

def startup_diagnostic():
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
    last_generated_files = [] 
    
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
                print("[System] Attempting rollback...")
                for f in last_generated_files:
                    if restore_latest_checkpoint(f["filepath"]):
                        print(f"✓ Successfully rewound {f['filepath']}.")
                continue
            
            if user_input.lower() == 'ship it':
                if not last_generated_files:
                    print("[System] No files to ship.")
                    continue

                print(f"[System] Running Validation Gate on {len(last_generated_files)} file(s)...")
                all_pass = True
                
                for f in last_generated_files:
                    filepath, code = f["filepath"], f["code"]
                    val = full_validation(".", code, filepath)
                    if not val.get("all_pass"):
                        print(f"[System] Validation Failed for {filepath}. {val.get('message', '')}")
                        all_pass = False
                        break
                        
                    if not is_safe_path(".", filepath) or is_protected_path(filepath):
                        print(f"[Security Block] Boundary violation on {filepath}")
                        all_pass = False
                        break

                if all_pass:
                    print("[System] Validation Passed! Tests ✓ Lint ✓ AI Safety ✓")
                    paths_to_commit = []
                    
                    for f in last_generated_files:
                        filepath, code = f["filepath"], f["code"]
                        os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
                        with open(filepath, "w", encoding="utf-8") as file_obj:
                            file_obj.write(code)
                        paths_to_commit.append(filepath)
                        save_memory(db_conn, last_task, code, success=True)
                        
                    log_routing_outcome("general_task", "python", "local", success=True, attempts=1)
                    try:
                        pr_url = ship_change(".", paths_to_commit, last_task)
                        print(f"\n✓ Opened PR: {pr_url}")
                    except Exception as git_err:
                        print(f"\n[git error] Failed to push or create PR: {git_err}")
                else:
                    save_memory(db_conn, last_task, "Failed validation", success=False)
                    log_routing_outcome("general_task", "python", "local", success=False, attempts=1)
                continue
            
            if not user_input.strip():
                continue
                
            print("[System] Reading workspace context...")
            last_task = user_input
            
            past_examples = recall_similar(db_conn, user_input)
            memory_string = "\n\n".join(past_examples) if past_examples else "None available yet."
            workspace_string = get_workspace_context(".")
            
            context = {"repo_path": ".", "system_prompt": f"RELEVANT PAST EXAMPLES:\n{memory_string}\n\nWORKSPACE CONTEXT:\n{workspace_string}"}
            
            print("[Router is evaluating the task...]")
            result = route_task(user_input, "general_task", context, dummy_thresholds)
            
            source = result.get("source", "unknown")
            files_to_write = result.get("result", {}).get("files", [])
            
            if not files_to_write:
                print(f"[{source} model] Failed to generate valid code blocks.")
                continue
                
            print(f"[{source} model] ✓ Targeting {len(files_to_write)} file(s):")
            
            # ALL-OR-NOTHING SECURITY GATE
            security_failed = False
            for f in files_to_write:
                filepath, code = f["filepath"], f["code"]
                print(f"  - {filepath}")
                
                if not is_safe_path(".", filepath):
                    print(f"\n[Security Block] Path traversal detected: {filepath}")
                    security_failed = True
                elif is_protected_path(filepath):
                    print(f"\n[Security Block] Attempted to modify protected path: {filepath}")
                    security_failed = True
                elif not filepath.endswith(".py"):
                    print(f"\n[Security Block] Locdex is restricted to .py files. Blocked: {filepath}")
                    security_failed = True
                elif flags := check_ast_security(code):
                    print(f"\n[Security Block] Malicious code in {filepath}:")
                    for flag in flags: print(f" - {flag}")
                    security_failed = True
                    
            if security_failed:
                print("Write operation aborted for ALL files to protect the host system.")
                continue
            
            # SAFE TO WRITE
            last_generated_files = files_to_write
            for f in files_to_write:
                filepath, code = f["filepath"], f["code"]
                save_checkpoint(filepath)
                os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as file_obj:
                    file_obj.write(code)
            print(f"(Code saved to {len(files_to_write)} file(s) in your working directory)")
            
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