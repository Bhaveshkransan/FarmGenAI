"""
generate_maharashtra_history.py
Generates 2-year realistic historical price data for the top 7 Maharashtra crops
anchored to real mandi prices and MSP from the actual datasets.
"""
import json
import random
import math
import datetime
import os

# ── Real data anchors from cleaned_mandi_prices.json & cleaned_msp_prices.json ──
# Top 7 Maharashtra crops by production weight/area
CROP_DATA = {
    'Sugarcane': {
        'base_price_kg': 3.75,      # Rs/kg (FRP price approx)
        'msp_per_kg': 3.40,         # FRP 2026-27
        'arrival_avg': 8500,        # MT
        'volatility': 0.05,         # Low volatility (govt controlled)
        'peak_months': [11, 12, 1, 2, 3],   # Nov-Mar (crushing season)
        'low_months': [6, 7, 8, 9]          # Monsoon - pre-harvest
    },
    'Soybean': {
        'base_price_kg': 69.64,     # From cleaned_mandi_prices.json
        'msp_per_kg': 53.28,        # From cleaned_msp_prices.json
        'arrival_avg': 1200,
        'volatility': 0.15,
        'peak_months': [11, 12, 1], # Post-harvest Nov-Jan
        'low_months': [7, 8, 9]     # Pre-harvest
    },
    'Cotton': {
        'base_price_kg': 65.0,      # MSP ~6620/quintal
        'msp_per_kg': 66.20,        # MSP 2026-27
        'arrival_avg': 900,
        'volatility': 0.12,
        'peak_months': [11, 12, 1, 2],
        'low_months': [6, 7, 8]
    },
    'Jowar': {
        'base_price_kg': 60.00,     # From cleaned_mandi_prices.json
        'msp_per_kg': 36.99,        # From cleaned_msp_prices.json
        'arrival_avg': 100,
        'volatility': 0.10,
        'peak_months': [3, 4, 5],   # Rabi harvest
        'low_months': [10, 11]
    },
    'Onion': {
        'base_price_kg': 22.0,      # Typical Maharashtra onion price
        'msp_per_kg': None,         # No MSP for onion
        'arrival_avg': 3500,
        'volatility': 0.35,         # HIGH volatility
        'peak_months': [4, 5, 6],   # Summer harvest
        'low_months': [11, 12, 1]   # Kharif harvest dip
    },
    'Bajra': {
        'base_price_kg': 35.58,     # From cleaned_mandi_prices.json
        'msp_per_kg': 27.75,        # From cleaned_msp_prices.json
        'arrival_avg': 120,
        'volatility': 0.12,
        'peak_months': [11, 12],    # Kharif harvest
        'low_months': [6, 7]
    },
    'Rice': {
        'base_price_kg': 34.71,     # Paddy from cleaned_mandi_prices.json (converted to rice)
        'msp_per_kg': 23.69,        # Paddy MSP
        'arrival_avg': 360,
        'volatility': 0.08,
        'peak_months': [11, 12, 1],
        'low_months': [6, 7, 8]
    }
}

DISTRICTS = [
    'Nashik', 'Pune', 'Ahmednagar', 'Solapur', 'Sangli', 'Satara',
    'Kolhapur', 'Aurangabad', 'Nagpur', 'Amravati', 'Latur', 'Jalgaon',
    'Osmanabad', 'Nanded', 'Buldhana', 'Akola', 'Washim', 'Yavatmal'
]

# Crop-district affinity (which districts produce which crops heavily)
CROP_DISTRICT_MAP = {
    'Sugarcane': ['Pune', 'Satara', 'Sangli', 'Kolhapur', 'Solapur', 'Ahmednagar'],
    'Soybean': ['Latur', 'Osmanabad', 'Nanded', 'Aurangabad', 'Buldhana', 'Akola'],
    'Cotton': ['Aurangabad', 'Nagpur', 'Amravati', 'Washim', 'Yavatmal', 'Buldhana'],
    'Jowar': ['Solapur', 'Osmanabad', 'Latur', 'Sangli', 'Ahmednagar', 'Pune'],
    'Onion': ['Nashik', 'Ahmednagar', 'Pune', 'Solapur', 'Satara', 'Sangli'],
    'Bajra': ['Aurangabad', 'Jalgaon', 'Ahmednagar', 'Nashik', 'Nanded', 'Osmanabad'],
    'Rice': ['Nagpur', 'Bhandara', 'Gondia', 'Ratnagiri', 'Raigad', 'Kolhapur']
}

