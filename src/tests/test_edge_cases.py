"""Tests for edge cases and special scenarios."""

import pytest
from decimal import Decimal
from unittest.mock import patch
from src.agent import Agent
from src.models import AccountData


@pytest.fixture
def leap_year_account():
    """ACC1004 with leap year DOB."""
    return AccountData(
        account_id="ACC1004",
        full_name="Rahul Mehta",
        dob="1988-02-29",
        aadhaar_last4="1357",
        pincode="400004",
        balance=Decimal("3200.50")
    )


@pytest.fixture
def zero_balance_account():
    """ACC1003 with zero balance."""
    return AccountData(
        account_id="ACC1003",
        full_name="Priya Agarwal",
        dob="1992-08-10",
        aadhaar_last4="2468",
        pincode="400003",
        balance=Decimal("0.00")
    )


class TestLeapYearDOB:
    """Test handling of leap year date of birth."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_leap_year_dob_exact_match(self, mock_lookup, leap_year_account):
        """Test verification with exact leap year DOB."""
        mock_lookup.return_value = (True, leap_year_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1004")
        agent.next("Rahul Mehta")
        response = agent.next("1988-02-29")
        
        assert "verified" in response["message"].lower()
        assert agent.state.is_verified
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_leap_year_dob_wrong_date(self, mock_lookup, leap_year_account):
        """Test verification failure with nearby but incorrect date."""
        mock_lookup.return_value = (True, leap_year_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1004")
        agent.next("Rahul Mehta")
        response = agent.next("1988-02-28")
        
        assert "doesn't match" in response["message"].lower()
        assert not agent.state.is_verified


class TestZeroBalance:
    """Test handling of zero balance account."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_zero_balance_display(self, mock_lookup, zero_balance_account):
        """Test that zero balance is displayed correctly."""
        mock_lookup.return_value = (True, zero_balance_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1003")
        agent.next("Priya Agarwal")
        response = agent.next("1992-08-10")
        
        assert "verified" in response["message"].lower()
        assert "0.00" in response["message"] or "0" in response["message"]
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_payment_on_zero_balance(self, mock_lookup, zero_balance_account):
        """Test that payment is rejected on zero balance."""
        mock_lookup.return_value = (True, zero_balance_account, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1003")
        agent.next("Priya Agarwal")
        agent.next("1992-08-10")
        
        response = agent.next("I want to pay 100")
        
        assert "exceeds" in response["message"].lower()


class TestNaturalLanguageVariations:
    """Test various natural language input formats."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_account_id_with_spaces(self, mock_lookup):
        """Test account ID with spaces."""
        account_data = AccountData(
            account_id="ACC1001",
            full_name="Nithin Jain",
            dob="1990-05-14",
            aadhaar_last4="4321",
            pincode="400001",
            balance=Decimal("1250.75")
        )
        mock_lookup.return_value = (True, account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        response = agent.next("it's ACC 1001")
        
        assert agent.state.account_id == "ACC1001"
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_dob_natural_language(self, mock_lookup):
        """Test DOB in natural language format."""
        account_data = AccountData(
            account_id="ACC1001",
            full_name="Nithin Jain",
            dob="1990-05-14",
            aadhaar_last4="4321",
            pincode="400001",
            balance=Decimal("1250.75")
        )
        mock_lookup.return_value = (True, account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        response = agent.next("I was born on 14th May 1990")
        
        assert "verified" in response["message"].lower()
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_amount_natural_language(self, mock_lookup):
        """Test amount in natural language."""
        account_data = AccountData(
            account_id="ACC1001",
            full_name="Nithin Jain",
            dob="1990-05-14",
            aadhaar_last4="4321",
            pincode="400001",
            balance=Decimal("1250.75")
        )
        mock_lookup.return_value = (True, account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        response = agent.next("I want to pay a thousand rupees")
        
        assert agent.state.payment_amount == Decimal("1000")


class TestLongNames:
    """Test handling of long names."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_long_name_verification(self, mock_lookup):
        """Test verification with a very long name."""
        account_data = AccountData(
            account_id="ACC1002",
            full_name="Rajarajeswari Balasubramaniam",
            dob="1985-11-23",
            aadhaar_last4="9876",
            pincode="400002",
            balance=Decimal("540.00")
        )
        mock_lookup.return_value = (True, account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1002")
        response = agent.next("you can call me Raja but my full name is Rajarajeswari Balasubramaniam")
        
        # Should extract the full name correctly
        assert agent.state.provided_name == "Rajarajeswari Balasubramaniam"


class TestCaseSensitivity:
    """Test case sensitivity in verification."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_name_case_sensitivity(self, mock_lookup):
        """Test that name matching is case-sensitive."""
        account_data = AccountData(
            account_id="ACC1001",
            full_name="Nithin Jain",
            dob="1990-05-14",
            aadhaar_last4="4321",
            pincode="400001",
            balance=Decimal("1250.75")
        )
        mock_lookup.return_value = (True, account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("nithin jain")  # lowercase
        response = agent.next("1990-05-14")
        
        # Should fail due to case mismatch
        assert "doesn't match" in response["message"].lower()
        assert not agent.state.is_verified


class TestAPIErrors:
    """Test handling of API errors."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_api_timeout(self, mock_lookup):
        """Test handling of API timeout."""
        mock_lookup.return_value = (False, None, "Request timed out. Please try again.")
        
        agent = Agent()
        agent.next("Hi")
        response = agent.next("ACC1001")
        
        assert "timed out" in response["message"].lower() or "try again" in response["message"].lower()
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_api_connection_error(self, mock_lookup):
        """Test handling of connection error."""
        mock_lookup.return_value = (False, None, "Could not connect to the server.")
        
        agent = Agent()
        agent.next("Hi")
        response = agent.next("ACC1001")
        
        assert "connect" in response["message"].lower() or "server" in response["message"].lower()


class TestStateRecovery:
    """Test that agent maintains state correctly."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_repeated_information(self, mock_lookup):
        """Test that providing information multiple times doesn't break state."""
        account_data = AccountData(
            account_id="ACC1001",
            full_name="Nithin Jain",
            dob="1990-05-14",
            aadhaar_last4="4321",
            pincode="400001",
            balance=Decimal("1250.75")
        )
        mock_lookup.return_value = (True, account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        
        # Provide name again
        agent.next("My name is Nithin Jain")
        
        # Should still work
        response = agent.next("1990-05-14")
        assert "verified" in response["message"].lower()
