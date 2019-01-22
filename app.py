from flask import Flask, Response, request, abort, send_from_directory, render_template
from PIL import Image
from io import BytesIO
import os
import traceback
import json
import re


app = Flask(__name__)
WIDTH = 500
HEIGHT = 400
COL_NUM = 2

try:
    with open('./config.json', 'r') as f:
        config = json.load(f)
        root_dir = {key: os.path.abspath(val) for key, val in config['base_dirs'].items()}
except (FileNotFoundError, OSError):
    root_dir = {'default': os.path.abspath('./static')}


@app.route('/img/<base>/<path:filename>')
def image(base, filename):
    base_dir = root_dir[base]
    try:
        w = int(request.args['w'])
        h = int(request.args['h'])
    except (KeyError, ValueError):
        return send_from_directory(base_dir, filename)

    try:
        im = Image.open(os.path.join(base_dir, filename))
        im.thumbnail((w, h), Image.ANTIALIAS)
        im = im.convert('RGB')
        io = BytesIO()

        im.save(io, format='JPEG')
        return Response(io.getvalue(), mimetype='image/jpeg')

    except IOError:
        traceback.print_exc()
        abort(404)

    return send_from_directory(base_dir, filename)


@app.route('/')
def home():
    folders = []
    for name, path in root_dir.items():
        folders.append({
            'name': name,
            'path': '/'.join(['dir', name])
        })
    return render_template('base.html', **{
        'folders': folders
    })


@app.route('/dir/<base>/', methods=['POST', 'GET'])
@app.route('/dir/<base>/<path:subdir>/', methods=['POST', 'GET'])
def index(base, subdir=None):
    images = []

    if base not in root_dir:
        abort(404)

    if subdir is None:
        base_dir = root_dir[base]
    else:
        base_dir = os.path.join(root_dir[base], subdir)
    files = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]
    if 'filter' in request.args:
        regexp = request.args['filter']
        files = [f for f in files if re.search(regexp, f.split(os.sep)[-1]) is not None]

    files = sorted(files)

    folders = []
    dirs = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    if subdir is not None:
        folders.append({
            'name': '..',
            'path': '..'
        })
    dirs = sorted(dirs)
    for d in dirs:
        if os.path.isdir(d):
            folders.append({
                'name': d.split(os.sep)[-1],
                'path': '/' + '/'.join(['dir', base, os.path.relpath(d, root_dir[base])])
            })

    for filename in files:
        if not filename.endswith('.jpg') and not filename.endswith('.png'):
            continue
        im = Image.open(filename)
        w, h = im.size
        aspect = 1.0 * w / h
        if aspect > 1.0 * WIDTH / HEIGHT:
            width = min(w, WIDTH)
            height = width / aspect
        else:
            height = min(h, HEIGHT)
            width = height * aspect
        images.append({
            'width': int(width),
            'height': int(height),
            'name': filename.split(os.sep)[-1],
            'src': '/' + '/'.join(['img', base, os.path.relpath(filename, root_dir[base])])
        })

    images = reshape_list(images, COL_NUM)

    return render_template('main.html', **{
        'images': images,
        'cols': COL_NUM,
        'folders': folders
    })


def reshape_list(ori, row_len=2):
    cols = [[] for _ in range(len(ori) // row_len + int(len(ori) % row_len > 0))]
    row_idx = 0
    for idx, ele in enumerate(ori):
        cols[row_idx].append(ele)
        row_idx += int(idx % row_len == row_len - 1)
    return cols


if __name__ == '__main__':
    app.run(host='0.0.0.0')
