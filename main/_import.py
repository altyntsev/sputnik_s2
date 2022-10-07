import sys
import os
import re
import time
import glob
import math
import json
from datetime import datetime, timedelta
from pprint import pprint
import numpy as np
from osgeo import gdal, ogr, osr
from typing import List, Dict, Any, Optional, Tuple, Literal
from collections import defaultdict

from alt_proc.dict_ import dict_
import alt_proc.time
import alt_proc.cfg
import alt_proc.file
import alt_proc.pg
import alt_proc.os_
from alt_proc.types import Strict

import gis.geom
import gis.tif

import sputnik.db
import sputnik.utils

MAIN_DIR = os.path.dirname(__file__) + '/'

