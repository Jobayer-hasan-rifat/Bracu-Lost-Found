"""
Simple Flask server to handle ride share API requests
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import json

# Create Flask app
app = Flask(__name__)

# Configure CORS - allow specific origin with credentials
CORS(app, 
     resources={r'/*': {
         'origins': 'http://localhost:3000',  # Specific frontend origin
         'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With'],
         'supports_credentials': True,
         'expose_headers': ['Content-Type', 'Authorization'],
         'max_age': 600  # Cache preflight requests for 10 minutes
     }})

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

# Custom JSON encoder to handle ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MongoJSONEncoder, self).default(obj)

app.json_encoder = MongoJSONEncoder

# Routes for ride share posts
@app.route('/api/ride/posts', methods=['GET'])
@app.route('/ride/posts', methods=['GET'])
def get_ride_posts():
    """Get all ride share posts"""
    try:
        # Get all ride posts from the database
        posts = list(db.ride_posts.find({}))
        return jsonify(posts)
    except Exception as e:
        print(f"Error in get_ride_posts: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ride/posts/<post_id>', methods=['PUT'])
@app.route('/ride/posts/<post_id>', methods=['PUT'])
def update_ride_post(post_id):
    """Update a ride share post"""
    try:
        # Get post data from request
        data = request.get_json()
        
        # Update the post in the database
        result = db.ride_posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": data}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Post not found or no changes made"}), 404
            
        return jsonify({"message": "Ride post updated successfully"}), 200
    except Exception as e:
        print(f"Error in update_ride_post: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ride/posts/<post_id>', methods=['DELETE'])
@app.route('/ride/posts/<post_id>', methods=['DELETE'])
def delete_ride_post(post_id):
    """Delete a ride share post"""
    try:
        # Delete the post from the database
        result = db.ride_posts.delete_one({"_id": ObjectId(post_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Post not found"}), 404
            
        return jsonify({"message": "Ride post deleted successfully"}), 200
    except Exception as e:
        print(f"Error in delete_ride_post: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Routes for user management
@app.route('/api/admin/users', methods=['GET'])
@app.route('/admin/users', methods=['GET'])
def get_users():
    """Get all users with optional filtering"""
    try:
        # Get filter type from query params
        filter_type = request.args.get('filter', 'all')
        
        # Apply filters based on filter type
        if filter_type == 'pending':
            users = list(db.users.find({"verification_status": "pending"}))
        elif filter_type == 'verified':
            users = list(db.users.find({"verification_status": "approved"}))
        else:
            users = list(db.users.find({}))
            
        return jsonify(users)
    except Exception as e:
        print(f"Error in get_users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/users/<user_id>/verify', methods=['PUT'])
@app.route('/admin/users/<user_id>/verify', methods=['PUT'])
def verify_user(user_id):
    """Verify a user"""
    try:
        # Update user verification status
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"verification_status": "approved"}}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "User not found or already verified"}), 404
            
        return jsonify({"message": "User verified successfully"}), 200
    except Exception as e:
        print(f"Error in verify_user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/users/<user_id>/reject', methods=['PUT'])
@app.route('/admin/users/<user_id>/reject', methods=['PUT'])
def reject_user(user_id):
    """Reject a user"""
    try:
        # Update user verification status
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"verification_status": "rejected"}}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "User not found or already rejected"}), 404
            
        return jsonify({"message": "User rejected successfully"}), 200
    except Exception as e:
        print(f"Error in reject_user: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Routes for marketplace items
@app.route('/api/marketplace/items', methods=['GET'])
@app.route('/marketplace/items', methods=['GET'])
def get_marketplace_items():
    """Get all marketplace items"""
    try:
        # Get all marketplace items from the database
        items = list(db.marketplace_items.find({}))
        return jsonify(items)
    except Exception as e:
        print(f"Error in get_marketplace_items: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Routes for lost & found items
@app.route('/api/lost-found/items', methods=['GET'])
@app.route('/lost-found/items', methods=['GET'])
def get_lost_found_items():
    """Get all lost & found items"""
    try:
        # Get all lost & found items from the database
        items = list(db.lost_found_items.find({}))
        return jsonify(items)
    except Exception as e:
        print(f"Error in get_lost_found_items: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Routes for announcements
@app.route('/api/announcements', methods=['GET'])
@app.route('/announcements', methods=['GET'])
def get_announcements():
    """Get all announcements"""
    try:
        # Get all announcements from the database
        announcements = list(db.announcements.find({}))
        return jsonify(announcements)
    except Exception as e:
        print(f"Error in get_announcements: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/statistics', methods=['GET'])
@app.route('/admin/statistics', methods=['GET'])
def get_statistics():
    """Get platform statistics for the admin dashboard"""
    try:
        # Count users by verification status
        total_users = db.users.count_documents({})
        verified_users = db.users.count_documents({'verification_status': 'approved'})
        pending_users = db.users.count_documents({'verification_status': 'pending'})
        
        # Count items by type
        ride_share_posts = db.ride_posts.count_documents({})
        marketplace_items = db.marketplace_items.count_documents({})
        lost_found_items = db.lost_found_items.count_documents({})
        
        # Get recent items
        recent_ride_share_posts = list(db.ride_posts.find({}).sort('_id', -1).limit(5))
        recent_marketplace_items = list(db.marketplace_items.find({}).sort('_id', -1).limit(5))
        recent_lost_found_items = list(db.lost_found_items.find({}).sort('_id', -1).limit(5))
        
        statistics = {
            'users': {
                'total': total_users,
                'verified': verified_users,
                'pending': pending_users
            },
            'items': {
                'ride_share': ride_share_posts,
                'marketplace': marketplace_items,
                'lost_found': lost_found_items
            },
            'recent': {
                'ride_share': recent_ride_share_posts,
                'marketplace': recent_marketplace_items,
                'lost_found': recent_lost_found_items
            }
        }
        
        return jsonify(statistics)
    except Exception as e:
        print(f"Error in get_statistics: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Routes for notifications
@app.route('/api/notifications/page/<page>', methods=['GET'])
@app.route('/notifications/page/<page>', methods=['GET'])
def get_notifications_by_page(page):
    """Get notifications by page"""
    try:
        # Sample notifications data
        notifications = [
            {
                "_id": "1",
                "title": "Welcome to BRACU Eureka",
                "content": "Thank you for joining our platform!",
                "type": "info",
                "active": True,
                "created_at": "2023-01-01T12:00:00Z"
            },
            {
                "_id": "2",
                "title": "New Ride Share Feature",
                "content": "Check out our new ride sharing feature!",
                "type": "feature",
                "active": True,
                "created_at": "2023-01-02T12:00:00Z"
            }
        ]
        return jsonify(notifications)
    except Exception as e:
        print(f"Error in get_notifications_by_page: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Routes for authentication
@app.route('/api/auth/login', methods=['POST'])
@app.route('/auth/login', methods=['POST'])
def login():
    """Login a user"""
    try:
        # Get login data from request
        data = request.get_json()
        identifier = data.get('identifier')  # Can be email or username
        password = data.get('password')
        
        print(f"Login attempt with identifier: {identifier}")
        
        # Check if it's an admin login
        if identifier == 'admin@example.com' and password == 'admin123':
            # Return admin token
            return jsonify({
                "access_token": "admin-token-123",
                "user": {
                    "_id": "admin-123",
                    "email": identifier,
                    "name": "Admin User",
                    "role": "admin"
                }
            })
        
        # For student login - create a mock student user
        if identifier and password:
            # For testing purposes, allow any login
            student_user = {
                "_id": "student-123",
                "email": identifier if '@' in identifier else f"{identifier}@example.com",
                "name": "Student User",
                "role": "student",
                "verification_status": "verified"
            }
            
            # Return user token
            return jsonify({
                "access_token": "student-token-123",
                "user": student_user
            })
        
        # If we get here, credentials are invalid
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Error in login: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
@app.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        # Get registration data from request
        data = request.get_json()
        email = data.get('email')
        
        # Check if user already exists
        existing_user = db.users.find_one({"email": email})
        if existing_user:
            return jsonify({"error": "User already exists"}), 409
        
        # Create new user
        new_user = {
            "email": email,
            "name": data.get('name', ''),
            "password": data.get('password', ''),  # In a real app, you would hash this
            "verification_status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        result = db.users.insert_one(new_user)
        
        return jsonify({
            "message": "User registered successfully",
            "user_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        print(f"Error in register: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Handle OPTIONS requests
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
