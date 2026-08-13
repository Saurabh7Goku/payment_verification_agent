"""Validation utilities for payment information."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


def validate_account_id(account_id: str) -> Tuple[bool, Optional[str]]:
    """Validate account ID format."""
    if not account_id:
        return False, "Account ID cannot be empty"
    
    # Normalize: remove spaces, convert to uppercase
    normalized = account_id.strip().replace(" ", "").upper()
    
    # Basic format check (ACC followed by digits)
    if not re.match(r'^ACC\d+$', normalized):
        return False, "Account ID must be in format ACC followed by numbers"
    
    return True, normalized


def validate_amount(amount: Decimal, balance: Decimal) -> Tuple[bool, Optional[str]]:
    """Validate payment amount."""
    if amount <= 0:
        return False, "Amount must be greater than zero"
    
    # Check decimal places
    if amount.as_tuple().exponent < -2:
        return False, "Amount cannot have more than 2 decimal places"
    
    if amount > balance:
        return False, f"Amount ₹{amount} exceeds outstanding balance ₹{balance}"
    
    return True, None


def luhn_check(card_number: str) -> bool:
    """Validate card number using Luhn algorithm."""
    # Remove spaces and validate it's all digits
    card_number = card_number.replace(" ", "")
    
    if not card_number.isdigit():
        return False
    
    # Luhn algorithm
    digits = [int(d) for d in card_number]
    checksum = 0
    
    # Process from right to left
    for i in range(len(digits) - 1, -1, -1):
        digit = digits[i]
        
        # Double every second digit from right
        if (len(digits) - i) % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        
        checksum += digit
    
    return checksum % 10 == 0


def validate_card_number(card_number: str) -> Tuple[bool, Optional[str]]:
    """Validate card number format and Luhn check."""
    if not card_number:
        return False, "Card number is required"
    
    # Normalize: remove spaces
    normalized = card_number.replace(" ", "")
    
    # Check if it's all digits
    if not normalized.isdigit():
        return False, "Card number must contain only digits"
    
    # Check length (13-19 digits for most cards)
    if len(normalized) < 13 or len(normalized) > 19:
        return False, "Card number must be between 13 and 19 digits"
    
    # Luhn check
    if not luhn_check(normalized):
        return False, "Invalid card number (failed Luhn check)"
    
    return True, normalized


def validate_cvv(cvv: str, card_number: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validate CVV format."""
    if not cvv:
        return False, "CVV is required"
    
    # Normalize: remove spaces
    normalized = cvv.replace(" ", "")
    
    if not normalized.isdigit():
        return False, "CVV must contain only digits"
    
    # Standard cards: 3 digits, Amex: 4 digits
    # Check if it's Amex (starts with 34 or 37)
    is_amex = False
    if card_number:
        card_clean = card_number.replace(" ", "")
        if card_clean.startswith(("34", "37")):
            is_amex = True
    
    expected_length = 4 if is_amex else 3
    
    if len(normalized) != expected_length:
        if is_amex:
            return False, "CVV must be 4 digits for American Express"
        else:
            return False, "CVV must be 3 digits"
    
    return True, normalized


def validate_expiry(month: int, year: int) -> Tuple[bool, Optional[str]]:
    """Validate card expiry date."""
    if not month or not year:
        return False, "Expiry month and year are required"
    
    if month < 1 or month > 12:
        return False, "Expiry month must be between 1 and 12"
    
    # Handle 2-digit year (convert to 4-digit)
    if year < 100:
        year += 2000
    
    # Check if card has expired
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    if year < current_year:
        return False, "Card has expired"
    
    if year == current_year and month < current_month:
        return False, "Card has expired"
    
    return True, None


def validate_dob(dob_str: str) -> Tuple[bool, Optional[str]]:
    """Validate and normalize date of birth."""
    if not dob_str:
        return False, "Date of birth is required"
    
    try:
        # Try to parse the date
        date = datetime.strptime(dob_str, "%Y-%m-%d")
        
        # Basic sanity check
        if date.year < 1900 or date.year > datetime.now().year - 18:
            return False, "Invalid date of birth"
        
        return True, dob_str
    except ValueError:
        return False, "Date of birth must be in YYYY-MM-DD format"


def mask_card_number(card_number: str) -> str:
    """Mask card number for display/logging."""
    if len(card_number) < 4:
        return "****"
    return f"****{card_number[-4:]}"


def mask_cvv(cvv: str) -> str:
    """Mask CVV for display/logging."""
    return "***"
