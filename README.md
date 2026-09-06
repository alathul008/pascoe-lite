# 🔁 Pascoe-Lite

**Autonomous Payment Failure Recovery Engine — Razorpay AI Buildathon | Track: AI Revenue Recovery**

Pascoe-Lite is a Streamlit prototype that analyzes simulated failed-payment webhook telemetry and generates a tailored recovery strategy with an independent rule-based safety layer.

> **Demo / portfolio project:** The webhook events and customer/payment identifiers in this repository are synthetic. This prototype does not process real customer payment data and is not an official Razorpay integration.

## What it demonstrates

- Failure-aware payment recovery reasoning
- Simulated payment-failure webhook ingestion
- Gemini 2.5 Flash structured JSON generation
- Context-specific recovery strategies
- Hinglish customer messaging for user drop-off scenarios
- Professional English messaging for structural/technical failures
- Independent deterministic guardrails that can override the model
- Sensitive-data, false-urgency, guarantee, and risk-code checks
- Streamlit dashboard for interactive demonstration

## Architecture

```text
Simulated Failed Webhook
          │
          ▼
   Failure Telemetry
          │
          ▼
   Gemini 2.5 Flash
          │
          ▼
 Structured Recovery JSON
          │
          ▼
Independent Rule-Based
     Guardrail Layer
          │
     ┌────┴────┐
     ▼         ▼
   Safe       Hold
     │         │
     ▼         ▼
Customer     Manual
 Message      Review
```

## Demo scenarios

1. **UPI Timeout** — gateway/PSP timeout with a user-drop-off recovery path.
2. **Insufficient Funds Card Decline** — balance-related card failure with an alternative-payment recommendation.
3. **OTP Dropoff** — incomplete 3DS/OTP authentication with a retry/re-authentication strategy.

## Guardrail design

The model is **not trusted to decide its own safety status**.

After Gemini returns a structured response, Pascoe-Lite independently checks the customer-facing message for:

- Sensitive financial information
- CVV/PIN/password/OTP exposure
- Excessive numeric financial data
- False urgency or coercive language
- Unsubstantiated guarantees
- Risk/fraud-related error codes

The deterministic layer can downgrade `Safe to deploy` → `Hold`, but it never upgrades `Hold` → `Safe`.

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/alathul008/pascoe-lite.git
cd pascoe-lite
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the app

```bash
streamlit run app.py
```

The app asks for the Gemini API key at runtime, so the key is not stored in the repository.

## Security note

**Never commit a real Gemini, AWS, Razorpay, or other API credential.** Use environment variables or a local secrets file and keep them excluded through `.gitignore`.

## Screenshots

### UPI timeout
![UPI timeout demo](screenshots/upi-timeout.png)

### Insufficient funds
![Insufficient funds demo](screenshots/insufficient-funds.png)

### OTP drop-off
![OTP drop-off demo](screenshots/otp-dropoff.png)

## Tech stack

- Python
- Streamlit
- Google Gemini API (`google-genai`)
- JSON
- Regular-expression based deterministic guardrails

## License

MIT
