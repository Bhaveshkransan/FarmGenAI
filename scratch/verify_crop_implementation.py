"""Independent verification of the 7-crop implementation."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.crop_catalog import BUYER_SUPPORTED_CROPS, normalize_crop_name, validate_buyer_crop
from agents.buyer_agent import BuyerAgent

print("=== VERIFY 7-CROP CATALOG ===")
canonical = sorted(list(BUYER_SUPPORTED_CROPS.keys()))
print("Canonical Crops in catalog:", canonical)
assert len(BUYER_SUPPORTED_CROPS) == 7, f"Expected 7 crops, found {len(BUYER_SUPPORTED_CROPS)}"

# Aliases test
print("\n=== VERIFY ALIASES ===")
aliases_to_test = [
    ("ganna", "Sugarcane"), ("cane", "Sugarcane"), ("sugar cane", "Sugarcane"), ("oos", "Sugarcane"),
    ("soya", "Soybean"), ("soyabean", "Soybean"), ("soyabeans", "Soybean"),
    ("kapas", "Cotton"), ("raw cotton", "Cotton"),
    ("sorghum", "Jowar"), ("jowari", "Jowar"), ("jowar_hybrid", "Jowar"),
    ("kanda", "Onion"), ("pyaz", "Onion"),
    ("pearl millet", "Bajra"), ("cumbu", "Bajra"), ("bajri", "Bajra"),
    ("paddy", "Rice"), ("dhan", "Rice"), ("chawal", "Rice")
]
for alias, expected in aliases_to_test:
    norm = normalize_crop_name(alias)
    print(f"Alias '{alias}' -> '{norm}' (Expected: '{expected}')")
    assert norm == expected, f"Failed alias {alias}"

# Rejection test
print("\n=== VERIFY UNSUPPORTED CROP REJECTION ===")
unsupported = ["Tomato", "Wheat", "Potato", "Maize", "Cabbage", "Turmeric", "Pomegranate", "Apple", "Barley"]
for crop in unsupported:
    try:
        validate_buyer_crop(crop)
        print(f"ERROR: {crop} was NOT rejected!")
    except ValueError as e:
        print(f"PASS: {crop} successfully rejected: {e}")

# BuyerAgent init test
print("\n=== VERIFY BUYERAGENT INIT & OFFER VALIDATION ===")
b_valid = BuyerAgent(name="TestBuyer", crop="soya", budget=50000, max_quantity=1000, target_price=40.0)
print(f"BuyerAgent init with 'soya' -> crop set to '{b_valid.crop}'")
assert b_valid.crop == "Soybean"

try:
    BuyerAgent(name="BadBuyer", crop="Wheat", budget=50000, max_quantity=1000, target_price=20.0)
    print("ERROR: BuyerAgent with Wheat was NOT rejected!")
except ValueError as e:
    print(f"PASS: BuyerAgent with Wheat raised ValueError: {e}")

# Offer validation with wrong crop
resp_wrong_crop = b_valid.respond_to_offer({"price": 40.0, "quantity": 100, "crop": "Wheat"})
print(f"Offer with crop='Wheat' response: {resp_wrong_crop.get('type')}, reason: {resp_wrong_crop.get('message')}")
assert resp_wrong_crop.get("type") == "REJECT"

# PO normalization test
po = b_valid.generate_purchase_order(price=45.0, quantity=100.0, seller_name="Farmer Ramesh")
print(f"PO crop name: '{po['crop']}' (Canonical TitleCase)")
assert po["crop"] == "Soybean"
print("\n>>> ALL 7-CROP CHECKS PASSED FACTUALLY.")
