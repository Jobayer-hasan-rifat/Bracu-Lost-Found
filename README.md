# BRACU Eureka

A BRAC University Lost & Found platform with additional marketplace, ride sharing, and bus booking services.

## Project Structure

```
bracu-eureka/
├── backend/           # Flask backend
│   ├── app/
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── views/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── requirements.txt
│   └── run.py
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── utils/
│   │   └── App.js
│   ├── package.json
│   └── public/
└── README.md
```

## Prerequisites

- Python 3.8+
- Node.js 14+
- MongoDB
- npm or yarn

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Unix/MacOS:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the backend directory with the following variables:
   ```
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret-key
   MONGO_URI=mongodb://localhost:27017/bracu_eureka
   ```

6. Run the backend server:
   ```bash
   python run.py
   ```
   The backend will start on the default Flask-SocketIO port (typically 5000) or any available port if 5000 is in use.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```
   The frontend will start on port 3000 by default. The application is configured to automatically connect to the backend on any available port.

## Features

- User Authentication
- Marketplace (Buy/Sell/Swap)
- Lost & Found
- Ride Share & Bus Booking System
  - Post rides for sharing with other students
  - Book bus tickets for routes around BRAC University
  - Real-time messaging with ride/bus post creators
  - Manage bookings through user dashboard

## API Endpoints

### Authentication
- POST /api/auth/register - Register a new user
- POST /api/auth/login - Login user

### Marketplace
- GET /api/marketplace/items - Get all items
- POST /api/marketplace/items - Create new item
- GET /api/marketplace/items/:id - Get item details
- PUT /api/marketplace/items/:id - Update item
- DELETE /api/marketplace/items/:id - Delete item

### Lost & Found
- GET /api/lost-found/items - Get all lost/found items
- POST /api/lost-found/items - Report lost/found item
- GET /api/lost-found/items/:id - Get item details
- PUT /api/lost-found/items/:id - Update item status

### Ride Booking
- GET /api/ride/routes - Get available routes
- POST /api/ride/bookings - Create new booking
- GET /api/ride/bookings - Get user bookings
- PUT /api/ride/bookings/:id - Update booking
- DELETE /api/ride/bookings/:id - Cancel booking 