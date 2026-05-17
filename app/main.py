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

# MongoDB Database
from app.database_mongo import mongo_db

app = FastAPI(title="Second-hand Valuation API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    print(f"✅ Static files mounted from {frontend_path}")

# ตัวแปรสำหรับเก็บสถานะ connection
DB_READY = False

@app.on_event("startup")
async def startup_event():
    global DB_READY
    DB_READY = await mongo_db.connect()

def load_price_data():
    """โหลดข้อมูลราคาจาก database"""
    # ใช้ MongoDB หรือ fallback
    return {}

def check_image_quality(image_array):
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
    
    return {'score': max(0, quality_score), 'warnings': warnings, 'blur_score': laplacian_var, 'brightness': brightness}

def detect_defects_advanced(image_array):
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
    
    if adjusted_score < 0.03:
        defects = []
        adjusted_score = 0.01
    
    return defects, adjusted_score, quality

def analyze_condition(image, image_count=1):
    image_array = np.array(image)
    defects, damage_score, quality = detect_defects_advanced(image_array)
    
    if damage_score < 0.01:
        condition_score = 100
    elif damage_score < 0.03:
        condition_score = 95
    elif damage_score < 0.06:
        condition_score = 88
    elif damage_score < 0.10:
        condition_score = 75
    elif damage_score < 0.15:
        condition_score = 65
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
        'grade': grade, 'grade_desc': grade_desc, 'score': condition_score,
        'multiplier': multiplier, 'defects': defects, 'damage_score': round(damage_score, 4),
        'confidence': 0.92 if condition_score >= 85 else 0.85
    }

def calculate_price(brand, model, condition_multiplier, age_months=12, has_box=True, has_charger=True):
    # ใช้ข้อมูลจาก MongoDB
    if DB_READY:
        import asyncio
        # เรียก async function
        loop = asyncio.new_event_loop()
        product = loop.run_until_complete(mongo_db.get_product_price(brand, model))
        if product:
            base_secondhand = product['secondhand_avg']
            buy_price = product.get('buy_price', base_secondhand * 0.7)
        else:
            base_secondhand = 8000
            buy_price = 5000
    else:
        base_secondhand = 8000
        buy_price = 5000
    
    age_depreciation = min(0.5, age_months * 0.02)
    accessory_bonus = (0.05 if has_box else 0) + (0.03 if has_charger else 0)
    final_price = base_secondhand * condition_multiplier * (1 - age_depreciation) * (1 + accessory_bonus)
    
    return {
        'price': round(final_price),
        'price_range': {'min': round(final_price * 0.85), 'max': round(final_price * 1.15)},
        'buy_price': round(buy_price * condition_multiplier * (1 - age_depreciation) * 0.9),
        'factors': {
            'condition_multiplier': condition_multiplier,
            'age_depreciation': round(age_depreciation, 2),
            'accessory_bonus': accessory_bonus,
            'market_avg': base_secondhand
        }
    }

# ========== MAIN API ==========
@app.get("/")
def root():
    return {"message": "Second-hand Valuation System API", "status": "running"}

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
        
        # บันทึกประวัติลง MongoDB
        if DB_READY:
            await mongo_db.add_history({
                'product': f"{brand}_{model}",
                'condition': condition['grade'],
                'condition_score': condition['score'],
                'damage_score': condition['damage_score'],
                'price': price_result['price'],
                'buy_price': price_result['buy_price'],
                'defects': condition['defects']
            })
        
        result = {
            'success': True,
            'product': {'brand': brand, 'model': model},
            'condition': {
                'grade': condition['grade'], 'grade_desc': condition['grade_desc'],
                'score': condition['score'], 'defects': condition['defects'],
                'confidence': condition['confidence'], 'damage_score': condition['damage_score'],
                'image_count': image_count
            },
            'valuation': {
                'median_price': price_result['price'], 'price_range': price_result['price_range'],
                'buy_price': price_result['buy_price'], 'factors': price_result['factors']
            },
            'recommendation': get_recommendation(condition['grade'], price_result['price'], price_result['buy_price'], condition['grade_desc'])
        }
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)}, status_code=400)

def get_recommendation(grade, price, buy_price, grade_desc):
    if grade == 'A':
        return f"✨ {grade_desc} ({price:,} บาท) เหมาะสำหรับขายต่อ | รับซื้อ {buy_price:,} บาท"
    elif grade == 'B':
        return f"👍 {grade_desc} ขายได้จริงที่ {price:,} บาท | รับซื้อ {buy_price:,} บาท"
    elif grade == 'C':
        return f"⚠️ {grade_desc} แนะนำขาย {price:,} บาท | รับซื้อ {buy_price:,} บาท"
    else:
        return f"🔧 {grade_desc} ขาย {price:,} บาท หรือซ่อมก่อนขาย | รับซื้อ {buy_price:,} บาท"

# ========== ADMIN & PUBLIC API ==========
@app.get("/admin/brands")
async def admin_get_brands():
    if DB_READY:
        return await mongo_db.get_brands()
    return {}

@app.delete("/admin/brand/{brand_id}")
async def admin_delete_brand(brand_id: str):
    if DB_READY:
        success = await mongo_db.delete_brand(brand_id)
        return {"success": success, "message": f"Deleted {brand_id}"}
    return {"success": False, "error": "Database not ready"}

@app.get("/admin/products/all")
async def admin_get_products():
    if DB_READY:
        return await mongo_db.get_products()
    return {}

@app.delete("/admin/product/{product_key}")
async def admin_delete_product(product_key: str):
    if DB_READY:
        success = await mongo_db.delete_product(product_key)
        return {"success": success, "message": f"Deleted {product_key}"}
    return {"success": False, "error": "Database not ready"}

@app.get("/admin/history")
async def admin_get_history(limit: int = 50):
    if DB_READY:
        return await mongo_db.get_history(limit)
    return []

@app.get("/public/brands")
async def public_get_brands():
    if DB_READY:
        return await mongo_db.get_brands()
    return {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)