from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import io
import json
import os
import sys
from datetime import datetime

# OpenCV fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV not available - using simple mode")

import numpy as np

# Database
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from app.database import db
    print("✅ Database loaded successfully")
except Exception as e:
    print(f"⚠️ Database not found: {e}, creating simple version")
    class SimpleDB:
        def add_history(self, record): pass
        def get_history(self, limit=100): return []
        def get_products(self): return {}
        def get_product_price(self, brand, model): return None
    db = SimpleDB()

app = FastAPI(title="Second-hand Valuation API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Static Files (สำหรับให้บริการหน้าเว็บ)
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    print(f"✅ Static files mounted from {frontend_path}")
else:
    print(f"⚠️ Frontend folder not found at {frontend_path}")

def load_price_data():
    """โหลดข้อมูลราคาจาก database (Admin จัดการ)"""
    products = db.get_products()
    prices = {}
    for key, product in products.items():
        prices[key] = {
            "new_price": product["new_price"],
            "secondhand_avg": product["secondhand_avg"],
            "buy_price": product.get("buy_price", product["secondhand_avg"] * 0.7)
        }
    
    if not prices:
        print("⚠️ No data in database, using default prices")
        prices = {
            "iphone_14": {"new_price": 32900, "secondhand_avg": 25000, "buy_price": 22000},
            "iphone_13": {"new_price": 29900, "secondhand_avg": 18000, "buy_price": 15000},
            "iphone_12": {"new_price": 25900, "secondhand_avg": 13000, "buy_price": 10000},
            "samsung_s23": {"new_price": 28900, "secondhand_avg": 19000, "buy_price": 16000},
            "samsung_s22": {"new_price": 26900, "secondhand_avg": 14000, "buy_price": 11000},
            "xiaomi_12": {"new_price": 16900, "secondhand_avg": 9000, "buy_price": 7000}
        }
    
    return prices

def check_image_quality(image_array):
    """ตรวจสอบคุณภาพรูปภาพ (ความชัด, แสงสว่าง)"""
    if not CV2_AVAILABLE:
        return {'score': 100, 'warnings': [], 'blur_score': 100, 'brightness': 128}
    
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = np.mean(gray)
    
    quality_score = 100
    warnings = []
    
    if laplacian_var < 50:
        quality_score -= 30
        warnings.append("ภาพเบลอ")
    elif laplacian_var < 100:
        quality_score -= 15
        warnings.append("ภาพไม่คมชัด")
    
    if brightness < 50:
        quality_score -= 30
        warnings.append("ภาพมืดเกินไป")
    elif brightness < 80:
        quality_score -= 15
        warnings.append("ภาพค่อนข้างมืด")
    elif brightness > 220:
        quality_score -= 15
        warnings.append("ภาพสว่างเกินไป")
    
    return {
        'score': max(0, quality_score),
        'warnings': warnings,
        'blur_score': laplacian_var,
        'brightness': brightness
    }

def detect_defects_advanced(image_array):
    """ตรวจจับรอยขีดข่วนและตำหนิขั้นสูง"""
    if not CV2_AVAILABLE:
        return [], 0.01, {'score': 100, 'warnings': []}
    
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    quality = check_image_quality(image_array)
    
    if quality['score'] < 50:
        return [f"⚠️ {w}" for w in quality['warnings']], 0.01, quality
    
    h, w = gray.shape
    if h > 800 or w > 800:
        scale = 800 / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        gray = cv2.resize(gray, new_size)
    
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 150, 250)
    edge_density = np.sum(edges) / (edges.shape[0] * edges.shape[1])
    edge_density = min(0.5, edge_density)
    adjusted_score = edge_density * 0.08
    adjusted_score = min(0.3, adjusted_score)
    
    defects = []
    if adjusted_score > 0.06:
        defects.append("รอยขีดข่วนเล็กน้อย")
    if adjusted_score > 0.12:
        defects.append("รอยขีดข่วนชัดเจน")
    if adjusted_score > 0.20:
        defects.append("สภาพโทรมหนัก")
    
    if adjusted_score < 0.03:
        defects = []
        adjusted_score = 0.01
    
    return defects, adjusted_score, quality

def analyze_condition(image, image_count=1):
    image_array = np.array(image)
    defects, damage_score, quality = detect_defects_advanced(image_array)
    
    if damage_score < 0.01:
        condition_score = 100
    elif damage_score < 0.02:
        condition_score = 98
    elif damage_score < 0.03:
        condition_score = 95
    elif damage_score < 0.04:
        condition_score = 92
    elif damage_score < 0.06:
        condition_score = 88
    elif damage_score < 0.08:
        condition_score = 82
    elif damage_score < 0.10:
        condition_score = 75
    elif damage_score < 0.15:
        condition_score = 65
    elif damage_score < 0.20:
        condition_score = 55
    else:
        condition_score = max(0, 100 - (damage_score * 200))
    
    condition_score = round(condition_score)
    
    if condition_score >= 92:
        grade = 'A'
        multiplier = 0.97
        grade_desc = "สภาพเหมือนใหม่"
    elif condition_score >= 85:
        grade = 'A'
        multiplier = 0.94
        grade_desc = "สภาพดีมาก"
    elif condition_score >= 75:
        grade = 'B'
        multiplier = 0.87
        grade_desc = "สภาพดี"
    elif condition_score >= 62:
        grade = 'B'
        multiplier = 0.79
        grade_desc = "สภาพปานกลาง"
    elif condition_score >= 48:
        grade = 'C'
        multiplier = 0.68
        grade_desc = "มีรอยใช้งาน"
    else:
        grade = 'D'
        multiplier = 0.55
        grade_desc = "สภาพมีรอยชัดเจน"
    
    if quality['warnings']:
        defects.extend([f"⚠️ {w}" for w in quality['warnings']])
    
    return {
        'grade': grade,
        'grade_desc': grade_desc,
        'score': condition_score,
        'multiplier': multiplier,
        'defects': defects,
        'damage_score': round(damage_score, 4),
        'confidence': 0.92 if condition_score >= 85 else 0.85
    }

