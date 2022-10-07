from _init import script
from _import import *
import s2_lib
import sputnik.s3
import sputnik.db

class Params(Strict):
    project_id: int

script.start()
params = Params(**script.params)
cfg = alt_proc.cfg.read(MAIN_DIR + '_cfg/_main.cfg')
sputnik_cfg = alt_proc.cfg.read_global('sputnik')
s3 = sputnik.s3.S3()
db = sputnik.db.connect_db()
sql = """
    select *, st_astext(border) as border_wkt 
    from sputnik.projects where project_id=%s
    """
project = db.sql(sql, params.project_id, return_one=True)

mgrses = s2_lib.border_to_mgrs(project.border_wkt)
# alt_proc.file.pkl_save('mgrses.pkl', mgrses)
# mgrses = alt_proc.file.pkl_load('mgrses.pkl')

year0 = int(project.start_date[:4])
year1 = int(project.end_date[:4])
month0 = int(project.start_date[5:7])
month1 = int(project.end_date[5:7])
date0 = project.start_date.replace('-', '')
date1 = project.end_date.replace('-', '')
n_found = 0
project_border = gis.geom.Geom(wkt=project.border_wkt)
for mgrs in mgrses:
    for year in range(year0, year1+1):
        for month in range(1,12):
            if year == year0 and month < month0:
                continue
            if year == year1 and month > month1:
                continue
            url = cfg.l2a_url.format(mgrs=f'{mgrs[0:2]}/{mgrs[2]}/{mgrs[3:]}', year=year, month=month)
            scene_dirs = s3.list(url)
            for scene_dir in scene_dirs:
                scene_id = alt_proc.file.dir_name(scene_dir)
                # S2B_6RXT_20210727_0_L2A
                date = scene_id.split('_')[2]
                if date < date0 or date > date1:
                    continue
                scene = s2_lib.Scene(params.project_id, scene_id)
                if scene.doc:
                    continue
                meta = scene.get_meta()
                border = gis.geom.Geom(geojson=meta.border_gj)
                if not border.intersects(project_border):
                    continue
                n_found += 1
                scene.new(meta)
                scene.ql()

print(f'Found {n_found} new scenes')

script.exit()


