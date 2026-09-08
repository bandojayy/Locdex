from unittest.mock import patch
from src.locdex.router import route_task

# FIX: We now patch the function directly in the router's namespace
@patch('src.locdex.router.run_cloud')
@patch('src.locdex.router.full_validation')
@patch('src.locdex.router.run_local_with_confidence') 
def test_router_auto_healing_and_fallback(mock_run_local, mock_validate, mock_run_cloud):
    """
    Verify the router attempts local generation 3 times, feeds errors back to the model, 
    and successfully escalates to the cloud upon exhaustion.
    """
    # 1. Setup the Simulation
    mock_run_local.return_value = {"diff": "print('local failure')", "filepath": "test.py"}
    mock_validate.return_value = {"all_pass": False, "message": "Simulated syntax error"}
    mock_run_cloud.return_value = {"diff": "print('cloud success')", "filepath": "test.py", "provider": "deepseek"}
    
    # 2. Execute the Router
    context = {"system_prompt": "Mock system prompt"}
    result = route_task("Fix this bug", "general_task", context, {})
    
    # 3. Verify the Architecture behaved correctly
    assert mock_validate.call_count == 3, f"Expected 3 local attempts, but got {mock_validate.call_count}"
    assert mock_run_cloud.called, "Router failed to escalate to cloud model after local exhaustion."
    assert result["result"]["diff"] == "print('cloud success')"
    assert result["source"] == "cloud"