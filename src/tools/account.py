"""Account lookup API client."""

import os
import requests
from typing import Optional, Tuple
from decimal import Decimal
from ..models import AccountData


class AccountAPIError(Exception):
    """Base exception for account API errors."""
    pass


class AccountNotFoundError(AccountAPIError):
    """Account not found."""
    pass


class AccountAPI:
    """Client for account lookup API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url or os.getenv(
            "API_BASE_URL",
            "https://se-payment-verification-api.service.external.usea2.aws.prodigaltech.com"
        )
        self.timeout = timeout
    
    def lookup_account(self, account_id: str) -> Tuple[bool, Optional[AccountData], Optional[str]]:
        """
        Look up account by ID.
        
        Returns:
            Tuple of (success, account_data, error_message)
        """
        url = f"{self.base_url}/api/lookup-account"
        
        try:
            response = requests.post(
                url,
                json={"account_id": account_id},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                account_data = AccountData(
                    account_id=data["account_id"],
                    full_name=data["full_name"],
                    dob=data["dob"],
                    aadhaar_last4=data["aadhaar_last4"],
                    pincode=data["pincode"],
                    balance=Decimal(str(data["balance"]))
                )
                return True, account_data, None
            
            elif response.status_code == 404:
                error_data = response.json()
                error_msg = error_data.get("message", "Account not found")
                return False, None, error_msg
            
            else:
                return False, None, f"Unexpected error: HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, None, "Request timed out. Please try again."
        
        except requests.exceptions.ConnectionError:
            return False, None, "Could not connect to the server. Please try again later."
        
        except requests.exceptions.RequestException as e:
            return False, None, f"Network error: {str(e)}"
        
        except (KeyError, ValueError) as e:
            return False, None, f"Invalid response from server: {str(e)}"
