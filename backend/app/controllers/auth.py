from flask import Blueprint, request, jsonify, current_app, url_for, render_template_string
from pymongo import MongoClient
from ..models.user import User
import os
import jwt
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import uuid
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, decode_token
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from bson.objectid import ObjectId
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

auth_bp = Blueprint('auth_bp', __name__)
# Use the application's mongo_client instead of creating a new connection
user_model = User(None)  # Will be initialized properly when used with the correct database

@auth_bp.route('/me', methods=['GET'])
@jwt_required(optional=True)
def get_current_user():
    try:
        # Get the identity from the JWT token
        current_user_id = get_jwt_identity()
        
        # If no user is authenticated, return empty response with 200 status
        if not current_user_id:
            return jsonify({'authenticated': False}), 200
        
        # Initialize the user model with the current app's database
        from ..db import get_db
        db = get_db()
        
        # Find the user by ID - handle both ObjectId and email formats
        user = None
        try:
            # Try to find by ObjectId
            from bson.objectid import ObjectId
            user = db.users.find_one({"_id": ObjectId(current_user_id)})
        except:
            # If not a valid ObjectId, try as email or username
            user = db.users.find_one({"email": current_user_id})
            if not user:
                user = db.users.find_one({"username": current_user_id})
        
        if not user:
            return jsonify({'error': 'User not found', 'authenticated': False}), 200
        
        # Remove sensitive information
        user.pop('password', None)
        
        # Convert ObjectId to string for JSON serialization
        if '_id' in user and not isinstance(user['_id'], str):
            user['_id'] = str(user['_id'])
        
        return jsonify({'user': user, 'authenticated': True}), 200
    except Exception as e:
        current_app.logger.error(f"Error getting current user: {str(e)}")
        # Return a 200 response even on error to prevent frontend crashes
        return jsonify({'error': 'Failed to get user information', 'authenticated': False}), 200

# Secret key for JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')

# Upload folder for ID card photos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Email configuration
EMAIL_SERVER = os.environ.get('EMAIL_SERVER', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', 'your-email@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'your-app-password')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'BRACU Eureka <your-email@gmail.com>')

