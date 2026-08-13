"""LLM-based extraction of structured data from natural language."""

import os
import re
from typing import Optional
from decimal import Decimal, InvalidOperation
from openai import OpenAI
from .models import ExtractedInput


class Extractor:
    """Extracts structured information from user input using LLM."""
    
    EXTRACTION_PROMPT = """You are a data extraction assistant for a payment collection system.

Extract structured information from the user's message. Follow these rules strictly:

1. Extract ONLY information explicitly present in the current message
2. Return null for any field not mentioned
3. Normalize data to the specified formats:
   - account_id: Remove spaces, convert to uppercase (e.g., "acc 1001" → "ACC1001")
   - full_name: Preserve exact capitalization and spacing
   - dob: Convert to YYYY-MM-DD format (e.g., "May 14, 1990" → "1990-05-14", "14-05-1990" → "1990-05-14")
   - aadhaar_last4: Extract last 4 digits only (e.g., "ends with 4321" → "4321")
   - pincode: Extract 6 digits, handle spaced input (e.g., "4 0 0 0 0 1" → "400001")
   - amount: Convert to decimal number (e.g., "a thousand rupees" → 1000.00, "five hundred" → 500.00)
   - card_number: Remove spaces and dashes (e.g., "4532 0151 1283 0366" → "4532015112830366")
   - cvv: Extract digits, handle spelled out (e.g., "one two three" → "123")
   - expiry_month: Extract month as integer 1-12 (e.g., "December" → 12, "12/27" → 12)
   - expiry_year: Extract 4-digit year (e.g., "2027", "27" → 2027, "December 2027" → 2027)
   - cardholder_name: Extract name as provided

4. Handle natural language variations:
   - "my account is ACC1001" → account_id: "ACC1001"
   - "I was born on 14th May 1990" → dob: "1990-05-14"
   - "last four of Aadhaar is 4321" → aadhaar_last4: "4321"
   - "I want to pay a thousand rupees" → amount: 1000.00
   - "just clear the full amount" → interpret as wanting to pay full balance, but set amount: null (caller will handle)
   - "card number is 4532 0151 1283 0366" → card_number: "4532015112830366"
   - "expires December 2027" → expiry_month: 12, expiry_year: 2027
   - "CVV is one two three" → cvv: "123"

5. Do NOT invent or guess missing information
6. Do NOT make verification decisions
7. Do NOT authorize payments
8. For amounts like "full amount", "complete balance", return null (the system will handle it)

Return a JSON object with these fields (use null for absent fields):
{
  "account_id": string or null,
  "full_name": string or null,
  "dob": string (YYYY-MM-DD) or null,
  "aadhaar_last4": string (4 digits) or null,
  "pincode": string (6 digits) or null,
  "amount": number or null,
  "card_number": string (digits only) or null,
  "cvv": string (digits only) or null,
  "expiry_month": integer (1-12) or null,
  "expiry_year": integer (4-digit year) or null,
  "cardholder_name": string or null
}"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning:free")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def extract(self, user_input: str, context: Optional[str] = None) -> ExtractedInput:
        """
        Extract structured data from user input.
        
        Args:
            user_input: The user's message
            context: Optional context about what information is being collected
        
        Returns:
            ExtractedInput with parsed fields
        """
        try:
            # Add context hint if provided
            context_hint = ""
            if context:
                context_hint = f"\n\nContext: {context}\nIf the user provides just numbers or simple data, interpret based on this context."
            
            # Build the message
            messages = [
                {"role": "system", "content": self.EXTRACTION_PROMPT + context_hint},
                {"role": "user", "content": user_input}
            ]
            
            # Call OpenRouter API via OpenAI-compatible interface
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            if not content or content.strip() == "":
                print("Extraction warning: Empty response from LLM")
                return self._fallback_extraction(user_input, context)
            
            # Clean the content - sometimes models add markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            
            # Parse JSON and create ExtractedInput
            import json
            data = json.loads(content)
            
            # Convert amount to Decimal if present
            if data.get("amount") is not None:
                try:
                    data["amount"] = Decimal(str(data["amount"]))
                except (InvalidOperation, ValueError):
                    data["amount"] = None
            
            llm_result = ExtractedInput(**data)
            
            # If LLM returned all nulls, try fallback extraction
            if self._is_empty_extraction(llm_result):
                print("LLM returned empty extraction, trying fallback...")
                fallback_result = self._fallback_extraction(user_input, context)
                # Use fallback if it found something
                if not self._is_empty_extraction(fallback_result):
                    return fallback_result
            
            return llm_result
        
        except json.JSONDecodeError as e:
            # JSON parsing failed - log what we received
            print(f"Extraction error: Invalid JSON from LLM")
            print(f"  Received: {content[:200] if 'content' in locals() else 'No content'}")
            return self._fallback_extraction(user_input, context)
        
        except Exception as e:
            # If extraction fails, return empty
            # Log the error in production
            print(f"Extraction error: {e}")
            return self._fallback_extraction(user_input, context)
    
    def _fallback_extraction(self, user_input: str, context: Optional[str] = None) -> ExtractedInput:
        """
        Fallback extraction using regex patterns when LLM fails.
        
        Args:
            user_input: The user's message
            context: Optional context about what's being collected
        
        Returns:
            ExtractedInput with any patterns matched
        """
        result = ExtractedInput()
        user_clean = user_input.strip()
        
        # Account ID pattern: ACC followed by digits
        acc_match = re.search(r'\b(ACC\s*\d{4})\b', user_input, re.IGNORECASE)
        if acc_match:
            result.account_id = acc_match.group(1).replace(' ', '').upper()
        
        # Date of birth: YYYY-MM-DD
        dob_match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', user_input)
        if dob_match:
            result.dob = dob_match.group(0)
        
        # 4 digits alone could be Aadhaar last 4 or pincode first 4
        four_digits = re.search(r'^\s*(\d{4})\s*$', user_clean)
        if four_digits:
            # If context suggests Aadhaar or verification, treat as Aadhaar
            if context and ('aadhaar' in context.lower() or 'verification' in context.lower()):
                result.aadhaar_last4 = four_digits.group(1)
            else:
                # Could be Aadhaar - set it anyway since it's 4 digits
                result.aadhaar_last4 = four_digits.group(1)
        
        # 6 digits - likely pincode
        six_digits = re.search(r'^\s*(\d{6})\s*$', user_clean)
        if six_digits:
            result.pincode = six_digits.group(1)
        
        # Amount patterns
        amount_match = re.search(r'\b(\d+(?:\.\d{2})?)\s*(?:rupees?|rs\.?|₹)?\b', user_input, re.IGNORECASE)
        if amount_match:
            try:
                result.amount = Decimal(amount_match.group(1))
            except:
                pass
        
        print(f"[FALLBACK] Extracted aadhaar_last4={result.aadhaar_last4}, pincode={result.pincode}")
        return result
    
    def _is_empty_extraction(self, extracted: ExtractedInput) -> bool:
        """Check if extraction result is completely empty."""
        return all([
            extracted.account_id is None,
            extracted.full_name is None,
            extracted.dob is None,
            extracted.aadhaar_last4 is None,
            extracted.pincode is None,
            extracted.amount is None,
            extracted.card_number is None,
            extracted.cvv is None,
            extracted.expiry_month is None,
            extracted.expiry_year is None,
            extracted.cardholder_name is None
        ])
    
    def detect_full_amount_intent(self, user_input: str) -> bool:
        """
        Detect if user wants to pay the full balance.
        
        This is a simple heuristic check.
        """
        lower_input = user_input.lower()
        full_amount_phrases = [
            "full amount",
            "complete amount",
            "entire amount",
            "full balance",
            "complete balance",
            "entire balance",
            "clear the full",
            "clear full",
            "pay all",
            "pay everything",
            "whole amount",
            "total amount",
            "total balance"
        ]
        
        return any(phrase in lower_input for phrase in full_amount_phrases)
    
    def generate_contextual_response(
        self, 
        user_input: str, 
        base_message: str, 
        context: Optional[str] = None
    ) -> str:
        """
        Generate a natural, contextual response using pattern matching and templates.
        Varies responses based on user's specific input.
        
        Args:
            user_input: What the user just said
            base_message: The core information/request we need to convey
            context: Optional context about current conversation state
        
        Returns:
            A natural, friendly response
        """
        user_lower = user_input.lower().strip()
        
        # Pattern detection
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        help_requests = ["help", "assist", "support", "need"]
        questions = ["what", "how", "why", "when", "where", "can you", "could you", "would you"]
        confirmations = ["ok", "okay", "sure", "yes", "alright", "fine", "proceed", "continue", "go ahead"]
        
        is_greeting = any(greet in user_lower for greet in greetings)
        is_help_request = any(word in user_lower for word in help_requests)
        is_question = any(q in user_lower for q in questions)
        is_confirmation = user_lower in confirmations or len(user_lower) <= 5
        
        # ACCOUNT ID COLLECTION
        if "account id" in base_message.lower():
            if is_greeting and not is_help_request:
                return "Hello! To help you with your payment, I'll need your account ID. Could you share that with me?"
            elif is_help_request:
                return "I'm here to help! To get started with your payment, could you please provide your account ID?"
            elif is_question:
                return "To assist you, I'll need your account ID first. It should be in the format ACC followed by numbers."
            elif "thank" in user_lower:
                return "You're welcome! Now, could you please provide your account ID to proceed?"
            elif is_confirmation:
                return "Great! Could you please share your account ID? It should be in the format ACC followed by numbers."
            else:
                return "I'll need your account ID to proceed. Could you please provide it? It should be in the format ACC followed by numbers."
        
        # NAME COLLECTION
        elif "full name" in base_message.lower():
            if is_greeting:
                return "Hello! For verification, could you please confirm your full name?"
            elif is_question:
                return "I need your full name to verify your identity. Could you please share it?"
            elif len(user_lower) > 30:  # Longer response
                return "Thank you for that. Now, could you please confirm your full name for verification?"
            elif is_confirmation:
                return "Perfect! Could you please confirm your full name?"
            else:
                return "Got it. Could you please confirm your full name for verification?"
        
        # SECONDARY VERIFICATION (DOB, Aadhaar, Pincode)
        elif "date of birth" in base_message.lower() or "aadhaar" in base_message.lower() or "pincode" in base_message.lower():
            if is_greeting:
                return "Hello! For verification, I need one more detail: your date of birth (YYYY-MM-DD), last 4 digits of Aadhaar, or your pincode."
            elif is_question:
                return "I need one more piece of information to verify your identity. Could you provide your date of birth (YYYY-MM-DD), last 4 digits of Aadhaar, or pincode?"
            elif "what" in user_lower and ("else" in user_lower or "more" in user_lower or "next" in user_lower):
                return "For verification, I'll need one more detail: your date of birth (YYYY-MM-DD), the last 4 digits of your Aadhaar, or your pincode."
            elif is_confirmation:
                return "Great! I need one more detail for verification: your date of birth (YYYY-MM-DD), last 4 digits of Aadhaar, or pincode."
            else:
                return "Thanks! For verification, could you provide your date of birth (YYYY-MM-DD), last 4 digits of Aadhaar, or your pincode?"
        
        # PAYMENT AMOUNT
        elif "how much" in base_message.lower() or ("pay" in base_message.lower() and "amount" in base_message.lower()):
            if is_greeting:
                return "Hello! Your balance is ready. How much would you like to pay today?"
            elif is_question:
                return "You can pay any amount up to your outstanding balance. What amount would you like to pay?"
            elif is_confirmation or "ready" in user_lower or "proceed" in user_lower:
                return "Perfect! How much would you like to pay today? You can pay any amount up to your balance."
            else:
                return "Please let me know how much you'd like to pay. You can pay any amount up to your outstanding balance."
        
        # CARD DETAILS
        elif "card" in base_message.lower() and "details" in base_message.lower():
            # Check if asking for specific missing items
            if "I still need the following:" in base_message:
                items = base_message.split("I still need the following:")[1].split(".")[0].strip()
                if is_question and ("next" in user_lower or "now" in user_lower):
                    return f"Next, I need these card details: {items}. Could you provide them?"
                elif is_confirmation:
                    return f"Perfect! I just need: {items}."
                else:
                    return f"I still need these card details: {items}. Please provide them."
            else:
                if is_question and ("next" in user_lower or "what" in user_lower):
                    return "Next, I'll need your card information: card number, CVV, expiry date, and cardholder name."
                elif is_confirmation:
                    return "Great! Now I'll need your card details: card number, CVV, expiry date, and cardholder name."
                else:
                    return "I'll need your card information to process the payment: card number, CVV, expiry date, and cardholder name."
        
        # For everything else, use the base message
        return base_message
