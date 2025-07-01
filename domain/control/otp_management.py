import pyotp
import pyqrcode
import io
import base64
from data_source.userqueries import set_otp_secret, get_user_by_id

def generate_otp(user_id):

    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"

    otp_secret = pyotp.random_base32()
    if not set_otp_secret(user_id, otp_secret):
        return None, "Failed to update user with OTP secret"

    # Generate provisioning URI and QR
    uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(
        name=user["email"],
        issuer_name="BuddiesFinders"
    )
    qr = pyqrcode.create(uri)
    buffer = io.BytesIO()
    qr.png(buffer, scale=5)
    qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_data_url = f"data:image/png;base64,{qr_b64}"

    return {"qr": qr_data_url, "secret": otp_secret}, None
