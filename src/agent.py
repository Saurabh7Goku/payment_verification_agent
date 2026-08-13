"""Main Payment Collection AI Agent."""

import os
from decimal import Decimal
from typing import Optional
from dotenv import load_dotenv

from .models import State, ConversationState, ExtractedInput, AccountData
from .extraction import Extractor
from .validators import (
    validate_account_id,
    validate_amount,
    validate_card_number,
    validate_cvv,
    validate_expiry,
    validate_dob,
    mask_card_number
)
from .tools.account import AccountAPI
from .tools.payment import PaymentAPI


# Load environment variables
load_dotenv()


class Agent:
    """Payment collection conversational agent."""
    
    def __init__(self):
        """Initialize the agent with fresh state."""
        self.state = ConversationState()
        self.extractor = Extractor()
        self.account_api = AccountAPI()
        self.payment_api = PaymentAPI()
        self.last_user_input = ""
    
    def next(self, user_input: str) -> dict:
        """
        Process one turn of the conversation.
        
        Args:
            user_input: The user's message as a plain string
        
        Returns:
            {"message": str}
        """
        # Special handling for START state - just greet and transition
        if self.state.current_state == State.START:
            self.state.current_state = State.COLLECT_ACCOUNT_ID
            return {"message": "Hello! I'm here to help you with your payment. Please share your account ID to get started."}
        
        # Store user input for contextual responses
        self.last_user_input = user_input
        
        # Determine context for extraction based on current state
        extraction_context = self._get_extraction_context()
        
        # Extract structured information from user input
        extracted = self.extractor.extract(user_input, context=extraction_context)
        
        # Update state with any newly extracted information
        self._update_collected_info(extracted, user_input)
        
        # Process based on current state
        response = self._process_state()
        
        return {"message": response}
    
    def _get_extraction_context(self) -> str:
        """Get context hint for extraction based on current state."""
        if self.state.current_state == State.COLLECT_ACCOUNT_ID:
            return "Collecting account ID (format: ACC followed by numbers)"
        elif self.state.current_state == State.COLLECT_IDENTITY:
            if not self.state.provided_name:
                return "Collecting user's full name for verification"
            else:
                return "Collecting verification info: date of birth (YYYY-MM-DD), Aadhaar last 4 digits, or 6-digit pincode"
        elif self.state.current_state == State.COLLECT_PAYMENT_AMOUNT:
            return "Collecting payment amount in rupees"
        elif self.state.current_state == State.COLLECT_CARD_DETAILS:
            return "Collecting card payment details: card number, CVV, expiry date, cardholder name"
        else:
            return ""
    
    def _update_collected_info(self, extracted: ExtractedInput, raw_input: str):
        """Update conversation state with extracted information."""
        
        # Debug: Print what was extracted
        print(f"[EXTRACTION] From '{raw_input}':")
        print(f"  - account_id: {extracted.account_id}")
        print(f"  - full_name: {extracted.full_name}")
        print(f"  - dob: {extracted.dob}")
        print(f"  - aadhaar_last4: {extracted.aadhaar_last4}")
        print(f"  - pincode: {extracted.pincode}")
        print(f"  - amount: {extracted.amount}")
        
        # Account ID
        if extracted.account_id and not self.state.account_id:
            self.state.account_id = extracted.account_id
        
        # Identity information
        if extracted.full_name and not self.state.provided_name:
            self.state.provided_name = extracted.full_name
        
        if extracted.dob and not self.state.provided_dob:
            self.state.provided_dob = extracted.dob
        
        if extracted.aadhaar_last4 and not self.state.provided_aadhaar_last4:
            self.state.provided_aadhaar_last4 = extracted.aadhaar_last4
        
        if extracted.pincode and not self.state.provided_pincode:
            self.state.provided_pincode = extracted.pincode
        
        # Payment amount
        if extracted.amount is not None and not self.state.payment_amount:
            self.state.payment_amount = extracted.amount
        elif self.extractor.detect_full_amount_intent(raw_input) and self.state.account_data:
            # User wants to pay full balance
            self.state.payment_amount = self.state.account_data.balance
        
        # Card details
        if extracted.card_number and not self.state.card_number:
            self.state.card_number = extracted.card_number
        
        if extracted.cvv and not self.state.cvv:
            self.state.cvv = extracted.cvv
        
        if extracted.expiry_month and not self.state.expiry_month:
            self.state.expiry_month = extracted.expiry_month
        
        if extracted.expiry_year and not self.state.expiry_year:
            self.state.expiry_year = extracted.expiry_year
        
        if extracted.cardholder_name and not self.state.cardholder_name:
            self.state.cardholder_name = extracted.cardholder_name
    
    def _contextual_response(self, base_message: str, context: Optional[str] = None) -> str:
        """Generate a contextual response based on user's last input."""
        if not self.last_user_input:
            return base_message
        
        # Check if it's a simple acknowledgment or greeting that doesn't need contextualization
        simple_inputs = ["ok", "okay", "yes", "sure", "proceed", "continue", "go ahead"]
        if self.last_user_input.lower().strip() in simple_inputs:
            return base_message
        
        return self.extractor.generate_contextual_response(
            self.last_user_input,
            base_message,
            context
        )
    
    def _process_state(self) -> str:
        """Process current state and return appropriate response."""
        
        if self.state.current_state == State.START:
            return self._handle_start()
        
        elif self.state.current_state == State.COLLECT_ACCOUNT_ID:
            return self._handle_collect_account_id()
        
        elif self.state.current_state == State.LOOKUP_ACCOUNT:
            return self._handle_lookup_account()
        
        elif self.state.current_state == State.COLLECT_IDENTITY:
            return self._handle_collect_identity()
        
        elif self.state.current_state == State.VERIFY_IDENTITY:
            return self._handle_verify_identity()
        
        elif self.state.current_state == State.VERIFIED:
            return self._handle_verified()
        
        elif self.state.current_state == State.COLLECT_PAYMENT_AMOUNT:
            return self._handle_collect_payment_amount()
        
        elif self.state.current_state == State.COLLECT_CARD_DETAILS:
            return self._handle_collect_card_details()
        
        elif self.state.current_state == State.PROCESS_PAYMENT:
            return self._handle_process_payment()
        
        elif self.state.current_state == State.SUCCESS:
            return self._handle_success()
        
        elif self.state.current_state == State.FAILED:
            return self._handle_failed()
        
        elif self.state.current_state == State.TERMINATED:
            return self._handle_terminated()
        
        else:
            return "I encountered an unexpected error. Please start over."
    
    def _handle_start(self) -> str:
        """Handle START state."""
        self.state.current_state = State.COLLECT_ACCOUNT_ID
        return "Hello! I'm here to help you with your payment. Please share your account ID to get started."
    
    def _handle_collect_account_id(self) -> str:
        """Handle COLLECT_ACCOUNT_ID state."""
        if not self.state.account_id:
            base_message = "I didn't catch your account ID. Could you please provide it? It should be in the format ACC followed by numbers."
            return self._contextual_response(
                base_message, 
                context="User needs to provide their account ID to proceed with payment"
            )
        
        # Validate account ID format
        is_valid, result = validate_account_id(self.state.account_id)
        if not is_valid:
            self.state.account_id = None
            return f"{result} Please provide a valid account ID."
        
        # Normalize the account ID
        self.state.account_id = result
        
        # Move to lookup
        self.state.current_state = State.LOOKUP_ACCOUNT
        return self._handle_lookup_account()
    
    def _handle_lookup_account(self) -> str:
        """Handle LOOKUP_ACCOUNT state."""
        # Call account lookup API
        success, account_data, error = self.account_api.lookup_account(self.state.account_id)
        
        if not success:
            self.state.current_state = State.FAILED
            self.state.error_message = error
            return f"I'm sorry, {error}. Please verify your account ID and try again."
        
        # Store account data
        self.state.account_data = account_data
        
        # Move to identity collection
        self.state.current_state = State.COLLECT_IDENTITY
        return self._handle_collect_identity()
    
    def _handle_collect_identity(self) -> str:
        """Handle COLLECT_IDENTITY state."""
        # Check what we have collected
        has_name = bool(self.state.provided_name)
        has_secondary = bool(
            self.state.provided_dob or 
            self.state.provided_aadhaar_last4 or 
            self.state.provided_pincode
        )
        
        # Debug: Print what we have
        print(f"[COLLECT_IDENTITY] has_name={has_name}, has_secondary={has_secondary}")
        print(f"  - provided_name: {self.state.provided_name}")
        print(f"  - provided_dob: {self.state.provided_dob}")
        print(f"  - provided_aadhaar_last4: {self.state.provided_aadhaar_last4}")
        print(f"  - provided_pincode: {self.state.provided_pincode}")
        
        if not has_name:
            base_message = "Could you please confirm your full name for verification?"
            return self._contextual_response(
                base_message,
                context="Need user's full name for identity verification"
            )
        
        if not has_secondary:
            base_message = "For verification, could you please provide your date of birth (in YYYY-MM-DD format), the last 4 digits of your Aadhaar, or your pincode?"
            return self._contextual_response(
                base_message,
                context="Need secondary verification factor (DOB, Aadhaar, or pincode)"
            )
        
        # We have both name and at least one secondary factor
        self.state.current_state = State.VERIFY_IDENTITY
        return self._handle_verify_identity()
    
    def _handle_verify_identity(self) -> str:
        """Handle VERIFY_IDENTITY state (deterministic verification)."""
        # This is a deterministic security check - no LLM involvement
        
        if not self.state.account_data:
            self.state.current_state = State.FAILED
            return "I encountered an error. Please start over."
        
        # Check retry limit
        if self.state.verification_attempts >= self.state.max_verification_attempts:
            self.state.current_state = State.TERMINATED
            return "I'm sorry, but verification has failed too many times. For security reasons, this session has been terminated. Please contact support for assistance."
        
        # Increment attempts
        self.state.verification_attempts += 1
        
        # Strict name matching
        name_match = (
            self.state.provided_name == self.state.account_data.full_name
        )
        
        if not name_match:
            # Name doesn't match - ask to try again
            remaining = self.state.max_verification_attempts - self.state.verification_attempts
            if remaining > 0:
                # Clear the incorrect name so they can provide it again
                self.state.provided_name = None
                self.state.current_state = State.COLLECT_IDENTITY
                return f"The name you provided doesn't match our records. You have {remaining} attempt(s) remaining. Please provide your full name as it appears on your account."
            else:
                self.state.current_state = State.TERMINATED
                return "I'm sorry, but verification has failed. For security reasons, this session has been terminated. Please contact support for assistance."
        
        # Check secondary factors
        dob_match = (
            self.state.provided_dob and 
            self.state.provided_dob == self.state.account_data.dob
        )
        
        aadhaar_match = (
            self.state.provided_aadhaar_last4 and 
            self.state.provided_aadhaar_last4 == self.state.account_data.aadhaar_last4
        )
        
        pincode_match = (
            self.state.provided_pincode and 
            self.state.provided_pincode == self.state.account_data.pincode
        )
        
        secondary_match = dob_match or aadhaar_match or pincode_match
        
        if not secondary_match:
            # Secondary factor doesn't match
            remaining = self.state.max_verification_attempts - self.state.verification_attempts
            if remaining > 0:
                # Clear secondary factors
                self.state.provided_dob = None
                self.state.provided_aadhaar_last4 = None
                self.state.provided_pincode = None
                self.state.current_state = State.COLLECT_IDENTITY
                return f"The information you provided doesn't match our records. You have {remaining} attempt(s) remaining. Please provide your date of birth, Aadhaar last 4 digits, or pincode."
            else:
                self.state.current_state = State.TERMINATED
                return "I'm sorry, but verification has failed. For security reasons, this session has been terminated. Please contact support for assistance."
        
        # Verification successful!
        self.state.is_verified = True
        self.state.current_state = State.VERIFIED
        return self._handle_verified()
    
    def _handle_verified(self) -> str:
        """Handle VERIFIED state - user has been verified."""
        balance = self.state.account_data.balance
        self.state.current_state = State.COLLECT_PAYMENT_AMOUNT
        return f"Identity verified. Your outstanding balance is ₹{balance}. How much would you like to pay today?"
    
    def _handle_collect_payment_amount(self) -> str:
        """Handle COLLECT_PAYMENT_AMOUNT state."""
        # Security check: ensure verified
        if not self.state.is_verified:
            self.state.current_state = State.FAILED
            return "Verification required before proceeding with payment."
        
        if not self.state.payment_amount:
            base_message = "Please let me know how much you'd like to pay. You can pay any amount up to your outstanding balance."
            return self._contextual_response(
                base_message,
                context="Need payment amount from user"
            )
        
        # Validate amount
        is_valid, error = validate_amount(
            self.state.payment_amount,
            self.state.account_data.balance
        )
        
        if not is_valid:
            # Clear invalid amount
            self.state.payment_amount = None
            return f"{error}. Please provide a valid payment amount."
        
        # Amount is valid
        self.state.current_state = State.COLLECT_CARD_DETAILS
        return f"Great! I'll process a payment of ₹{self.state.payment_amount}. Please provide your card details - card number, CVV, expiry date, and cardholder name."
    
    def _handle_collect_card_details(self) -> str:
        """Handle COLLECT_CARD_DETAILS state."""
        # Security check: ensure verified
        if not self.state.is_verified:
            self.state.current_state = State.FAILED
            return "Verification required before proceeding with payment."
        
        # Check what card details we still need
        missing = []
        
        if not self.state.card_number:
            missing.append("card number")
        if not self.state.cvv:
            missing.append("CVV")
        if not self.state.expiry_month or not self.state.expiry_year:
            missing.append("expiry date")
        if not self.state.cardholder_name:
            missing.append("cardholder name")
        
        if missing:
            base_message = f"I still need the following: {', '.join(missing)}. Please provide these details."
            return self._contextual_response(
                base_message,
                context=f"Need card details: {', '.join(missing)}"
            )
        
        # Validate all card details before proceeding
        validation_errors = []
        
        # Validate card number
        is_valid, result = validate_card_number(self.state.card_number)
        if not is_valid:
            validation_errors.append(result)
            self.state.card_number = None
        else:
            self.state.card_number = result  # Store normalized version
        
        # Validate CVV
        is_valid, result = validate_cvv(self.state.cvv, self.state.card_number)
        if not is_valid:
            validation_errors.append(result)
            self.state.cvv = None
        else:
            self.state.cvv = result
        
        # Validate expiry
        is_valid, error = validate_expiry(self.state.expiry_month, self.state.expiry_year)
        if not is_valid:
            validation_errors.append(error)
            self.state.expiry_month = None
            self.state.expiry_year = None
        
        if validation_errors:
            return f"There's an issue with your card details: {' '.join(validation_errors)}. Please provide correct information."
        
        # All card details are valid
        self.state.current_state = State.PROCESS_PAYMENT
        return self._handle_process_payment()
    
    def _handle_process_payment(self) -> str:
        """Handle PROCESS_PAYMENT state."""
        # Final security check: ensure verified
        if not self.state.is_verified:
            self.state.current_state = State.FAILED
            return "Verification required before proceeding with payment."
        
        # Process payment via API
        success, payment_response, error = self.payment_api.process_payment(
            account_id=self.state.account_id,
            amount=self.state.payment_amount,
            cardholder_name=self.state.cardholder_name,
            card_number=self.state.card_number,
            cvv=self.state.cvv,
            expiry_month=self.state.expiry_month,
            expiry_year=self.state.expiry_year
        )
        
        # Clear sensitive card data immediately after API call
        cvv_copy = self.state.cvv
        self.state.cvv = None
        
        if success and payment_response and payment_response.success:
            # Payment successful
            self.state.transaction_id = payment_response.transaction_id
            self.state.current_state = State.SUCCESS
            return self._handle_success()
        else:
            # Payment failed
            self.state.current_state = State.FAILED
            self.state.error_message = error
            
            # Determine if this is user-fixable
            if payment_response and payment_response.error_code in [
                "invalid_card", "invalid_cvv", "invalid_expiry"
            ]:
                # User can retry with correct details
                # Clear the invalid fields
                if payment_response.error_code == "invalid_card":
                    self.state.card_number = None
                elif payment_response.error_code == "invalid_cvv":
                    # CVV already cleared
                    pass
                elif payment_response.error_code == "invalid_expiry":
                    self.state.expiry_month = None
                    self.state.expiry_year = None
                
                self.state.current_state = State.COLLECT_CARD_DETAILS
                return f"Payment failed: {error}. Please provide correct card details."
            
            elif payment_response and payment_response.error_code == "insufficient_balance":
                # User can retry with a lower amount
                self.state.payment_amount = None
                self.state.current_state = State.COLLECT_PAYMENT_AMOUNT
                return f"Payment failed: {error}. Please provide a valid amount."
            
            else:
                # Terminal failure
                return self._handle_failed()
    
    def _handle_success(self) -> str:
        """Handle SUCCESS state."""
        message = (
            f"Payment successful! Your transaction ID is {self.state.transaction_id}. "
            f"You've paid ₹{self.state.payment_amount} towards your account. "
            f"Thank you for your payment!"
        )
        
        self.state.current_state = State.TERMINATED
        return message
    
    def _handle_failed(self) -> str:
        """Handle FAILED state."""
        error_msg = self.state.error_message or "An unexpected error occurred"
        message = (
            f"I'm sorry, but I couldn't process your payment. {error_msg}. "
            f"Please try again later or contact support for assistance."
        )
        
        self.state.current_state = State.TERMINATED
        return message
    
    def _handle_terminated(self) -> str:
        """Handle TERMINATED state."""
        return "This session has ended. If you need further assistance, please start a new conversation."
