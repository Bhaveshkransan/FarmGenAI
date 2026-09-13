# c:\PROJECT\FarmGenAI\shared\crop_master.py

# 7-Crop Maharashtra MVP Canonical Scope
# DO NOT ADD CROPS WITHOUT ARCHITECTURAL APPROVAL

CROPS = {
    "SUGARCANE": {
        "crop_id": "SUGARCANE",
        "name": "Sugarcane",
        "state": "Maharashtra",
        "image": "sugarcane.jpg",
        "varieties": ["Co 86032", "Co 0238"],
        "mandi_api_mapping": "Sugarcane",
        "ml_mapping": "Sugarcane",
        "rag_mapping": "Sugarcane"
    },
    "SOYBEAN": {
        "crop_id": "SOYBEAN",
        "name": "Soybean",
        "state": "Maharashtra",
        "image": "soybean.jpg",
        "varieties": ["JS 335", "MAUS 71"],
        "mandi_api_mapping": "Soyabean",
        "ml_mapping": "Soybean",
        "rag_mapping": "Soybean"
    },
    "COTTON": {
        "crop_id": "COTTON",
        "name": "Cotton",
        "state": "Maharashtra",
        "image": "cotton.jpg",
        "varieties": ["Bt Cotton", "Desi Cotton"],
        "mandi_api_mapping": "Cotton",
        "ml_mapping": "Cotton",
        "rag_mapping": "Cotton"
    },
    "JOWAR": {
        "crop_id": "JOWAR",
        "name": "Jowar (Sorghum)",
        "state": "Maharashtra",
        "image": "jowar.jpg",
        "varieties": ["Rabi Jowar", "Kharif Jowar"],
        "mandi_api_mapping": "Jowar(Sorghum)",
        "ml_mapping": "Jowar (Sorghum)",
        "rag_mapping": "Jowar"
    },
    "ONION": {
        "crop_id": "ONION",
        "name": "Onion",
        "state": "Maharashtra",
        "image": "onion.jpg",
        "varieties": ["Nashik Red", "White Onion"],
        "mandi_api_mapping": "Onion",
        "ml_mapping": "Onion",
        "rag_mapping": "Onion"
    },
    "BAJRA": {
        "crop_id": "BAJRA",
        "name": "Bajra (Pearl Millet)",
        "state": "Maharashtra",
        "image": "bajra.jpg",
        "varieties": ["Hybrid Bajra", "Local Bajra"],
        "mandi_api_mapping": "Bajra(Pearl Millet)",
        "ml_mapping": "Bajra (Pearl Millet)",
        "rag_mapping": "Bajra"
    },
    "RICE": {
        "crop_id": "RICE",
        "name": "Rice",
        "state": "Maharashtra",
        "image": "rice.jpg",
        "varieties": ["Basmati", "Indrayani", "Kolam"],
        "mandi_api_mapping": "Rice",
        "ml_mapping": "Rice",
        "rag_mapping": "Rice"
    }
}

def get_allowed_crop_names():
    return [c["name"] for c in CROPS.values()]

def get_allowed_ml_mappings():
    return [c["ml_mapping"] for c in CROPS.values()]

def get_crop_by_name(name):
    for c in CROPS.values():
        if c["name"].lower() == name.lower() or c["ml_mapping"].lower() == name.lower():
            return c
    return None
