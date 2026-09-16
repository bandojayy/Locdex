import os
import sys
import docker
import shlex
import requests
from io import BytesIO
from .safety import check_ast_security

def detect_language(filepath: str) -> str:
    """Helper function to detect file language by extension."""
    if filepath.endswith('.py'):
        return "python"
    return "unknown"

def quick_check(code: str, language: str = "python") -> bool:
    """Fast syntax validation without spinning up the full sandbox."""
    if language == "python":
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError:
            return False
    return True

class MockSubprocessResult:
    """A helper class to keep Docker results compatible with existing code."""
    def __init__(self, returncode, stdout, stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def get_or_build_sandbox_image(client):
    """Ensures the locdex-sandbox image exists, building it locally if necessary."""
    image_name = "locdex-sandbox:latest"
    try:
        client.images.get(image_name)
    except docker.errors.ImageNotFound:
        # Build a custom image with pytest pre-installed so we don't need internet later
        dockerfile = b"FROM python:3.13-slim\nRUN pip install -q pytest\n"
        client.images.build(fileobj=BytesIO(dockerfile), tag=image_name, rm=True)
    return image_name

def run_sandboxed(cmd, timeout=15, repo_path="."):
    """Runs untrusted code inside an ephemeral, air-gapped Docker container."""
    try:
        client = docker.from_env()
    except docker.errors.DockerException:
        return None, "Docker daemon is not running. Please start Docker Desktop."

    # 1. Get our pre-built image
    image_name = get_or_build_sandbox_image(client)
    
    abs_repo = os.path.abspath(repo_path)
    
    # 2. Sanitize the command for the Linux container
    sanitized_cmd = ["python" if arg == sys.executable else arg for arg in cmd]
    cmd_str = shlex.join(sanitized_cmd)
    
    try:
        # 3. Spin up the strictly air-gapped sandbox
        container = client.containers.run(
            image=image_name,
            command=["sh", "-c", cmd_str],
            volumes={abs_repo: {'bind': '/workspace', 'mode': 'rw'}},
            working_dir='/workspace',
            detach=True,
            network_mode='none',  # Strict Air-Gap: No internet access for the payload
            mem_limit='128m',     # Prevent memory exhaustion attacks
            environment={}        # Explicitly empty environment (no API keys)
        )
        
        try:
            # 4. Wait for execution and capture results
            result = container.wait(timeout=timeout)
            logs = container.logs().decode('utf-8')
            return MockSubprocessResult(result['StatusCode'], logs), None
            
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            # 5. Vaporize infinite loops
            container.kill()
            return None, f"Execution timed out after {timeout} seconds."
        finally:
            # 6. Guaranteed cleanup
            container.remove(force=True)
            
    except Exception as e:
        return None, str(e)

def full_validation(repo_path: str, code: str, filepath: str) -> dict:
    """
    Runs the full suite of validation checks:
    1. Syntax Check
    2. AST Security Linter
    3. Consistency Check (if available)
    4. Pytest Execution (Docker Sandboxed)
    """
    try:
        compile(code, filepath, "exec")
    except SyntaxError as e:
        return {"all_pass": False, "lint_pass": False, "message": f"Syntax Error: {e}"}

    security_flags = check_ast_security(code)
    if security_flags:
        return {"all_pass": False, "lint_pass": False, "message": "Security Flags:\n" + "\n".join(security_flags)}
        
    try:
        from .consistency import check_consistency
        consistency_errs = check_consistency(repo_path, code)
        if consistency_errs:
            return {"all_pass": False, "lint_pass": False, "message": f"Consistency Errors:\n{consistency_errs}"}
    except ImportError:
        pass

    # Execute tests securely inside Docker
    res, err = run_sandboxed([sys.executable, "-m", "pytest", repo_path], timeout=15, repo_path=repo_path)
    
    if err:
        return {"all_pass": False, "lint_pass": True, "message": f"Test Execution Timeout/Error:\n{err}"}
        
    if res and res.returncode != 0:
        return {"all_pass": False, "lint_pass": True, "message": f"Tests Failed:\n{res.stdout}\n{res.stderr}"}

    return {"all_pass": True, "lint_pass": True, "message": "All validation checks passed."}