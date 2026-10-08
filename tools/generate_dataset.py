from pathlib import Path
from datetime import datetime, timedelta
import csv, json, math, random, uuid

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / 'civicsense_large_dataset.csv'
SUMMARY_PATH = DATA_DIR / 'dataset_summary.json'

random.seed(20261007)

categories = {
    'Pothole': ('Road Maintenance Department', ['deep pothole', 'broken road surface', 'multiple road cracks', 'dangerous road cavity']),
    'Garbage': ('Solid Waste Department', ['overflowing waste bin', 'uncollected garbage pile', 'mixed waste on roadside', 'garbage near public area']),
    'Drainage': ('Drainage & Sewerage Department', ['blocked storm drain', 'sewage overflow', 'waterlogging near drain', 'damaged drainage cover']),
    'Street Light': ('Electrical Department', ['street light not working', 'flickering pole light', 'damaged lamp pole', 'dark road stretch']),
    'Water Leakage': ('Water Supply Department', ['pipeline leakage', 'water flowing from broken pipe', 'leaking public connection', 'road flooding from water line']),
    'Illegal Dumping': ('Solid Waste Department', ['construction debris dumped', 'bulk waste dumped illegally', 'waste dumped beside road', 'debris near open plot']),
    'Damaged Footpath': ('Public Works Department', ['broken footpath tiles', 'unsafe pedestrian path', 'footpath obstruction', 'damaged curb and pavement']),
    'Other': ('General Civic Department', ['damaged public asset', 'unsafe roadside obstruction', 'public infrastructure issue', 'civic maintenance problem']),
}
statuses = ['Reported', 'Assigned', 'In Progress', 'Resolved']
status_weights = [0.18, 0.14, 0.23, 0.45]
severities = ['Low', 'Medium', 'High', 'Critical']
severity_weights = [0.18, 0.49, 0.26, 0.07]
wards = [
    ('Akurdi', 18.6514, 73.7784), ('Nigdi', 18.6510, 73.7691), ('Ravet', 18.6518, 73.7350),
    ('Pimpri', 18.6298, 73.7997), ('Chinchwad', 18.6279, 73.8009), ('Bhosari', 18.6291, 73.8500),
    ('Wakad', 18.5975, 73.7898), ('Hinjawadi', 18.5913, 73.7389), ('Baner', 18.5590, 73.7868),
    ('Aundh', 18.5590, 73.8070), ('Shivajinagar', 18.5308, 73.8475), ('Kothrud', 18.5074, 73.8077),
    ('Hadapsar', 18.5089, 73.9259), ('Viman Nagar', 18.5679, 73.9143), ('Kharadi', 18.5515, 73.9348),
]
road_types = ['arterial road', 'residential street', 'market road', 'service lane', 'school zone', 'industrial road', 'bus corridor']
weather = ['Clear', 'Cloudy', 'Light Rain', 'Heavy Rain', 'Post-Rain', 'Hot/Dry']
sources = ['Citizen Web', 'AR Camera', 'Municipal Patrol', 'Community Volunteer']
landmarks = ['main junction', 'bus stop', 'school gate', 'market entrance', 'society entrance', 'hospital road', 'bridge approach', 'park boundary', 'temple road', 'metro access road']
notes = [
    'Requires site inspection and geo-verification before work order.',
    'Citizen image and location coordinates validated by portal workflow.',
    'Issue may affect pedestrian or vehicle safety during peak hours.',
    'Nearby civic assets should be checked during the same field visit.',
    'Priority can increase if repeated reports appear in the same cluster.',
    'Recommended for ward engineer review and closure evidence after repair.',
]

TARGET_ROWS = 82000
start = datetime(2025, 1, 1, 6, 0, 0)
now = datetime(2026, 10, 7, 20, 0, 0)
seconds_range = int((now - start).total_seconds())

fields = [
    'record_id','complaint_code','ward','category','description','latitude','longitude','location_label',
    'severity','status','department','reported_at','updated_at','resolution_hours','source','duplicate_group',
    'image_tag','validation_score','citizen_sentiment','crew_size','estimated_cost_inr','model_label','model_confidence',
    'weather','road_type','asset_id','field_note'
]

status_count = {s: 0 for s in statuses}
category_count = {c: 0 for c in categories}
severity_count = {s: 0 for s in severities}
ward_count = {w[0]: 0 for w in wards}
resolved_hours_sum = 0.0
resolved_count = 0

