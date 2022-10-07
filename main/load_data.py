from _init import script
from _import import *
import s2_lib
import sputnik.s3
import sputnik.db

class Params(Strict):
    project_id: int
    scene_id: str

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

scene = s2_lib.Scene(params.project_id, params.scene_id)
scene.get_files(['TCI.tif'])
dest_dir = f'{sputnik_cfg.storage_dir}projects/{params.project_id}/rgb/'
alt_proc.file.mkdir(dest_dir)
alt_proc.file.copy('TCI.tif', f'{dest_dir}{params.scene_id}-rgb.tif')

sql = """
    insert into products 
    (project_id, product, product_id, date)
    values (%s, 'rgb', %s, %s)
    on conflict (project_id, product_id) do nothing 
    """
db.sql(sql, (params.project_id, f'{params.scene_id}-rgb', scene.doc.date))

script.exit()


