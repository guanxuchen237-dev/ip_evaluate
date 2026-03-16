import pymongo

# Config
MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "novel_analysis"

def check_db():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Check Qidian
    q_col = db['qidian_novels']
    q_count = q_col.count_documents({})
    print(f"Qidian Novels Count: {q_count}")
    if q_count > 0:
        print("Sample Qidian Data:")
        print(q_col.find_one({}, {'_id':0, 'title':1, 'monthly_ticket_count':1, 'word_count':1}))
        
    print("-" * 30)

    # Check Zongheng
    z_col = db['zongheng_novels'] # Assuming this name, will verify
    z_count = z_col.count_documents({})
    print(f"Zongheng Novels Count: {z_count}")
    
    # Try alternate name if 0
    if z_count == 0:
        print("Checking for other collections...")
        print(db.list_collection_names())

    if z_count > 0:
        print("Sample Zongheng Data:")
        item = z_col.find_one()
        # Print relevant fields to check mapping
        print(item)

if __name__ == "__main__":
    check_db()
