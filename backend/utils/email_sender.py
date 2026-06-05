# Mock Email Sender for Local Development
def send_reset_email(email, reset_link):
    print("\n" + "="*50)
    print(f"[MOCK EMAIL SENDER] Sending Password Reset")
    print(f"[MOCK EMAIL SENDER] Recipient: {email}")
    print(f"[MOCK EMAIL SENDER] Reset Link: {reset_link}")
    print("="*50 + "\n")
    return True
