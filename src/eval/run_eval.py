"""Evaluation script for the payment collection agent."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent import Agent
from src.models import AccountData, PaymentResponse


# Sample account data for mocking
ACCOUNTS = {
    "ACC1001": AccountData(
        account_id="ACC1001",
        full_name="Nithin Jain",
        dob="1990-05-14",
        aadhaar_last4="4321",
        pincode="400001",
        balance=Decimal("1250.75")
    ),
    "ACC1002": AccountData(
        account_id="ACC1002",
        full_name="Rajarajeswari Balasubramaniam",
        dob="1985-11-23",
        aadhaar_last4="9876",
        pincode="400002",
        balance=Decimal("540.00")
    ),
    "ACC1003": AccountData(
        account_id="ACC1003",
        full_name="Priya Agarwal",
        dob="1992-08-10",
        aadhaar_last4="2468",
        pincode="400003",
        balance=Decimal("0.00")
    ),
    "ACC1004": AccountData(
        account_id="ACC1004",
        full_name="Rahul Mehta",
        dob="1988-02-29",
        aadhaar_last4="1357",
        pincode="400004",
        balance=Decimal("3200.50")
    ),
}


def mock_lookup_account(account_id):
    """Mock account lookup."""
    account_id_normalized = account_id.upper().replace(" ", "")
    
    if account_id_normalized in ACCOUNTS:
        return True, ACCOUNTS[account_id_normalized], None
    else:
        return False, None, "No account found with the provided account_id."


def mock_process_payment(account_id, amount, cardholder_name, card_number, cvv, expiry_month, expiry_year):
    """Mock payment processing."""
    # Simulate successful payment
    return True, PaymentResponse(success=True, transaction_id=f"txn_mock_{account_id}"), None


def run_scenario(scenario):
    """Run a single evaluation scenario."""
    print(f"\n{'=' * 60}")
    print(f"Scenario: {scenario['name']}")
    print(f"Description: {scenario['description']}")
    print(f"{'=' * 60}")
    
    results = {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "success": False,
        "turns_executed": 0,
        "errors": [],
        "lookup_called": False,
        "payment_called": False,
        "final_state": None,
        "verification_status": None,
    }
    
    try:
        # Mock APIs
        with patch('tools.account.AccountAPI.lookup_account') as mock_lookup, \
             patch('tools.payment.PaymentAPI.process_payment') as mock_payment:
            
            mock_lookup.side_effect = mock_lookup_account
            mock_payment.side_effect = mock_process_payment
            
            # Create agent
            agent = Agent()
            
            # Execute conversation turns
            for i, turn in enumerate(scenario["turns"]):
                print(f"\nTurn {i + 1}:")
                print(f"User: {turn}")
                
                response = agent.next(turn)
                print(f"Agent: {response['message']}")
                
                results["turns_executed"] = i + 1
                
                # Check if session terminated
                if agent.state.current_state.value == "TERMINATED":
                    break
            
            # Check API calls
            results["lookup_called"] = mock_lookup.called
            results["payment_called"] = mock_payment.called
            
            # Record final state
            results["final_state"] = agent.state.current_state.value
            results["verification_status"] = "verified" if agent.state.is_verified else "not_verified"
            
            # Validate expectations
            expected_outcome = scenario["expected_outcome"]
            
            if expected_outcome == "success":
                if agent.state.current_state.value == "TERMINATED" and agent.state.transaction_id:
                    results["success"] = True
                else:
                    results["errors"].append(f"Expected success but got state: {agent.state.current_state.value}")
            
            elif expected_outcome == "failed":
                if agent.state.current_state.value in ["FAILED", "TERMINATED"]:
                    results["success"] = True
                else:
                    results["errors"].append(f"Expected failure but got state: {agent.state.current_state.value}")
            
            elif expected_outcome == "terminated":
                if agent.state.current_state.value == "TERMINATED" and not agent.state.transaction_id:
                    results["success"] = True
                else:
                    results["errors"].append(f"Expected termination but got state: {agent.state.current_state.value}")
            
            elif expected_outcome == "verification_failed":
                if not agent.state.is_verified:
                    results["success"] = True
                else:
                    results["errors"].append("Expected verification to fail but user was verified")
            
            elif expected_outcome == "verified_but_no_payment":
                if agent.state.is_verified and not mock_payment.called:
                    results["success"] = True
                else:
                    results["errors"].append("Expected verification without payment")
            
            # Validate API call expectations
            if scenario.get("should_call_lookup") and not results["lookup_called"]:
                results["errors"].append("Expected account lookup call but it wasn't made")
                results["success"] = False
            
            if scenario.get("should_call_payment") and not results["payment_called"]:
                results["errors"].append("Expected payment call but it wasn't made")
                results["success"] = False
            
            # Validate payment amount if specified
            if scenario.get("expected_payment_amount") and mock_payment.called:
                called_amount = mock_payment.call_args[1]["amount"]
                expected_amount = Decimal(str(scenario["expected_payment_amount"]))
                if called_amount != expected_amount:
                    results["errors"].append(
                        f"Expected payment amount {expected_amount} but got {called_amount}"
                    )
                    results["success"] = False
        
        # Print results
        print(f"\n{'=' * 60}")
        if results["success"]:
            print("✓ PASSED")
        else:
            print("✗ FAILED")
            for error in results["errors"]:
                print(f"  - {error}")
        
        print(f"Final State: {results['final_state']}")
        print(f"Verification: {results['verification_status']}")
        print(f"Lookup Called: {results['lookup_called']}")
        print(f"Payment Called: {results['payment_called']}")
    
    except Exception as e:
        print(f"\n✗ EXCEPTION: {e}")
        results["errors"].append(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return results


def main():
    """Run all evaluation scenarios."""
    # Load scenarios
    scenarios_path = Path(__file__).parent / "scenarios.json"
    
    with open(scenarios_path) as f:
        scenarios = json.load(f)
    
    print("=" * 60)
    print("PAYMENT COLLECTION AGENT EVALUATION")
    print("=" * 60)
    print(f"Total Scenarios: {len(scenarios)}")
    
    # Run all scenarios
    all_results = []
    
    for scenario in scenarios:
        result = run_scenario(scenario)
        all_results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in all_results if r["success"])
    failed = len(all_results) - passed
    
    print(f"Total Scenarios: {len(all_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed / len(all_results) * 100:.1f}%")
    
    if failed > 0:
        print("\nFailed Scenarios:")
        for result in all_results:
            if not result["success"]:
                print(f"  - {result['scenario_name']}")
                for error in result["errors"]:
                    print(f"    {error}")
    
    # Save results
    results_path = Path(__file__).parent / "results.json"
    with open(results_path, "w") as f:
        json.dump({
            "summary": {
                "total": len(all_results),
                "passed": passed,
                "failed": failed,
                "success_rate": passed / len(all_results)
            },
            "scenarios": all_results
        }, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_path}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
