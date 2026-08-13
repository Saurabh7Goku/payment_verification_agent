"""Data models for the payment collection agent."""

from enum import Enum
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class State(str, Enum):
    """Agent conversation states."""
    START = "START"
    COLLECT_ACCOUNT_ID = "COLLECT_ACCOUNT_ID"
    LOOKUP_ACCOUNT = "LOOKUP_ACCOUNT"
    COLLECT_IDENTITY = "COLLECT_IDENTITY"
    VERIFY_IDENTITY = "VERIFY_IDENTITY"
    VERIFIED = "VERIFIED"
    COLLECT_PAYMENT_AMOUNT = "COLLECT_PAYMENT_AMOUNT"
    COLLECT_CARD_DETAILS = "COLLECT_CARD_DETAILS"
    PROCESS_PAYMENT = "PROCESS_PAYMENT"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class ExtractedInput(BaseModel):
    """Structured data extracted from user input by LLM."""
    account_id: Optional[str] = None
    full_name: Optional[str] = None
    dob: Optional[str] = None  # YYYY-MM-DD format
    aadhaar_last4: Optional[str] = None
    pincode: Optional[str] = None
    amount: Optional[Decimal] = None
    card_number: Optional[str] = None
    cvv: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    cardholder_name: Optional[str] = None


class AccountData(BaseModel):
    """Account information from lookup API."""
    account_id: str
    full_name: str
    dob: str
    aadhaar_last4: str
    pincode: str
    balance: Decimal


class ConversationState(BaseModel):
    """Complete conversation state maintained by the agent."""
    current_state: State = State.START
    
    # Collected information
    account_id: Optional[str] = None
    provided_name: Optional[str] = None
    provided_dob: Optional[str] = None
    provided_aadhaar_last4: Optional[str] = None
    provided_pincode: Optional[str] = None
    
    # Account data from API
    account_data: Optional[AccountData] = None
    
    # Verification
    is_verified: bool = False
    verification_attempts: int = 0
    max_verification_attempts: int = 3
    
    # Payment information
    payment_amount: Optional[Decimal] = None
    card_number: Optional[str] = None
    cvv: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    cardholder_name: Optional[str] = None
    
    # Transaction result
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = False


class PaymentMethod(BaseModel):
    """Payment method structure for API."""
    type: str = "card"
    card: dict


class PaymentRequest(BaseModel):
    """Payment API request."""
    account_id: str
    amount: Decimal
    payment_method: PaymentMethod


class PaymentResponse(BaseModel):
    """Payment API response."""
    success: bool
    transaction_id: Optional[str] = None
    error_code: Optional[str] = None
