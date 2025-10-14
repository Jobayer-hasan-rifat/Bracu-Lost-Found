from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient
from ..models.user import User
import os
import jwt
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from bson import ObjectId
from .. import cache
from datetime import datetime

# Secret key for JWT - should match the one in app/__init__.py
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')

admin_bp = Blueprint('admin_bp', __name__)
client = MongoClient(os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.bracu_eureka
user_model = User(db)

# Admin authentication middleware
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # Get the JWT data
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    'message': 'Missing or invalid token',
                    'authenticated': False,
                    'authorized': False
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Try the new flask_jwt_extended format first
            try:
                decoded = decode_token(token)
                # Check if token has admin role claim
                if decoded.get('role') == 'admin':
                    # Admin token verified
                    return fn(*args, **kwargs)
                
                # Get the identity and check if user is admin in database
                user_id = decoded.get('sub')
                if user_id:
                    user = db.users.find_one({'_id': ObjectId(user_id)})
                    if user and user.get('role') == 'admin':
                        return fn(*args, **kwargs)
                
                return jsonify({
                    'message': 'Admin privileges required',
                    'authenticated': True,
                    'authorized': False
                }), 403
                
            except Exception:
                # Try legacy format
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
                if payload.get('role') == 'admin' and payload.get('admin_id'):
                    # Legacy admin token
                    return fn(*args, **kwargs)
                elif 'user_id' in payload:
                    # Legacy user token - check if admin
                    user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
                    if user and user.get('role') == 'admin':
                        return fn(*args, **kwargs)
                
                return jsonify({
                    'message': 'Admin privileges required',
                    'authenticated': True,
                    'authorized': False
                }), 403
                
        except Exception as e:
            return jsonify({
                'message': f'Error: {str(e)}',
                'authenticated': False,
                'authorized': False
            }), 401
            
    return wrapper

@admin_bp.route('/pending-users', methods=['GET'])
@jwt_required()
@admin_required
def get_pending_users():
    """Get all users who are pending verification"""
    try:
        # Add debug logging
        current_app.logger.debug("Fetching pending users")
        pending_users = list(db.users.find({'verification_status': 'pending'}, {'password': 0}))
        
        # Convert ObjectId to string
        for user in pending_users:
            user['_id'] = str(user['_id'])
        
            # Make sure the ID card photo URL is properly formatted
            if 'id_card_photo' in user and user['id_card_photo']:
                # Ensure the URL starts with / if it's a relative path
                if not user['id_card_photo'].startswith('/') and not user['id_card_photo'].startswith('http'):
                    user['id_card_photo'] = '/' + user['id_card_photo']
        
        current_app.logger.debug(f"Found {len(pending_users)} pending users")
        return jsonify(pending_users), 200
    except Exception as e:
        current_app.logger.error(f"Error getting pending users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/verified-users', methods=['GET'])
@jwt_required()
@admin_required
@cache.cached(timeout=60)  # Cache for 60 seconds to reduce rate limit issues
def get_verified_users():
    """Get all verified users"""
    try:
        # Add debug logging
        current_app.logger.debug("Fetching verified users")
        verified_users = list(db.users.find({'verification_status': 'approved'}, {'password': 0}))
        
        # Convert ObjectId to string
        for user in verified_users:
            user['_id'] = str(user['_id'])
        
            # Make sure the ID card photo URL is properly formatted
            if 'id_card_photo' in user and user['id_card_photo']:
                # Ensure the URL starts with / if it's a relative path
                if not user['id_card_photo'].startswith('/') and not user['id_card_photo'].startswith('http'):
                    user['id_card_photo'] = '/' + user['id_card_photo']
        
        # Add cache control headers
        response = jsonify(verified_users)
        response.headers['Cache-Control'] = 'max-age=60'
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error fetching verified users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/approve-user/<user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def approve_user(user_id):
    """Approve a user's verification request"""
    try:
        # Add debug logging
        current_app.logger.debug(f"Approving user with ID: {user_id}")
        
        # Check if user exists
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            current_app.logger.warning(f"User not found with ID: {user_id}")
            return jsonify({'error': 'User not found'}), 404
         
        # Update user verification status
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'verification_status': 'approved',
                'updated_at': datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            current_app.logger.warning(f"No changes made when approving user: {user_id}")
            return jsonify({'error': 'User already approved or not found'}), 400
        
        current_app.logger.info(f"User {user_id} approved successfully")
        return jsonify({'message': 'User approved successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error approving user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reject-user/<user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def reject_user(user_id):
    """Reject a user's verification request"""
    try:
        # Add debug logging
        current_app.logger.debug(f"Rejecting user with ID: {user_id}")
        
        # Check if user exists
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            current_app.logger.warning(f"User not found with ID: {user_id}")
            return jsonify({'error': 'User not found'}), 404
             
        # Update user verification status
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'verification_status': 'rejected',
                'updated_at': datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            current_app.logger.warning(f"No changes made when rejecting user: {user_id}")
            return jsonify({'error': 'User already rejected or not found'}), 400
        
        current_app.logger.info(f"User {user_id} rejected successfully")
        return jsonify({'message': 'User rejected successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error rejecting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user/<user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user_details(user_id):
    """Get detailed information about a user"""
    try:
        # Find user by ID
        user = db.users.find_one({'_id': ObjectId(user_id)}, {'password': 0})
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Convert ObjectId to string for JSON serialization
        user['_id'] = str(user['_id'])
        
        # Make sure the ID card photo URL is properly formatted
        if 'id_card_photo' in user and user['id_card_photo']:
            # Ensure the URL starts with / if it's a relative path
            if not user['id_card_photo'].startswith('/') and not user['id_card_photo'].startswith('http'):
                user['id_card_photo'] = '/' + user['id_card_photo']
                
        return jsonify(user), 200
    except Exception as e:
        current_app.logger.error(f"Error getting user details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/delete-user/<user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    """Admin deletes a user account by ID"""
    try:
        result = db.users.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Admin error deleting user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/edit-user/<user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def edit_user(user_id):
    """Edit user information"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check if user exists
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Fields that admin is allowed to edit
        allowed_fields = ['name', 'email', 'username', 'department', 'semester', 'verification_status']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
            
        # Add updated_at timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update user
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        if result.modified_count == 0:
            return jsonify({'error': 'No changes made or user not found'}), 400
            
        # Clear cache
        cache.delete('admin_pending_users')
        cache.delete('admin_verified_users')
        
        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error editing user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/statistics', methods=['GET', 'POST', 'OPTIONS'])
@jwt_required()
@admin_required
@cache.cached(timeout=30)  # Cache statistics for 30 seconds to ensure real-time synchronization
def get_statistics():
    """Get platform statistics for admin dashboard"""
    try:
        # Count users
        total_users = db.users.count_documents({})
        verified_users = db.users.count_documents({'verification_status': 'approved'})
        pending_users = db.users.count_documents({'verification_status': 'pending'})
        
        # Count rooms and bookings
        total_rooms = db.rooms.count_documents({'active': True})
        total_bookings = db.bookings.count_documents({})
        
        # Count marketplace items - use marketplace_items collection instead of items
        total_items = db.marketplace_items.count_documents({})

        # Lost & Found statistics
        total_lost_found = db.lost_found_items.count_documents({})
        lost_items = db.lost_found_items.count_documents({'item_type': 'lost'})
        found_items = db.lost_found_items.count_documents({'item_type': 'found'})

        # Share ride statistics
        total_share_rides = db.share_rides.count_documents({})
        active_share_rides = db.share_rides.count_documents({'status': 'active'})
        inactive_share_rides = db.share_rides.count_documents({'status': {'$ne': 'active'}})

        # Get recent activities
        recent_bookings = list(db.bookings.find().sort('created_at', -1).limit(5))
        # Use marketplace_items collection instead of items
        recent_items = list(db.marketplace_items.find().sort('created_at', -1).limit(5))
        # Get recent lost & found items
        recent_lost_found = list(db.lost_found_items.find().sort('created_at', -1).limit(5))
        
        # Convert ObjectId to string
        for booking in recent_bookings:
            try:
                booking['_id'] = str(booking.get('_id', ''))
                booking['user_id'] = str(booking.get('user_id', ''))
                booking['room_id'] = str(booking.get('room_id', ''))
            except Exception as e:
                current_app.logger.error(f"Error processing booking: {str(e)}")
                # Continue with next booking if there's an error
                continue
            
        for item in recent_items:
            try:
                item['_id'] = str(item.get('_id', ''))
                
                # Safely handle user_id which might be missing or invalid
                user_id = item.get('user_id', '')
                if not user_id:
                    # Try alternative fields that might contain user ID
                    user_id = item.get('seller_id', '') or item.get('created_by', '')
                
                # Convert user_id to string if it exists
                if user_id:
                    item['user_id'] = str(user_id)
                    
                    # Add user details to items - with proper error handling
                    try:
                        user = db.users.find_one({'_id': ObjectId(user_id)})
                        if user:
                            item['seller'] = {
                                'id': str(user['_id']),
                                'name': user.get('name', 'Unknown'),
                                'email': user.get('email', '')
                            }
                        else:
                            # Fallback if user not found
                            item['seller'] = {
                                'id': str(user_id),
                                'name': 'Unknown User',
                                'email': ''
                            }
                    except Exception as e:
                        current_app.logger.error(f"Error finding user for item: {str(e)}")
                        # Fallback if ObjectId conversion fails
                        item['seller'] = {
                            'id': str(user_id) if user_id else '',
                            'name': 'Unknown User',
                            'email': ''
                        }
            except Exception as e:
                current_app.logger.error(f"Error processing marketplace item: {str(e)}")
                # Continue with next item if there's an error
                continue
        
        # Process recent lost & found items
        for item in recent_lost_found:
            try:
                item['_id'] = str(item.get('_id', ''))
                
                # Safely handle user_id which might be missing or invalid
                user_id = item.get('user_id', '')
                if user_id:
                    item['user_id'] = str(user_id)
                    
                    # Add user details to items - with proper error handling
                    try:
                        user = db.users.find_one({'_id': ObjectId(user_id)})
                        if user:
                            item['user'] = {
                                'id': str(user['_id']),
                                'name': user.get('name', 'Unknown'),
                                'email': user.get('email', '')
                            }
                    except Exception as e:
                        current_app.logger.error(f"Error finding user for lost & found item: {str(e)}")
            except Exception as e:
                current_app.logger.error(f"Error processing lost & found item: {str(e)}")
                continue

        # Add cache control headers
        response = jsonify({
            'users': {
                'total': total_users,
                'verified': verified_users,
                'pending': pending_users
            },
            'rooms': {
                'total': total_rooms
            },
            'bookings': {
                'total': total_bookings
            },
            'marketplace': {
                'total_items': total_items
            },
            'lost_found': {
                'total': total_lost_found,
                'lost': lost_items,
                'found': found_items
            },
            'rideshare': {
                'total': total_share_rides,
                'active': active_share_rides,
                'inactive': inactive_share_rides
            },
            'recent_activities': {
                'bookings': recent_bookings,
                'items': recent_items,
                'lost_found': recent_lost_found
            }
        })
        response.headers['Cache-Control'] = 'max-age=60'
        return response, 200
    except Exception as e:
        # Log the detailed error for debugging
        current_app.logger.error(f"Error in get_statistics: {str(e)}")
        
        # Return a more graceful error response with fallback data
        try:
            # Try to return at least some basic statistics
            basic_stats = {
                'users': {
                    'total': db.users.count_documents({}) if 'users' in db.list_collection_names() else 0,
                    'verified': 0,
                    'pending': 0
                },
                'marketplace': {
                    'total_items': db.marketplace_items.count_documents({}) if 'marketplace_items' in db.list_collection_names() else 0
                },
                'lost_found': {
                    'total': db.lost_found_items.count_documents({}) if 'lost_found_items' in db.list_collection_names() else 0,
                    'lost': 0,
                    'found': 0
                },
                'error_details': f"Some statistics could not be loaded: {str(e)}"
            }
            return jsonify(basic_stats), 200
        except Exception as fallback_error:
            # If even the fallback fails, return a simple error message
            current_app.logger.error(f"Fallback error in get_statistics: {str(fallback_error)}")
            return jsonify({
                'error': 'Statistics temporarily unavailable',
                'message': 'The system is experiencing technical difficulties. Please try again later.'
            }), 500 


@admin_bp.route('/lost-found/items', methods=['GET'])
@jwt_required()
@admin_required
def get_lost_found_items():
    """Get all lost & found items for admin management"""
    try:
        items = list(db.lost_found_items.find().sort('created_at', -1))
        
        # Convert ObjectId to string
        for item in items:
            item['_id'] = str(item['_id'])
            if 'user_id' in item:
                user_id = item['user_id']
                item['user_id'] = str(user_id)
                
                # Add user details
                try:
                    user = db.users.find_one({'_id': ObjectId(user_id)})
                    if user:
                        item['user'] = {
                            'id': str(user['_id']),
                            'name': user.get('name', 'Unknown'),
                            'email': user.get('email', '')
                        }
                except Exception as e:
                    current_app.logger.error(f"Error finding user for lost & found item: {str(e)}")
        
        return jsonify(items), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_lost_found_items: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/lost-found/items/<item_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_lost_found_item(item_id):
    """Update a lost & found item"""
    try:
        data = request.get_json()
        
        # Validate item exists
        item = db.lost_found_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        # Update fields
        update_data = {'updated_at': datetime.utcnow()}
        allowed_fields = ['title', 'description', 'location', 'date', 'status', 'images', 'category', 'item_type']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        db.lost_found_items.update_one(
            {'_id': ObjectId(item_id)},
            {'$set': update_data}
        )
        
        # Clear all related caches
        cache.delete('view/api/lost-found/items')
        cache.delete(f'view/api/lost-found/items/{item_id}')
        cache.delete_many('view/api/lost-found/*')
        cache.delete_many('view/api/admin/*')
        
        return jsonify({'message': 'Item updated successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in update_lost_found_item: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/lost-found/items/<item_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_lost_found_item(item_id):
    """Delete a lost & found item"""
    try:
        # Check if item exists
        item = db.lost_found_items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        # Delete item
        db.lost_found_items.delete_one({'_id': ObjectId(item_id)})
        
        # Clear all related caches
        cache.delete('view/api/lost-found/items')
        cache.delete(f'view/api/lost-found/items/{item_id}')
        cache.delete_many('view/api/lost-found/*')
        cache.delete_many('view/api/admin/*')
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in delete_lost_found_item: {str(e)}")
        return jsonify({'error': str(e)}), 500