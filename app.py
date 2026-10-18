import io
import os
import re
import time
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from urllib.parse import urlencode, quote
from flask import Flask, request, jsonify, send_file, render_template, abort
from itsdangerous import URLSafeSerializer, BadSignature

try:
    from dotenv import load_dotenv
    venv_env = os.path.join(os.path.dirname(__file__), ".venv", ".env")
    if os.path.exists(venv_env):
        load_dotenv(venv_env)
    else:
        load_dotenv()
except ImportError:
    pass

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

_serializer = URLSafeSerializer(SECRET_KEY, salt="py-upi-qr")
UPI_ID_REGEX = re.compile(r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$")


def build_upi_url(upi_id: str, shop_name: str, amount: float, note: str) -> str:
    """Build a standards-compliant UPI deep-link."""
    params = {
        "pa": upi_id,
        "pn": shop_name,
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tn": note,
    }
    return "upi://pay?" + urlencode(params, quote_via=quote)


def generate_qr_png(upi_url: str) -> bytes:
    """Return raw PNG bytes for a QR code that encodes upi_url."""
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0D0D0D", back_color="#F2EEE9")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf.read()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True, silent=True) or {}

    # ── Validate upi_id ──────────────────────────────────────────────────────
    upi_id = str(data.get("upi_id", "")).strip()
    if not upi_id or not UPI_ID_REGEX.match(upi_id):
        return jsonify({"error": "Invalid UPI ID. Format should be username@handle."}), 400

    # ── Validate amount ──────────────────────────────────────────────────────
    try:
        amount = float(data.get("amount", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount. Please enter a number."}), 400
    if amount <= 0 or amount > 100_000:
        return jsonify({"error": "Amount must be between ₹0.01 and ₹1,00,000."}), 400
    # Round to 2 decimal places
    amount = round(amount, 2)

    # ── Validate validity_seconds (integer from 30 to 3600) ──────────────────
    try:
        validity = int(data.get("validity_seconds", data.get("validity", 300)))
    except (TypeError, ValueError):
        return jsonify({"error": "Validity must be a whole number of seconds."}), 400
    if validity < 30 or validity > 3600:
        return jsonify({"error": "Validity must be between 30 seconds and 60 minutes."}), 400

    # ── Validate note / message ──────────────────────────────────────────────
    note = str(data.get("note", data.get("message", ""))).strip()
    if len(note) > 50:
        return jsonify({"error": "Note must be 50 characters or fewer."}), 400

    # ── Validate shop name ───────────────────────────────────────────────────
    shop_name = str(data.get("shop_name", "")).strip()
    if not shop_name:
        return jsonify({"error": "Shop / business name is required."}), 400

    expiry = int(time.time()) + validity

    # Sign the payload so the browser cannot tamper with it
    token = _serializer.dumps({
        "upi_id": upi_id,
        "amount": amount,
        "note": note,
        "shop_name": shop_name,
        "expiry": expiry,
    })

    return jsonify({
        "qr_url": f"/qr?token={token}",
        "expiry": expiry,
        "amount": amount,
        "shop_name": shop_name,
    })


@app.route("/qr")
def qr():
    token = request.args.get("token", "")
    try:
        payload = _serializer.loads(token)
    except BadSignature:
        abort(403)

    if int(time.time()) > payload["expiry"]:
        abort(410)   # Gone – QR has expired

    upi_url = build_upi_url(
        payload["upi_id"],
        payload["shop_name"],
        payload["amount"],
        payload.get("note", payload.get("message", "")),
    )
    png_bytes = generate_qr_png(upi_url)
    return send_file(
        io.BytesIO(png_bytes),
        mimetype="image/png",
        max_age=0,
    )


if __name__ == "__main__":
    app.run(debug=True)