def get_seasonal_multiplier(month, crop_name):
    """Returns a price multiplier based on crop seasonality (supply/demand)."""
    crop = CROP_DATA[crop_name]
    if month in crop['peak_months']:
        # High supply = lower prices in peak harvest months
        return random.uniform(0.85, 1.00)
    elif month in crop['low_months']:
        # Low supply = higher prices in lean months
        return random.uniform(1.05, 1.25)
    else:
        return random.uniform(0.95, 1.08)

def add_market_event(day_index, crop_name):
    """Simulate market events like droughts, govt interventions."""
    # Random market shocks every ~60 days
    if day_index % 60 == 0 and random.random() < 0.3:
        if crop_name == 'Onion':
            return random.uniform(0.5, 2.0)  # Extreme onion price events
        return random.uniform(0.85, 1.20)
    return 1.0

def generate_data(days=730):
    start_date = datetime.date(2024, 9, 1)  # 2 years back from Sep 2026
    records = []

    # For continuity, track last price per (crop, district)
    last_price = {}

    for day in range(days):
        current_date = start_date + datetime.timedelta(days=day)
        month = current_date.month
        year = current_date.year

        # Macro inflation trend (2% per year)
        inflation = 1.0 + (day / 730.0) * 0.04

        for crop_name, crop_info in CROP_DATA.items():
            base = crop_info['base_price_kg']
            vol = crop_info['volatility']
            msp = crop_info['msp_per_kg']

            # Use crop-district affinity
            primary_districts = CROP_DISTRICT_MAP.get(crop_name, DISTRICTS[:6])
            day_districts = random.sample(primary_districts, min(4, len(primary_districts)))

            for district in day_districts:
                key = (crop_name, district)
                prev_price = last_price.get(key, base)

                # Price walk: blend of mean-reversion + random noise + seasonality
                seasonal = get_seasonal_multiplier(month, crop_name)
                shock = add_market_event(day, crop_name)
                noise = random.gauss(0, vol * 0.3)

                # Mean revert to seasonal base
                target = base * seasonal * inflation
                price = prev_price + 0.3 * (target - prev_price) + noise + (target * vol * random.uniform(-0.5, 0.5))

                # Price must not go below MSP (govt floor)
                if msp:
                    price = max(price, msp * inflation)

                # Apply shock
                price = price * shock
                price = max(price, 1.0)  # Never negative
                price = round(price, 2)

                # Arrival varies by season and district
                base_arrival = crop_info['arrival_avg']
                if month in crop_info['peak_months']:
                    arrival = round(random.uniform(base_arrival * 0.8, base_arrival * 1.5), 1)
                else:
                    arrival = round(random.uniform(base_arrival * 0.2, base_arrival * 0.8), 1)

                records.append({
                    "crop": crop_name,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "state": "Maharashtra",
                    "district": district,
                    "mandi_name": f"{district} APMC",
                    "price_per_quintal": round(price * 100, 2),
                    "price_per_kg": price,
                    "msp_per_kg": msp,
                    "arrival_mt": arrival
                })

                last_price[key] = price

    return records

if __name__ == "__main__":
    print("Generating realistic 2-year Maharashtra crop price history...")
    records = generate_data(730)
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'dataset', 'maharashtra_historical_prices.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)
    
    # Print summary stats
    from collections import defaultdict
    crop_stats = defaultdict(list)
    for r in records:
        crop_stats[r['crop']].append(r['price_per_kg'])
    
    print(f"\nGenerated {len(records)} records")
    print("\nPrice Statistics:")
    print(f"{'Crop':<25} {'Min':>8} {'Avg':>8} {'Max':>8} {'Records':>8}")
    print("-" * 60)
    for crop, prices in sorted(crop_stats.items()):
        print(f"{crop:<25} {min(prices):>7.2f}  {sum(prices)/len(prices):>7.2f}  {max(prices):>7.2f}  {len(prices):>7}")
    
    print(f"\nSaved to {output_path}")
