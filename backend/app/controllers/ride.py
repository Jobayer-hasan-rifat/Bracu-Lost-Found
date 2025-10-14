from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
import datetime

ride_bp = Blueprint('ride', __name__)
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

# Share ride endpoints
@ride_bp.route('/share', methods=['GET'])
def get_share_rides():
    """Get all active share rides"""
    try:
        rides = list(db.share_rides.find({'status': 'active'}))
        
        # Process ride data
        for ride in rides:
            ride['_id'] = str(ride['_id'])
            ride['user_id'] = str(ride['user_id'])
        
        return jsonify(rides), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@ride_bp.route('/share/user', methods=['GET'])
@jwt_required()
def get_user_share_rides():
    """Get share rides posted by the currently logged-in user"""
    try:
        user_id = get_jwt_identity()
        rides = list(db.share_rides.find({'user_id': user_id}))
        
        # Process ride data
        for ride in rides:
            ride['_id'] = str(ride['_id'])
            ride['user_id'] = str(ride['user_id'])
        
        return jsonify(rides), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@ride_bp.route('/share', methods=['POST'])
@jwt_required()
def create_share_ride():
    """Create a new share ride"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Check if this is an update (ride_id is present) or a new ride
        ride_id = data.get('_id')
        
        # Validate request data
        required_fields = ['from_location', 'to_location', 'date', 'time', 'vehicle_type', 'phone_number', 'seats_available']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing {field}'}), 400
        
        # Additional validation for paid rides
        if data.get('is_paid', False):
            if 'fee_per_seat' not in data or 'payment_method' not in data:
                return jsonify({'error': 'Fee per seat and payment method are required for paid rides'}), 400
        
        # Get user info for the ride
        user = db.users.find_one({'_id': ObjectId(user_id)})
        user_name = user.get('name', 'Unknown User') if user else 'Unknown User'
        user_email = user.get('email', 'No email') if user else 'No email'
        
        # Prepare ride data
        ride_data = {
            'user_id': user_id,
            'user_name': user_name,
            'user_email': user_email,
            'from_location': data['from_location'],
            'to_location': data['to_location'],
            'date': data['date'],
            'time': data['time'],
            'vehicle_type': data['vehicle_type'],
            'phone_number': data['phone_number'],
            'seats_available': int(data['seats_available']),
            'is_paid': data.get('is_paid', False),
            'fee_per_seat': int(data.get('fee_per_seat', 0)),
            'payment_method': data.get('payment_method', 'in_person'),
            'description': data.get('description', ''),
            'status': 'active',
            'updated_at': datetime.datetime.utcnow()
        }
        
        # If it's an update, update the existing ride
        if ride_id:
            try:
                # Verify the ride belongs to the current user
                existing_ride = db.share_rides.find_one({'_id': ObjectId(ride_id)})
                if not existing_ride:
                    return jsonify({'error': 'Ride not found'}), 404
                    
                if existing_ride['user_id'] != user_id:
                    return jsonify({'error': 'You can only edit your own rides'}), 403
                
                # Update the ride
                db.share_rides.update_one(
                    {'_id': ObjectId(ride_id)},
                    {'$set': ride_data}
                )
                
                return jsonify({
                    'message': 'Share ride updated successfully',
                    'ride_id': ride_id
                }), 200
                
            except Exception as e:
                return jsonify({'error': f'Error updating ride: {str(e)}'}), 400
        
        # If it's a new ride, add created_at timestamp
        ride_data['created_at'] = datetime.datetime.utcnow()
        
        # Insert the new ride
        result = db.share_rides.insert_one(ride_data)
        
        return jsonify({
            'message': 'Share ride created successfully',
            'ride_id': str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@ride_bp.route('/share/<ride_id>', methods=['DELETE'])
@jwt_required()
def delete_share_ride(ride_id):
    """Delete a share ride (only by the owner or admin)"""
    try:
        user_id = get_jwt_identity()
        ride = db.share_rides.find_one({'_id': ObjectId(ride_id)})
        if not ride:
            return jsonify({'error': 'Ride not found'}), 404
        is_owner = str(ride['user_id']) == user_id
        user = db.users.find_one({'_id': ObjectId(user_id)})
        is_admin = user and user.get('role') == 'admin'
        if not (is_owner or is_admin):
            return jsonify({'error': 'Unauthorized'}), 403
        db.share_rides.delete_one({'_id': ObjectId(ride_id)})
        return jsonify({'message': 'Share ride deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Booking endpoints
@ride_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_user_bookings():
    """Get all bookings for the current user"""
    try:
        user_id = get_jwt_identity()
        bookings = list(db.bookings.find({'user_id': user_id, 'status': 'active'}))
        
        # Process booking data
        for booking in bookings:
            booking['_id'] = str(booking['_id'])
            if 'ride_id' in booking:
                booking['ride_id'] = str(booking['ride_id'])
            if 'user_id' in booking:
                booking['user_id'] = str(booking['user_id'])
            if 'ride' in booking and booking['ride']:
                if '_id' in booking['ride']:
                    booking['ride']['_id'] = str(booking['ride']['_id'])
                if 'user_id' in booking['ride']:
                    booking['ride']['user_id'] = str(booking['ride']['user_id'])
        
        return jsonify(bookings), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@ride_bp.route('/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    """Create a new booking for a ride share"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Validate request data
        required_fields = ['ride_id', 'seats']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing {field}'}), 400
        
        # Get the ride
        ride = db.share_rides.find_one({'_id': ObjectId(data['ride_id'])})
        if not ride:
            return jsonify({'error': 'Ride not found'}), 404
        
        # Check if user is trying to book their own ride
        if str(ride['user_id']) == user_id:
            return jsonify({'error': 'You cannot book your own ride'}), 400
        
        # Check if there are enough seats available
        seats_requested = int(data['seats'])
        if seats_requested > ride['seats_available']:
            return jsonify({'error': f'Not enough seats available. Only {ride["seats_available"]} left'}), 400
        
        # Get user info
        user = db.users.find_one({'_id': ObjectId(user_id)})
        user_name = user.get('name', 'Unknown User') if user else 'Unknown User'
        user_email = user.get('email', 'No email') if user else 'No email'
        
        # Create booking
        booking = {
            'user_id': user_id,
            'user_name': user_name,
            'user_email': user_email,
            'ride_id': data['ride_id'],
            'ride': ride,  # Store a copy of the ride at booking time
            'seats': seats_requested,
            'pickup_location': data.get('pickup_location', ride['from_location']),
            'dropoff_location': data.get('dropoff_location', ride['to_location']),
            'status': 'active',
            'created_at': datetime.datetime.utcnow(),
            'updated_at': datetime.datetime.utcnow()
        }
        
        # Insert booking
        result = db.bookings.insert_one(booking)
        
        # Update available seats in the ride
        new_seats_available = ride['seats_available'] - seats_requested
        db.share_rides.update_one(
            {'_id': ObjectId(data['ride_id'])},
            {'$set': {
                'seats_available': new_seats_available,
                # If no seats left, mark as booked
                'status': 'booked' if new_seats_available == 0 else 'active'
            }}
        )
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking_id': str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@ride_bp.route('/bookings/<booking_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    """Cancel a booking with time restriction (30 minutes before ride)"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Validate request data
        if 'reason' not in data:
            return jsonify({'error': 'Missing cancellation reason'}), 400
        
        # Get the booking
        booking = db.bookings.find_one({'_id': ObjectId(booking_id)})
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Check if user owns the booking
        if str(booking['user_id']) != user_id:
            return jsonify({'error': 'You can only cancel your own bookings'}), 403
        
        # Check if booking is already cancelled
        if booking['status'] != 'active':
            return jsonify({'error': 'Booking is already cancelled or completed'}), 400
        
        # Check time restriction - 30 minutes before ride
        ride_datetime_str = f"{booking['ride']['date']} {booking['ride']['time']}"
        try:
            # Parse the ride datetime
            ride_datetime = datetime.datetime.strptime(ride_datetime_str, '%Y-%m-%d %H:%M')
            
            # Get current time
            current_time = datetime.datetime.utcnow()
            
            # Calculate time difference in minutes
            time_diff = (ride_datetime - current_time).total_seconds() / 60
            
            # Check if less than 30 minutes before ride
            if time_diff < 30:
                return jsonify({'error': 'Cannot cancel booking less than 30 minutes before ride'}), 400
        except Exception as e:
            # If there's an error parsing the datetime, log it but continue with cancellation
            print(f"Error checking time restriction: {str(e)}")
        
        # Update booking status
        db.bookings.update_one(
            {'_id': ObjectId(booking_id)},
            {'$set': {
                'status': 'cancelled',
                'cancellation_reason': data['reason'],
                'cancelled_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow()
            }}
        )
        
        # Update ride seats
        db.share_rides.update_one(
            {'_id': ObjectId(booking['ride_id'])},
            {'$inc': {'seats_available': booking['seats']},
             '$set': {'status': 'active'}}  # Set back to active since seats are available again
        )
        
        return jsonify({'message': 'Booking cancelled successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ADMIN: get all share rides (including inactive/removed)
@ride_bp.route('/share/admin/all', methods=['GET'])
@jwt_required()
def admin_get_all_share_rides():
    try:
        # Get admin info from token
        from flask_jwt_extended import decode_token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
            
        token = auth_header.split(' ')[1]
        decoded = decode_token(token)
        
        # Check if it's an admin token
        if decoded.get('role') != 'admin' or decoded.get('sub') != '470@gmail.com':
            return jsonify({'error': 'Admin privileges required'}), 403
            
        # Fetch all ride shares
        rides = list(db.share_rides.find())
        
        # Process ride data
        for ride in rides:
            ride['_id'] = str(ride['_id'])
            ride['user_id'] = str(ride['user_id'])
            
            # Add user information
            try:
                ride_user = db.users.find_one({'_id': ObjectId(ride['user_id'])})
                if ride_user:
                    ride['user'] = {
                        'name': ride_user.get('name', 'Unknown'),
                        'email': ride_user.get('email', 'No email'),
                        '_id': str(ride_user['_id'])
                    }
            except Exception:
                # If user info can't be fetched, add placeholder
                ride['user'] = {
                    'name': 'Unknown User',
                    'email': 'No email available'
                }
        
        return jsonify(rides), 200
            
    except Exception as e:
        return jsonify({'error': f'Error accessing ride share data: {str(e)}'}), 500