# Create a limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# HTML template for password reset email
PASSWORD_RESET_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4285f4; color: white; padding: 10px 20px; text-align: center; }
        .content { padding: 20px; border: 1px solid #ddd; }
        .button { display: inline-block; background-color: #4285f4; color: white; text-decoration: none; padding: 10px 20px; border-radius: 4px; }
        .footer { margin-top: 20px; font-size: 12px; color: #777; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>BRACU Eureka Password Reset</h2>
        </div>
        <div class="content">
            <p>Hello {{name}},</p>
            <p>We received a request to reset your password for your BRACU Eureka account. If you didn't make this request, you can ignore this email.</p>
            <p>To reset your password, click the button below. This link will expire in 1 hour.</p>
            <p style="text-align: center;">
                <a href="{{reset_link}}" class="button">Reset Password</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p>{{reset_link}}</p>
            <p>Thank you,<br>The BRACU Eureka Team</p>
        </div>
        <div class="footer">
            <p>This is an automated email. Please do not reply to this message.</p>
        </div>
    </div>
</body>
</html>
"""

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(to_email, subject, html_content):
    """Send an email using SMTP"""
    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        
        # Attach HTML content
        part = MIMEText(html_content, 'html')
        msg.attach(part)
        
        # Connect to server and send
        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
        
        current_app.logger.info(f"Password reset email sent to {to_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("20 per hour")  # Limit registration attempts
def register():
    try:
        # Get form data - check if both form data and files exist
        if not request.form:
            return jsonify({'error': 'Missing form data'}), 400
            
        if 'id_card_photo' not in request.files:
            return jsonify({'error': 'ID card photo is required for registration'}), 400
        
        # Extract data
        data = request.form.to_dict()
        file = request.files['id_card_photo']
        
        # Validate required fields
        required_fields = ['name', 'username', 'email', 'password', 'student_id', 'department', 'semester']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate student ID format (must be 8 digits)
        if not data['student_id'].isdigit() or len(data['student_id']) != 8:
            return jsonify({'error': 'Student ID must be an 8-digit number'}), 400
        
        # Validate email format (must be name@g.bracu.ac.bd)
        email = data['email'].strip()
        if not email.endswith('@g.bracu.ac.bd'):
            return jsonify({'error': 'Email must be in the format name@g.bracu.ac.bd'}), 400
        
        # Validate password strength
        password = data['password']
        if (not any(c.isupper() for c in password) or
            not any(c.islower() for c in password) or
            not any(c.isdigit() for c in password) or
            not any(c in '!@#$%^&*()_+-=[]{};\'"\\|,.<>/?' for c in password)):
            return jsonify({'error': 'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character'}), 400
        
        # Check if username or email already exists
        client = current_app.mongo_client
        db = client.get_database()
        users_collection = db.users
        
        existing_user = users_collection.find_one({"$or": [{"email": email}, {"username": data['username']}]})
        if existing_user:
            if existing_user.get('email') == email:
                return jsonify({'error': 'Email already registered'}), 400
            else:
                return jsonify({'error': 'Username already taken'}), 400
        
        # Save the ID card photo if valid
        id_card_url = None
        if file.filename == '':
            return jsonify({'error': 'No ID card photo selected'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Use unique filename to avoid collisions
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            id_card_url = f"/uploads/{unique_filename}"
        else:
            return jsonify({'error': 'Invalid file format. Only PNG, JPG, JPEG are allowed'}), 400
        
        # Create user object
        new_user = {
            "email": email,
            "username": data['username'],
            "password": generate_password_hash(data['password']),
            "name": data['name'],
            "student_id": data['student_id'],
            "department": data['department'],
            "semester": data['semester'],
            "id_card_photo": id_card_url,
            "verification_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert user into database
        result = users_collection.insert_one(new_user)
        
        return jsonify({
            'message': 'Registration successful. Your account is pending approval by an administrator. You will be notified when your account is verified.',
            'user_id': str(result.inserted_id),
            'status': 'pending'
        }), 201
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'An error occurred during registration. Please try again.'}), 500

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Strict rate limit for login attempts to prevent brute force
def login():
    try:
        data = request.get_json()
        
        # Check if identifier (email/username) and password are provided
        if not data or 'identifier' not in data or 'password' not in data:
            return jsonify({"error": "Username/Email and password are required"}), 400
        
        # Check if user exists and password is correct
        client = current_app.mongo_client
        db = client.get_database()
        users_collection = db.users
        
        identifier = data['identifier'].strip()
        password = data['password']
        
        # Try to find user by email or username
        user = users_collection.find_one({"$or": [{"email": identifier}, {"username": identifier}]})
        if not user:
            return jsonify({"error": "Invalid username/email or password"}), 401
        
        # Check password
        if not check_password_hash(user['password'], password):
            return jsonify({"error": "Invalid username/email or password"}), 401
        
        # Check if user is approved
        verification_status = user.get('verification_status')
        if not verification_status or verification_status != 'approved':
            return jsonify({
                'error': 'Your account is pending approval. Please check back later.',
                'status': verification_status or 'pending'
            }), 403
        
        # Generate access token
        access_token = create_access_token(
            identity=str(user['_id']),
            expires_delta=timedelta(days=1)
        )
        
        # Return user info and token
        user_info = {
            'id': str(user['_id']),
            'email': user['email'],
            'username': user['username'],
            'name': user['name'],
            'student_id': user.get('student_id', ''),
            'department': user.get('department', '')
        }
        
        return jsonify({
            'user': user_info,
            'access_token': access_token
        }), 200
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "An error occurred during login. Please try again."}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per hour")  # Limit password reset requests
def forgot_password():
    try:
        data = request.get_json()
        
        # Check if email is provided
        if not data or 'email' not in data:
            return jsonify({"error": "Email is required"}), 400
            
        email = data['email'].strip()
        
        # Validate email format (must be name@g.bracu.ac.bd)
        if not email.endswith('@g.bracu.ac.bd'):
            return jsonify({'error': 'Email must be in the format name@g.bracu.ac.bd'}), 400
        
        # Generate reset token
        reset_info = user_model.create_password_reset_token(email)
        if not reset_info:
            # Don't reveal if email exists or not for security reasons
            return jsonify({"message": "If your email is registered, you will receive password reset instructions"}), 200
        
        # Create reset link
        # In a real-world scenario, this would be a frontend URL
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_url}/reset-password?token={reset_info['token']}"
        
        # Log the reset link for development purposes
        current_app.logger.info(f"Password reset link for {email}: {reset_link}")
        
        # For development: Return the token directly instead of sending an email
        # In production, you would want to actually send the email
        try:
            # Prepare email content
            email_content = render_template_string(
                PASSWORD_RESET_EMAIL_TEMPLATE,
                name=reset_info['name'],
                reset_link=reset_link
            )
            
            # Try to send email, but don't fail if it doesn't work
            send_email(
                to_email=email,
                subject="BRACU Eureka - Password Reset",
                html_content=email_content
            )
        except Exception as e:
            current_app.logger.error(f"Email sending failed but continuing: {str(e)}")
        
        # Return success with token for development
        return jsonify({
            "message": "Password reset instructions have been sent.",
            "dev_info": {
                "reset_link": reset_link,
                "token": reset_info['token'],
                "expires": reset_info['expiry'].isoformat()
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Forgot password error: {str(e)}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500

@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    try:
        data = request.get_json()
        
        # Check if token is provided
        if not data or 'token' not in data:
            return jsonify({"error": "Reset token is required"}), 400
            
        token = data['token']
        
        # Verify token
        user_info = user_model.verify_reset_token(token)
        if not user_info:
            return jsonify({"error": "Invalid or expired reset token"}), 400
            
        return jsonify({"valid": True, "email": user_info['email']}), 200
    except Exception as e:
        current_app.logger.error(f"Verify reset token error: {str(e)}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        
        # Check if required fields are provided
        if not data or 'token' not in data or 'password' not in data:
            return jsonify({"error": "Reset token and new password are required"}), 400
            
        token = data['token']
        password = data['password']
        
        # Validate password strength
        if (not any(c.isupper() for c in password) or
            not any(c.islower() for c in password) or
            not any(c.isdigit() for c in password) or
            not any(c in '!@#$%^&*()_+-=[]{};\'"\\|,.<>/?' for c in password)):
            return jsonify({'error': 'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character'}), 400
        
        # Reset password
        success = user_model.reset_password(token, password)
        if not success:
            return jsonify({"error": "Invalid or expired reset token"}), 400
            
        return jsonify({"message": "Password has been reset successfully. You can now log in with your new password."}), 200
    except Exception as e:
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500

@auth_bp.route('/admin/login', methods=['POST'])
@limiter.limit("5 per minute")  # Very strict limit for admin login attempts
def admin_login():
    try:
        data = request.get_json()
        
        # Check if email and password are provided
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400
        
        email = data['email'].strip()
        password = data['password']

        # First check hardcoded admin credentials
        if email == "470@gmail.com" and password == "bracu2025":
            # Generate admin JWT token
            access_token = create_access_token(
                identity="470@gmail.com",  # Use email as identity
                additional_claims={
                    "role": "admin",
                    "email": "470@gmail.com"
                },
                expires_delta=timedelta(days=7)  # Extend token validity to 7 days
            )
            
            return jsonify({
                'admin': {
                    'email': '470@gmail.com',
                    'role': 'admin'
                },
                'access_token': access_token
            }), 200

        # If not hardcoded admin, check database
        client = current_app.mongo_client
        db = client.get_database()
        users_collection = db.users
        
        admin_user = users_collection.find_one({
            "email": email,
            "role": "admin"
        })
        
        if not admin_user or not check_password_hash(admin_user['password'], password):
            return jsonify({"error": "Invalid admin credentials"}), 401
        
        # Generate admin JWT token with admin role and user ID
        access_token = create_access_token(
            identity=str(admin_user['_id']),
            additional_claims={"role": "admin"},
            expires_delta=timedelta(days=1)
        )
        
        return jsonify({
            'admin': {
                'id': str(admin_user['_id']),
                'email': admin_user['email'],
                'role': 'admin'
            },
            'access_token': access_token
        }), 200
    except Exception as e:
        current_app.logger.error(f"Admin login error: {str(e)}")
        return jsonify({"error": "An error occurred during login. Please try again."}), 500

@auth_bp.route('/verify-token', methods=['GET'])
@limiter.limit("100 per minute")  # Higher limit for token verification as it's frequently used
def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # For JWT tokens created with flask_jwt_extended
        from flask_jwt_extended import decode_token
        
        try:
            # Try to decode token
            decoded = decode_token(token)
            role = decoded.get('role')
            identity = decoded.get('sub')
            
            # Check if it's an admin token
            if role == 'admin' and identity == '470@gmail.com':
                return jsonify({
                    'admin': {
                        'email': '470@gmail.com',
                        'role': 'admin'
                    },
                    'valid': True,
                    'admin': True,
                    'access_token': token  # Return the token back for reuse
                }), 200
            
            # If not admin, check if it's a regular user
            if identity:
                client = current_app.mongo_client
                db = client.get_database()
                users_collection = db.users
                
                # For regular users, try to find by ObjectId first
                try:
                    user = users_collection.find_one({"_id": ObjectId(identity)})
                except:
                    # If not ObjectId, try finding by email
                    user = users_collection.find_one({"email": identity})
                
                if user:
                    user_info = {
                        'id': str(user['_id']),
                        'email': user['email'],
                        'name': user['name']
                    }
                    return jsonify({'user': user_info, 'valid': True, 'admin': False}), 200
            
            return jsonify({'error': 'Invalid token payload'}), 401
            
        except Exception as token_error:
            # It might be one of our old manual JWT tokens, try the old way
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            
            # Check if it's an old user token
            if 'user_id' in payload:
                client = current_app.mongo_client
                db = client.get_database()
                users_collection = db.users
                
                user = users_collection.find_one({"_id": ObjectId(payload['user_id'])})
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                user_info = {
                    'id': str(user['_id']),
                    'email': user['email'],
                    'name': user['name']
                }
                return jsonify({'user': user_info, 'valid': True, 'admin': False}), 200
                
            # Check if it's an old admin token
            elif 'admin_id' in payload and payload['role'] == 'admin':
                return jsonify({
                    'admin': {
                        'email': '470@gmail.com',
                        'role': 'admin'
                    },
                    'valid': True,
                    'admin': True
                }), 200
            
            return jsonify({'error': 'Invalid token payload'}), 401
            
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@auth_bp.route('/init-test-user', methods=['GET'])
@limiter.limit("5 per hour")  # Very strict limit as this is a development endpoint
def init_test_user():
    try:
        client = current_app.mongo_client
        db = client.get_database()
        users_collection = db.users
        
        # Check if test user already exists
        test_user = users_collection.find_one({"email": "test@example.com"})
        if test_user:
            return jsonify({"message": "Test user already exists", "user_id": str(test_user['_id'])}), 200
        
        # Create test user
        new_user = {
            "email": "test@example.com",
            "password": generate_password_hash("password123"),
            "name": "Test User",
            "role": "user"
        }
        
        result = users_collection.insert_one(new_user)
        
        return jsonify({"message": "Test user created successfully", "user_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/init-demo-data', methods=['GET'])
def init_demo_data():
    """Initialize demo data for testing - only for development"""
    try:
        client = current_app.mongo_client
        db = client.get_database()
        users_collection = db.users
        items_collection = db.marketplace_items
        rooms_collection = db.rooms
        bookings_collection = db.bookings
        
        # Clear existing data
        users_collection.delete_many({})
        items_collection.delete_many({})
        rooms_collection.delete_many({})
        bookings_collection.delete_many({})
        
        # Create admin user
        admin_user = {
            "email": "470@gmail.com",
            "password": generate_password_hash("bracu2025"),
            "name": "Admin User",
            "role": "admin",
            "verification_status": "approved",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        admin_id = users_collection.insert_one(admin_user).inserted_id
        
        # Create test users
        test_users = []
        for i in range(5):
            user = {
                "email": f"student{i+1}@g.bracu.ac.bd",
                "password": generate_password_hash("password123"),
                "name": f"Test Student {i+1}",
                "student_id": f"2020100{i+1}",
                "department": "Computer Science and Engineering",
                "semester": f"{i+1}th",
                "phone": f"017123456{i+1}",
                "verification_status": "approved" if i < 3 else "pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "id_card_photo": "/uploads/default_id_card.jpg"  # Default image
            }
            user_id = users_collection.insert_one(user).inserted_id
            test_users.append({"id": user_id, "name": user["name"]})
        
        # Create test items
        items = [
            {
                "title": "Data Structures Textbook",
                "description": "Gently used textbook for CSE220",
                "price": 500.0,
                "category": "Books",
                "user_id": test_users[0]["id"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Scientific Calculator",
                "description": "Casio fx-991ES PLUS, like new",
                "price": 1200.0,
                "category": "Electronics",
                "user_id": test_users[1]["id"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        for item in items:
            items_collection.insert_one(item)
        
        # Create test rooms
        rooms = [
            {
                "name": "UB40201",
                "building": "UB4",
                "floor": "2",
                "capacity": 40,
                "type": "Lecture Room",
                "active": True
            },
            {
                "name": "UB50301",
                "building": "UB5",
                "floor": "3",
                "capacity": 30,
                "type": "Lab",
                "active": True
            }
        ]
        
        room_ids = []
        for room in rooms:
            room_id = rooms_collection.insert_one(room).inserted_id
            room_ids.append(room_id)
        
        # Create test bookings
        bookings = [
            {
                "room_id": room_ids[0],
                "user_id": test_users[0]["id"],
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "start_time": "10:00",
                "end_time": "12:00",
                "purpose": "CSE470 Project Meeting",
                "status": "approved",
                "created_at": datetime.utcnow()
            },
            {
                "room_id": room_ids[1],
                "user_id": test_users[1]["id"],
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "start_time": "14:00",
                "end_time": "16:00",
                "purpose": "Study Group",
                "status": "pending",
                "created_at": datetime.utcnow()
            }
        ]
        
        for booking in bookings:
            bookings_collection.insert_one(booking)
        
        # Generate tokens for easy testing
        admin_token = create_access_token(
            identity="admin",
            additional_claims={"role": "admin"},
            expires_delta=timedelta(days=7)
        )
        
        user_token = create_access_token(
            identity=str(test_users[0]["id"]),
            expires_delta=timedelta(days=7)
        )
        
        return jsonify({
            "message": "Demo data initialized successfully",
            "admin": {"email": "470@gmail.com", "password": "bracu2025", "token": admin_token},
            "users": [
                {"email": "student1@g.bracu.ac.bd", "password": "password123", "token": user_token, "status": "approved"},
                {"email": "student2@g.bracu.ac.bd", "password": "password123", "status": "approved"},
                {"email": "student3@g.bracu.ac.bd", "password": "password123", "status": "approved"},
                {"email": "student4@g.bracu.ac.bd", "password": "password123", "status": "pending"},
                {"email": "student5@g.bracu.ac.bd", "password": "password123", "status": "pending"}
            ],
            "items_count": items_collection.count_documents({}),
            "rooms_count": rooms_collection.count_documents({}),
            "bookings_count": bookings_collection.count_documents({})
        }), 200
    except Exception as e:
        current_app.logger.error(f"Init demo data error: {str(e)}")
        return jsonify({"error": str(e)}), 500 