"""Payment processing API client."""

import os
import requests
from typing import Optional, Tuple
from decimal import Decimal
from ..models import PaymentResponse


class PaymentAPIError(Exception):
    """Base exception for payment API errors."""
    pass


class PaymentAPI:
    """Client for payment processing API."""
    
    # Error code mappings to user-friendly messages
    ERROR_MESSAGES = {
        "account_not_found": "Account not found",
        "invalid_amount": "Invalid payment amount",
        "insufficient_balance": "Payment amount exceeds your outstanding balance",
        "invalid_card": "Invalid card number",
        "invalid_cvv": "Invalid CVV",
        "invalid_expiry": "Card has expired or expiry date is invalid",
    }
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url or os.getenv(
            "API_BASE_URL",
            "https://se-payment-verification-api.service.external.usea2.aws.prodigaltech.com"
        )
        self.timeout = timeout
    
    def process_payment(
        self,
        account_id: str,
        amount: Decimal,
        cardholder_name: str,
        card_number: str,
        cvv: str,
        expiry_month: int,
        expiry_year: int
    ) -> Tuple[bool, Optional[PaymentResponse], Optional[str]]:
        """
        Process a card payment.
        
        Returns:
            Tuple of (success, payment_response, error_message)
        """
        url = f"{self.base_url}/api/process-payment"
        
        # Construct payload
        payload = {
            "account_id": account_id,
            "amount": float(amount),  # API expects float
            "payment_method": {
                "type": "card",
                "card": {
                    "cardholder_name": cardholder_name,
                    "card_number": card_number,
                    "cvv": cvv,
                    "expiry_month": expiry_month,
                    "expiry_year": expiry_year
                }
            }
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                payment_response = PaymentResponse(
                    success=data.get("success", True),
                    transaction_id=data.get("transaction_id")
                )
                return True, payment_response, None
            
            elif response.status_code == 422:
                # Payment failed with specific error code
                data = response.json()
                error_code = data.get("error_code", "unknown_error")
                error_msg = self.ERROR_MESSAGES.get(
                    error_code,
                    f"Payment failed: {error_code}"
                )
                
                payment_response = PaymentResponse(
                    success=False,
                    error_code=error_code
                )
                return False, payment_response, error_msg
            
            else:
                return False, None, f"Unexpected error: HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, None, "Payment request timed out. Please try again."
        
        except requests.exceptions.ConnectionError:
            return False, None, "Could not connect to payment server. Please try again later."
        
        except requests.exceptions.RequestException as e:
            return False, None, f"Network error: {str(e)}"
        
        except (KeyError, ValueError) as e:
            return False, None, f"Invalid response from server: {str(e)}"
