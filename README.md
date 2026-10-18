# Py-UPI — UPI Payment QR Generator

A minimal Flask dashboard that generates a signed, expiring UPI payment QR code.

---

## Setup

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Configuration

Open `app.py` and replace the placeholder values at the top:

```python
UPI_ID     = "yourname@upi"          # your real UPI ID
SECRET_KEY = "change-this-secret-key-before-deploying"
```

## Run

```bash
python app.py
```

Then open your browser at **http://127.0.0.1:5000**.

---

## How it works

1. Fill in the form and click **Generate QR**.
2. The server validates the inputs and returns a signed token (via _itsdangerous_) that encodes the amount, message, shop name and expiry time.
3. The browser displays the QR code and a live countdown timer.
4. When the countdown reaches zero, the QR image is hidden and replaced with **"QR Expired"**.
5. The `/qr` endpoint also checks the expiry server-side and returns **HTTP 410 Gone** for expired tokens, so a saved URL cannot be reused after expiry.

---

> **Important limitation:** The QR expiry is enforced only by this page and this server. The UPI protocol itself does not support expiring QR codes — a person who scanned the QR before it expired can still complete the payment after the timer runs out. This demo also cannot detect whether a payment was actually made; no payment gateway or webhook is integrated.
