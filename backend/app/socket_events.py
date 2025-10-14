from flask import request, current_app
from flask_socketio import emit, join_room, leave_room
from app.models.message import Message
from app.models.user import User
from pymongo import MongoClient
from bson import ObjectId
import json
import base64
import os
import uuid
from datetime import datetime

# Initialize MongoDB client
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

# Dictionary to store active users and their socket IDs
active_users = {}

def init_socket_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print('Client connected:', request.sid)
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print('Client disconnected:', request.sid)
        
        # Remove user from active users
        for user_id, sid in list(active_users.items()):
            if sid == request.sid:
                del active_users[user_id]
                emit('user_status', {'user_id': user_id, 'status': 'offline'}, broadcast=True)
                break
    
    @socketio.on('register_user')
    def handle_register_user(data):
        """Register user with their socket ID"""
        user_id = data.get('user_id')
        if user_id:
            active_users[user_id] = request.sid
            print(f'User {user_id} registered with socket ID: {request.sid}')
            
            # Join a personal room for private messages
            join_room(user_id)
            
            # Broadcast user's online status
            emit('user_status', {'user_id': user_id, 'status': 'online'}, broadcast=True)
    
    @socketio.on('join_conversation')
    def handle_join_conversation(data):
        """Join a conversation room"""
        conversation_id = data.get('conversation_id')
        if conversation_id:
            join_room(conversation_id)
            print(f'User joined conversation: {conversation_id}')
    
    @socketio.on('leave_conversation')
    def handle_leave_conversation(data):
        """Leave a conversation room"""
        conversation_id = data.get('conversation_id')
        if conversation_id:
            leave_room(conversation_id)
            print(f'User left conversation: {conversation_id}')
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """Handle sending a message"""
        try:
            # Extract message data
            sender_id = data.get('sender_id')
            receiver_id = data.get('receiver_id')
            content = data.get('content')
            item_id = data.get('item_id')
            image_data = data.get('image')
            
            # Process image if provided
            image_url = None
            if image_data:
                # Extract base64 data
                image_format, image_base64 = image_data.split(',', 1)
                image_bytes = base64.b64decode(image_base64)
                
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(os.getcwd(), 'uploads', 'messages')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"{uuid.uuid4()}.png"
                filepath = os.path.join(upload_dir, filename)
                
                # Save the image
                with open(filepath, 'wb') as f:
                    f.write(image_bytes)
                
                # Set the image URL for the message
                image_url = f"/uploads/messages/{filename}"
            
            # Create message data
            message_data = {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "content": content,
                "item_id": item_id,
                "image_url": image_url
            }
            
            # Save message to database
            message_id = Message.create_message(message_data)
            
            if message_id:
                # Get sender info from the database directly
                try:
                    sender = db.users.find_one({'_id': ObjectId(sender_id)})
                    sender_name = sender.get('name', 'Unknown') if sender else "Unknown"
                except Exception as e:
                    print(f"Error getting sender info: {str(e)}")
                    sender_name = "Unknown"
                
                # Prepare message for frontend
                message = {
                    "_id": message_id,
                    "sender_id": sender_id,
                    "receiver_id": receiver_id,
                    "sender_name": sender_name,
                    "content": content,
                    "image_url": image_url,
                    "item_id": item_id,
                    "item_type": data.get('item_type'),
                    "item_title": data.get('item_title'),
                    "created_at": datetime.utcnow().isoformat(),
                    "read": False
                }
                
                # Emit to both sender and receiver
                emit('new_message', message, room=sender_id)
                emit('new_message', message, room=receiver_id)
                
                # Also emit to conversation room if applicable
                conversation_id = data.get('conversation_id')
                if conversation_id:
                    emit('new_message', message, room=conversation_id)
                
                return {'status': 'success', 'message': 'Message sent successfully', 'data': message}
            else:
                emit('error', {'message': 'Failed to save message'}, room=request.sid)
                return {'status': 'error', 'message': 'Failed to save message'}
                
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            emit('error', {'message': f'Error: {str(e)}'}, room=request.sid)
            return {'status': 'error', 'message': str(e)}
    
    @socketio.on('mark_as_read')
    def handle_mark_as_read(data):
        """Mark messages as read"""
        message_id = data.get('message_id')
        user_id = data.get('user_id')
        
        if not message_id or not user_id:
            emit('error', {'message': 'Message ID and user ID are required'}, room=request.sid)
            return
        
        try:
            # Update message in database
            result = Message.mark_message_read(message_id, user_id)
            
            if result:
                # Get the message to notify the sender
                message = Message.get_message_by_id(message_id)
                
                if message:
                    # Notify sender that message was read
                    sender_id = message['sender_id']
                    if sender_id in active_users:
                        emit('message_read', {'message_id': message_id}, room=active_users[sender_id])
                    
                    # Send confirmation to the reader
                    emit('mark_read_success', {'message_id': message_id}, room=request.sid)
            else:
                emit('error', {'message': 'Failed to mark message as read'}, room=request.sid)
        except Exception as e:
            print(f"Error marking message as read: {str(e)}")
            emit('error', {'message': f'Error: {str(e)}'}, room=request.sid)
