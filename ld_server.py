from flask import Flask, jsonify, request, abort
from flask_compress import Compress
from collections import defaultdict
import imp, logging, subprocess, shlex, re, sys, time, gzip, pysam, threading
from subprocess import CalledProcessError

app = Flask(__name__)
Compress(app)

config = {}
try:
    _conf_module = imp.load_source('config', 'config.py')
except Exception as e:
    print('Could not load config.py')
    raise
for key in dir(_conf_module):
    if not key.startswith('_'):
        config[key] = getattr(_conf_module, key)
print(config)

gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(config['log_level'])

cpra_re = re.compile('-|:|_')
pos_tabix = {panel: defaultdict(lambda: pysam.TabixFile(config['panels'][panel]['position_mapping'], parser=None)) for panel in config['panels'].keys()}

class RequestException(Exception):
    pass

def get_params():
    """
    Parses query parameters: variant, window, panel, r2_thresh (optional)
    Returns a dict with cpra (list int,int,str,str), window (int), panel (str)
    Raises if bad parameters
    """
    variant = request.args.get('variant')
    window = request.args.get('window')
    panel = request.args.get('panel')
    r2_thresh = request.args.get('r2_thresh')
    if r2_thresh is None:
        r2_thresh = 0
    if variant is None or window is None or panel is None:
        raise RequestException({'status': 400, 'message': 'required query parameters: variant, window, panel'})
    try:
        r2_thresh = float(r2_thresh)
        if r2_thresh < 0 or r2_thresh > 1:
            raise ValueError()
    except ValueError as e:
        raise RequestException({'status': 400, 'message': 'r2_thresh must be between 0 and 1'})
    cpra = re.split(cpra_re, variant)
    if len(cpra) != 4:
        raise RequestException({'status': 400, 'message': 'variant must be given as chr:pos:ref:alt'})
    try:
        cpra[0] = int(cpra[0].lower().replace('chr', '').replace('x', '23'))
        cpra[1] = int(cpra[1])
        cpra[2] = cpra[2].upper()
        cpra[3] = cpra[3].upper()
        window = int(window)
    except ValueError as e:
        raise RequestException({'status': 400, 'message': 'chromosome, variant and window must be integers'}) from e
    if cpra[0] < 1 or cpra[0] > 23:
        raise RequestException({'status': 400, 'message': 'chromosome must be between 1 and 23'})
    if window < config['window']['min'] or window > config['window']['max']:
        raise RequestException({'status': 400, 'message': 'window must be between ' + str(config['window']['min']) + ' and ' + str(config['window']['max'])})
    if panel not in config['panels']:
        raise RequestException({'status': 400, 'message': 'supported panels: ' + ','.join(config['panels'].keys())})
    return {'cpra': cpra, 'window': window, 'panel': panel, 'r2_thresh': r2_thresh}

def get_region_mapping(cpra, panel, window):
    """
    Gets tomahawk position for the query variant and a tomahawk_position-to-variant mapping for variants in the given panel within the given window
    Returns a tuple (tomahawk chr:pos, dict from tomahawk chr:pos to chr:pos:ref:alt)
    Raises if variant not found
    """
    twk2cpra = {} # mapping from tomahawk positions chr:pos to actual variants chr:pos:ref:alt
    twk = None # tomahawk position of query variant
    s = cpra.split(':')
    tabix_iter = pos_tabix[panel][threading.get_ident()].fetch(s[0], max(1,int(s[1])-round(window/2)-1), int(s[1])+round(window/2), parser=None)
    for row in tabix_iter:
        s = row.split('\t')
        if s[2] == cpra:
            twk = s[3]
        twk2cpra[s[3]] = s[2]
    if twk is None:
        raise RequestException({'status': 404, 'message': 'variant not found: ' + cpra})
    return (twk, twk2cpra)

def get_tempfile():
    """
    Creates a .two temp file. Raises if cannot create file
    Returns temp file path
    Raises if cannot create file
    """
    try:
        tempfile = subprocess.check_output(shlex.split('mktemp --suffix .two -p ' + config['tempdir'])).decode(sys.stdout.encoding).strip()
    except CalledProcessError:
        app.logger.error('could not create temp file! ' + tempfile + ' return code: ' + str(cpe.returncode) + ', output: ' + cpe.output.decode(sys.stdout.encoding))
        raise RequestException({'status': 500, 'message': ''})
    return tempfile

def compute_ld(cmd, twofile):
    """
    Calls tomahawk to compute LD with the given command writing to the given .two file
    Returns tomahawk log
    Raises if command fails (position not found / no output (typically too small window) / other)
    """
    try:
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT).decode(sys.stdout.encoding).strip()
    except CalledProcessError as cpe:
        if 'no blocks overlapping the provided range' in cpe.output.decode(sys.stdout.encoding) or 'no data found for reference' in cpe.output.decode(sys.stdout.encoding):
            app.logger.error('position not found, this shouldn\'t happen')
            subprocess.call(['rm', twofile])
            raise RequestException({'status': 404, 'message': 'position not found'})
        elif 'no surrounding variants' in cpe.output.decode(sys.stdout.encoding):
            app.logger.warning('no surrounding variants')
            subprocess.call(['rm', twofile])
            raise RequestException({'status': 400, 'message': 'no output from tomahawk, try a bigger window size'})
        else:
            app.logger.error('tomahawk scalc failed! return code: ' + str(cpe.returncode) + ', output: ' + cpe.output.decode(sys.stdout.encoding))
            subprocess.call(['rm', twofile])
            raise RequestException({'status': 500, 'message': 'tomahawk scalc failed'})
    return out

