# BRACU Eureka - System Documentation

## Table of Contents
1. [System Architecture](#system-architecture)
2. [User Authentication and Authorization](#user-authentication-and-authorization)
   - [User Registration](#user-registration)
   - [User Authentication](#user-authentication)
   - [Admin Approval Process](#admin-approval-process)
3. [Post Management](#post-management)
   - [Marketplace](#marketplace)
   - [Ride Share](#ride-share)
   - [Lost & Found](#lost--found)
4. [Real-time Messaging System](#real-time-messaging-system)
5. [User Profile and Activity](#user-profile-and-activity)
6. [Admin Functions](#admin-functions)
   - [User Verification](#user-verification)
   - [Announcement System](#announcement-system)
7. [Notable Helper Functions](#notable-helper-functions)

## System Architecture

The application follows a client-server architecture with:

- **Frontend**: React-based single-page application
- **Backend**: Flask Python server with Socket.IO for real-time features
- **Database**: MongoDB for data storage

The system uses JWT (JSON Web Tokens) for authentication, WebSockets for real-time messaging, and a RESTful API structure for most operations.

## User Authentication and Authorization

### User Registration

**Implementation Files:**
- **Backend**: `backend/app/models/user.py` - `User.create_user()`
- **Frontend**: `frontend/src/pages/Register.js`

**Process Flow:**
1. User submits registration form with personal details
2. Data is validated on both client and server sides
3. Password is hashed using `werkzeug.security.generate_password_hash`
4. New user is inserted into MongoDB with 'pending' verification status
5. User receives notification that registration is pending admin approval

**Code Highlights:**
```python
# From backend/app/models/user.py
def create_user(self, user_data):
    self._init_collection()
    # Hash password
    hashed_password = generate_password_hash(user_data['password'])
    
    user = {
        'email': user_data['email'],
        'password': hashed_password,
        'name': user_data['name'],
        'student_id': user_data['student_id'],
        'department': user_data['department'],
        'semester': user_data.get('semester', ''),
        'phone': user_data['phone'],
        'id_card_photo': user_data.get('id_card_photo', None),
        'verification_status': 'pending',  # pending, approved, rejected
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    result = self.collection.insert_one(user)
    return str(result.inserted_id)
```

### User Authentication

**Implementation Files:**
- **Backend**: 
  - `backend/app/auth.py` - Contains JWT auth decorators
  - `backend/app/routes/auth_routes.py` - Login endpoint
- **Frontend**:
  - `frontend/src/pages/Login.js`
  - `frontend/src/contexts/AuthContext.js`

**Process Flow:**
1. User submits login credentials
2. Backend verifies credentials with `check_password_hash`
3. If valid, a JWT token is generated with user ID and expiration
4. Token is stored in client localStorage and used for subsequent API calls
5. Protected routes use `login_required` or `admin_required` decorators

**Code Highlights:**
```python
# From backend/app/auth.py
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            current_user = get_db().users.find_one({'_id': data['user_id']})
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
        except:
            return jsonify({'message': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated_function
```

### Admin Approval Process

**Implementation Files:**
- **Backend**: 
  - `backend/app/models/user.py` - `get_pending_users()`, `approve_user()`, `reject_user()`
- **Frontend**:
  - `frontend/src/pages/Admin/VerificationRequests.js`

**Process Flow:**
1. Admin views list of pending verification requests
2. Admin reviews student ID card photos and user details
3. Admin approves or rejects the request
4. User's verification_status is updated in the database
5. On next login, user can access features requiring verification

**Code Highlights:**
```python
# From backend/app/models/user.py
def get_pending_users(self):
    """Get all users with pending verification status"""
    self._init_collection()
    users = list(self.collection.find({'verification_status': 'pending'}))
    for user in users:
        user['_id'] = str(user['_id'])
        # Don't return password hash
        if 'password' in user:
            del user['password']
    return users

def approve_user(self, user_id):
    """Approve a user's verification request"""
    self._init_collection()
    result = self.collection.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'verification_status': 'approved', 'updated_at': datetime.utcnow()}}
    )
    return result.modified_count > 0
```

## Post Management

### Marketplace

**Implementation Files:**
- **Backend**:
  - `backend/app/models/marketplace.py` - CRUD operations for items
  - `backend/app/routes/marketplace_routes.py` - API endpoints
- **Frontend**:
  - `frontend/src/pages/Marketplace.js` - Main Marketplace page
  - `frontend/src/components/CreateItemForm.js` - Item creation form

**Process Flow:**
1. User creates a new marketplace listing via form
2. Images are uploaded to server with unique filenames
3. Item details are stored in MongoDB with creator info
4. All users can view marketplace listings
5. Users can view details, contact seller, or purchase items
6. Item creators can edit or delete their own listings

**User Verification Logic:**
- Frontend uses helper function `isItemCreator(item)` to determine if the current user created an item
- Different buttons shown based on ownership: "You Listed This Item" vs "Buy Now"/"Contact Seller"

### Ride Share

**Implementation Files:**
- **Backend**:
  - `backend/app/models/ride_share.py` - Ride post and booking functionality
  - `backend/app/routes/ride_routes.py` - API endpoints
- **Frontend**:
  - `frontend/src/pages/RideShare.js` - Main page
  - `frontend/src/components/RideShare/CreateRideForm.js` - Ride creation form
  - `frontend/src/components/RideShare/RideFilter.js` - Filtering options

**Process Flow:**
1. User creates a ride share post with route, date, time, and available seats
2. System stores post data with creator information
3. Other users can view, filter, and book rides
4. Booking reduces available seats count
5. Users can cancel bookings with reason
6. Creators can edit/delete posts without active bookings

**Code Highlights:**
```python
# From backend/app/models/ride_share.py
@staticmethod
def create_ride_post(user_id, user_email, user_name, from_location, to_location, 
                     date, time, seats_available, description=None, is_paid=False, 
                     fee_per_seat=0, payment_method=None, contact_number=None):
    """
    Create a new ride share post
    """
    db = get_db()
    ride_post = {
        "creator_id": user_id,
        "creator_email": user_email,
        "creator_name": user_name,
        "from_location": from_location,
        "to_location": to_location,
        "date": date,
        "time": time,
        "seats_available": seats_available,
        "description": description,
        "is_paid": is_paid,
        "fee_per_seat": fee_per_seat if is_paid else 0,
        "payment_method": payment_method if is_paid else None,
        "contact_number": contact_number,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.ride_posts.insert_one(ride_post)
    return str(result.inserted_id)
```

### Lost & Found

**Implementation Files:**
- **Backend**:
  - `backend/app/models/lost_found.py` - Item CRUD operations
  - `backend/app/routes/lost_found_routes.py` - API endpoints
- **Frontend**:
  - `frontend/src/pages/LostAndFound.js` - Main page
  - `frontend/src/components/LostFound/CreateItemForm.js` - Item creation form

**Process Flow:**
1. User submits lost or found item report with details and images
2. System stores information with creator data
3. Other users can view, search, and filter items
4. Item creator gets edit/delete options
5. Other users see contact button to message item reporter

**User Verification Logic:**
- Same pattern as Marketplace, using `isItemCreator(item)` helper function
- Different actions shown based on whether current user created post

## Real-time Messaging System

**Implementation Files:**
- **Backend**:
  - `backend/app/models/message.py` - Message storage and retrieval
  - `backend/app/socket_events.py` - WebSocket event handlers
  - `backend/app/socket_handlers.py` - Socket.IO implementation
- **Frontend**:
  - `frontend/src/components/Messaging/MessageList.js` - Conversation list
  - `frontend/src/components/Messaging/ChatWindow.js` - Active conversation
  - `frontend/src/contexts/SocketContext.js` - WebSocket connection

**Process Flow:**
1. "Contact" buttons on posts initiate conversations
2. Messages are delivered in real-time via WebSockets
3. Messages are stored in MongoDB with sender/receiver info
4. Messages appear in both users' profile pages
5. Images can be attached and shared
6. Read status is tracked and displayed

**Code Highlights:**
```python
# From backend/app/models/message.py
@staticmethod
def create_message(data):
    """Create a new message"""
    message = {
        "sender_id": ObjectId(data["sender_id"]),
        "receiver_id": ObjectId(data["receiver_id"]),
        "content": data["content"],
        "item_id": ObjectId(data["item_id"]) if data.get("item_id") else None,
        "image_url": data.get("image_url"),  # Support for image attachments
        "read": False,
        "created_at": datetime.utcnow()
    }
    
    # Create or get conversation
    conversation = db.conversations.find_one({
        "$or": [
            {
                "participant1_id": ObjectId(data["sender_id"]),
                "participant2_id": ObjectId(data["receiver_id"])
            },
            {
                "participant1_id": ObjectId(data["receiver_id"]),
                "participant2_id": ObjectId(data["sender_id"])
            }
        ]
    })
    
    if not conversation:
        conversation = {
            "participant1_id": ObjectId(data["sender_id"]),
            "participant2_id": ObjectId(data["receiver_id"]),
            "last_message": data["content"],
            "last_message_time": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        db.conversations.insert_one(conversation)
    else:
        db.conversations.update_one(
            {"_id": conversation["_id"]},
            {
                "$set": {
                    "last_message": data["content"],
                    "last_message_time": datetime.utcnow()
                }
            }
        )
    
    result = db.messages.insert_one(message)
    return str(result.inserted_id) if result.inserted_id else None
```

**Socket Events:**
```python
# From backend/app/socket_events.py
@socketio.on('send_message')
def handle_message(data):
    """Handle incoming message event"""
    try:
        # Validate data
        if not all(k in data for k in ['sender_id', 'receiver_id', 'content']):
            emit('error', {'message': 'Invalid message data'}, room=request.sid)
            return
            
        # Create message in database
        message_id = Message.create_message(data)
        
        if not message_id:
            emit('error', {'message': 'Failed to save message'}, room=request.sid)
            return
            
        # Get the complete message object
        message = Message.get_message_by_id(message_id)
        
        if not message:
            emit('error', {'message': 'Failed to retrieve message'}, room=request.sid)
            return
            
        # Broadcast to sender and receiver
        emit('receive_message', message, room=user_rooms.get(data['sender_id'], request.sid))
        
        # Send to receiver if online
        receiver_sid = user_rooms.get(data['receiver_id'])
        if receiver_sid:
            emit('receive_message', message, room=receiver_sid)
            
        # Emit notification for receiver
        if receiver_sid:
            emit('new_message_notification', {
                'message': f"New message from {data.get('sender_name', 'Someone')}",
                'sender_id': data['sender_id']
            }, room=receiver_sid)
            
    except Exception as e:
        print(f"Error in handle_message: {str(e)}")
        emit('error', {'message': 'Server error processing message'}, room=request.sid)
```

## User Profile and Activity

**Implementation Files:**
- **Backend**:
  - `backend/app/routes/user_routes.py` - User profile endpoints
- **Frontend**:
  - `frontend/src/pages/Profile.js` - Profile page
  - `frontend/src/components/Profile/ActivityTab.js` - Activity display

**Process Flow:**
1. User profile tracks all activity across platform
2. Activity tabs show posts, messages, and bookings
3. Messages section shows all conversations
4. Posts section shows created marketplace items, ride shares, and lost/found items
5. Bookings tab shows ride share bookings

## Admin Functions

### User Verification

**Implementation Files:**
- **Backend**:
  - `backend/app/models/user.py` - Admin verification functions
  - `backend/app/routes/admin_routes.py` - Admin endpoints
- **Frontend**:
  - `frontend/src/pages/Admin/VerificationRequests.js`
  - `frontend/src/components/AdminRoute.js` - Protected routes

**Process Flow:**
1. Admin views pending verification requests
2. Each request shows student details and ID card
3. Admin approves or rejects each request
4. System updates user verification status
5. Email notifications sent to users (optional)

### Announcement System

**Implementation Files:**
- **Backend**:
  - `backend/app/models/announcement.py` - Announcement CRUD
  - `backend/app/routes/announcement_routes.py` - API endpoints
- **Frontend**:
  - `frontend/src/pages/Admin/CreateAnnouncement.js`
  - `frontend/src/components/Announcements/AnnouncementList.js`

**Process Flow:**
1. Admin creates announcements with title, content, and type
2. Announcements are stored with creation timestamp
3. Users see announcements on dashboard and relevant sections
4. Announcements can be filtered by type (general, marketplace, rides, lost/found)
5. Admin can edit or delete existing announcements

**Code Example:**
```python
# From backend/app/models/announcement.py
@staticmethod
def create_announcement(title, content, announcement_type, created_by):
    """
    Create a new announcement
    """
    db = get_db()
    announcement = {
        "title": title,
        "content": content,
        "type": announcement_type,  # 'general', 'marketplace', 'ride_share', 'lost_found'
        "created_by": created_by,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.announcements.insert_one(announcement)
    return str(result.inserted_id)
```

## Notable Helper Functions

### User Verification in Frontend

**Implementation Files:**
- `frontend/src/utils/helpers.js` - Contains common helper functions

**Key Functions:**
1. `isItemCreator(item)` - Compares current user ID with item creator ID
2. `getCurrentUser()` - Extracts user info from JWT token
3. `formatDateTime(dateString)` - Standardizes date/time display

**Code Example:**
```javascript
// From frontend/src/utils/helpers.js
export const isItemCreator = (item) => {
  const currentUser = getCurrentUser();
  return currentUser && currentUser.id === item.creator_id;
};

export const getCurrentUser = () => {
  const token = localStorage.getItem('token');
  if (!token) return null;
  
  try {
    // Decode JWT token to extract user information
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Error decoding token:', error);
    return null;
  }
};
```

### Backend Utilities

**Implementation Files:**
- `backend/app/utils/helpers.py` - Server-side utilities

**Key Functions:**
1. `upload_file(file)` - Handles file uploads and storage
2. `generate_unique_filename(filename)` - Creates unique filenames for uploaded images
3. `sanitize_input(text)` - Prevents injection attacks

### API Error Handling

**Implementation Files:**
- `backend/app/routes/*.py` - All route files include standard error handling

**Pattern:**
```python
@bp.route('/endpoint', methods=['POST'])
@login_required
def endpoint():
    try:
        # Process request
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": "Server error"}), 500
```
