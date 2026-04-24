# 🎟️ EventGuard: The Smart Ticket System
### *Where High-Level Security Meets Seamless Entry*

Most people think a ticketing app is just a website that shows a QR code. 
**EventGuard** is different. It’s an enterprise-grade, decoupled system built to solve real-world problems like ticket fraud, screenshot sharing, and link leakage. 🛡️

---

## 🏗️ The "50/50" Hybrid: Why Python + HTML?
One of the coolest parts of this project is its architecture. It’s split right down the middle between **Backend Logic** and **Frontend Interactivity**.

* **🧠 Python (The Brain):** Lives on the backend server. It handles the heavy lifting—managing the PostgreSQL database, verifying security tokens, and sending out professional emails via the Resend API. 
* **📱 HTML/JS (The Body):** Lives locally on the **User's Phone**. To make the app feel "alive," we need code running locally. JavaScript handles the **30-second QR scramble** and opens the **Mobile Camera** for scanning. 

> **The Concept:** Python is perfect for secure server-side logic, but we need HTML and JavaScript to handle real-time, client-side tasks like hardware access and dynamic UI updates.

---

## 🔐 The "Triple-Lock" Security
I didn't just want it to work; I wanted it to be unhackable. Here are the three layers of defense:

* **⏱️ The 30-Second Scramble (TOTP):** The QR code on the student's phone isn't a static image. It’s a live token that refreshes every 30 seconds.
    * *Why?* To stop "Replay Attacks." A screenshot taken 1 minute ago is useless at the gate.
* **🤝 The Digital Handshake (Device Binding):** When a student first opens their link, the server "pairs" with that specific phone using a secure browser cookie.
    * *Why?* If they forward the link to a friend, the friend gets an "Access Denied" screen. The ticket stays with the original owner.
* **🎲 The Opaque URL (UUID v4):** We don't use simple numbers like `ticket/101`. We use 32-character random strings.
    * *Why?* It’s mathematically impossible for a hacker to "guess" another student's ticket URL.

---

## 🛠️ The Tech Stack
* **Backend:** Python (Flask) 🐍
* **Database:** PostgreSQL 🐘
* **Email:** Resend API ✉️
* **Frontend:** HTML5, CSS3, & JavaScript 🌐
* **Analytics:** Streamlit (Admin Dashboard) 📊

---

## 👨‍💻 Admin Command Center
I also built a **Live Dashboard** for the event volunteers. 
* **Live Ticker:** See registrations happen in real-time.
* **Smart Scanning:** The scanner doesn't just check the ticket; it pulls the student's **Roll Number** and **Name** directly from the database to verify their ID.
* **Entry Tracking:** Automatically updates status from `'not attended'` to `'attended'` the moment they walk through the door. 🚪🏃‍♂️
