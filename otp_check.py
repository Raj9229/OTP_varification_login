from flask import Flask, render_template, request, session, redirect, url_for, flash
from random import randint
from flask_mail import Mail, Message
import json
import os
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session
app.config['SESSION_COOKIE_SECURE'] = True  # For HTTPS environments
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['PERMANENT_SESSION_LIFETIME'] = 600  # 10 min session timeout

# Config file handling
base_dir = os.path.abspath(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, 'static')
config_path = os.path.join(static_dir, 'config.js')

# Create static directory if needed
os.makedirs(static_dir, exist_ok=True)

# Create config template if it doesn't exist
if not os.path.exists(config_path):
    default_config = {
        "param": {
            "gmail-user": "your-email@gmail.com",
            "gmail-password": "your-app-password"
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=4)
    
    print(f"Config template created at: {config_path}")
    print("Please update with your Gmail credentials before running.")
    exit(1)

# Load config
try:
    with open(config_path, 'r') as f:
        content = f.read()
        # Remove JS comments if present
        if content.strip().startswith('//'):
            content = '\n'.join(line for line in content.split('\n') 
                               if not line.strip().startswith('//'))
        params = json.loads(content)['param']
        
    # Check if default credentials
    if params['gmail-user'] == "your-email@gmail.com":
        print(f"Please update {config_path} with your actual Gmail credentials.")
        exit(1)
except Exception as e:
    print(f"Config error: {e}")
    exit(1)

# Configure Flask-Mail
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password'],
    MAIL_DEFAULT_SENDER=params['gmail-user']
)
mail = Mail(app)

# Helper function to send OTP emails
def send_otp_email(email, otp, is_resend=False):
    try:
        subject = 'Your New Verification Code' if is_resend else 'Your Verification Code'
        msg = Message(
            subject=subject,
            recipients=[email],
            body=f'Your verification code is: {otp}\nThis code will expire in 10 minutes.'
        )
        mail.send(msg)
        return True, None
    except Exception as e:
        return False, str(e)

# Routes
@app.route('/')
def index():
    return render_template('email_form.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        email = request.form['email']
        # Generate 6-digit OTP
        otp = randint(100000, 999999)
        
        # Store OTP with timestamp for expiration check
        session['otp'] = str(otp)
        session['email'] = email
        session['otp_time'] = time.time()
        
        # Send OTP email
        success, error = send_otp_email(email, otp)
        if success:
            return render_template('otp_form.html', email=email)
        else:
            return render_template('email_form.html', 
                                  message=f"Failed to send verification code: {error}",
                                  message_class="error")
    
    # Handle GET request (for resend)
    elif request.method == 'GET' and request.args.get('email'):
        email = request.args.get('email')
        # Generate new OTP
        otp = randint(100000, 999999)
        session['otp'] = str(otp)
        session['email'] = email
        session['otp_time'] = time.time()
        
        # Send OTP email
        success, error = send_otp_email(email, otp, is_resend=True)
        if success:
            return render_template('otp_form.html', 
                                  email=email, 
                                  message="New verification code sent!",
                                  message_class="success")
        else:
            return render_template('otp_form.html', 
                                  email=email,
                                  message=f"Failed to send new code: {error}",
                                  message_class="error")
    
    # Default case - show email form
    return render_template('email_form.html')

@app.route('/validate', methods=['POST'])
def validate():
    user_otp = request.form['otp']
    email = request.form['email']
    
    # Check if OTP is expired (10 minutes)
    if 'otp_time' in session and (time.time() - session['otp_time']) > 600:
        return render_template('otp_form.html', 
                              email=email,
                              message="Verification code expired. Please request a new one.",
                              message_class="error")
    
    # Verify OTP
    if 'otp' in session and session['otp'] == user_otp:
        # OTP is correct
        # Clear sensitive session data
        session.pop('otp', None)
        session.pop('otp_time', None)
        
        # Keep email for future reference if needed
        return render_template('success.html', email=email)
    else:
        # OTP is incorrect
        return render_template('otp_form.html', 
                              email=email,
                              message="Invalid verification code. Please try again.",
                              message_class="error")

if __name__ == '__main__':
    app.run(debug=True)