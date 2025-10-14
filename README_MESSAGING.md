# Real-Time Messaging System Documentation

## Overview

This document provides details on the real-time messaging system implemented for the BRACU Eureka platform. The system enables users to contact post creators in the Marketplace, Ride Share, and Bus Booking sections, with real-time updates and message history.

## Features

- **Real-time messaging** using WebSockets (Flask-SocketIO)
- **Contact verification** - Only non-creators can initiate contact
- **Message storage** - All messages stored in the database
- **Image support** - Users can send both text and images
- **User profile integration** - Conversations accessible from user profiles
- **Post-specific conversations** - Messages linked to specific marketplace items or ride shares

## Technical Implementation

### Backend Components

1. **Flask-SocketIO Integration**
   - WebSocket server for real-time communication
   - Event handlers for message sending/receiving

2. **Message Model**
   - MongoDB schema for storing messages
   - Fields: sender_id, receiver_id, post_id, post_type, content, attachment_url, timestamp

3. **Message Controller**
   - REST API endpoints for message history
   - Conversation management

### Frontend Components

1. **Socket Utility**
   - Connection management
   - Event handling

2. **Message Components**
   - `MessageChat.js` - Chat interface component
   - `ContactButton.js` - Button for initiating contact
   - `MessageActivity.js` - User profile message center

## Usage Flow

1. **Initiating Contact**
   - User views a marketplace item or ride share post
   - If user is not the creator, they see a "Contact" button
   - Clicking the button opens a dialog to send the first message

2. **Messaging**
   - After initial contact, a conversation thread is created
   - Both users can send text messages and images
   - Messages appear in real-time for both parties

3. **Message Activity**
   - Users can view all their conversations in their profile
   - Selecting a conversation opens the full chat history

## API Endpoints

- `GET /api/messages/conversations` - Get all conversations for current user
- `GET /api/messages/conversations/post/:post_type/:post_id` - Get conversations for a specific post
- `GET /api/messages/messages/:other_user_id` - Get messages between current user and another user
- `POST /api/messages/messages/post/:post_type/:post_id/user/:user_id` - Send initial message

## WebSocket Events

- `connect` - Client connects to the server
- `authenticate` - Client authenticates with JWT token
- `join_conversation` - Client joins a conversation room
- `send_message` - Client sends a message
- `new_message` - Server broadcasts a new message
- `message_read` - Server notifies when a message is read

## Installation and Setup

### Backend Dependencies

```
Flask==2.0.1
Flask-JWT-Extended==4.3.1
Flask-SocketIO==5.3.6
Flask-CORS==3.0.10
Flask-Compress==1.10.1
Flask-Caching==1.10.1
Flask-Limiter==1.4
pymongo==4.0.1
python-dotenv==0.19.0
Werkzeug==2.0.1
eventlet==0.33.3
gunicorn==20.1.0
Pillow==8.3.1
python-socketio==5.4.0
```

### Frontend Dependencies

```
react
react-dom
react-router-dom
@mui/material
@mui/icons-material
axios
socket.io-client==4.8.1
react-scripts
```

### System Requirements

1. **MongoDB**: The project requires MongoDB to be installed and running
   ```bash
   # On Ubuntu
   sudo systemctl start mongodb
   
   # On Windows
   # MongoDB should be running as a service or can be started from MongoDB Compass
   ```

2. **Node.js and npm**: Required for the frontend (v14+ recommended)

3. **Python**: Version 3.8+ recommended

4. **Image Processing**: The Pillow library requires some system dependencies that might need to be installed separately depending on the OS

### Running the Messaging System

1. The messaging system is integrated with the main application. Follow the setup instructions in the main README.md file to set up the backend and frontend.

2. The backend server will automatically start the WebSocket server when you run:
   ```bash
   python run.py
   ```
   The server will use the default Flask-SocketIO port (typically 5000) or any available port if 5000 is in use.

3. The frontend is configured to automatically connect to the backend regardless of which port it's running on.

4. To test if the messaging system is working properly:
   - Log in with two different user accounts in separate browser windows/tabs
   - Navigate to a ride share or bus booking post created by one of the users
   - From the other user account, click the "Contact" button to start a conversation
   - Messages should appear in real-time for both users

## Testing

Use the provided test script to verify WebSocket functionality:

```bash
python test_socket.py
```