def calculate_price(brand, model, condition_multiplier, age_months=12, has_box=True, has_charger=True):
    product = db.get_product_price(brand, model)
    
    if product:
        new_price = product['new_price']
        base_secondhand = product['secondhand_avg']
        buy_price = product.get('buy_price', base_secondhand * 0.7)
    else:
        new_price = 15000
        base_secondhand = 8000
        buy_price = 5000
    
    age_depreciation = min(0.5, age_months * 0.02)
    accessory_bonus = (0.05 if has_box else 0) + (0.03 if has_charger else 0)
    final_price = base_secondhand * condition_multiplier * (1 - age_depreciation) * (1 + accessory_bonus)
    
    return {
        'price': round(final_price),
        'price_range': {
            'min': round(final_price * 0.85),
            'max': round(final_price * 1.15)
        },
        'buy_price': round(buy_price * condition_multiplier * (1 - age_depreciation) * 0.9),
        'factors': {
            'condition_multiplier': condition_multiplier,
            'age_depreciation': round(age_depreciation, 2),
            'accessory_bonus': accessory_bonus,
            'new_price': new_price,
            'market_avg': base_secondhand
        }
    }

# ========== MAIN API ENDPOINTS ==========
@app.get("/")
def root():
    return {"message": "Second-hand Valuation System API", "status": "running"}

@app.get("/products")
def get_products():
    return load_price_data()

@app.post("/evaluate")
async def evaluate_phone(
    file: UploadFile = File(...),
    brand: str = Form(...),
    model: str = Form(...),
    age_months: int = Form(12),
    has_box: bool = Form(True),
    has_charger: bool = Form(True),
    image_count: int = Form(1)
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        
        condition = analyze_condition(image, image_count)
        price_result = calculate_price(brand, model, condition['multiplier'], age_months, has_box, has_charger)
        
        try:
            db.add_history({
                'product': f"{brand}_{model}",
                'condition': condition['grade'],
                'condition_score': condition['score'],
                'damage_score': condition['damage_score'],
                'price': price_result['price'],
                'buy_price': price_result['buy_price'],
                'defects': condition['defects']
            })
        except:
            pass
        
        condition['image_count'] = image_count
        
        result = {
            'success': True,
            'product': {'brand': brand, 'model': model},
            'condition': {
                'grade': condition['grade'],
                'grade_desc': condition['grade_desc'],
                'score': condition['score'],
                'defects': condition['defects'],
                'confidence': condition['confidence'],
                'damage_score': condition['damage_score'],
                'image_count': image_count
            },
            'valuation': {
                'median_price': price_result['price'],
                'price_range': price_result['price_range'],
                'buy_price': price_result['buy_price'],
                'factors': price_result['factors']
            },
            'recommendation': get_recommendation(condition['grade'], price_result['price'], price_result['buy_price'], condition['grade_desc'])
        }
        
        return JSONResponse(result)
    
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)}, status_code=400)

def get_recommendation(grade, price, buy_price, grade_desc):
    if grade == 'A':
        return f"✨ {grade_desc} ({price:,} บาท) เหมาะสำหรับขายต่อหรือใช้เอง | รับซื้อ {buy_price:,} บาท"
    elif grade == 'B':
        return f"👍 {grade_desc} ขายได้จริงที่ {price:,} บาท | รับซื้อ {buy_price:,} บาท"
    elif grade == 'C':
        return f"⚠️ {grade_desc} แนะนำขาย {price:,} บาท หรือลดอีก 5% เพื่อขายเร็ว | รับซื้อ {buy_price:,} บาท"
    else:
        return f"🔧 {grade_desc} ขาย {price:,} บาท หรือซ่อมก่อนขาย | รับซื้อ {buy_price:,} บาท"

# ========== ADMIN API (ไม่มี Authentication สำหรับ Render) ==========
@app.get("/admin/brands")
def admin_get_brands():
    """ดึงข้อมูลยี่ห้อ"""
    try:
        brands_file = 'data/brands.json'
        if os.path.exists(brands_file):
            with open(brands_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        "apple": {"name": "Apple iPhone", "icon": "🍎", "models": ["14", "13", "12"]},
        "samsung": {"name": "Samsung", "icon": "📱", "models": ["S24", "S23", "S22"]},
        "xiaomi": {"name": "Xiaomi", "icon": "📱", "models": ["13", "12"]}
    }

@app.get("/admin/products/all")
def admin_get_products():
    """ดึงข้อมูลสินค้าทั้งหมด"""
    try:
        products_file = 'data/products.json'
        if os.path.exists(products_file):
            with open(products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

@app.get("/admin/history")
def admin_get_history(limit: int = 50):
    """ดึงประวัติการประเมิน"""
    try:
        history_file = 'data/history.json'
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return history[-limit:]
    except:
        pass
    return []

# Public API สำหรับหน้า Main
@app.get("/public/brands")
def public_get_brands():
    """API สำหรับหน้า Main ใช้ดึงข้อมูลยี่ห้อ"""
    try:
        brands_file = 'data/brands.json'
        if os.path.exists(brands_file):
            with open(brands_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        "apple": {"name": "Apple iPhone", "icon": "🍎", "models": ["14", "13", "12"]},
        "samsung": {"name": "Samsung", "icon": "📱", "models": ["S24", "S23", "S22"]},
        "xiaomi": {"name": "Xiaomi", "icon": "📱", "models": ["13", "12"]}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)