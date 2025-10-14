from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, DESCENDING

client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

class Order:
    @staticmethod
    def create_order(data):
        """Create a new order"""
        order = {
            "item_id": ObjectId(data["item_id"]),
            "buyer_id": ObjectId(data["buyer_id"]),
            "seller_id": ObjectId(data["seller_id"]),
            "delivery_info": data["delivery_info"],
            "payment_info": data["payment_info"],
            "status": "confirmed",
            "total_amount": float(data["total_amount"]),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.orders.insert_one(order)
        if result.inserted_id:
            # Mark the item as sold
            db.marketplace_items.update_one(
                {"_id": ObjectId(data["item_id"])},
                {"$set": {"status": "sold", "sold_at": datetime.utcnow()}}
            )
            return str(result.inserted_id)
        return None

    @staticmethod
    def get_user_orders(user_id, as_buyer=True):
        """Get orders for a user (as buyer or seller)"""
        query = {"buyer_id": ObjectId(user_id)} if as_buyer else {"seller_id": ObjectId(user_id)}
        orders = list(db.orders.find(query).sort("created_at", DESCENDING))
        
        # Process orders
        for order in orders:
            order["_id"] = str(order["_id"])
            order["item_id"] = str(order["item_id"])
            order["buyer_id"] = str(order["buyer_id"])
            order["seller_id"] = str(order["seller_id"])
            
            # Get item details
            item = db.marketplace_items.find_one({"_id": ObjectId(order["item_id"])})
            if item:
                order["item"] = {
                    "title": item.get("title"),
                    "price": item.get("price"),
                    "image": item.get("images", [])[0] if item.get("images") else None
                }
                
            # Get buyer/seller details
            user_id = ObjectId(order["seller_id"] if as_buyer else order["buyer_id"])
            user = db.users.find_one({"_id": user_id})
            if user:
                order["other_party"] = {
                    "name": user.get("name"),
                    "email": user.get("email")
                }
                
        return orders
