from pathlib import Path
from collections import Counter
import csv

path = Path(__file__).resolve().parents[1] / 'data' / 'civicsense_large_dataset.csv'
category = Counter(); status = Counter(); severity = Counter(); rows = 0
with path.open(encoding='utf-8', newline='') as f:
    for row in csv.DictReader(f):
        rows += 1
        category[row['category']] += 1
        status[row['status']] += 1
        severity[row['severity']] += 1
print('Rows:', f'{rows:,}')
print('Top categories:', category.most_common())
print('Status:', status)
print('Severity:', severity)