def view_ld(cmd, twofile):
    """
    Calls tomahawk view with the given command to get LD output from the given .two file
    Returns tomahawk view output
    Raises if command fails
    """
    try:
        out = subprocess.check_output(shlex.split(cmd)).decode(sys.stdout.encoding).strip()
    except CalledProcessError as cpe:
        app.logger.error('tomahawk view failed! return code: ' + str(cpe.returncode) + ', output: ' + cpe.output.decode(sys.stdout.encoding))
        raise RequestException({'status': 500, 'message': 'tomahawk view failed'})
    finally:
        subprocess.call(['rm', twofile])
    return out

def parse_ld(data, cpra, r2_thresh, twk2cpra):
    """
    Parses the given tomahawk LD output using the given query variant and tomahawk_position-to-variant mapping
    Returns a list of dicts with keys variation1,variation2,r2,d_prime where variation1 is the query variant
    """
    data_iter = iter(data.split('\n'))
    for line in data_iter:
        if not line.startswith('#') and line != '':
            break
    hdr = {h:i for i,h in enumerate(line.strip().split('\t'))}
    res = []
    used = {}
    for line in data_iter:
        s = line.strip().split('\t')
        if float(s[hdr['R2']]) < r2_thresh:
            continue
        var1 = s[hdr['ridA']] + ':' + s[hdr['posA']]
        var2 = s[hdr['ridB']] + ':' + s[hdr['posB']]
        if var1 not in twk2cpra:
            app.logger.warning(var1 + ' tomahawk position not in given mapping, this should not happen. Ignoring')
        elif var2 not in twk2cpra:
            app.logger.warning(var2 + ' tomahawk position not in given mapping, this should not happen. Ignoring')
        else:
            var1 = twk2cpra[var1]
            var2 = twk2cpra[var2]
            if var2 == cpra:
                temp = var1
                var1 = var2
                var2 = temp
            if var1 == cpra and var2 not in used:
                res.append({'variation1': var1, 'variation2': var2, 'r2': round(float(s[hdr['R2']]), config['num_decimals']), 'd_prime': round(float(s[hdr['Dprime']]), config['num_decimals'])})
                used[var2] = True
    return res

@app.route('/')
def index():
    return jsonify({})

@app.route('/api/ld')
def ld():
    """
    API endpoint for getting LD between a query variant and variants within a base pair window
    Returns a JSON object with ld,time_tabix,time_ld,time_view,time_total
    Aborts the request in case of bad query parameters or errors
    """
    t_total = time.time()
    try:
        params = get_params()
    except RequestException as e:
        abort(e.args[0]['status'], e.args[0]['message'])
    cpra = params['cpra']
    panel = params['panel']
    filename = config['panels'][panel]['file_template'].replace('[CHROMOSOME]', str(cpra[0]).replace('23', config['panels'][panel]['X_in_filename']))
    cpra_str = ':'.join([str(f) for f in cpra])
    t = time.time()
    try:
        mapping = get_region_mapping(cpra_str, panel, params['window'])
    except RequestException as e:
        abort(e.args[0]['status'], e.args[0]['message'])
    t = round(time.time()-t, 3)
    app.logger.info('{} seconds tabix'.format(t))
    result = {}
    result['time_tabix'] = t
    twkcp = mapping[0].split(':')
    try:
        tempfile = get_tempfile()
    except RequestException as e:
        abort(e.args[0]['status'], e.args[0]['message'])
    cmd_scalc = 'tomahawk scalc -i ' + filename + ' -o ' + tempfile + ' -I ' + twkcp[0] + ':' + str(int(twkcp[1])-1) + '-' + twkcp[1] + ' -w ' + str(round(params['window']/2))
    app.logger.info(cmd_scalc)
    t = time.time()
    try:
        out = compute_ld(cmd_scalc, tempfile)
    except RequestException as e:
        abort(e.args[0]['status'], e.args[0]['message'])
    t = round(time.time()-t, 3)
    app.logger.info('{} seconds computing ld'.format(t))
    result['time_ld'] = t
    #result['log'] = out
    cmd_view = 'tomahawk view -i ' + tempfile
    app.logger.info(cmd_view)
    t = time.time()
    try:
        out = view_ld(cmd_view, tempfile)
    except RequestException as e:
        abort(e.args[0]['status'], e.args[0]['message'])
    result['ld'] = parse_ld(out, cpra_str, params['r2_thresh'], mapping[1])
    t = round(time.time()-t, 3)
    app.logger.info('{} seconds viewing and parsing ld'.format(t))
    result['time_view'] = t
    result['time_total'] = round(time.time()-t_total, 3)
    return jsonify(result)
