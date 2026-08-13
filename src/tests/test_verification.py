"""Tests specifically for verification logic."""

import pytest
from decimal import Decimal
from unittest.mock import patch
from src.agent import Agent
from src.models import AccountData


@pytest.fixture
def mock_account():
    """Standard mock account."""
    return AccountData(
        account_id="ACC1001",
        full_name="Nithin Jain",
        dob="1990-05-14",
        aadhaar_last4="4321",
        pincode="400001",
        balance=Decimal("1250.75")
    )


class TestVerificationDeterminism:
    """Test that verification is deterministic and not LLM-controlled."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_exact_name_match_required(self, mock_lookup, mock_account):
        """Test that name must match exactly."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        
        # Try similar but not exact name
        agent.next("Nithin K Jain")  # Added middle initial
        response = agent.next("1990-05-14")
        
        assert not agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_exact_dob_match_required(self, mock_lookup, mock_account):
        """Test that DOB must match exactly."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        
        # Try close but incorrect date
        response = agent.next("1990-05-15")  # Off by one day
        
        assert not agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_exact_aadhaar_match_required(self, mock_lookup, mock_account):
        """Test that Aadhaar last 4 must match exactly."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        
        # Try incorrect Aadhaar
        response = agent.next("4322")  # Off by one digit
        
        assert not agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_exact_pincode_match_required(self, mock_lookup, mock_account):
        """Test that pincode must match exactly."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        
        # Try incorrect pincode
        response = agent.next("400002")  # Different pincode
        
        assert not agent.state.is_verified


class TestVerificationRetries:
    """Test retry behavior for verification."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_retry_after_wrong_name(self, mock_lookup, mock_account):
        """Test that user can retry after providing wrong name."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        
        # First attempt - wrong name
        agent.next("Wrong Name")
        response = agent.next("1990-05-14")
        
        assert "attempt" in response["message"].lower()
        assert not agent.state.is_verified
        
        # Second attempt - correct name
        agent.next("Nithin Jain")
        response = agent.next("1990-05-14")
        
        assert agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_retry_after_wrong_secondary_factor(self, mock_lookup, mock_account):
        """Test that user can retry after providing wrong secondary factor."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        
        # First attempt - wrong DOB
        response = agent.next("1995-01-01")
        
        assert "attempt" in response["message"].lower()
        assert not agent.state.is_verified
        
        # Second attempt - correct DOB
        response = agent.next("1990-05-14")
        
        assert agent.state.is_verified


class TestVerificationSecurity:
    """Test security aspects of verification."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_no_account_data_leakage(self, mock_lookup, mock_account):
        """Test that actual DOB/Aadhaar/pincode are never exposed."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        responses = []
        
        responses.append(agent.next("Hi"))
        responses.append(agent.next("ACC1001"))
        responses.append(agent.next("Nithin Jain"))
        responses.append(agent.next("wrong dob"))
        
        # Check that actual values are never in responses
        all_text = " ".join([r["message"] for r in responses])
        
        assert "1990-05-14" not in all_text
        assert "4321" not in all_text
        assert "400001" not in all_text
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_verification_required_before_balance(self, mock_lookup, mock_account):
        """Test that balance is not shown before verification."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        response = agent.next("ACC1001")
        
        # Balance should not be in response before verification
        assert "1250.75" not in response["message"]
        assert "balance" not in response["message"].lower()


class TestSecondaryFactorFlexibility:
    """Test that any ONE secondary factor is sufficient."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_dob_only(self, mock_lookup, mock_account):
        """Test verification with only DOB (no Aadhaar or pincode)."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("1990-05-14")
        
        assert agent.state.is_verified
        assert not agent.state.provided_aadhaar_last4
        assert not agent.state.provided_pincode
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_aadhaar_only(self, mock_lookup, mock_account):
        """Test verification with only Aadhaar (no DOB or pincode)."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("4321")
        
        assert agent.state.is_verified
        assert not agent.state.provided_dob
        assert not agent.state.provided_pincode
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_pincode_only(self, mock_lookup, mock_account):
        """Test verification with only pincode (no DOB or Aadhaar)."""
        mock_lookup.return_value = (True, mock_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("400001")
        
        assert agent.state.is_verified
        assert not agent.state.provided_dob
        assert not agent.state.provided_aadhaar_last4
