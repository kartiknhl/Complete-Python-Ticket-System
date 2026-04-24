import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
import pyotp

from flask import Flask, jsonify, make_response, redirect, render_template, request, session, url_for
import resend

db_pass = os.environ.get('DB_PASSWORD')
resend_key = os.environ.get('RESEND_API_KEY')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_URL = f"postgresql://kartik:{db_pass}@qr-data.postgres.database.azure.com/postgres?sslmode=require"
TICKETS_DIR = os.path.join(BASE_DIR, "static", "Tickets")


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_fest_key_2026")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("SESSION_COOKIE_SECURE")),
)

DOOR_PASSWORD = os.environ.get("DOOR_PASSWORD", "fest")
resend.api_key = resend_key
SENDER_EMAIL = "tickets@workhive.studio"

os.makedirs(TICKETS_DIR, exist_ok=True)


def get_db_connection():
    return psycopg2.connect(DB_URL)


def initialize_database():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attendees (
                    id SERIAL PRIMARY KEY,
                    ticket_id VARCHAR(8) UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    roll_number TEXT NOT NULL,
                    email TEXT NOT NULL,
                    totp_secret VARCHAR(50),
                    device_token VARCHAR(255),
                    status TEXT NOT NULL DEFAULT 'Not Attended'
                )
                """
            )
            cursor.execute("ALTER TABLE attendees ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(50)")
            cursor.execute("ALTER TABLE attendees ADD COLUMN IF NOT EXISTS device_token VARCHAR(255)")
        connection.commit()
    finally:
        connection.close()


def generate_unique_ticket_id():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            while True:
                ticket_id = uuid.uuid4().hex[:8]
                cursor.execute(
                    "SELECT 1 FROM attendees WHERE ticket_id = %s",
                    (ticket_id,),
                )
                existing = cursor.fetchone()
                if existing is None:
                    return ticket_id
    finally:
        connection.close()


def send_resend_ticket(name, user_email, ticket_id):
    ticket_link = f"{request.url_root.rstrip('/')}/ticket/{ticket_id}"
    resend.Emails.send(
        {
            "from": SENDER_EMAIL,
            "to": [user_email],
            "subject": "Your college fest ticket",
            "html": (
                f"<p>Hello {name}!</p>"
                f"<p>Your live ticket link is ready: <a href=\"{ticket_link}\">Open Ticket</a></p>"
            ),
        }
    )


def get_attendee_by_email(email):
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT name, ticket_id, roll_number, totp_secret, device_token FROM attendees WHERE email = %s",
                (email,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def get_attendee_by_ticket_id(ticket_id):
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT name, email, ticket_id, totp_secret, device_token, status FROM attendees WHERE ticket_id = %s",
                (ticket_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def update_device_token(ticket_id, new_token):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE attendees SET device_token = %s WHERE ticket_id = %s",
                (new_token, ticket_id),
            )
        connection.commit()
    finally:
        connection.close()


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        email = request.form.get("email", request.form.get("user_email", "")).strip()

        if not name or not roll_no or not email:
            return render_template("register.html", error="All fields are required."), 400

        existing_attendee = get_attendee_by_email(email)
        if existing_attendee is not None:
            return render_template(
                "register.html",
                error="This email is already registered.",
                existing_email=email,
            )

        ticket_id = generate_unique_ticket_id()
        totp_secret = pyotp.random_base32()

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO attendees (ticket_id, name, roll_number, email, totp_secret, device_token, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (ticket_id, name, roll_no, email, totp_secret, None, "Not Attended"),
                )
            connection.commit()
        finally:
            connection.close()

        try:
            send_resend_ticket(name, email, ticket_id)
        except Exception as e:
            print(f"\n[CRITICAL RESEND ERROR] -> {e}\n")

        # Redirect to the success page
        return render_template('success.html', name=name)

    return render_template("register.html")


@app.route("/resend", methods=["POST"])
def resend_ticket():
    email = request.form.get("email", "").strip()

    if not email:
        return render_template("register.html", error="Email is required to resend a ticket."), 400

    attendee = get_attendee_by_email(email)
    if attendee is None:
        return render_template("register.html", error="No registration found for this email."), 404

    try:
        send_resend_ticket(attendee["name"], email, attendee["ticket_id"])
    except Exception as e:
        print(f"\n[CRITICAL RESEND ERROR] -> {e}\n")
        return render_template("register.html", error="Unable to resend ticket right now.", existing_email=email), 500

    return render_template("success.html", message="Ticket successfully resent to your email!")


@app.route("/ticket/<ticket_id>")
def live_ticket(ticket_id):
    attendee = get_attendee_by_ticket_id(ticket_id)
    if attendee is None:
        return render_template("error.html", message="Ticket not found."), 404

    current_device_cookie = request.cookies.get("device_id")

    if attendee["device_token"] is None:
        new_token = str(uuid.uuid4())
        update_device_token(ticket_id, new_token)

        response = make_response(
            render_template(
                "ticket.html",
                name=attendee["name"],
                ticket_id=attendee["ticket_id"],
                totp_secret=attendee["totp_secret"],
                status=attendee["status"],
            )
        )
        response.set_cookie(
            "device_id",
            new_token,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="Lax",
            secure=bool(os.environ.get("SESSION_COOKIE_SECURE")),
        )
        return response

    if current_device_cookie == attendee["device_token"]:
        return render_template(
            "ticket.html",
            name=attendee["name"],
            ticket_id=attendee["ticket_id"],
            totp_secret=attendee["totp_secret"],
            status=attendee["status"],
        )

    return render_template(
        "error.html",
        message="⚠️ ACCESS DENIED: This ticket has already been claimed on another device.",
    ), 403


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == DOOR_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Incorrect password.")

    return render_template("login.html")


@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("scanner.html")


@app.route("/verify_scan", methods=["POST"])
def verify_scan():
    payload = request.get_json(silent=True) or {}
    scanned_data = str(payload.get("qr_data", "")).strip()

    if ":" not in scanned_data:
        return jsonify({"status": "error", "message": "Invalid QR payload format"}), 400

    uuid_part, totp_part = scanned_data.split(":", 1)
    uuid_part = uuid_part.strip()
    totp_part = totp_part.strip()

    if not uuid_part or not totp_part:
        return jsonify({"status": "error", "message": "Invalid QR payload format"}), 400

    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM attendees WHERE ticket_id = %s",
                (uuid_part,),
            )
            user = cursor.fetchone()

            if user is None:
                return jsonify({"status": "error", "message": "Ticket Not Found"}), 404

            if user.get("status") == "Attended":
                return jsonify({"status": "error", "message": "ALREADY SCANNED: Access Denied"}), 403

            secret = user.get("totp_secret")
            if not secret:
                return jsonify({"status": "error", "message": "Invalid or Expired Token"}), 400

            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(totp_part, valid_window=1)

            if not is_valid:
                return jsonify({"status": "error", "message": "Invalid or Expired Token"}), 400

            cursor.execute(
                "UPDATE attendees SET status = 'Attended' WHERE ticket_id = %s",
                (uuid_part,),
            )
        connection.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Verification successful",
                "name": user["name"],
                "roll_number": user["roll_number"],
            }
        )
    finally:
        connection.close()


@app.route("/verify", methods=["POST"])
def verify_ticket():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Unauthorized", "color": "red"}), 403

    data = request.get_json(silent=True) or {}
    ticket_id = str(data.get("ticket_id", "")).strip()

    if not ticket_id:
        return jsonify({"status": "invalid", "message": "No QR data received.", "color": "red"}), 400

    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT name, status FROM attendees WHERE ticket_id = %s",
                (ticket_id,),
            )
            attendee = cursor.fetchone()

            if attendee is None:
                return jsonify({"status": "invalid", "message": "INVALID TICKET", "color": "red"})

            if attendee["status"] == "Attended":
                return jsonify({"status": "used", "message": f"ALREADY USED: {attendee['name']}", "color": "orange"})

            cursor.execute(
                "UPDATE attendees SET status = 'Attended' WHERE ticket_id = %s",
                (ticket_id,),
            )
        connection.commit()
        return jsonify({"status": "success", "message": f"ACCESS GRANTED: {attendee['name']}", "color": "green"})
    finally:
        connection.close()


initialize_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
