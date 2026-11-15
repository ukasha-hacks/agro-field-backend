"""Extract four HWSD v2.0 sample-point estimates from the FAO-linked downloads.

Preparation dependency: access-parser==0.0.6. Not imported by the API.
"""
import csv
import hashlib
import json
import math
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/Field_Shift_Relevant_Data'
OUTPUT = DATA / 'supplemental'
BASE = 'https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/'
SOURCE = 'https://www.fao.org/land-water/resources/tools/databases/hwsd/en'


def save_estimates(points, layers, cache):
    estimates, selected = {}, []
    for point in points:
        unit = point['mapping_unit_id']
        topsoil = [r for r in layers if r['HWSD2_SMU_ID'] == unit and r['TOPDEP'] == 0 and r['BOTDEP'] == 20]
        # Choose the largest mapped component, not an arithmetic average of pH values.
        row = sorted(topsoil, key=lambda r: (-r['SHARE'], r['SEQUENCE']))[0]
        ph = row['PH_WATER']
        if ph is None or not 0 <= ph <= 14:
            raise ValueError(f'No valid topsoil pH for {point["sample_id"]}')
        estimates[point['sample_id']] = dict(ph=round(ph, 2), depth_cm=[0, 20], mapping_unit_id=unit,
            latitude=float(point['latitude']), longitude=float(point['longitude']),
            component_share_percent=row['SHARE'], source_url=SOURCE, resolution='30 arc-seconds, approximately 1 km',
            method='HWSD v2.0 dominant soil-map component, topsoil pH in water; sample-area estimate, not a farm measurement')
        selected.append(dict(point=point, database_row=row))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'soil_points.json').write_text(json.dumps(estimates, indent=2, allow_nan=False) + '\n')
    (OUTPUT / 'soil_selected_rows.json').write_text(json.dumps(selected, indent=2, allow_nan=False) + '\n')
    files = [dict(url=BASE + name, sha256=hashlib.sha256((cache / name).read_bytes()).hexdigest())
             for name in ['HWSD2_DB.zip', 'HWSD2_RASTER.zip']]
    manifest = dict(retrieved_at_utc=datetime.now(timezone.utc).isoformat(), source_url=SOURCE,
        allowed_resource='FAO GAEZ', version='HWSD v2.0 download linked by FAO', sources=files,
        selection='Raster cell containing each existing sample point; layer 0-20 cm; highest SHARE, then lowest SEQUENCE for ties.',
        limitations='A dominant mapped component may occupy less than half a mapping unit. Estimates are not field measurements. No farm pH or soil treatment is inferred.')
    (OUTPUT / 'soil_download_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print({key: value['ph'] for key, value in estimates.items()})


def download(cache=None):
    from access_parser import AccessParser
    cache = cache or ROOT / 'data/.download-cache'
    cache.mkdir(parents=True, exist_ok=True)
    for name in ['HWSD2_DB.zip', 'HWSD2_RASTER.zip']:
        if not (cache / name).exists():
            urlretrieve(BASE + name, cache / name)
    points = list(csv.DictReader((DATA / 'inputs/maps/sample_locations.csv').open()))
    with zipfile.ZipFile(cache / 'HWSD2_RASTER.zip') as archive:
        with archive.open('HWSD2.bil') as raster:
            for point in sorted(points, key=lambda p: -float(p['latitude'])):
                row = math.floor((90 - float(point['latitude'])) * 120)
                col = math.floor((float(point['longitude']) + 180) * 120)
                raster.seek((row * 43200 + col) * 2)
                point['mapping_unit_id'] = struct.unpack('<H', raster.read(2))[0]
    with zipfile.ZipFile(cache / 'HWSD2_DB.zip') as archive:
        archive.extract('HWSD2.mdb', cache)
    data = AccessParser(str(cache / 'HWSD2.mdb')).parse_table('HWSD2_LAYERS')
    units = {p['mapping_unit_id'] for p in points}
    keys = list(data)
    layers = [dict(zip(keys, values)) for values in zip(*data.values())
              if dict(zip(keys, values))['HWSD2_SMU_ID'] in units]
    save_estimates(points, layers, cache)


if __name__ == '__main__':
    download()
