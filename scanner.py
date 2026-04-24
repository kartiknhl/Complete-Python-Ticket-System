import cv2
from pyzbar.pyzbar import decode
import sqlite3
import time

# --- 1. Database Setup ---
conn = sqlite3.connect('fest_database.db')
cursor = conn.cursor()

# --- 2. Camera Setup ---
# '0' is usually the default built-in laptop webcam. 
# If you use an external USB camera, you might need to change this to '1'
cap = cv2.VideoCapture(0)

print("--- Fest Scanner Started ---")
print("Point the QR code at the camera.")
print("Press 'q' on your keyboard to quit the scanner.")

# A dictionary to remember recently scanned tickets 
# This stops the camera from scanning the same ticket 30 times a second
recent_scans = {}

while True:
    # Read the live video feed frame by frame
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not access the camera.")
        break

    # Find and decode any QR codes in the current frame
    decoded_objects = decode(frame)

    for obj in decoded_objects:
        # Extract the hidden ticket ID from the QR code
        ticket_id = obj.data.decode('utf-8')
        
        # Debounce: Skip if we just scanned this exact ticket in the last 3 seconds
        current_time = time.time()
        if ticket_id in recent_scans and current_time - recent_scans[ticket_id] < 3:
            continue 
        recent_scans[ticket_id] = current_time

        # --- 3. Database Verification ---
        cursor.execute("SELECT name, status FROM attendees WHERE ticket_id = ?", (ticket_id,))
        result = cursor.fetchone()

        # Get coordinates to draw a box around the QR code on the screen
        (x, y, w, h) = obj.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Logic to check the ticket validity
        if result is None:
            # Fake or invalid ticket
            text = "INVALID TICKET!"
            color = (0, 0, 255) # Red (OpenCV uses BGR format, not RGB)
            print(f"ALERT: Fake ticket scanned! ID: {ticket_id}")
            
        else:
            name, status = result
            if status == "Attended":
                # Ticket is real, but already used
                text = f"ALREADY USED: {name}"
                color = (0, 165, 255) # Orange
                print(f"WARNING: Double entry attempt by {name}")
                
            else:
                # Ticket is real and valid!
                text = f"ACCESS GRANTED: {name}"
                color = (0, 255, 0) # Green
                print(f"SUCCESS: {name} has entered the fest.")
                
                # Instantly update the database so they can't use it again
                cursor.execute("UPDATE attendees SET status = 'Attended' WHERE ticket_id = ?", (ticket_id,))
                conn.commit()

        # Draw the Result Text above the QR code box
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Show the video feed window
    cv2.imshow("Fest Ticket Scanner", frame)

    # Listen for the 'q' key to stop the program
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- 4. Cleanup ---
cap.release()
cv2.destroyAllWindows()
conn.close()
print("Scanner shut down securely.")