import streamlit as st
from google import genai
import json
import re

st.set_page_config(page_title="Pascoe-Lite | Payment Recovery Engine", layout="wide")

FAILED_TRANSACTIONS = {
    "UPI Timeout": {
        "transaction_id": "pay_QW7xJ2kLmN9pRt",
        "event": "payment.failed",
        "amount": 149900,
        "currency": "INR",
        "method": "upi",
        "error_code": "GATEWAY_TIMEOUT",
        "error_description": "UPI collect request timed out after 90s, no response from PSP",
        "customer_vpa": "demo-user@synthetic-upi",
        "attempt_count": 1,
        "created_at": "2026-09-05T10:12:34Z"
    },
    "Insufficient Funds Card Decline": {
        "transaction_id": "pay_LK3vB8nWzQ4sYt",
        "event": "payment.failed",
        "amount": 899900,
        "currency": "INR",
        "method": "card",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Payment failed due to insufficient funds in the account",
        "card_network": "Visa",
        "card_last4": "4242",
        "attempt_count": 2,
        "created_at": "2026-09-05T11:45:02Z"
    },
    "OTP Dropoff": {
        "transaction_id": "pay_XP9dF1mCvB2eRz",
        "event": "payment.failed",
        "amount": 249900,
        "currency": "INR",
        "method": "card",
        "error_code": "OTP_TIMEOUT_ERROR",
        "error_description": "User did not complete 3DS/OTP authentication within allotted time",
        "card_network": "Mastercard",
        "card_last4": "8891",
        "attempt_count": 1,
        "created_at": "2026-09-05T12:03:19Z"
    }
}

SYSTEM_INSTRUCTION = """You are Pascoe-Lite, an autonomous payment failure recovery compliance engine for Razorpay merchants.
You will be given a raw failed transaction webhook payload. Your job is strict and non-negotiable:

1. Analyze the root cause of the failure using only the fields provided.
2. Propose a tailored recovery strategy appropriate to the failure type (e.g. retry timing, alternate payment method nudge, balance top-up reminder, re-authentication prompt).
3. Draft a High_Conversion_Message intended for the end customer:
   - If the failure is a user-dropoff type (UPI timeout, OTP dropoff, user abandonment) write it in a natural, warm Hinglish tone (Roman script, mixing Hindi and English as urban Indian users actually text).
   - If the failure is a structural/technical error (gateway error, bad request, systemic decline unrelated to user action) write it in clean, professional English.
4. Set Guardrail_Status to "Hold" if the message would need to reference sensitive financial details beyond last4/amount, imply guaranteed approval, pressure the user with false urgency, or if the error suggests fraud/risk review is needed. Otherwise set it to "Safe to deploy".

Output STRICTLY a single valid JSON object and nothing else. No markdown fences, no commentary, no preamble. The JSON must have exactly these keys:
{
  "Root_Cause_Analysis": "...",
  "Tailored_Recovery_Strategy": "...",
  "High_Conversion_Message": "...",
  "Guardrail_Status": "..."
}
"""

SENSITIVE_PATTERNS = [
    r"\b\d{12,19}\b",
    r"\bcvv\b", r"\bpin\b", r"\bpassword\b", r"\botp is\b", r"\botp:\s*\d",
    r"\baadhaar\b", r"\bpan\s*card\b",
]

FALSE_URGENCY_PATTERNS = [
    r"last chance", r"final warning", r"account.*(blocked|suspended|closed)",
    r"immediately or", r"within \d+ minutes? or", r"act now",
]

GUARANTEE_PATTERNS = [
    r"guaranteed", r"100% approv", r"will definitely (go through|work)",
    r"assured (refund|approval)",
]

RISK_ERROR_CODES = {"FRAUD_SUSPECTED", "RISK_REVIEW_REQUIRED", "BLOCKED_MERCHANT"}


