# app.py
from flask import Flask, render_template, request, redirect, send_file, jsonify, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from pipeline import run_transcription
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# Use environment variable for secret key with a fallback
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

status_message = "Idle"

# Simple user class
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Hardcoded admin user
ADMIN_USERNAME = "remark"
ADMIN_PASSWORD = "remark"

@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USERNAME:
        return User(user_id)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    print("Serving index.html")
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe():
    global status_message
    transcript_path = None
    try:
        file = request.files.get('file')
        if not file:
            status_message = "❌ No file provided."
            return "No file provided", 400

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        transcript_path = run_transcription(local_file=file_path, status_callback=update_status)

        if transcript_path:
            status_message = "✅ Transcription complete."
            return send_file(transcript_path, as_attachment=True)

        status_message = "❌ Transcription failed."
        return "Transcription failed", 500
    except Exception as e:
        status_message = f"❌ Error: {str(e)}"
        return str(e), 500

@app.route('/status')
@login_required
def status():
    return jsonify({"status": status_message})

def update_status(msg):
    global status_message
    status_message = msg

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)


