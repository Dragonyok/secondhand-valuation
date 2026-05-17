import json
import os
from datetime import datetime
from typing import Dict, List, Any

class Database:
    def __init__(self):
        self.data_dir = 'data'
        self.brands_file = f'{self.data_dir}/brands.json'  # ใหม่: จัดการยี่ห้อ
        self.products_file = f'{self.data_dir}/products.json'  # ใหม่: จัดการสินค้า
        self.prices_file = f'{self.data_dir}/phone_prices.json'
        self.history_file = f'{self.data_dir}/history.json'
        self.users_file = f'{self.data_dir}/users.json'
        self.init_files()
    
    def init_files(self):
        os.makedirs(self.data_dir, exist_ok=True)
        
        # สร้างไฟล์ brands.json ถ้าไม่มี
        if not os.path.exists(self.brands_file):
            default_brands = {
                "apple": {
                    "name": "Apple iPhone",
                    "icon": "🍎",
                    "models": ["14", "13", "12", "11", "SE"]
                },
                "samsung": {
                    "name": "Samsung",
                    "icon": "📱",
                    "models": ["S24", "S23", "S22", "A54", "A34"]
                },
                "xiaomi": {
                    "name": "Xiaomi",
                    "icon": "📱",
                    "models": ["13", "12", "11", "Redmi Note 12"]
                },
                "poco": {
                    "name": "Poco",
                    "icon": "⚡",
                    "models": ["F5", "F4", "X5", "M5"]
                },
                "huawei": {
                    "name": "Huawei",
                    "icon": "📱",
                    "models": ["P60", "P50", "Mate 50", "Nova 11"]
                },
                "oppo": {
                    "name": "OPPO",
                    "icon": "📱",
                    "models": ["Find X6", "Reno 10", "A78"]
                },
                "vivo": {
                    "name": "vivo",
                    "icon": "📱",
                    "models": ["X100", "V29", "Y36"]
                }
            }
            self.save_brands(default_brands)
        
        # สร้างไฟล์ products.json ถ้าไม่มี (เก็บราคาแยกตามรุ่น)
        if not os.path.exists(self.products_file):
            default_products = {
                "apple_14": {
                    "brand": "apple",
                    "model": "14",
                    "new_price": 32900,
                    "secondhand_avg": 25000,
                    "buy_price": 22000
                },
                "apple_13": {
                    "brand": "apple",
                    "model": "13",
                    "new_price": 29900,
                    "secondhand_avg": 18000,
                    "buy_price": 15000
                },
                "apple_12": {
                    "brand": "apple",
                    "model": "12",
                    "new_price": 25900,
                    "secondhand_avg": 13000,
                    "buy_price": 10000
                },
                "samsung_S23": {
                    "brand": "samsung",
                    "model": "S23",
                    "new_price": 28900,
                    "secondhand_avg": 19000,
                    "buy_price": 16000
                },
                "samsung_S22": {
                    "brand": "samsung",
                    "model": "S22",
                    "new_price": 26900,
                    "secondhand_avg": 14000,
                    "buy_price": 11000
                },
                "xiaomi_13": {
                    "brand": "xiaomi",
                    "model": "13",
                    "new_price": 16900,
                    "secondhand_avg": 9000,
                    "buy_price": 7000
                }
            }
            self.save_products(default_products)
        
        # สร้างไฟล์ prices (สำหรับ backward compatibility)
        if not os.path.exists(self.prices_file):
            self.save_prices(self.get_products())
        
        # สร้างไฟล์ history
        if not os.path.exists(self.history_file):
            self.save_history([])
        
        # สร้างไฟล์ users
        if not os.path.exists(self.users_file):
            default_users = {
                "admin": {
                    "password": "admin123",
                    "role": "admin",
                    "name": "ผู้ดูแลระบบ"
                }
            }
            self.save_users(default_users)
    
    # Brand Management
    def get_brands(self) -> Dict:
        with open(self.brands_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_brands(self, brands: Dict):
        with open(self.brands_file, 'w', encoding='utf-8') as f:
            json.dump(brands, f, ensure_ascii=False, indent=2)
    
    def add_brand(self, brand_id: str, name: str, icon: str = "📱", models: List[str] = None):
        brands = self.get_brands()
        brands[brand_id] = {
            "name": name,
            "icon": icon,
            "models": models or []
        }
        self.save_brands(brands)
        return True
    
    def update_brand_models(self, brand_id: str, models: List[str]):
        brands = self.get_brands()
        if brand_id in brands:
            brands[brand_id]["models"] = models
            self.save_brands(brands)
            return True
        return False
    
    def delete_brand(self, brand_id: str):
        brands = self.get_brands()
        if brand_id in brands:
            del brands[brand_id]
            self.save_brands(brands)
            return True
        return False
    
    # Product Management
    def get_products(self) -> Dict:
        with open(self.products_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_products(self, products: Dict):
        with open(self.products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
    
    def add_product(self, product_key: str, brand: str, model: str, new_price: int, secondhand_avg: int, buy_price: int):
        products = self.get_products()
        products[product_key] = {
            "brand": brand,
            "model": model,
            "new_price": new_price,
            "secondhand_avg": secondhand_avg,
            "buy_price": buy_price
        }
        self.save_products(products)
        
        # อัปเดต brands.json ให้มีรุ่นนี้ด้วย
        brands = self.get_brands()
        if brand in brands and model not in brands[brand]["models"]:
            brands[brand]["models"].append(model)
            self.save_brands(brands)
        
        return True
    
    def update_product(self, product_key: str, data: Dict):
        products = self.get_products()
        if product_key in products:
            products[product_key].update(data)
            self.save_products(products)
            return True
        return False
    
    def delete_product(self, product_key: str):
        products = self.get_products()
        if product_key in products:
            del products[product_key]
            self.save_products(products)
            return True
        return False
    
    def get_product_price(self, brand: str, model: str) -> Dict:
        products = self.get_products()
        key = f"{brand}_{model}".lower().replace(" ", "_")
        if key in products:
            return products[key]
        
        # ลองค้นหาแบบ case-insensitive
        for k, v in products.items():
            if v.get("brand", "").lower() == brand.lower() and v.get("model", "").lower() == model.lower():
                return v
        return None
    
    # Legacy Price Management (สำหรับ backward compatibility)
    def get_prices(self) -> Dict:
        products = self.get_products()
        # แปลงเป็นรูปแบบเดิม
        prices = {}
        for key, value in products.items():
            prices[key] = {
                "new_price": value["new_price"],
                "secondhand_avg": value["secondhand_avg"],
                "buy_price": value["buy_price"]
            }
        return prices
    
    def save_prices(self, prices: Dict):
        # แปลงกลับเป็น products format
        products = {}
        for key, value in prices.items():
            parts = key.split("_")
            brand = parts[0] if len(parts) > 0 else "unknown"
            model = "_".join(parts[1:]) if len(parts) > 1 else key
            products[key] = {
                "brand": brand,
                "model": model,
                "new_price": value["new_price"],
                "secondhand_avg": value["secondhand_avg"],
                "buy_price": value.get("buy_price", value["secondhand_avg"] * 0.7)
            }
        self.save_products(products)
    
    # History Management
    def get_history(self, limit: int = 100) -> List:
        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history[-limit:]
    
    def save_history(self, history: List):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def add_history(self, record: Dict):
        history = self.get_history(10000)
        record['timestamp'] = datetime.now().isoformat()
        history.append(record)
        self.save_history(history)
    
    # User Management
    def get_users(self) -> Dict:
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_users(self, users: Dict):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def verify_user(self, username: str, password: str) -> bool:
        users = self.get_users()
        if username in users:
            return users[username]['password'] == password
        return False
    
    def add_user(self, username: str, password: str, name: str, role: str = 'user'):
        users = self.get_users()
        users[username] = {"password": password, "role": role, "name": name}
        self.save_users(users)

db = Database()