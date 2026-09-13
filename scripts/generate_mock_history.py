import json
import random
import datetime
import os

CROPS = [
    'Onion', 'Tomato', 'Soybean', 'Cotton', 'Grapes', 
    'Sugarcane', 'Pomegranate', 'Tur (Pigeon Pea)', 'Chana (Gram)'
]

DISTRICTS = ['Nashik', 'Pune', 'Ahmednagar', 'Jalgaon', 'Solapur', 'Sangli', 'Satara', 'Kolhapur', 'Aurangabad', 'Nagpur']

def generate_data(days=730):
    start_date = datetime.date.today() - datetime.timedelta(days=days)
    records = []
    
    # Base prices to anchor randomness
    base_prices = {
        'Onion': 25, 'Tomato': 30, 'Soybean': 45, 'Cotton': 60, 
        'Grapes': 80, 'Sugarcane': 3, 'Pomegranate': 90, 
        'Tur (Pigeon Pea)': 70, 'Chana (Gram)': 55
    }

    for day in range(days):
        current_date = start_date + datetime.timedelta(days=day)
        
        # Add some seasonality based on month
        month = current_date.month
        
        for crop in CROPS:
            # Base price
            base = base_prices[crop]
            
            # Seasonality modifier (e.g. higher in summer, lower in harvest)
            seasonality_multiplier = 1.0 + (0.2 * (month % 3) / 3.0) 
            
            # General trend (slight inflation over 2 years)
            trend_multiplier = 1.0 + (day / 730.0) * 0.1
            
            # Random noise (weather anomalies, daily market fluctuation)
            noise = random.uniform(0.85, 1.15)
            
            price_per_kg = base * seasonality_multiplier * trend_multiplier * noise
            
            # Generate a few records for different districts per day
            for district in random.sample(DISTRICTS, 3):
                district_noise = random.uniform(0.95, 1.05)
                final_price = round(price_per_kg * district_noise, 2)
                
                records.append({
                    "crop": crop,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "state": "Maharashtra",
                    "district": district,
                    "mandi_name": f"{district} APMC",
                    "price_per_quintal": final_price * 100,
                    "price_per_kg": final_price,
                    "arrival_mt": round(random.uniform(50, 500), 2)
                })

    output_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'dataset', 'mock_historical_prices.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4)
        
    print(f"Generated {len(records)} records for {days} days. Saved to {output_path}")

if __name__ == "__main__":
    generate_data(730)
