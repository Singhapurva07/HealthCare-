
A comprehensive platform designed specifically for chronically ill patients in India, offering personalized care, smart recommendations, and seamless health tracking with support for Hindi language and CDSCO-approved medicines.
Healthcare Application

A Flask-based web app for chronically ill patients in India, offering accessible health tools with Hindi support, CDSCO-approved medicines, and accessibility features like high-contrast mode and voice navigation.

Features

Login & Signup: Secure user authentication with hashed passwords.
Virtual Caretaker: AI-driven (Gemini API) health advice in English/Hindi (e.g., “Dhyaan rakhein”), aware of upcoming reminders.
Medicine Recommender: Suggests CDSCO-approved drugs (e.g., Paracetamol) with preventions.
Symptom Checker: Analyzes symptoms, stores recent checks in MySQL.
Prescription & Reports Upload: Summarizes PDFs/images, stores in MySQL.
Reminder Calendar: FullCalendar for scheduling reminders.
Website Significance: Explains platform’s purpose for Indian patients.
Accessibility: High-contrast mode, voice navigation, Hindi support.
Technologies

Backend: Flask, MySQL, Python
Frontend: HTML, Tailwind CSS, JavaScript, jQuery, FullCalendar
AI: Google Gemini API (gemini-1.5-flash)
Libraries: mysql-connector-python, werkzeug, python-dotenv, google-generativeai, pdfplumber, Pillow
Prerequisites

Python 3.8+
MySQL 8.0+
Gemini API key (get from https://aistudio.google.com)
Windows 10/11
Browser: Chrome or Edge
Installation

Set Up Project:
Place files in C:\Users\Apurva Singh\Desktop\healthcare.
Install Dependencies: Open cmd and run: pip install flask mysql-connector-python werkzeug python-dotenv google-generativeai pdfplumber Pillow
Set Up MySQL: Start MySQL: net start mysql Log in: mysql -u root -p Password: root@123 If password fails: ALTER USER 'root'@'localhost' IDENTIFIED BY 'root@123'; Create database: DROP DATABASE IF EXISTS healthcare_db; CREATE DATABASE healthcare_db; GRANT ALL ON healthcare_db.* TO 'root'@'localhost'; EXIT;
Create Uploads Folder: mkdir Uploads icacls Uploads /grant Everyone:F
Configuration

Create .env file in C:\Users\Apurva Singh\Desktop\healthcare: GEMINI_API_KEY=your_gemini_api_key Get key from https://aistudio.google.com.
Running the Application

Navigate to project: cd C:\Users\Apurva Singh\Desktop\healthcare
Run: python app.py Access at http://localhost:5000. If port 5000 is busy: python app.py --port 5001
Stop: Press Ctrl+C.
Usage

Sign Up/Login: Create account at /signup, log in at /login.
Virtual Caretaker: Ask “What should I do for a headache?” or “मुझे सिरदर्द के लिए क्या करना चाहिए?” for advice in a styled box.
Medicine Recommender: Enter “cough” for drug suggestions.
Symptom Checker: Input “headache, fever” for causes and actions.
Prescription Upload: Add PDF/image for summaries.
Reminder Calendar: Add reminders (e.g., “Insulin” at “2025-06-03T08:00”).
Accessibility: Toggle high-contrast mode, hear voice feedback.
Troubleshooting

Virtual Caretaker Fails:
Check logs for “NoneType” errors.
Verify reminders table: mysql -u root -p USE healthcare; DESC reminders; If broken: DROP TABLE reminders; Restart app.py.
Check Gemini API key: python -c "import google.generativeai as genai; genai.configure(api_key='your_api_key'); print([m.name for m in genai.list_models()])" If invalid, update key or use MODEL_NAME='gemini-pro' in app.py.
MySQL Errors: ALTER USER 'root'@'localhost' IDENTIFIED BY 'root@123'; DROP DATABASE IF EXISTS healthcare_db; CREATE DATABASE healthcare_db; GRANT ALL ON healthcare_db.* TO 'root'@'localhost'; net stop mysql net start mysql
CDN Issues: Download assets: mkdir static cd static curl -o fullcalendar.min.css https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css curl -o fullcalendar.min.js https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js curl -o jquery.min.js https://code.jquery.com/jquery-3.6.0.min.js curl -o lottie-player.js https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js Update dashboard.html to use /static/ paths.
License
MIT License

Contact
Email: apurva.singh@example.com
Report issues with logs and steps.

Built for Indian patients, June 2, 2025.
