from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from datetime import datetime

app = FastAPI(title="Admin API")
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== DATABASE FUNCTIONS ==========
def get_data_dir():
    return 'data'

def load_brands():
    brands_file = f'{get_data_dir()}/brands.json'
    if os.path.exists(brands_file):
        with open(brands_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "apple": {"name": "Apple iPhone", "icon": "🍎", "models": ["14", "13", "12"]},
        "samsung": {"name": "Samsung", "icon": "📱", "models": ["S24", "S23", "S22"]},
        "xiaomi": {"name": "Xiaomi", "icon": "📱", "models": ["13", "12"]}
    }

def save_brands(brands):
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(f'{get_data_dir()}/brands.json', 'w', encoding='utf-8') as f:
        json.dump(brands, f, ensure_ascii=False, indent=2)

def load_products():
    products_file = f'{get_data_dir()}/products.json'
    if os.path.exists(products_file):
        with open(products_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "apple_14": {"brand": "apple", "model": "14", "new_price": 32900, "secondhand_avg": 25000, "buy_price": 22000},
        "apple_13": {"brand": "apple", "model": "13", "new_price": 29900, "secondhand_avg": 18000, "buy_price": 15000},
        "apple_12": {"brand": "apple", "model": "12", "new_price": 25900, "secondhand_avg": 13000, "buy_price": 10000}
    }

def save_products(products):
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(f'{get_data_dir()}/products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def load_history():
    history_file = f'{get_data_dir()}/history.json'
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(f'{get_data_dir()}/history.json', 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_users():
    users_file = f'{get_data_dir()}/users.json'
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"admin": {"password": "admin123", "role": "admin", "name": "ผู้ดูแลระบบ"}}

# ========== AUTHENTICATION ==========
def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    users = load_users()
    username = credentials.username
    password = credentials.password
    
    if username in users and users[username]['password'] == password:
        return username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

# ========== API ENDPOINTS ==========
@app.get("/")
def root():
    return {"message": "Admin API is running", "status": "ok"}

# ========== PUBLIC APIS (ไม่ต้องใช้ Authentication) ==========
@app.get("/public/brands")
def public_get_brands():
    """API สำหรับหน้า Main ใช้ดึงข้อมูลยี่ห้อ"""
    return load_brands()

@app.get("/public/products")
def public_get_products():
    """API สำหรับหน้า Main ใช้ดึงข้อมูลสินค้า"""
    return load_products()

@app.get("/public/product/{brand}/{model}")
def public_get_product(brand: str, model: str):
    """API สำหรับตรวจสอบราคาสินค้า"""
    products = load_products()
    product_key = f"{brand}_{model}".lower().replace(" ", "_")
    if product_key in products:
        return products[product_key]
    return {"error": "Product not found"}

# ========== ADMIN APIS (ต้องใช้ Authentication) ==========
# Brands API
@app.get("/admin/brands")
def get_brands(username: str = Depends(verify_admin)):
    return load_brands()

@app.post("/admin/brand/{brand_id}")
def add_brand(brand_id: str, brand_data: dict, username: str = Depends(verify_admin)):
    brands = load_brands()
    brands[brand_id] = brand_data
    save_brands(brands)
    return {"success": True, "message": f"Added brand {brand_id}"}

@app.put("/admin/brand/{brand_id}/models")
def update_brand_models(brand_id: str, models: List[str], username: str = Depends(verify_admin)):
    brands = load_brands()
    if brand_id in brands:
        brands[brand_id]["models"] = models
        save_brands(brands)
        return {"success": True, "message": f"Updated models for {brand_id}"}
    raise HTTPException(status_code=404, detail="Brand not found")

@app.delete("/admin/brand/{brand_id}")
def delete_brand(brand_id: str, username: str = Depends(verify_admin)):
    brands = load_brands()
    if brand_id in brands:
        del brands[brand_id]
        save_brands(brands)
        return {"success": True, "message": f"Deleted brand {brand_id}"}
    raise HTTPException(status_code=404, detail="Brand not found")

# Products API
@app.get("/admin/products/all")
def get_all_products(username: str = Depends(verify_admin)):
    return load_products()

@app.post("/admin/product/new")
def add_new_product(product: dict, username: str = Depends(verify_admin)):
    products = load_products()
    product_key = f"{product['brand']}_{product['model']}".lower().replace(" ", "_")
    products[product_key] = product
    save_products(products)
    
    # อัปเดต brands.json ให้มีรุ่นนี้ด้วย
    brands = load_brands()
    brand_id = product['brand'].lower()
    model_name = product['model']
    if brand_id in brands and model_name not in brands[brand_id].get("models", []):
        brands[brand_id].setdefault("models", []).append(model_name)
        save_brands(brands)
    
    return {"success": True, "message": f"Added product {product_key}"}

@app.put("/admin/product/{product_key}")
def update_product(product_key: str, product_data: dict, username: str = Depends(verify_admin)):
    products = load_products()
    if product_key in products:
        products[product_key].update(product_data)
        save_products(products)
        return {"success": True, "message": f"Updated product {product_key}"}
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/admin/product/{product_key}")
def delete_product(product_key: str, username: str = Depends(verify_admin)):
    products = load_products()
    if product_key in products:
        del products[product_key]
        save_products(products)
        return {"success": True, "message": f"Deleted product {product_key}"}
    raise HTTPException(status_code=404, detail="Product not found")

# History API
@app.get("/admin/history")
def get_history(limit: int = 50, username: str = Depends(verify_admin)):
    history = load_history()
    return history[-limit:]

# Buy API
@app.post("/admin/buy")
def buy_product(request: dict, username: str = Depends(verify_admin)):
    product_key = request.get('product_key')
    grade = request.get('condition_grade', 'B')
    
    products = load_products()
    if product_key not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    
    grade_multiplier = {'A': 0.95, 'B': 0.85, 'C': 0.70, 'D': 0.50}
    buy_price = products[product_key]['buy_price']
    final_price = int(buy_price * grade_multiplier.get(grade, 0.70))
    
    return {
        "success": True,
        "product": product_key,
        "buy_price": final_price,
        "original_buy_price": buy_price,
        "condition": grade,
        "message": f"รับซื้อในราคา {final_price:,} บาท"
    }

# Test endpoint (ไม่ต้องใช้ auth - สำหรับทดสอบ)
@app.get("/test/brands")
def test_brands():
    return load_brands()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)