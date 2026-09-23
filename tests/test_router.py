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
    # 1. Setup the Simulation (UPDATED FOR MULTI-FILE ARCHITECTURE)
    mock_run_local.return_value = {
        "files": [{"filepath": "test.py", "code": "print('local failure')"}],
        "confidence": 0.9
    }
    mock_validate.return_value = {
        "all_pass": False,
        "message": "Simulated syntax error"
    }
    mock_run_cloud.return_value = {
        "files": [{"filepath": "test.py", "code": "print('cloud success')"}],
        "confidence": 0.9
    }

    # 2. Execute the Router
    context = {"system_prompt": "Mock system prompt"}
    result = route_task("Fix this bug", "general_task", context, {})

    # 3. Verify the Architecture behaved correctly
    assert mock_validate.call_count == 3, \
        f"Expected 3 local attempts, but got {mock_validate.call_count}"
        
    assert result["source"] == "cloud", "Expected final fallback to be cloud"
    assert len(result["result"]["files"]) == 1, "Expected cloud to return valid files array"
    assert result["result"]["files"][0]["code"] == "print('cloud success')"