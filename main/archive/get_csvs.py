import alt_path
from _import import *
import requests

csv_url = 'https://scihub.copernicus.eu/catalogueview'
sats = ['S2A', 'S2B']
dest_dir = '/alt_proc/storage/copernicus_csv/'

def parse_html(url):
    res = requests.get(url)
    if not res.ok:
        raise Exception(f'Request failed: {url}')
    links = re.findall(r'<img src="/icons/(folder|text).gif" .+></td><td><a href="(.+)">.+</a>', res.text)
    links = [link[1].strip('/') for link in links]
    return links

def parse_csv(url):
    res = requests.get(url)
    if not res.ok:
        raise Exception(f'Request failed: {url}')
    for line in res.text.split('\n')[1:]:
        if not line.strip():
            continue
        product_id, filename = line.split(',')[:2]
        if '_MSIL1C_' not in filename:
            continue

        mgrs = filename[39:39+5]
        scenes[mgrs].append((product_id, filename))

for sat in sats:
    years = parse_html(f'{csv_url}/{sat}/')
    for year in years:
        monthes = parse_html(f'{csv_url}/{sat}/{year}/')
        for month in monthes:
            pkl_file = f'{dest_dir}{sat}/{year}/{month}.pkl'
            if os.path.exists(pkl_file):
                continue
            print(f'{sat}/{year}/{month}')
            scenes = defaultdict(list)
            alt_proc.file.mkdir(f'{dest_dir}{sat}/{year}/')
            csvs = parse_html(f'{csv_url}/{sat}/{year}/{month}/')
            for csv in csvs:
                parse_csv(f'{csv_url}/{sat}/{year}/{month}/{csv}')
            alt_proc.file.pkl_save(pkl_file, scenes)


stop