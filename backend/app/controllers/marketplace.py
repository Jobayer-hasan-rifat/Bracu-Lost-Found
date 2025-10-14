from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
import datetime
import os
from ..utils.upload import save_image
from .. import cache, limiter
from werkzeug.utils import secure_filename
import uuid

marketplace_bp = Blueprint('marketplace', __name__)
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

@marketplace_bp.route('/items', methods=['GET'])
@limiter.limit("30 per minute")
def get_items():
    try:
        # Get all items with user details in a single query using aggregation
        pipeline = [
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user_details'
                }
            },
            {
                '$unwind': {
                    'path': '$user_details',
                    'preserveNullAndEmptyArrays': True
                }
            }
        ]
        
        items = list(db.marketplace_items.aggregate(pipeline))
        
        # Process the items
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
            # Add user details in a clean format
            if 'user_details' in item:
                item['user'] = {
                    'name': item['user_details'].get('name', ''),
                    'email': item['user_details'].get('email', '')
                }
                del item['user_details']
        
        # Add cache control headers
        response = jsonify(items)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error fetching items: {str(e)}")
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route('/items', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def create_item():
    try:
        user_id = get_jwt_identity()
        data = request.form.to_dict()
        # Validate required fields
        required_fields = ['title', 'description', 'price', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads')
        MARKETPLACE_FOLDER = os.path.join(UPLOAD_FOLDER, 'marketplace')
        if not os.path.exists(MARKETPLACE_FOLDER):
            os.makedirs(MARKETPLACE_FOLDER)
        # Handle multiple images
        images = request.files.getlist('images')
        image_urls = []
        for file in images[:3]:  # Limit to 3 images
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Create a timestamp-based filename to avoid conflicts
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(MARKETPLACE_FOLDER, unique_filename)
                file.save(file_path)
                image_urls.append(f"/uploads/marketplace/{unique_filename}")
        if not image_urls:
            return jsonify({'error': 'No image(s) provided'}), 400
        item_data = {
            "title": data['title'],
            "description": data['description'],
            "price": float(data['price']),
            "category": data['category'],
            "images": image_urls,
            "user_id": ObjectId(user_id),
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }
        result = db.marketplace_items.insert_one(item_data)
        
        # Clear all related caches to ensure real-time updates
        cache.delete('view/api/marketplace/items')
        cache.delete(f'view/api/marketplace/user-items/{user_id}')
        cache.delete(f'view/api/marketplace/items/user/{user_id}')
        cache.delete_many('view/api/marketplace/*')
        
        # Clear admin dashboard cache to ensure item appears there immediately
        cache.delete_many('view/api/admin/*')
        cache.delete('admin_statistics')
        cache.delete_many('view/api/admin/*')  # Clear admin related caches
        
        return jsonify({"message": "Item created successfully", "item_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route('/items/user/<user_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_items_by_user(user_id):
    try:
        # Get user's items with full details
        items = list(db.marketplace_items.find({'user_id': ObjectId(user_id)}))
        
        # Get user details
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Process each item
        for item in items:
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
            # Add user details to each item
            item['user'] = {
                "name": user.get('name', ''),
                "email": user.get('email', '')
            }
        
        # Add cache control headers
        response = jsonify(items)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error fetching user items: {str(e)}")
        return jsonify({'error': str(e)}), 500

@marketplace_bp.route('/items/<item_id>', methods=['GET'])
@limiter.limit("60 per minute")
def get_item(item_id):
    try:
        # Get the item from the database - safely handle ObjectId conversion
        try:
            item = db.marketplace_items.find_one({'_id': ObjectId(item_id)})
        except:
            # Try to find by string ID if ObjectId conversion fails
            item = db.marketplace_items.find_one({'_id': item_id})
            
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        # Convert ObjectId to string
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        
        # Get user details
        user = db.users.find_one({"_id": ObjectId(item['user_id'])})
        if user:
            item['user'] = {
                "name": user.get('name', ''),
                "email": user.get('email', '')
            }
        
        # Add cache control headers
        response = jsonify(item)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route('/items/<item_id>', methods=['PUT'])
@limiter.limit("20 per minute")
@jwt_required()
def update_item(item_id):
    try:
        # Get user's ID from JWT token
        current_user_id = get_jwt_identity()
        
        # Get item data from request
        data = request.form.to_dict() if request.form else request.get_json()
        
        # Get the item from the database - safely handle ObjectId conversion
        try:
            item = db.marketplace_items.find_one({'_id': ObjectId(item_id)})
        except:
            # Try to find by string ID if ObjectId conversion fails
            item = db.marketplace_items.find_one({'_id': item_id})
            
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        # Check if user is hardcoded admin
        is_hardcoded_admin = current_user_id == "admin"
        
        # Helper function to safely handle ObjectId conversion
        def get_user_by_id(user_id):
            try:
                # Try to find user by ObjectId
                return db.users.find_one({'_id': ObjectId(user_id)})
            except:
                # If not a valid ObjectId, try to find by email
                return db.users.find_one({'email': user_id})
        
        # If not hardcoded admin, check database
        if not is_hardcoded_admin:
            current_user = get_user_by_id(current_user_id)
            if not current_user:
                return jsonify({'error': 'User not found'}), 404
            is_admin = current_user.get('role') == 'admin'
        else:
            is_admin = True
            
        # Check if the current user is the owner of the item
        # Handle different formats of user_id (ObjectId, string, email)
        try:
            is_owner = str(item['user_id']) == current_user_id
            if not is_owner:
                # Also check if user_id might be stored as email
                user_by_email = db.users.find_one({'email': current_user_id})
                if user_by_email:
                    is_owner = str(item['user_id']) == str(user_by_email['_id'])
        except:
            is_owner = False
        
        # For admin panel, always allow admins to edit/delete
        # For regular users, only allow if they own the item
        if not is_owner and not is_admin:
            # Log the details for debugging
            current_app.logger.info(f"Auth failed: user_id={current_user_id}, item.user_id={item.get('user_id')}, is_admin={is_admin}")
            return jsonify({'error': 'Unauthorized to update this item'}), 403
        
        # Update item data
        update_data = {
            "title": data.get('title', item['title']),
            "description": data.get('description', item['description']),
            "price": float(data.get('price', item['price'])),
            "category": data.get('category', item['category']),
            "updated_at": datetime.datetime.utcnow()
        }
        
        # Handle multiple images
        if 'images' in request.files:
            images = request.files.getlist('images')
            image_urls = []
            
            # Delete old images if they exist
            if item.get('images'):
                for old_image_url in item['images']:
                    old_image_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', '../uploads'), old_image_url.lstrip('/uploads/'))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
            
            # Create marketplace folder if it doesn't exist
            UPLOAD_FOLDER = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads'))
            MARKETPLACE_FOLDER = os.path.join(UPLOAD_FOLDER, 'marketplace')
            if not os.path.exists(MARKETPLACE_FOLDER):
                os.makedirs(MARKETPLACE_FOLDER)
            
            # Save new images
            for file in images[:3]:  # Limit to 3 images
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    # Create a timestamp-based filename to avoid conflicts
                    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(MARKETPLACE_FOLDER, unique_filename)
                    file.save(file_path)
                    image_urls.append(f"/uploads/marketplace/{unique_filename}")
            
            if image_urls:
                update_data['images'] = image_urls
        
        # Update item in database
        result = db.marketplace_items.update_one(
            {'_id': ObjectId(item_id)},
            {'$set': update_data}
        )
        
        # Get updated item
        updated_item = db.marketplace_items.find_one({'_id': ObjectId(item_id)})
        if updated_item:
            updated_item['_id'] = str(updated_item['_id'])
            updated_item['user_id'] = str(updated_item['user_id'])
        
        # Clear all related caches
        cache.delete('view/api/marketplace/items')
        cache.delete(f'view/api/marketplace/items/{item_id}')
        cache.delete(f'view/api/marketplace/user-items/{str(item["user_id"])}')
        cache.delete(f'view/api/marketplace/items/user/{str(item["user_id"])}')
        cache.delete_many('view/api/marketplace/*')
        cache.delete_many('view/api/admin/*')  # Clear admin related caches
        
        return jsonify(updated_item), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route('/items/<item_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
@jwt_required()
def delete_item(item_id):
    try:
        # Get user's ID from JWT token
        current_user_id = get_jwt_identity()
        
        # Get the item from database
        item = db.marketplace_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        # Check if user is hardcoded admin
        is_hardcoded_admin = current_user_id == "admin"
        
        # Helper function to safely handle ObjectId conversion
        def get_user_by_id(user_id):
            try:
                # Try to find user by ObjectId
                return db.users.find_one({'_id': ObjectId(user_id)})
            except:
                # If not a valid ObjectId, try to find by email
                return db.users.find_one({'email': user_id})
        
        # If not hardcoded admin, check database
        if not is_hardcoded_admin:
            current_user = get_user_by_id(current_user_id)
            if not current_user:
                return jsonify({'error': 'User not found'}), 404
            is_admin = current_user.get('role') == 'admin'
        else:
            is_admin = True
            
        # Check if the current user is the owner of the item
        # Handle different formats of user_id (ObjectId, string, email)
        try:
            is_owner = str(item['user_id']) == current_user_id
            if not is_owner:
                # Also check if user_id might be stored as email
                user_by_email = db.users.find_one({'email': current_user_id})
                if user_by_email:
                    is_owner = str(item['user_id']) == str(user_by_email['_id'])
        except:
            is_owner = False
        
        # Allow deletion if user owns the item or is admin
        if not is_owner and not is_admin:
            return jsonify({'error': 'Unauthorized to delete this item'}), 403
        
        # Store user_id before deleting for cache invalidation
        user_id = str(item['user_id'])
        
        # Delete images
        if 'images' in item:
            for image_url in item['images']:
                try:
                    image_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', '../uploads'), image_url.lstrip('/uploads/'))
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting image {image_url}: {str(e)}")
        
        # Delete item from database
        db.marketplace_items.delete_one({'_id': ObjectId(item_id)})
        
        # Clear all related caches
        cache.delete('view/api/marketplace/items')
        cache.delete(f'view/api/marketplace/items/{item_id}')
        cache.delete(f'view/api/marketplace/user-items/{user_id}')
        cache.delete(f'view/api/marketplace/items/user/{user_id}')
        cache.delete_many('view/api/marketplace/*')
        cache.delete_many('view/api/admin/*')  # Clear admin related caches
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 