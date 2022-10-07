from _init import script
from _import import *
import s2_lib

class Params(Strict):
    project_id: int

script.start()
params = Params(**script.params)
cfg = alt_proc.cfg.read(MAIN_DIR + '_cfg/_main.cfg')
sputnik_cfg = alt_proc.cfg.read_global('sputnik')
db = sputnik.db.connect_db()
sql = """
    select *, st_astext(border) as border_wkt 
    from sputnik.projects where project_id=%s
    """
project = db.sql(sql, params.project_id, return_one=True)

mgrses = s2_lib.border_to_mgrs(project.border_wkt)

year0 = int(project.start_date[:4])
year1 = int(project.end_date[:4])
date0 = project.start_date.replace('-', '')
date1 = project.end_date.replace('-', '')
n_found = 0
for sat in ['S2A', 'S2B']:
    for year in range(year0, year1+1):
        for month in range(1,12):
            pkl_file = f'{sputnik_cfg.storage_dir}{cfg.csv_dir}{sat}/{year}/{month:02d}.pkl'
            if not os.path.exists(pkl_file):
                continue
            scenes_by_mgrs = alt_proc.file.pkl_load(pkl_file)
            for mgrs in mgrses:
                for product_id, filename in scenes_by_mgrs[mgrs]:
                    date = filename[11:19]
                    if date < date0 or date > date1:
                        continue
                    meta = s2_lib.parse_filename(filename)
                    scene = s2_lib.Scene(params.project_id, meta.scene_id)
                    scene.new(meta)
                    stop

            stop


stop

script.exit()


