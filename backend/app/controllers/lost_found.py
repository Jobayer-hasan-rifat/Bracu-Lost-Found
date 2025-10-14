from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
import datetime
import os
import base64
import uuid
from werkzeug.utils import secure_filename
from ..utils.upload import save_image
from .. import cache, limiter

lost_found_bp = Blueprint('lost_found', __name__)
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

# Configure upload folder for Lost & Found images
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads', 'lost_found')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to save base64 image
def save_base64_image(base64_string, folder):
    try:
        # Extract the image data from the base64 string
        if ',' in base64_string:
            header, base64_data = base64_string.split(',', 1)
        else:
            base64_data = base64_string
            
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        
        # Generate a unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        
        # Make sure the folder exists
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'lost_found')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Create the full path
        file_path = os.path.join(upload_folder, filename)
        
        # Save the image
        with open(file_path, 'wb') as f:
            f.write(image_data)
            
        # Return the URL path for the image
        return f"/uploads/lost_found/{filename}"
    except Exception as e:
        current_app.logger.error(f"Error saving base64 image: {str(e)}")
        return None

@lost_found_bp.route('/items', methods=['GET'])
@limiter.limit("30 per minute")
def get_items():
    items = list(db.lost_found_items.find())
    for item in items:
        item['_id'] = str(item['_id'])
        if 'user_id' in item:
            user_id = item['user_id']
            item['user_id'] = str(user_id)
            
            # Add creator information
            try:
                user = db.users.find_one({'_id': ObjectId(user_id)})
                if user:
                    item['creator_name'] = user.get('name', 'Anonymous')
                    item['creator_email'] = user.get('email', 'No email provided')
                else:
                    item['creator_name'] = 'Anonymous'
                    item['creator_email'] = 'No email provided'
            except Exception as e:
                current_app.logger.error(f"Error getting creator info: {str(e)}")
                item['creator_name'] = 'Anonymous'
                item['creator_email'] = 'No email provided'
    
    # Add cache control headers
    response = jsonify(items)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response, 200

