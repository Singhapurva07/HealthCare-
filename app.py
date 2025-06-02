from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime, timedelta
import logging
import pdfplumber
from PIL import Image
import io
import base64

app = Flask(__name__)
app.secret_key = '2f8b60bda6a957bc9414887f7'
app.config['UPLOAD_FOLDER'] = 'Uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Configure Gemini API
try:
    genai.configure(api_key=GEMINI_API_KEY)
    MODEL_NAME = 'gemini-1.5-flash'
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    logging.error(f"Gemini API configuration error: {e}")
    raise

# MySQL configuration
db_config = {
    'user': 'root',
    'password': 'root@123',
    'host': 'localhost',
    'database': 'healthcare_db'
}

# Initialize database
def init_db():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(100),
                date_time DATETIME,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symptom_checks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                symptoms TEXT,
                result TEXT,
                check_time DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                file_name VARCHAR(255),
                file_type VARCHAR(50),
                summary TEXT,
                upload_time DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        logging.info("Database initialized successfully")
    except mysql.connector.Error as e:
        logging.error(f"Database initialization error: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Validate user_id in session
def validate_user_id():
    if 'user_id' not in session:
        return False
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user is not None
    except mysql.connector.Error as e:
        logging.error(f"Session validation error: {e}")
        return False

@app.route('/')
def index():
    if validate_user_id():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('login.html', error='Username and password are required')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute('SELECT id, password FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                logging.info(f"User {username} logged in successfully")
                return redirect(url_for('dashboard'))
            return render_template('login.html', error='Invalid credentials')
        except mysql.connector.Error as e:
            logging.error(f"Login error: {e}")
            return render_template('login.html', error=f'Database error: {e}')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        if not all([username, password, email]):
            return render_template('signup.html', error='All fields are required')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                           (username, generate_password_hash(password), email))
            conn.commit()
            cursor.close()
            conn.close()
            logging.info(f"User {username} signed up successfully")
            return redirect(url_for('login'))
        except mysql.connector.Error as e:
            logging.error(f"Signup error: {e}")
            return render_template('signup.html', error='Username or email already exists')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if not validate_user_id():
        return redirect(url_for('login'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM reminders WHERE user_id = %s AND date_time >= %s ORDER BY date_time LIMIT 5',
                       (session['user_id'], datetime.now()))
        reminders = cursor.fetchall()
        cursor.execute('SELECT * FROM symptom_checks WHERE user_id = %s ORDER BY check_time DESC LIMIT 3',
                       (session['user_id'],))
        symptom_checks = cursor.fetchall()
        cursor.execute('SELECT * FROM uploads WHERE user_id = %s ORDER BY upload_time DESC LIMIT 3',
                       (session['user_id'],))
        uploads = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('dashboard.html', reminders=reminders, error=None,
                               symptom_checks=symptom_checks, uploads=uploads)
    except mysql.connector.Error as e:
        logging.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', error=f'Database error: {e}', reminders=[],
                               symptom_checks=[], uploads=[])

@app.route('/virtual_caretaker', methods=['POST'])
def virtual_caretaker():
    if not validate_user_id():
        return jsonify({'error': 'Unauthorized'}), 401
    message = request.json.get('message')
    if not message:
        return jsonify({'response': 'Please enter a message'}), 400
    try:
        # Fetch next reminder
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT title, date_time FROM reminders WHERE user_id = %s AND date_time >= %s ORDER BY date_time LIMIT 1',
                       (session['user_id'], datetime.now()))
        next_reminder = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Build context safely
        if next_reminder:
            context = f"Next reminder: {next_reminder['title']} at {next_reminder['date_time'].strftime('%Y-%m-%d %H:%M:%S')}."
        else:
            context = "No upcoming reminders."
        
        # Construct prompt
        prompt = (
            f"You are a Virtual Caretaker for chronically ill patients in India. "
            f"Context: {context}. "
            f"Respond to the user's query: '{message}'. "
            f"Provide empathetic, actionable health advice (e.g., rest, hydration, vegan diet tips) in the Indian context. "
            f"Use Hindi phrases like 'Dhyaan rakhein' if appropriate. "
            f"Support Hindi queries if provided. "
            f"Keep responses concise, safe, and include a disclaimer to consult a doctor."
        )
        
        # Call Gemini API
        logging.debug(f"Calling Gemini API with prompt: {prompt}")
        response = model.generate_content(prompt)
        response_text = response.text if hasattr(response, 'text') else 'Unable to generate response.'
        
        return jsonify({'response': response_text})
    except mysql.connector.Error as e:
        logging.error(f"Virtual Caretaker database error: {e}")
        return jsonify({'response': f'Database error: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Virtual Caretaker error: {type(e).__name__}: {str(e)}")
        return jsonify({'response': f'Error: {str(e)}'}), 500

@app.route('/medicine_recommender', methods=['POST'])
def medicine_recommender():
    if not validate_user_id():
        return jsonify({'error': 'Unauthorized'}), 401
    problem = request.json.get('problem')
    if not problem:
        return jsonify({'response': 'Please describe the health problem'}), 400
    try:
        prompt = f"You are a medicine recommender for chronically ill patients in India. Based on the health problem: '{problem}', recommend appropriate medicines (use Indian drug names, e.g., Paracetamol, per CDSCO guidelines) and preventions (e.g., diet, rest). Provide clear, safe recommendations and note that patients should consult a doctor."
        response = model.generate_content(prompt)
        return jsonify({'response': response.text})
    except Exception as e:
        logging.error(f"Medicine Recommender error: {e}")
        return jsonify({'response': f'Error: {str(e)}'}), 500

@app.route('/symptom_checker', methods=['POST'])
def symptom_checker():
    if not validate_user_id():
        return jsonify({'error': 'Unauthorized'}), 401
    symptoms = request.json.get('symptoms')
    if not symptoms:
        return jsonify({'response': 'Please enter symptoms'}), 400
    try:
        prompt = f"You are a symptom checker for chronically ill patients in India. Based on symptoms: '{symptoms}', provide possible causes and suggested actions (e.g., consult a doctor, rest). Use Indian medical context and include a disclaimer to consult a doctor."
        response = model.generate_content(prompt)
        result = response.text
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO symptom_checks (user_id, symptoms, result, check_time) VALUES (%s, %s, %s, %s)',
                       (session['user_id'], symptoms, result, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'response': result})
    except Exception as e:
        logging.error(f"Symptom Checker error: {e}")
        return jsonify({'response': f'Error: {str(e)}'}), 500

@app.route('/upload_report', methods=['POST'])
def upload_report():
    if not validate_user_id():
        return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
    if file and (file.filename.endswith('.pdf') or file.filename.endswith(('.png', '.jpg', '.jpeg'))):
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            summary = ""
            if file.filename.endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    text = "".join(page.extract_text() or "" for page in pdf.pages)
                prompt = f"Summarize this medical document for a patient in India: '{text[:1000]}'. Highlight key points (e.g., prescribed medicines, diagnosis) in simple language."
                response = model.generate_content(prompt)
                summary = response.text
            else:
                img = Image.open(file_path)
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format=img.format)
                img_data = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                prompt = f"Analyze this medical image (e.g., prescription, lab report) for a patient in India. Summarize key details (e.g., medicines, diagnosis) in simple language."
                response = model.generate_content([prompt, {"inline_data": {"mime_type": f"image/{img.format.lower()}", "data": img_data}}])
                summary = response.text
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO uploads (user_id, file_name, file_type, summary, upload_time) VALUES (%s, %s, %s, %s, %s)',
                           (session['user_id'], file.filename, file.content_type, summary, datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'message': 'File uploaded and summarized', 'summary': summary})
        except Exception as e:
            logging.error(f"Upload error: {e}")
            return jsonify({'message': f'Error uploading file: {str(e)}'}), 500
    return jsonify({'message': 'Invalid file type'}), 400

