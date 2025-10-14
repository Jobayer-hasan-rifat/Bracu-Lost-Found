from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
import datetime
import os
from werkzeug.utils import secure_filename
import uuid
from .. import limiter

users_bp = Blueprint('users', __name__)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

@users_bp.route('/me', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required()
def get_current_user():
    """Get current user details from JWT token"""
    try:
        # Get user's ID from JWT token
        user_id = get_jwt_identity()
        
        # Get user data from database
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Remove sensitive information
        user.pop('password', None)
        
        # Convert ObjectId to string
        user['_id'] = str(user['_id'])

        # Fix profile_picture and id_card_photo URLs
        if 'profile_picture' in user and user['profile_picture']:
            if not user['profile_picture'].startswith('/uploads/') and not user['profile_picture'].startswith('http'):
                user['profile_picture'] = '/uploads/profiles/' + user['profile_picture']
        if 'id_card_photo' in user and user['id_card_photo']:
            if not user['id_card_photo'].startswith('/uploads/') and not user['id_card_photo'].startswith('http'):
                user['id_card_photo'] = '/uploads/' + user['id_card_photo']

        return jsonify(user), 200
    except Exception as e:
        current_app.logger.error(f"Error getting current user: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Constants
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads', 'profiles')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@users_bp.route('/<user_id>', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required()
def get_user(user_id):
    """Get user details"""
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Only allow users to access their own data
        if token_user_id != user_id:
            return jsonify({"error": "Unauthorized access to user data"}), 403
        
        # Get user data from database
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Remove sensitive information
        user.pop('password', None)
        
        # Convert ObjectId to string
        user['_id'] = str(user['_id'])

        # Fix profile_picture and id_card_photo URLs
        if 'profile_picture' in user and user['profile_picture']:
            if not user['profile_picture'].startswith('/uploads/') and not user['profile_picture'].startswith('http'):
                user['profile_picture'] = '/uploads/profiles/' + user['profile_picture']
        if 'id_card_photo' in user and user['id_card_photo']:
            if not user['id_card_photo'].startswith('/uploads/') and not user['id_card_photo'].startswith('http'):
                user['id_card_photo'] = '/uploads/' + user['id_card_photo']

        return jsonify(user), 200
    except Exception as e:
        current_app.logger.error(f"Error getting user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@users_bp.route('/<user_id>', methods=['PUT'])
@limiter.limit("10 per minute")
@jwt_required()
def update_user(user_id):
    """Update user details"""
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Only allow users to update their own data
        if token_user_id != user_id:
            return jsonify({"error": "Unauthorized to update user data"}), 403
        
        # Get updated data - handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        current_app.logger.info(f"Updating user {user_id} with data: {data}")
        
        # Handle base64 profile picture if present
        if 'profile_picture_data' in data and data['profile_picture_data']:
            try:
                # Extract base64 data
                image_data = data['profile_picture_data']
                if image_data.startswith('data:image'):
                    # Save the image
                    unique_filename = f"profile_{user_id}_{uuid.uuid4()}.jpg"
                    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    
                    # Extract the base64 data
                    header, base64_data = image_data.split(',', 1)
                    import base64
                    image_bytes = base64.b64decode(base64_data)
                    
                    # Save the image
                    with open(file_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    # Update profile picture path
                    profile_picture_url = f"/uploads/profiles/{unique_filename}"
                    data['profile_picture'] = profile_picture_url
                    
                    # Delete old profile picture if exists
                    user = db.users.find_one({"_id": ObjectId(user_id)})
                    if user and 'profile_picture' in user and user['profile_picture']:
                        old_file_path = os.path.join(os.path.dirname(UPLOAD_FOLDER), user['profile_picture'].lstrip('/'))
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
            except Exception as e:
                current_app.logger.error(f"Error processing profile picture: {str(e)}")
                
            # Remove the base64 data from the update
            data.pop('profile_picture_data', None)
        
        # Fields that can be updated
        allowed_fields = ['name', 'student_id', 'department', 'semester', 'phone', 'address']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # Add updated timestamp
        update_data['updated_at'] = datetime.datetime.utcnow()
        
        # Update user in database
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        # Get updated user data
        updated_user = db.users.find_one({"_id": ObjectId(user_id)})
        
        # Remove sensitive information
        updated_user.pop('password', None)
        
        # Convert ObjectId to string
        updated_user['_id'] = str(updated_user['_id'])
        
        return jsonify(updated_user), 200
    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@users_bp.route('/<user_id>/profile-picture', methods=['POST'])
@limiter.limit("5 per minute")
@jwt_required()
def update_profile_picture(user_id):
    """Update user profile picture"""
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Only allow users to update their own data
        if token_user_id != user_id:
            return jsonify({"error": "Unauthorized to update profile picture"}), 403
        
        # Check if file is provided
        if 'profile_picture' not in request.files:
            return jsonify({"error": "No profile picture provided"}), 400
        
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check if file is allowed
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format. Only PNG, JPG, JPEG, GIF are allowed"}), 400
        
        # Get user data
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Delete old profile picture if exists
        if 'profile_picture' in user and user['profile_picture']:
            old_file_path = os.path.join(os.path.dirname(UPLOAD_FOLDER), user['profile_picture'].lstrip('/'))
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Save new profile picture
        filename = secure_filename(file.filename)
        unique_filename = f"profile_{user_id}_{uuid.uuid4()}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Update profile picture path in database
        profile_picture_url = f"/uploads/profiles/{unique_filename}"
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "profile_picture": profile_picture_url,
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        
        return jsonify({
            "message": "Profile picture updated successfully",
            "profile_picture": profile_picture_url
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error updating profile picture: {str(e)}")
        return jsonify({"error": str(e)}), 500

@users_bp.route('/<user_id>/profile-picture', methods=['DELETE'])
@limiter.limit("5 per minute")
@jwt_required()
def delete_profile_picture(user_id):
    """Delete user profile picture"""
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Only allow users to delete their own profile picture
        if token_user_id != user_id:
            return jsonify({"error": "Unauthorized to delete profile picture"}), 403
        
        # Get user data
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Delete profile picture if exists
        if 'profile_picture' in user and user['profile_picture']:
            try:
                # Delete file from filesystem
                old_file_path = os.path.join(os.path.dirname(UPLOAD_FOLDER), user['profile_picture'].lstrip('/'))
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    current_app.logger.info(f"Deleted profile picture file: {old_file_path}")
            except Exception as e:
                current_app.logger.error(f"Error deleting profile picture file: {str(e)}")
        
        # Update user in database to remove profile picture
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {"profile_picture": ""},
             "$set": {"updated_at": datetime.datetime.utcnow()}}
        )
        
        return jsonify({
            "message": "Profile picture deleted successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting profile picture: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Duplicate endpoint removed

@users_bp.route('/<user_id>/purchases', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required(optional=True)
def get_user_purchases(user_id):
    """Get user purchase history"""
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Allow access if the token is valid or if it's a public profile
        # We'll still need to check if the user exists
        try:
            # Try to convert to ObjectId
            user_obj_id = ObjectId(user_id)
        except:
            # If conversion fails, use the string ID
            user_obj_id = user_id
            
        # Check if user exists
        user = db.users.find_one({"_id": user_obj_id})
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Get purchase history from database - check both collections
        # First check the user_purchases collection (new format)
        user_purchases = list(db.user_purchases.find({"buyer_id": user_id}))
        
        # Then check the purchases collection (old format)
        old_purchases = list(db.purchases.find({"user_id": user_obj_id}))
        
        # Combine both results
        all_purchases = []
        
        # Format user_purchases data (new format)
        for purchase in user_purchases:
            formatted_purchase = {
                '_id': str(purchase['_id']),
                'buyer_id': purchase.get('buyer_id', ''),
                'seller_id': purchase.get('seller_id', ''),
                'item_id': purchase.get('item_id', ''),
                'title': purchase.get('title', ''),
                'description': purchase.get('description', ''),
                'price': purchase.get('price', 0),
                'payment_method': purchase.get('payment_method', ''),
                'purchase_date': purchase.get('purchase_date', ''),
                'images': purchase.get('images', [])
            }
            all_purchases.append(formatted_purchase)
            
        # Format old purchases data
        for purchase in old_purchases:
            purchase['_id'] = str(purchase['_id'])
            purchase['user_id'] = str(purchase['user_id'])
            if 'item_id' in purchase:
                purchase['item_id'] = str(purchase['item_id'])
                
                # Get item details if available
                try:
                    item = db.marketplace_items.find_one({"_id": ObjectId(purchase['item_id'])})
                    if item:
                        purchase['title'] = item.get('title', '')
                        purchase['price'] = item.get('price', 0)
                        purchase['description'] = item.get('description', '')
                        purchase['images'] = item.get('images', [])
                except Exception as item_error:
                    print(f"Error getting item details: {str(item_error)}")
            
            all_purchases.append(purchase)
        
        return jsonify(all_purchases), 200
    except Exception as e:
        current_app.logger.error(f"Error getting purchase history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@users_bp.route('/purchases', methods=['POST'])
@limiter.limit("30 per minute")
@jwt_required(optional=True)
def create_purchase_record():
    """Create a new purchase record"""
    try:
        # Get user's ID from JWT token
        buyer_id = get_jwt_identity()
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Add buyer_id to data if not present
        if not data.get('buyer_id'):
            data['buyer_id'] = buyer_id
            
        # Add purchase date if not present
        if not data.get('purchase_date'):
            data['purchase_date'] = datetime.datetime.utcnow()
            
        # Insert purchase record
        result = db.user_purchases.insert_one(data)
        
        # Return success response
        return jsonify({
            "success": True,
            "message": "Purchase record created successfully",
            "purchase_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error creating purchase record: {str(e)}")
        return jsonify({"error": str(e)}), 500

@users_bp.route('/marketplace/user-items/<user_id>', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required()
def get_user_marketplace_items(user_id):
    """Get user's marketplace items"""
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Only allow users to access their own data
        if token_user_id != user_id:
            return jsonify({"error": "Unauthorized access to user data"}), 403
        
        # Get user's items from database
        items = list(db.marketplace_items.find({"user_id": ObjectId(user_id)}))
        
        # Convert ObjectId to string
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
        
        return jsonify(items), 200
    except Exception as e:
        current_app.logger.error(f"Error getting user items: {str(e)}")
        return jsonify({"error": str(e)}), 500 