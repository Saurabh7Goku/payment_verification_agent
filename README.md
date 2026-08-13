# Payment Collection AI Agent

A production-ready conversational AI agent for handling end-to-end payment collection workflows. Built with a hybrid architecture combining LLM-based natural language understanding with deterministic business logic for security-critical operations.

## 🚀 Quick Start for Recruiters

### Option A: Using OpenAI GPT Models (Recommended if you have OpenAI access)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env

# 3. Edit .env and add your OpenAI API key
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4o-mini

# 4. Run the agent
python src/cli.py
```

### Option B: Using OpenRouter (Free - No Credit Card Required)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Get a free API key from https://openrouter.ai/keys

# 3. Configure environment
cp .env.example .env

# 4. Edit .env and add your OpenRouter API key
# LLM_PROVIDER=openrouter
# OPENROUTER_API_KEY=sk-or-v1-your-key-here
# OPENROUTER_MODEL=poolside/laguna-xs-2.1:free

# 5. Run the agent
python src/cli.py
```

**Test with this conversation:**
```
You: Hi
Agent: Hello! I'm here to help you with your payment. Please share your account ID to get started.

You: ACC1001
Agent: Could you please confirm your full name for verification?

You: Nithin Jain
Agent: For verification, could you please provide your date of birth...

You: 1990-05-14
Agent: Identity verified. Your outstanding balance is ₹1,250.75. How much would you like to pay today?

You: 500
Agent: Great! I'll process a payment of ₹500. Please provide your card details...

You: Card: 4532015112830366, CVV: 123, Expiry: 12/2027, Name: Nithin Jain
Agent: Payment successful! Your transaction ID is [txn_id]. Thank you for your payment!
```

## Overview

This agent conducts a structured payment collection conversation:
1. Greets user and collects account ID
2. Looks up account via API
3. Verifies user identity (name + secondary factor)
4. Shares outstanding balance
5. Collects payment amount
6. Collects card details
7. Processes payment
8. Communicates outcome and closes

## Architecture

**Hybrid Design:**
- **LLM**: Extracts structured data from natural language, handles conversational variations
- **Deterministic Python**: Controls state transitions, verification, validation, API calls, authorization

**Key Principle:** Security-critical decisions (verification, payment authorization) are NEVER delegated to the LLM.

## Project Structure

```
payment-agent/
├── src/                  # Source code
│   ├── __init__.py       # Package initialization
│   ├── agent.py          # Main Agent class with state machine
│   ├── models.py         # Pydantic data models and enums
│   ├── extraction.py     # LLM-based data extraction
│   ├── validators.py     # Payment validation logic
│   ├── cli.py            # Interactive command-line interface
│   ├── tools/            # API clients
│   │   ├── __init__.py
│   │   ├── account.py    # Account lookup API client
│   │   └── payment.py    # Payment processing API client
│   ├── tests/            # Comprehensive test suite
│   │   ├── test_agent.py
│   │   ├── test_verification.py
│   │   ├── test_payment.py
│   │   └── test_edge_cases.py
│   └── eval/             # Evaluation framework
│       ├── scenarios.json # Test scenarios
│       └── run_eval.py   # Evaluation runner
├── docs/                 # Documentation
│   ├── DESIGN.md         # Architecture & design decisions
│   ├── QUICKSTART.md     # Quick start guide
│   ├── sample_conversations.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── SUBMISSION_CHECKLIST.md
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
└── verify_setup.py       # Setup verification script
```

## Setup

### Prerequisites

