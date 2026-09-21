import json

TARGET = {'Bajra', 'Jowar', 'Soybean', 'Cotton', 'Onion', 'Rice', 'Sugarcane', 'Paddy'}

# ── Clean Mandi Prices ────────────────────────────────────────────────────────
with open('backend/dataset/cleaned_mandi_prices.json', 'r') as f:
    mandi = json.load(f)

kept_mandi = []
for r in mandi:
    if r['crop'] in TARGET:
        r2 = dict(r)
        if r2['crop'] == 'Paddy':
            r2['crop'] = 'Rice'
        kept_mandi.append(r2)

with open('backend/dataset/cleaned_mandi_prices.json', 'w') as f:
    json.dump(kept_mandi, f, indent=4)

print(f"Mandi prices: {len(kept_mandi)}/{len(mandi)} records kept")
for r in kept_mandi:
    print(f"  {r['crop']}: Rs.{r['price_per_kg']}/kg")

# ── Clean MSP Prices ──────────────────────────────────────────────────────────
with open('backend/dataset/cleaned_msp_prices.json', 'r') as f:
    msp = json.load(f)

kept_msp = []
for r in msp:
    crop = r.get('crop', '')
    if crop == 'Paddy':
        r2 = dict(r)
        r2['crop'] = 'Rice'
        kept_msp.append(r2)
    elif crop in TARGET:
        kept_msp.append(r)

# Add Sugarcane FRP (it uses FRP, not MSP)
if not any(r['crop'] == 'Sugarcane' for r in kept_msp):
    kept_msp.append({
        'crop': 'Sugarcane',
        'crop_full_name': 'Sugarcane',
        'msp_price_per_quintal': 340.0,
        'msp_price_per_kg': 3.40,
        'year': '2026-27',
        'note': 'FRP set by CCEA. Not MSP but legally enforced floor price.'
    })

# Add Onion note (no MSP)
for r in kept_msp:
    if r['crop'] == 'Onion':
        r['note'] = 'No MSP for onion. Price is market-determined at APMC.'

with open('backend/dataset/cleaned_msp_prices.json', 'w') as f:
    json.dump(kept_msp, f, indent=4)

print(f"\nMSP prices: {len(kept_msp)} crops")
for r in kept_msp:
    print(f"  {r['crop']}: Rs.{r['msp_price_per_kg']}/kg")

print("\nDone!")
