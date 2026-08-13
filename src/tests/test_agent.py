"""Tests for the main Agent class."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from src.agent import Agent
from src.models import AccountData, PaymentResponse


@pytest.fixture
def mock_account_data():
    """Mock account data for testing."""
    return AccountData(
        account_id="ACC1001",
        full_name="Nithin Jain",
        dob="1990-05-14",
        aadhaar_last4="4321",
        pincode="400001",
        balance=Decimal("1250.75")
    )


@pytest.fixture
def agent():
    """Create a fresh agent instance."""
    return Agent()


class TestHappyPath:
    """Test successful payment flow."""
    
    @patch('tools.payment.PaymentAPI.process_payment')
    @patch('tools.account.AccountAPI.lookup_account')
    def test_successful_payment_flow(self, mock_lookup, mock_payment, agent, mock_account_data):
        """Test complete successful payment flow."""
        # Mock API responses
        mock_lookup.return_value = (True, mock_account_data, None)
        mock_payment.return_value = (
            True,
            PaymentResponse(success=True, transaction_id="txn_123456"),
            None
        )
        
        # Conversation flow
        responses = []
        
        # Start
        responses.append(agent.next("Hi"))
        assert "account ID" in responses[-1]["message"].lower()
        
        # Provide account ID
        responses.append(agent.next("My account ID is ACC1001"))
        assert "name" in responses[-1]["message"].lower()
        
        # Provide name
        responses.append(agent.next("Nithin Jain"))
        assert "date of birth" in responses[-1]["message"].lower() or "aadhaar" in responses[-1]["message"].lower()
        
        # Provide DOB
        responses.append(agent.next("1990-05-14"))
        assert "verified" in responses[-1]["message"].lower()
        assert "1250.75" in responses[-1]["message"]
        
        # Provide payment amount
        responses.append(agent.next("I want to pay 500"))
        assert "card" in responses[-1]["message"].lower()
        
        # Provide card details (all at once)
        responses.append(agent.next(
            "Card number is 4532015112830366, CVV is 123, "
            "expires 12/2027, name is Nithin Jain"
        ))
        assert "successful" in responses[-1]["message"].lower()
        assert "txn_123456" in responses[-1]["message"]


class TestAccountLookup:
    """Test account lookup scenarios."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_account_not_found(self, mock_lookup, agent):
        """Test handling of account not found."""
        mock_lookup.return_value = (False, None, "No account found with the provided account_id.")
        
        agent.next("Hi")
        response = agent.next("ACC9999")
        
        assert "sorry" in response["message"].lower()
        assert "account" in response["message"].lower()
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_invalid_account_id_format(self, mock_lookup, agent):
        """Test handling of invalid account ID format."""
        agent.next("Hi")
        response = agent.next("123456")
        
        assert "format" in response["message"].lower() or "valid" in response["message"].lower()


class TestVerification:
    """Test identity verification scenarios."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_correct_name_and_dob(self, mock_lookup, agent, mock_account_data):
        """Test verification with correct name and DOB."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("1990-05-14")
        
        assert "verified" in response["message"].lower()
        assert agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_correct_name_and_aadhaar(self, mock_lookup, agent, mock_account_data):
        """Test verification with correct name and Aadhaar last 4."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("last four of my Aadhaar is 4321")
        
        assert "verified" in response["message"].lower()
        assert agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_correct_name_and_pincode(self, mock_lookup, agent, mock_account_data):
        """Test verification with correct name and pincode."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("pincode is 400001")
        
        assert "verified" in response["message"].lower()
        assert agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_wrong_name(self, mock_lookup, agent, mock_account_data):
        """Test verification failure with wrong name."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("John Doe")
        response = agent.next("1990-05-14")
        
        assert "doesn't match" in response["message"].lower()
        assert not agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_wrong_dob(self, mock_lookup, agent, mock_account_data):
        """Test verification failure with wrong DOB."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("1995-01-01")
        
        assert "doesn't match" in response["message"].lower()
        assert not agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_verification_retry_limit(self, mock_lookup, agent, mock_account_data):
        """Test that verification fails after max attempts."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        
        # Attempt 1
        agent.next("Wrong Name")
        agent.next("1990-05-14")
        
        # Attempt 2
        agent.next("Another Wrong Name")
        agent.next("1990-05-14")
        
        # Attempt 3
        agent.next("Still Wrong Name")
        response = agent.next("1990-05-14")
        
        assert "terminated" in response["message"].lower()
        assert not agent.state.is_verified


class TestPaymentAmount:
    """Test payment amount collection and validation."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_partial_payment(self, mock_lookup, agent, mock_account_data):
        """Test partial payment (less than full balance)."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        # Get to verified state
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        
        # Pay partial amount
        response = agent.next("I want to pay 500")
        
        assert "500" in response["message"]
        assert agent.state.payment_amount == Decimal("500")
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_full_payment(self, mock_lookup, agent, mock_account_data):
        """Test full balance payment."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        # Get to verified state
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        
        # Pay full amount
        response = agent.next("just clear the full amount")
        
        assert agent.state.payment_amount == mock_account_data.balance
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_amount_exceeds_balance(self, mock_lookup, agent, mock_account_data):
        """Test rejection of amount exceeding balance."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        # Get to verified state
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        
        # Try to pay more than balance
        response = agent.next("I want to pay 5000")
        
        assert "exceeds" in response["message"].lower()
        assert agent.state.payment_amount is None


class TestOutOfOrderInformation:
    """Test handling of out-of-order information."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_multiple_fields_at_once(self, mock_lookup, agent, mock_account_data):
        """Test providing multiple pieces of information at once."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        
        # Provide account ID and name together
        response = agent.next("My account is ACC1001 and my name is Nithin Jain")
        
        assert agent.state.account_id == "ACC1001"
        assert agent.state.provided_name == "Nithin Jain"
        
        # Should ask for secondary verification
        assert "date of birth" in response["message"].lower() or "aadhaar" in response["message"].lower()


class TestSecurityChecks:
    """Test security-related behaviors."""
    
    def test_no_sensitive_data_exposure(self, agent):
        """Test that sensitive account data is not exposed."""
        # This would need more sophisticated testing in practice
        # For now, verify DOB/Aadhaar/pincode aren't in initial messages
        agent.next("Hi")
        response = agent.next("ACC1001")
        
        # Should not contain actual DOB, Aadhaar, or pincode values
        assert "1990-05-14" not in response["message"]
        assert "4321" not in response["message"]
        assert "400001" not in response["message"]
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_payment_blocked_without_verification(self, mock_lookup, agent, mock_account_data):
        """Test that payment cannot proceed without verification."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent.next("Hi")
        agent.next("ACC1001")
        
        # Try to skip verification
        agent.state.current_state = "COLLECT_PAYMENT_AMOUNT"
        agent.state.is_verified = False
        
        response = agent.next("I want to pay 500")
        
        assert "verification" in response["message"].lower()