- Python 3.11 or higher
- API key for one of the following:
  - **OpenRouter** ([Get one here](https://openrouter.ai/keys)) - Free
  - **OpenAI**

### Installation

1. Clone the repository:
```bash
git clone <https://github.com/Saurabh7Goku/payment_verification_agent>
cd payment_verification_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and configure your LLM provider:

**Option A: Using OpenRouter (Free models available)**
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=poolside/laguna-xs-2.1:free
```

**Option B: Using OpenAI GPT models**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Usage

### LLM Provider Configuration

This agent supports two LLM providers:

**OpenRouter** (Default)
- Access to multiple open-source models
- Free tier available
- Models: `poolside/laguna-xs-2.1:free`, `nvidia/nemotron-3.5-lightning:free`, etc.
- Get API key: https://openrouter.ai/keys

**OpenAI**
- Direct access to GPT models
- Requires paid account
- Models: `gpt-4o-mini`
- Get API key: https://platform.openai.com/api-keys

Configure via `.env` file:
```env
# For OpenRouter
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-xxx
OPENROUTER_MODEL=poolside/laguna-xs-2.1:free

# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini
```

### Interactive CLI

Run the agent in interactive mode:

```bash
python src/cli.py
```

Example conversation:
```
Agent: Hello! I'm here to help you with your payment. Please share your account ID to get started.
You: My account is ACC1001
Agent: Got it. Could you please confirm your full name?
You: Nithin Jain
Agent: Thanks. For verification, could you please provide your date of birth...
```

### Programmatic Usage

```python
from src.agent import Agent

agent = Agent()

response = agent.next("Hi")
print(response["message"])

response = agent.next("My account ID is ACC1001")
print(response["message"])

# ... continue conversation
```

## Testing

Run the full test suite:

```bash
pytest src/tests/ -v
```

Run specific test files:

```bash
pytest src/tests/test_agent.py -v
pytest src/tests/test_verification.py -v
pytest src/tests/test_payment.py -v
pytest src/tests/test_edge_cases.py -v
```

### Test Coverage

The test suite includes:
- **Happy path scenarios**: Successful payment flows
- **Account lookup**: Valid/invalid accounts, API errors
- **Verification**: All combinations of identity factors, retries, limits
- **Payment validation**: Amount checks, card validation, expiry checks
- **Edge cases**: Leap year DOB, zero balance, long names, natural language variations
- **Security**: Sensitive data handling, verification enforcement
- **Out-of-order information**: Multiple fields provided at once
- **Failure handling**: Various API and validation failures

## Evaluation

Run the automated evaluation suite:

```bash
python src/eval/run_eval.py
```

This executes 15+ scenarios covering:
- Successful payments (full and partial)
- Verification with different factors (DOB, Aadhaar, pincode)
- Verification failures and retries
- Edge cases (leap year, zero balance, long names)
- Natural language variations
- Out-of-order information handling
- Case sensitivity

Results are saved to `src/eval/results.json`.

## Sample Test Accounts

| Account ID | Full Name | DOB | Aadhaar Last 4 | Pincode | Balance |
|------------|-----------|-----|----------------|---------|---------|
| ACC1001 | Nithin Jain | 1990-05-14 | 4321 | 400001 | ₹1,250.75 |
| ACC1002 | Rajarajeswari Balasubramaniam | 1985-11-23 | 9876 | 400002 | ₹540.00 |
| ACC1003 | Priya Agarwal | 1992-08-10 | 2468 | 400003 | ₹0.00 |
| ACC1004 | Rahul Mehta | 1988-02-29 | 1357 | 400004 | ₹3,200.50 |

## Example Conversations

### A. Successful Payment

```
User: Hi
Agent: Hello! I'm here to help you with your payment. Please share your account ID to get started.

User: My account ID is ACC1001
Agent: Got it. Could you please confirm your full name?

User: Nithin Jain
Agent: Thanks. For verification, could you please provide your date of birth...

User: 1990-05-14
Agent: Identity verified. Your outstanding balance is ₹1,250.75. How much would you like to pay today?

User: I want to pay 500
Agent: Great! I'll process a payment of ₹500. Please provide your card details...

User: Card number is 4532015112830366, CVV is 123, expires 12/2027, name is Nithin Jain
Agent: Payment successful! Your transaction ID is txn_1762510325322_l1fl4oy. You've paid ₹500 towards your account. Thank you for your payment!
```

### B. Verification Failure with Retry

```
User: Hi
Agent: Hello! I'm here to help you with your payment...

User: ACC1001
Agent: Got it. Could you please confirm your full name?

User: John Doe
Agent: Thanks. For verification, could you please provide your date of birth...

User: 1990-05-14
Agent: The name you provided doesn't match our records. You have 2 attempt(s) remaining. Please provide your full name as it appears on your account.

User: Nithin Jain
Agent: Thanks. For verification, could you please provide your date of birth...

User: 1990-05-14
Agent: Identity verified. Your outstanding balance is ₹1,250.75...
```

### C. Natural Language Variations

```
User: Hey there
Agent: Hello! I'm here to help you with your payment...

User: yeah my account number is ACC1001 I think
Agent: Got it. Could you please confirm your full name?

User: it's Nithin, Nithin Jain
Agent: Thanks. For verification...

User: I was born on 14th May 1990
Agent: Identity verified. Your outstanding balance is ₹1,250.75...

User: can I do 500 for now?
Agent: Great! I'll process a payment of ₹500...

User: the card number is 4532 0151 1283 0366, CVV is one two three, expires December 2027, name Nithin Jain
Agent: Payment successful! Your transaction ID is...
```

### D. Payment Failure - Invalid Card

```
[... after verification ...]

User: Card: 1234567890123456, CVV: 123, Exp: 12/2027, Name: Nithin Jain
Agent: There's an issue with your card details: Invalid card number (failed Luhn check). Please provide correct information.

User: Card: 4532015112830366, CVV: 123, Exp: 12/2027, Name: Nithin Jain
Agent: Payment successful!...
```

### E. Out-of-Order Information

```
User: Hi, my account is ACC1001 and my name is Nithin Jain
Agent: Thanks. For verification, could you please provide your date of birth...

User: 1990-05-14
Agent: Identity verified. Your outstanding balance is ₹1,250.75...
```

### F. Leap Year DOB (ACC1004)

```
User: Hi
Agent: Hello!...

User: ACC1004
Agent: Got it. Could you please confirm your full name?

User: Rahul Mehta
Agent: Thanks. For verification...

User: 1988-02-29
Agent: Identity verified. Your outstanding balance is ₹3,200.50...
```

## Design Decisions

### 1. Why Hybrid Architecture?

**LLM Strengths:**
- Parsing natural language ("I was born on 14th May 1990" → "1990-05-14")
- Handling variations ("card number is 4532 0151 1283 0366" → "4532015112830366")
- Extracting intent from conversational input

**Deterministic Code Strengths:**
- Exact verification logic (no fuzzy matching)
- State machine control
- Security enforcement
- Retry limits
- Payment validation

**Result:** LLM for understanding, Python for control.

### 2. Why Explicit State Machine?

- Clear, testable state transitions
- No ambiguity about workflow progress
- Easy to add validation at each state
- Prevents skipping mandatory steps
- Enforceable security boundaries

### 3. Why Deterministic Verification?

Verification is security-critical. LLMs:
- Can be unpredictable
- May apply fuzzy matching inappropriately
- Could be prompt-injected
- Are not deterministic

Result: Verification uses exact string matching in Python, not LLM judgment.

### 4. Why Decimal for Money?

Floating point arithmetic can introduce rounding errors. Using `Decimal` ensures exact precision for financial calculations.

### 5. Security Measures

- Sensitive data (DOB, Aadhaar, pincode) never exposed to user
- CVV cleared from memory immediately after API call
- Card numbers validated (Luhn check) before API call
- Verification required before payment
- No LLM in authorization decisions
- Proper input validation at every step

## Known Limitations

1. **LLM Dependency**: Requires OpenAI API; extraction quality depends on model
2. **Single Session**: No persistence across restarts
3. **English Only**: Designed for English language input
4. **API Mocking**: Tests use mocked APIs; integration tests would require live endpoints
5. **Name Matching**: Strict case-sensitive matching; real systems might need fuzzy logic with appropriate safeguards

## Future Improvements

With more time, I would add:

1. **Conversation History**: Maintain context across multiple sessions
2. **Multi-Language Support**: Support for Hindi, regional languages
3. **Retry Strategies**: Configurable retry limits per verification factor
4. **Logging & Monitoring**: Structured logging, metrics, alerting
5. **Authentication**: Secure session management
6. **Database**: Persist conversation state and audit trail
7. **Rate Limiting**: Protect against abuse
8. **PCI Compliance**: Full payment card industry compliance measures
9. **Alternative Payment Methods**: UPI, net banking, wallets
10. **Fallback to Human**: Escalation path when agent cannot proceed

## API Reference

### Base URL
```
https://se-payment-verification-api.service.external.usea2.aws.prodigaltech.com
```

### POST /api/lookup-account
Fetches account details by account ID.

**Request:**
```json
{"account_id": "ACC1001"}
```

**Response (200 OK):**
```json
{
  "account_id": "ACC1001",
  "full_name": "Nithin Jain",
  "dob": "1990-05-14",
  "aadhaar_last4": "4321",
  "pincode": "400001",
  "balance": 1250.75
}
```

### POST /api/process-payment
Processes a card payment.

**Request:**
```json
{
  "account_id": "ACC1001",
  "amount": 500.00,
  "payment_method": {
    "type": "card",
    "card": {
      "cardholder_name": "Nithin Jain",
      "card_number": "4532015112830366",
      "cvv": "123",
      "expiry_month": 12,
      "expiry_year": 2027
    }
  }
}
```

**Response (200 Success):**
```json
{
  "success": true,
  "transaction_id": "txn_1762510325322_l1fl4oy"
}
```

## License

This is a take-home assignment implementation.

## Contact

For questions or issues, please contact the repository owner.
