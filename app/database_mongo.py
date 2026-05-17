import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import json

class MongoDB:
    def __init__(self):
        # ใช้ Environment Variable หรือกำหนดตรงๆ
        self.connection_string = os.getenv('MONGODB_URL', '')
        self.client = None
        self.db = None
        self.brands_collection = None
        self.products_collection = None
        self.history_collection = None
        
    async def connect(self):
        """เชื่อมต่อ MongoDB"""
        if not self.connection_string:
            print("⚠️ No MONGODB_URL found, using SimpleDB mode")
            return False
            
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client['valuai_db']
            self.brands_collection = self.db['brands']
            self.products_collection = self.db['products']
            self.history_collection = self.db['history']
            
            # สร้าง indexes
            await self.brands_collection.create_index("brand_id", unique=True)
            await self.products_collection.create_index("product_key", unique=True)
            
            # เพิ่มข้อมูลเริ่มต้นถ้ายังไม่มี
            await self.init_default_data()
            
            print("✅ MongoDB connected successfully")
            return True
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False
    
    async def init_default_data(self):
        """เพิ่มข้อมูลเริ่มต้น"""
        # ตรวจสอบว่ามีข้อมูลหรือยัง
        if await self.brands_collection.count_documents({}) == 0:
            default_brands = [
                {"brand_id": "apple", "name": "Apple iPhone", "icon": "🍎", "models": ["14", "13", "12", "11", "SE"]},
                {"brand_id": "samsung", "name": "Samsung", "icon": "📱", "models": ["S24", "S23", "S22", "A54"]},
                {"brand_id": "xiaomi", "name": "Xiaomi", "icon": "📱", "models": ["13", "12", "11"]},
                {"brand_id": "canon", "name": "Canon", "icon": "📷", "models": ["R50", "R10", "R8"]}
            ]
            await self.brands_collection.insert_many(default_brands)
            print("✅ Default brands added")
        
        if await self.products_collection.count_documents({}) == 0:
            default_products = [
                {"product_key": "apple_14", "brand": "apple", "model": "14", "new_price": 32900, "secondhand_avg": 25000, "buy_price": 22000},
                {"product_key": "apple_13", "brand": "apple", "model": "13", "new_price": 29900, "secondhand_avg": 18000, "buy_price": 15000},
                {"product_key": "apple_12", "brand": "apple", "model": "12", "new_price": 25900, "secondhand_avg": 13000, "buy_price": 10000},
                {"product_key": "canon_r50", "brand": "canon", "model": "R50", "new_price": 25900, "secondhand_avg": 18000, "buy_price": 13000}
            ]
            await self.products_collection.insert_many(default_products)
            print("✅ Default products added")
    
    # Brand operations
    async def get_brands(self):
        brands = await self.brands_collection.find({}).to_list(100)
        return {b['brand_id']: {"name": b['name'], "icon": b['icon'], "models": b['models']} for b in brands}
    
    async def add_brand(self, brand_id, name, icon, models):
        await self.brands_collection.update_one(
            {"brand_id": brand_id},
            {"$set": {"name": name, "icon": icon, "models": models}},
            upsert=True
        )
        return True
    
    async def delete_brand(self, brand_id):
        result = await self.brands_collection.delete_one({"brand_id": brand_id})
        return result.deleted_count > 0
    
    # Product operations
    async def get_products(self):
        products = await self.products_collection.find({}).to_list(100)
        return {p['product_key']: {"brand": p['brand'], "model": p['model'], "new_price": p['new_price'], "secondhand_avg": p['secondhand_avg'], "buy_price": p['buy_price']} for p in products}
    
    async def add_product(self, product_key, brand, model, new_price, secondhand_avg, buy_price):
        await self.products_collection.update_one(
            {"product_key": product_key},
            {"$set": {"brand": brand, "model": model, "new_price": new_price, "secondhand_avg": secondhand_avg, "buy_price": buy_price}},
            upsert=True
        )
        return True
    
    async def delete_product(self, product_key):
        result = await self.products_collection.delete_one({"product_key": product_key})
        return result.deleted_count > 0
    
    async def get_product_price(self, brand, model):
        product_key = f"{brand}_{model}".lower().replace(" ", "_")
        product = await self.products_collection.find_one({"product_key": product_key})
        if product:
            return product
        return None
    
    # History operations
    async def add_history(self, record):
        record['timestamp'] = datetime.now().isoformat()
        await self.history_collection.insert_one(record)
    
    async def get_history(self, limit=100):
        history = await self.history_collection.find({}).sort("timestamp", -1).limit(limit).to_list(limit)
        return history

# สร้าง instance
mongo_db = MongoDB()