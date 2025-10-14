"""
Script to remove the bus_routes collection from the database
"""
from pymongo import MongoClient

# Create a direct connection to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client.bracu_eureka

# Check if the bus_routes collection exists
if 'bus_routes' in db.list_collection_names():
    # Drop the collection
    db.bus_routes.drop()
    print("Successfully removed the bus_routes collection from the database.")
else:
    print("The bus_routes collection does not exist in the database.")

# Update the required_collections list in db.py
import fileinput
import sys

db_py_path = 'app/db.py'
try:
    with fileinput.FileInput(db_py_path, inplace=True) as file:
        for line in file:
            # Remove 'bus_routes' from the required_collections list
            if "'bus_routes'," in line:
                # Skip this line to remove it
                continue
            # Print all other lines unchanged
            print(line, end='')
    print(f"Successfully updated {db_py_path} to remove bus_routes from required collections.")
except Exception as e:
    print(f"Error updating {db_py_path}: {e}")