@app.route('/Uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    if not validate_user_id():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    title = data.get('title')
    date_time = data.get('date_time')
    description = data.get('description')
    if not all([title, date_time, description]):
        return jsonify({'message': 'All fields are required'}), 400
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reminders (user_id, title, date_time, description) VALUES (%s, %s, %s, %s)',
                       (session['user_id'], title, date_time, description))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Reminder added successfully'})
    except mysql.connector.Error as e:
        logging.error(f"Add reminder error: {e}")
        return jsonify({'message': f'Error adding reminder: {str(e)}'}), 500

@app.route('/get_calendar_data', methods=['GET'])
def get_calendar_data():
    if not validate_user_id():
        return jsonify({'error': 'Unauthorized'}), 401
    month = request.args.get('month')
    year = request.args.get('year')
    if not all([month, year]):
        return jsonify({'error': 'Month and year are required'}), 400
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        start_date = datetime(int(year), int(month), 1)
        end_date = (start_date + timedelta(days=31)).replace(day=1)
        cursor.execute('SELECT * FROM reminders WHERE user_id = %s AND date_time BETWEEN %s AND %s',
                       (session['user_id'], start_date, end_date))
        reminders = cursor.fetchall()
        events = [{
            'date': reminder['date_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            'type': 'reminder',
            'details': f"{reminder['title']}: {reminder['description']}"
        } for reminder in reminders]
        cursor.close()
        conn.close()
        return jsonify({'events': events})
    except Exception as e:
        logging.error(f"Calendar data error: {e}")
        return jsonify({'error': f'Error fetching calendar data: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)