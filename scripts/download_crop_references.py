"""Download GAEZ-linked FAO crop sheets once; the application reads the saved JSON."""
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/Field_Shift_Relevant_Data/supplemental'
CROPS = [
    ('coffee_arabica', 'Coffee — Arabica', 'Coffea arabica', 749),
    ('coffee_robusta', 'Coffee — Robusta', 'Coffea canephora', 750),
    ('banana', 'Banana — Musa acuminata', 'Musa acuminata', 7848),
    ('sugarcane', 'Sugarcane', 'Saccharum officinarum', 1884),
    ('vanilla', 'Vanilla', 'Vanilla planifolia', 2131),
    ('cotton', 'Cotton', 'Gossypium hirsutum', 1160),
]


def download():
    raw_dir = OUTPUT / 'fao_crop_sheets'
    raw_dir.mkdir(parents=True, exist_ok=True)
    crops, sources = [], []
    for crop_id, name, scientific_name, code in CROPS:
        url = f'https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id={code}'
        with urlopen(url, timeout=45) as response:
            raw = response.read(1_000_000)
        if scientific_name.encode() not in raw:
            raise ValueError(f'Unexpected species sheet: {url}')
        path = raw_dir / f'{code}.html'
        path.write_bytes(raw)
        tables = pd.read_html(io.BytesIO(raw))
        ecology, cultivation = tables[1], tables[3]
        crop = dict(crop_id=crop_id, crop_name=name, scientific_name=scientific_name, ecocrop_id=code)
        for label, prefix in [('Temperat. requir.', 'temperature_c'), ('Rainfall (annual)', 'annual_rainfall_mm'), ('Soil PH', 'soil_ph')]:
            row = ecology[ecology.iloc[:, 0].astype(str) == label].iloc[0]
            for index, suffix in enumerate(['optimal_min', 'optimal_max', 'absolute_min', 'absolute_max'], 1):
                crop[f'{prefix}_{suffix}'] = float(row.iloc[index])
        cycle = cultivation[cultivation.iloc[:, 2].astype(str) == 'Crop cycle'].iloc[0]
        crop['crop_cycle_days_min'], crop['crop_cycle_days_max'] = int(cycle.iloc[3]), int(cycle.iloc[4])
        for label, prefix in [('Soil texture', 'soil_texture'), ('Soil drainage', 'soil_drainage')]:
            row = ecology[ecology.iloc[:, 5].astype(str) == label].iloc[0]
            crop[f'{prefix}_optimal'], crop[f'{prefix}_absolute'] = str(row.iloc[6]), str(row.iloc[7])
        description = tables[0]
        span = str(description[description.iloc[:, 0].astype(str) == 'Life span'].iloc[0, 1])
        span_source = url
        if span == 'nan':
            span_source = f'https://ecocrop.apps.fao.org/ecocrop/srv/en/cropView?id={code}'
            with urlopen(span_source, timeout=45) as response:
                view_raw = response.read(1_000_000)
            if b'perennial' not in view_raw.lower():
                raise ValueError(f'Life span is unavailable: {span_source}')
            view_path = raw_dir / f'{code}_crop_view.html'
            view_path.write_bytes(view_raw)
            sources.append(dict(url=span_source, local_file=str(view_path.relative_to(OUTPUT)), sha256=hashlib.sha256(view_raw).hexdigest()))
            span = 'perennial'
        if span not in {'perennial', 'annual, perennial'}:
            raise ValueError(f'Unexpected life span: {span}')
        crop.update(source_resource='FAO GAEZ / ECOCROP', source_url=url, local_variety_validated=False,
                    life_span=span.replace(', ', '_or_'), life_span_source_url=span_source,
                    rotation_candidate='annual' in span)
        crops.append(crop)
        sources.append(dict(url=url, local_file=str(path.relative_to(OUTPUT)), sha256=hashlib.sha256(raw).hexdigest()))
    (OUTPUT / 'crops.json').write_text(json.dumps(crops, indent=2, allow_nan=False) + '\n')
    manifest = dict(retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                    allowed_resource='FAO GAEZ', catalogue_url='https://gaez.fao.org/pages/ecocrop-find-plant',
                    integration_reference='https://www.fao.org/land-water/resources/tools/databases/ecocrop/en', sources=sources,
                    limitations='Species references only. Perennials are not generated as seasonal replacement crops. Banana reference is Musa acuminata, not all banana varieties.')
    (OUTPUT / 'crop_download_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Saved {len(crops)} crop references and their original FAO sheets.')


if __name__ == '__main__':
    download()
