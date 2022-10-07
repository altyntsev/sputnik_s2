import _init
from _import import *
import untangle
import sputnik.s3


class FilenameMeta(Strict):
    scene_id: str
    sat: str
    date: str
    time: str
    mgrs: str
    level: Literal['L2A', 'L1C']


def parse_filename(filename) -> FilenameMeta:
    tpl = '(S2.)_MSI(...)_(....)(..)(..)T......_N...._R..._T(.....)_........T(......)'
    m = re.match(tpl, filename)
    if not m:
        raise Exception('Wrong filename')
    sat, level, year, month, day, mgrs, time = m.groups()
    date = '-'.join((year, month, day))
    scene_id = '_'.join((sat, level, date, time, mgrs))

    return FilenameMeta(scene_id=scene_id, sat=sat, date=date, time=time, mgrs=mgrs, level=level)


def border_to_mgrs(border_wkt):
    cfg = alt_proc.cfg.read(MAIN_DIR + '_cfg/_main.cfg')
    # todo kml from storage
    kml_file = alt_proc.file.find_one('*.kml')
    if not kml_file:
        alt_proc.os_.run(f'wget {cfg.mgrs_kml_url}')
        kml_file = alt_proc.file.find_one('*.kml')

    mgrses = set()
    print('Parse kml')
    xml = untangle.parse(kml_file)
    border = gis.geom.Geom(wkt=border_wkt)
    for pm in sputnik.utils.progress(xml.kml.Document.Folder[0].Placemark):
        mgrs = pm.name.cdata
        for poly in pm.MultiGeometry.Polygon:
            coord = poly.outerBoundaryIs.LinearRing.coordinates.cdata
            points = []
            for s in coord.replace('\n', ' ').replace('\t', ' ').split(' '):
                if not s:
                    continue
                xg, yg, _ = s.split(',')
                xg, yg = float(xg), float(yg)
                points.append((xg, yg))
            mgrs_border = gis.geom.Geom(polygon=points)

            if border.intersects(mgrs_border):
                mgrses.add(mgrs)

    return sorted(list(mgrses))


class SceneDoc(Strict):
    project_id: int
    scene_id: str
    filename: str
    date: str
    border: str
    xg0: float
    xg1: float
    yg0: float
    yg1: float


class AwsMeta(Strict):
    scene_id: str
    date: str
    mgrs: str
    filename: str
    border_gj: Any
    xg0: float
    xg1: float
    yg0: float
    yg1: float

class Scene:
    db = sputnik.db.connect_db()
    s3 = sputnik.s3.S3()
    cfg = alt_proc.cfg.read(MAIN_DIR + '_cfg/_main.cfg')
    sputnik_cfg = alt_proc.cfg.read_global('sputnik')
    doc: Optional[SceneDoc]

    def __init__(self, project_id, scene_id):
        self.project_id = project_id
        self.scene_id = scene_id
        self.read_doc()
        self.storage_dir = f'{Scene.sputnik_cfg.storage_dir}projects/{project_id}/'
        alt_proc.file.mkdir(self.storage_dir)
        _, mgrs, date = self.scene_id.split('_')[:3]
        year, month = date[:4], int(date[4:6])
        month_dir = Scene.cfg.l2a_url.format(mgrs=f'{mgrs[0:2]}/{mgrs[2]}/{mgrs[3:]}', year=year, month=month)
        self.aws_dir = f'{month_dir}{self.scene_id}/'

    def read_doc(self):
        sql = '''
            select * from sputnik.meta where project_id=%s and scene_id=%s
        '''
        row = Scene.db.sql(sql, (self.project_id, self.scene_id), return_one=True)
        self.doc = SceneDoc(**row) if row else None

    def get_meta(self):
        meta_text = Scene.s3.read(f'{self.aws_dir}/{self.scene_id}.json')
        meta = json.loads(meta_text)
        border_gj = meta['geometry']
        filename = meta['properties']['sentinel:product_id']
        _, mgrs, date = self.scene_id.split('_')[:3]
        date = date[:4] + '-' + date[4:6] + '-' + date[6:8]
        xg0, yg0, xg1, yg1 = meta['bbox']

        return AwsMeta(scene_id=self.scene_id, filename=filename, border_gj=border_gj, mgrs=mgrs, date=date,
            xg0=xg0, yg0=yg0, xg1=xg1, yg1=yg1)

    def new(self, meta: AwsMeta):
        border_wkt = gis.geom.Geom(geojson=meta.border_gj).wkt()
        sql = '''
            insert into sputnik.meta 
            (project_id, scene_id, date, border, filename, xg0, xg1, yg0, yg1) 
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        Scene.db.sql(sql, (self.project_id, self.scene_id, meta.date, border_wkt, meta.filename,
                           meta.xg0, meta.xg1, meta.yg0, meta.yg1))
        self.read_doc()
        print(f'New scene: {self.scene_id}')

    def ql(self):
        Scene.s3.get(f'{self.aws_dir}L2A_PVI.tif')
        ql_dir = f'{self.storage_dir}ql/'
        alt_proc.file.mkdir(ql_dir)
        alt_proc.os_.run(os.path.dirname(sys.executable) + '/gdal_translate L2A_PVI.tif ql.jpg')
        alt_proc.file.copy('ql.jpg', f'{ql_dir}{self.scene_id}-ql.jpg')

    def get_files(self, files):
        for file in files:
            Scene.s3.get(f'{self.aws_dir}{file}')

