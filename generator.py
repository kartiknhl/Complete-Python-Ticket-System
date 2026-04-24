import sqlite3
import qrcode
import os
import uuid

# --- 1. Database Setup ---
# This creates a file called 'fest_database.db' in your folder
conn = sqlite3.connect('fest_database.db')
cursor = conn.cursor()

# Create a table for attendees if it doesn't already exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendees (
        ticket_id TEXT PRIMARY KEY,
        name TEXT,
        roll_number TEXT,
        status TEXT
    )
''')
conn.commit()

# Create a folder to save the QR code images
if not os.path.exists("Tickets"):
    os.makedirs("Tickets")

# --- 2. Registration Logic ---
def register_student():
    print("--- New Student Registration ---")
    name = input("Enter Student Name: ")
    roll_no = input("Enter Roll Number: ")
    
    # Generate a unique cryptographic ID for the ticket
    ticket_id = str(uuid.uuid4())[:8] 
    
    # Save to Database with status 'Not Attended'
    cursor.execute("INSERT INTO attendees (ticket_id, name, roll_number, status) VALUES (?, ?, ?, ?)", 
                   (ticket_id, name, roll_no, "Not Attended"))
    conn.commit()
    
    # --- 3. QR Code Generation ---
    # We are encoding ONLY the unique ID into the QR code for security
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(ticket_id)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image as "Tickets/RollNumber_Ticket.png"
    filename = f"Tickets/{roll_no}_Ticket.png"
    img.save(filename)
    
    print(f"\nSuccess! Registered {name}.")
    print(f"Ticket ID: {ticket_id}")
    print(f"QR Code saved as: {filename}\n")

# Run the function
if __name__ == "__main__":
    while True:
        register_student()
        cont = input("Register another student? (y/n): ")
        if cont.lower() != 'y':
            break

conn.close()