@lost_found_bp.route('/items', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def create_item():
    try:
        user_id = get_jwt_identity()
        
        # Check if the request has form data or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            
            # Validate request data
            required_fields = ['title', 'description', 'item_type', 'location', 'date']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing {field}'}), 400
            
            # Validate item_type (lost or found)
            if data['item_type'] not in ['lost', 'found']:
                return jsonify({'error': 'Item type must be "lost" or "found"'}), 400
            
            new_item = {
                'title': data['title'],
                'description': data['description'],
                'item_type': data['item_type'],
                'location': data['location'],
                'date': data['date'],
                'user_id': ObjectId(user_id),
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'status': 'open',
                'contact': data.get('contact', ''),
                'phone': data.get('phone', '')
            }
            
            if 'category' in data:
                new_item['category'] = data['category']
            
            # Handle image upload
            if 'image' in request.files and request.files['image']:
                try:
                    image_file = request.files['image']
                    image_url = save_image(image_file, 'lost_found')
                    if image_url:
                        new_item['image'] = image_url
                except Exception as e:
                    current_app.logger.error(f"Error processing image: {str(e)}")
            
            # Handle ID card image upload
            if 'idCardImage' in request.files and request.files['idCardImage']:
                try:
                    id_card_file = request.files['idCardImage']
                    id_card_url = save_image(id_card_file, 'lost_found')
                    if id_card_url:
                        new_item['idCardImage'] = id_card_url
                except Exception as e:
                    current_app.logger.error(f"Error processing ID card image: {str(e)}")
        else:
            # Handle JSON request
            data = request.get_json()
            
            # Validate request data
            required_fields = ['title', 'description', 'item_type', 'location', 'date']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing {field}'}), 400
            
            # Validate item_type (lost or found)
            if data['item_type'] not in ['lost', 'found']:
                return jsonify({'error': 'Item type must be "lost" or "found"'}), 400
            
            new_item = {
                'title': data['title'],
                'description': data['description'],
                'item_type': data['item_type'],
                'location': data['location'],
                'date': data['date'],
                'user_id': ObjectId(user_id),
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'status': 'open',
                'contact': data.get('contact', ''),
                'phone': data.get('phone', '')
            }
            
            if 'category' in data:
                new_item['category'] = data['category']
            
            # Handle base64 image upload
            if 'image' in data and data['image'] and isinstance(data['image'], str) and data['image'].startswith('data:'):
                try:
                    # Save the base64 image
                    image_url = save_base64_image(data['image'], 'lost_found')
                    if image_url:
                        # Store the image path in the database
                        new_item['image'] = image_url
                        current_app.logger.info(f"Image saved successfully: {image_url}")
                except Exception as e:
                    current_app.logger.error(f"Error processing image: {str(e)}")
            
            # ID card image handling removed as requested
    except Exception as e:
        current_app.logger.error(f"Error creating lost & found item: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    result = db.lost_found_items.insert_one(new_item)
    
    # Clear all related caches
    cache.delete('view/api/lost-found/items')
    cache.delete(f'view/api/lost-found/user-items/{user_id}')
    cache.delete_many('view/api/lost-found/*')
    cache.delete_many('view/api/admin/*')  # Clear admin related caches
    
    return jsonify({
        'message': 'Item reported successfully',
        'item_id': str(result.inserted_id)
    }), 201

@lost_found_bp.route('/items/<item_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_item(item_id):
    try:
        item = db.lost_found_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        item['_id'] = str(item['_id'])
        if 'user_id' in item:
            user_id = item['user_id']
            item['user_id'] = str(user_id)
            
            # Add creator information
            try:
                user = db.users.find_one({'_id': user_id})
                if user:
                    item['creator_name'] = user.get('name', 'Anonymous')
                    item['creator_email'] = user.get('email', 'No email provided')
                else:
                    item['creator_name'] = 'Anonymous'
                    item['creator_email'] = 'No email provided'
            except Exception as e:
                current_app.logger.error(f"Error getting creator info: {str(e)}")
                item['creator_name'] = 'Anonymous'
                item['creator_email'] = 'No email provided'
        
        # Add cache control headers
        response = jsonify(item)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@lost_found_bp.route('/user-items/<user_id>', methods=['GET'])
@limiter.limit("30 per minute")
@jwt_required()
def get_user_items(user_id):
    try:
        # Get user's ID from JWT token for authorization
        token_user_id = get_jwt_identity()
        
        # Only allow users to access their own data or admin
        if token_user_id != user_id:
            # Check if user is admin
            admin_user = db.users.find_one({"_id": ObjectId(token_user_id), "role": "admin"})
            if not admin_user:
                return jsonify({"error": "Unauthorized access to user data"}), 403
        
        # Get user's items from database using ObjectId
        items = list(db.lost_found_items.find({"user_id": ObjectId(user_id)}))
        
        # Convert ObjectIds to strings
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
        
        # Add cache control headers
        response = jsonify(items)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error getting user items: {str(e)}")
        return jsonify({"error": str(e)}), 500

@lost_found_bp.route('/items/<item_id>', methods=['PUT'])
@limiter.limit("20 per minute")
@jwt_required()
def update_item(item_id):
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Check if item exists and belongs to user
        item = db.lost_found_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        if str(item['user_id']) != user_id:
            # Check if user is admin
            admin_user = db.users.find_one({"_id": ObjectId(user_id), "role": "admin"})
            if not admin_user:
                return jsonify({'error': 'Unauthorized to update this item'}), 403
        
        # Update fields
        update_data = {'updated_at': datetime.datetime.utcnow()}
        allowed_fields = ['title', 'description', 'location', 'date', 'status', 'category', 'contact', 'phone']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
                
        # Handle image update
        if 'image' in data and data['image'] and data['image'].startswith('data:'):
            try:
                # Save the base64 image
                image_filename = save_base64_image(data['image'], UPLOAD_FOLDER)
                if image_filename:
                    # Store the image path in the database
                    update_data['image'] = f"/api/lost-found/images/{image_filename}"
            except Exception as e:
                current_app.logger.error(f"Error processing image: {str(e)}")
        
        # Handle ID card image update
        if 'idCardImage' in data and data['idCardImage'] and data['idCardImage'].startswith('data:'):
            try:
                # Save the base64 image
                id_card_filename = save_base64_image(data['idCardImage'], UPLOAD_FOLDER)
                if id_card_filename:
                    # Store the image path in the database
                    update_data['idCardImage'] = f"/api/lost-found/images/{id_card_filename}"
            except Exception as e:
                current_app.logger.error(f"Error processing ID card image: {str(e)}")
        
        db.lost_found_items.update_one(
            {'_id': ObjectId(item_id)},
            {'$set': update_data}
        )
        
        # Clear all related caches
        cache.delete('view/api/lost-found/items')
        cache.delete(f'view/api/lost-found/items/{item_id}')
        cache.delete(f'view/api/lost-found/user-items/{str(item["user_id"])}')
        cache.delete_many('view/api/lost-found/*')
        cache.delete_many('view/api/admin/*')  # Clear admin related caches
        
        return jsonify({'message': 'Item updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@lost_found_bp.route('/items/<item_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
@jwt_required()
def delete_item(item_id):
    try:
        user_id = get_jwt_identity()
        
        # Check if item exists and belongs to user
        item = db.lost_found_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        if str(item['user_id']) != user_id:
            # Check if user is admin
            admin_user = db.users.find_one({"_id": ObjectId(user_id), "role": "admin"})
            if not admin_user:
                return jsonify({'error': 'Unauthorized to delete this item'}), 403
        
        # Store user_id before deleting for cache invalidation
        item_user_id = str(item['user_id'])
        
        # Delete item
        db.lost_found_items.delete_one({'_id': ObjectId(item_id)})
        
        # Clear all related caches
        cache.delete('view/api/lost-found/items')
        cache.delete(f'view/api/lost-found/items/{item_id}')
        cache.delete(f'view/api/lost-found/user-items/{item_user_id}')
        cache.delete_many('view/api/lost-found/*')
        cache.delete_many('view/api/admin/*')  # Clear admin related caches
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@lost_found_bp.route('/claim/<item_id>', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def claim_item(item_id):
    try:
        user_id = get_jwt_identity()
        
        # Check if item exists
        item = db.lost_found_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        # Only allow claiming "found" items
        if item['item_type'] != 'found':
            return jsonify({'error': 'Only found items can be claimed'}), 400
        
        # Already claimed
        if item['status'] == 'claimed':
            return jsonify({'error': 'Item already claimed'}), 400
        
        claim_data = request.get_json() or {}
        
        # Create claim
        claim = {
            'item_id': item_id,
            'claimant_id': user_id,
            'proof': claim_data.get('proof', ''),
            'contact': claim_data.get('contact', ''),
            'status': 'pending',
            'created_at': datetime.datetime.utcnow()
        }
        
        db.claims.insert_one(claim)
        
        # Clear related caches
        cache.delete(f'view/api/lost-found/items/{item_id}')
        cache.delete_many('view/api/lost-found/*')
        cache.delete_many('view/api/admin/*')
        
        return jsonify({'message': 'Claim submitted successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400 

# Route to serve images
@lost_found_bp.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving image: {str(e)}")
        return jsonify({'error': 'Image not found'}), 404

# Route to serve uploads directly
@lost_found_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    try:
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving upload: {str(e)}")
        return jsonify({'error': 'File not found'}), 404