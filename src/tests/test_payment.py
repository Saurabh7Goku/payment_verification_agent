"""Tests for payment processing."""

import pytest
from decimal import Decimal
from unittest.mock import patch
from src.agent import Agent
from src.models import AccountData, PaymentResponse


@pytest.fixture
def mock_account_data():
    """Mock account data."""
    return AccountData(
        account_id="ACC1001",
        full_name="Nithin Jain",
        dob="1990-05-14",
        aadhaar_last4="4321",
        pincode="400001",
        balance=Decimal("1250.75")
    )


@pytest.fixture
def verified_agent(mock_account_data):
    """Create an agent in verified state."""
    with patch('tools.account.AccountAPI.lookup_account') as mock_lookup:
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        agent.next("500")
        
        return agent


class TestPaymentSuccess:
    """Test successful payment scenarios."""
    
    @patch('tools.payment.PaymentAPI.process_payment')
    def test_valid_card_payment(self, mock_payment, verified_agent):
        """Test successful payment with valid card."""
        mock_payment.return_value = (
            True,
            PaymentResponse(success=True, transaction_id="txn_123"),
            None
        )
        
        response = verified_agent.next(
            "Card: 4532015112830366, CVV: 123, Exp: 12/2027, Name: Nithin Jain"
        )
        
        assert "successful" in response["message"].lower()
        assert "txn_123" in response["message"]


class TestPaymentFailures:
    """Test payment failure scenarios."""
    
    @patch('tools.payment.PaymentAPI.process_payment')
    def test_invalid_card(self, mock_payment, verified_agent):
        """Test handling of invalid card error."""
        mock_payment.return_value = (
            False,
            PaymentResponse(success=False, error_code="invalid_card"),
            "Invalid card number"
        )
        
        response = verified_agent.next(
            "Card: 4532015112830366, CVV: 123, Exp: 12/2027, Name: Nithin Jain"
        )
        
        assert "failed" in response["message"].lower()
        assert "card" in response["message"].lower()
    
    @patch('tools.payment.PaymentAPI.process_payment')
    def test_invalid_cvv(self, mock_payment, verified_agent):
        """Test handling of invalid CVV error."""
        mock_payment.return_value = (
            False,
            PaymentResponse(success=False, error_code="invalid_cvv"),
            "Invalid CVV"
        )
        
        response = verified_agent.next(
            "Card: 4532015112830366, CVV: 123, Exp: 12/2027, Name: Nithin Jain"
        )
        
        assert "failed" in response["message"].lower()
        assert "cvv" in response["message"].lower()
    
    @patch('tools.payment.PaymentAPI.process_payment')
    def test_expired_card(self, mock_payment, verified_agent):
        """Test handling of expired card error."""
        mock_payment.return_value = (
            False,
            PaymentResponse(success=False, error_code="invalid_expiry"),
            "Card has expired"
        )
        
        response = verified_agent.next(
            "Card: 4532015112830366, CVV: 123, Exp: 12/2020, Name: Nithin Jain"
        )
        
        assert "expired" in response["message"].lower() or "expiry" in response["message"].lower()
    
    @patch('tools.payment.PaymentAPI.process_payment')
    def test_insufficient_balance_error(self, mock_payment, verified_agent):
        """Test handling of insufficient balance error."""
        mock_payment.return_value = (
            False,
            PaymentResponse(success=False, error_code="insufficient_balance"),
            "Amount exceeds outstanding balance"
        )
        
        response = verified_agent.next(
            "Card: 4532015112830366, CVV: 123, Exp: 12/2027, Name: Nithin Jain"
        )
        
        assert "balance" in response["message"].lower()


class TestCardValidation:
    """Test card validation before API call."""
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_invalid_card_format(self, mock_lookup, mock_account_data):
        """Test rejection of invalid card format."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        agent.next("500")
        
        # Provide invalid card number
        response = agent.next("Card: 1234567890123456, CVV: 123, Exp: 12/2027, Name: Test")
        
        assert "card" in response["message"].lower()
        # Card should be rejected before API call
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_invalid_cvv_length(self, mock_lookup, mock_account_data):
        """Test rejection of invalid CVV length."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        agent.next("500")
        
        # Provide invalid CVV
        response = agent.next("Card: 4532015112830366, CVV: 12, Exp: 12/2027, Name: Test")
        
        assert "cvv" in response["message"].lower()
    
    @patch('tools.account.AccountAPI.lookup_account')
    def test_card_already_expired(self, mock_lookup, mock_account_data):
        """Test rejection of already expired card."""
        mock_lookup.return_value = (True, mock_account_data, None)
        
        agent = Agent()
        agent.next("Hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("1990-05-14")
        agent.next("500")
        
        # Provide expired card
        response = agent.next("Card: 4532015112830366, CVV: 123, Exp: 12/2020, Name: Test")
        
        assert "expired" in response["message"].lower()