def rule_based_guardrail_check(message: str, payload: dict) -> tuple[bool, list[str]]:
    reasons = []
    text = message.lower()

    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            reasons.append(f"Sensitive data pattern detected: `{pat}`")

    for pat in FALSE_URGENCY_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            reasons.append(f"False urgency / pressure language detected: `{pat}`")

    for pat in GUARANTEE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            reasons.append(f"Unsubstantiated guarantee language detected: `{pat}`")

    if payload.get("error_code") in RISK_ERROR_CODES:
        reasons.append(f"Underlying error_code '{payload.get('error_code')}' requires manual risk review")

    last4 = payload.get("card_last4")
    if last4:
        for match in re.findall(r"\d{5,}", message):
            reasons.append(f"Potential over-exposure of numeric financial data: '{match}'")

    return (len(reasons) == 0, reasons)


def run_recovery_engine(api_key: str, payload: dict) -> dict:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Failed transaction webhook payload:\n{json.dumps(payload, indent=2)}",
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "response_mime_type": "application/json",
            "temperature": 0.4,
        },
    )
    raw_text = response.text.strip()
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        cleaned = raw_text.strip("`").removeprefix("json").strip()
        result = json.loads(cleaned)

    llm_status = result.get("Guardrail_Status", "Hold")
    message = result.get("High_Conversion_Message", "")

    passed, reasons = rule_based_guardrail_check(message, payload)

    result["LLM_Reported_Status"] = llm_status
    if not passed:
        result["Guardrail_Status"] = "Hold"
        result["Guardrail_Override_Reasons"] = reasons
    else:
        result["Guardrail_Status"] = llm_status if llm_status.strip().lower().startswith(("safe", "hold")) else "Hold"
        result["Guardrail_Override_Reasons"] = []

    return result


def main():
    st.title("🔁 Pascoe-Lite")
    st.caption("Autonomous Payment Failure Recovery Engine — Razorpay AI Buildathon | Track: AI Revenue Recovery")

    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
        st.divider()
        st.header("📥 Select Failed Event")
        selected_event = st.selectbox("Simulated Razorpay Webhook", list(FAILED_TRANSACTIONS.keys()))
        run_btn = st.button("🚀 Run Recovery Analysis", use_container_width=True, type="primary")

    payload = FAILED_TRANSACTIONS[selected_event]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📡 Raw Ingested Webhook Payload")
        st.json(payload)
        st.caption(f"⚠️ Failure trigger field → `error_code`: **{payload.get('error_code')}**")

    with col2:
        st.subheader("🤖 Live AI Recovery Response")
        if run_btn:
            if not api_key:
                st.error("Enter your Gemini API Key in the sidebar to run the engine.")
            else:
                with st.spinner("Analyzing failure telemetry and generating recovery strategy..."):
                    try:
                        result = run_recovery_engine(api_key, payload)
                        status = result.get("Guardrail_Status", "Hold")
                        llm_status = result.get("LLM_Reported_Status", status)
                        override_reasons = result.get("Guardrail_Override_Reasons", [])

                        if status.strip().lower().startswith("safe"):
                            st.success(f"Guardrail_Status: {status}")
                        else:
                            st.warning(f"Guardrail_Status: {status}")

                        if override_reasons:
                            st.error(f"🛡️ Independent rule-based guardrail OVERRODE the model (model self-reported: '{llm_status}')")
                            with st.expander("Why this was held"):
                                for r in override_reasons:
                                    st.markdown(f"- {r}")
                        else:
                            st.caption(f"🛡️ Independent guardrail check passed · model self-reported: '{llm_status}'")

                        st.markdown("**🔍 Root Cause Analysis**")
                        st.info(result.get("Root_Cause_Analysis", ""))

                        st.markdown("**🎯 Tailored Recovery Strategy**")
                        st.write(result.get("Tailored_Recovery_Strategy", ""))

                        st.markdown("**💬 High Conversion Message**")
                        st.text_area(
                            "Customer-facing message",
                            value=result.get("High_Conversion_Message", ""),
                            height=120,
                            label_visibility="collapsed",
                            disabled=(status.strip().lower() != "safe to deploy" and status.strip().lower() != "safe"),
                        )

                        with st.expander("Raw JSON Response"):
                            st.json(result)

                    except Exception as e:
                        st.error(f"Engine error: {e}")
        else:
            st.info("Select an event and click **Run Recovery Analysis** to generate the AI response.")


if __name__ == "__main__":
    main()