with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for i in range(1, TARGET_ROWS + 1):
        ward_name, base_lat, base_lon = random.choice(wards)
        category = random.choice(list(categories))
        department, phrases = categories[category]
        severity = random.choices(severities, severity_weights, k=1)[0]
        status = random.choices(statuses, status_weights, k=1)[0]
        reported = start + timedelta(seconds=random.randint(0, seconds_range))
        if status == 'Resolved':
            resolution_hours = round(max(1.0, random.lognormvariate(3.35, 0.75)), 1)
            updated = min(reported + timedelta(hours=resolution_hours), now)
            resolved_hours_sum += resolution_hours
            resolved_count += 1
        else:
            resolution_hours = ''
            updated = min(reported + timedelta(hours=random.uniform(0.5, 150)), now)
        lat = base_lat + random.uniform(-0.012, 0.012)
        lon = base_lon + random.uniform(-0.014, 0.014)
        phrase = random.choice(phrases)
        landmark = random.choice(landmarks)
        road_type = random.choice(road_types)
        description = (
            f"{phrase.capitalize()} observed near {landmark} on a {road_type}. "
            f"Citizen reports obstruction/safety impact and requests municipal inspection. "
            f"Reference {uuid.uuid4().hex[:12]} captured for synthetic training and dashboard analytics."
        )
        validation = round(random.uniform(0.72, 0.999), 3)
        confidence = round(random.uniform(0.68, 0.995), 3)
        sentiment = random.choice(['Concerned', 'Urgent', 'Neutral', 'Frustrated'])
        crew = random.randint(1, 8) if status in ('Assigned', 'In Progress', 'Resolved') else 0
        cost_base = {'Low': 1200, 'Medium': 4500, 'High': 15000, 'Critical': 45000}[severity]
        cost = int(cost_base * random.uniform(0.65, 2.4))
        dup_group = f"DG-{random.randint(1, 18000):05d}" if random.random() < 0.23 else ''
        asset_id = f"AST-{ward_name[:3].upper()}-{random.randint(1000,9999)}"
        row = {
            'record_id': i,
            'complaint_code': f"CS-{reported:%y%m}-{i:07d}",
            'ward': ward_name,
            'category': category,
            'description': description,
            'latitude': f"{lat:.7f}",
            'longitude': f"{lon:.7f}",
            'location_label': f"Near {landmark}, {ward_name}, Pune metropolitan region",
            'severity': severity,
            'status': status,
            'department': department,
            'reported_at': reported.isoformat(timespec='seconds'),
            'updated_at': updated.isoformat(timespec='seconds'),
            'resolution_hours': resolution_hours,
            'source': random.choice(sources),
            'duplicate_group': dup_group,
            'image_tag': f"synthetic/{category.lower().replace(' ','_')}/{i % 5000:04d}.jpg",
            'validation_score': validation,
            'citizen_sentiment': sentiment,
            'crew_size': crew,
            'estimated_cost_inr': cost,
            'model_label': category,
            'model_confidence': confidence,
            'weather': random.choice(weather),
            'road_type': road_type,
            'asset_id': asset_id,
            'field_note': random.choice(notes),
        }
        writer.writerow(row)
        status_count[status] += 1
        category_count[category] += 1
        severity_count[severity] += 1
        ward_count[ward_name] += 1

summary = {
    'name': 'CivicSense Synthetic Civic Issue Dataset',
    'version': '1.0',
    'generated_for': 'CivicSense Advanced Prototype',
    'row_count': TARGET_ROWS,
    'column_count': len(fields),
    'file_name': CSV_PATH.name,
    'file_size_bytes': CSV_PATH.stat().st_size,
    'status_counts': status_count,
    'category_counts': category_count,
    'severity_counts': severity_count,
    'ward_counts': ward_count,
    'average_resolution_hours': round(resolved_hours_sum / resolved_count, 1) if resolved_count else 0,
    'geography_note': 'Synthetic coordinates are generated around Pune and Pimpri-Chinchwad demo zones; not real citizen records.',
    'privacy_note': '100% synthetic demonstration/training data. No real names, emails, phone numbers, or complaint records are included.',
}
SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(f'Generated {TARGET_ROWS:,} rows')
print(f'CSV size: {CSV_PATH.stat().st_size / (1024*1024):.2f} MB')
