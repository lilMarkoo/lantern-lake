"""Builds, installs and publishes Lantern Lake.

    python tools\\release.py bump 1.5.1 "First note." "Second note."   set the version and its notes
    python tools\\release.py build                                    LanternLake.exe and the release files
    python tools\\release.py install ["E:\\game\\Lantern Lake"]         make or refresh your playable copy
    python tools\\release.py upload                                   publish the release on GitHub

Settings live in release.json next to main.py:
    {"github": "your-name/lantern-lake", "min_launcher": "1.0.0", "install": "E:\\\\game\\\\Lantern Lake"}
"min_launcher" is the oldest launcher that can install this version. Raise it to the launcher's
LAUNCHER_VERSION only when an update needs the new launcher; players then get the full download instead.

Upload reads a GitHub token from the GITHUB_TOKEN environment variable (a fine-grained token with
"Contents: read and write" on the repository). The repository must be public so the launcher can see releases.
"""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAUNCHER = os.path.join(ROOT, 'launcher')
BUILD = os.path.join(ROOT, 'build')
PACKAGE = os.path.join(BUILD, 'LanternLake')
RELEASES = os.path.join(ROOT, 'release')
CONFIG = os.path.join(ROOT, 'release.json')
UA = 'LanternLakeRelease/1.0'

# standard library modules a future game update might reach for; the launcher carries them so a plain game
# update keeps working without a new launcher
STDLIB = '''json math random os sys time threading queue socket ctypes ctypes.wintypes struct collections
itertools functools array colorsys wave io copy heapq bisect string textwrap datetime calendar re zlib hashlib
base64 select selectors uuid pickle typing dataclasses enum statistics fractions decimal pathlib glob fnmatch
tempfile shutil traceback platform locale unicodedata operator contextlib weakref gzip csv http.client
urllib.request urllib.parse winreg runpy webbrowser secrets hmac binascii codecs difflib pprint abc numbers
signal errno stat atexit warnings inspect types'''.split()
EXTRA = ['numpy', 'pygame', 'pygame._sdl2', 'pygame._sdl2.controller', 'pygame._sdl2.audio', 'pygame.sndarray',
         'pygame.surfarray', 'pygame.mixer', 'pygame.font', 'pygame.sysfont']


def load_config():
    cfg = {}
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding='utf-8') as f:
            cfg = json.load(f)
    cfg.setdefault('github', '')
    cfg.setdefault('min_launcher', '1.0.0')
    cfg.setdefault('install', os.path.join(os.path.dirname(ROOT), 'Lantern Lake'))
    return cfg


def version_info():
    with open(os.path.join(ROOT, 'version.json'), encoding='utf-8') as f:
        return json.load(f)


def game_files():
    """The files an update ships: every top-level .py, the README and version.json."""
    files = sorted(n for n in os.listdir(ROOT) if n.endswith('.py') and os.path.isfile(os.path.join(ROOT, n)))
    files += ['README.md', 'version.json']
    return files


def game_modules():
    return {f[:-3] for f in game_files() if f.endswith('.py')}


def hidden_imports():
    mods = set(STDLIB) | set(EXTRA)
    own = game_modules()
    for f in game_files():
        if not f.endswith('.py'):
            continue
        with open(os.path.join(ROOT, f), encoding='utf-8') as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module]
            else:
                continue
            for n in names:
                if n.split('.')[0] not in own:
                    mods.add(n)
    clash = own & {m.split('.')[0] for m in mods}
    assert not clash, 'game module names clash with bundled modules: %s' % clash
    return sorted(mods)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------- bump
def bump(version, notes):
    info = version_info()
    info['version'] = version
    if notes:
        info['notes'] = notes
    info.pop('files', None)
    with open(os.path.join(ROOT, 'version.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
        f.write('\n')
    print('version.json ->', version, '(%d notes)' % len(info.get('notes', [])))


# ---------------------------------------------------------------------------- build
def write_game(dest):
    """Copies the game files into dest and writes version.json with the file list."""
    os.makedirs(dest, exist_ok=True)
    files = game_files()
    for f in files:
        if f != 'version.json':
            shutil.copyfile(os.path.join(ROOT, f), os.path.join(dest, f))
    info = version_info()
    info['files'] = files
    with open(os.path.join(dest, 'version.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
    return files


def build(skip_exe=False):
    cfg = load_config()
    info = version_info()
    ver = info['version']
    shutil.copyfile(os.path.join(ROOT, 'pixfont.py'), os.path.join(LAUNCHER, 'lfont.py'))
    for art in ('icon.ico', 'icon.png', 'banner.png'):
        if not os.path.exists(os.path.join(LAUNCHER, art)):
            subprocess.check_call([sys.executable, os.path.join(HERE, 'make_art.py')], cwd=ROOT)
            break
    dist = os.path.join(BUILD, 'dist')
    if not skip_exe or not os.path.exists(os.path.join(dist, 'LanternLake', 'LanternLake.exe')):
        cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
               '--name', 'LanternLake', '--icon', os.path.join(LAUNCHER, 'icon.ico'),
               '--add-data', os.path.join(LAUNCHER, 'banner.png') + os.pathsep + '.',
               '--add-data', os.path.join(LAUNCHER, 'icon.png') + os.pathsep + '.',
               '--paths', LAUNCHER, '--collect-submodules', 'pygame', '--collect-data', 'pygame',
               '--exclude-module', 'tkinter', '--exclude-module', '_tkinter',
               '--distpath', dist, '--workpath', os.path.join(BUILD, 'work'), '--specpath', BUILD]
        for m in hidden_imports():
            cmd += ['--hidden-import', m]
        cmd.append(os.path.join(LAUNCHER, 'launcher.py'))
        print('PyInstaller ...')
        subprocess.check_call(cmd, cwd=ROOT)
    # the package: launcher + game folder + update.json
    shutil.rmtree(PACKAGE, ignore_errors=True)
    shutil.copytree(os.path.join(dist, 'LanternLake'), PACKAGE)
    files = write_game(os.path.join(PACKAGE, 'game'))
    with open(os.path.join(PACKAGE, 'update.json'), 'w', encoding='utf-8') as f:
        json.dump({'github': cfg['github']}, f)
    # release files
    out = os.path.join(RELEASES, ver)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    full = os.path.join(out, 'LanternLake-%s-windows.zip' % ver)
    with zipfile.ZipFile(full, 'w', zipfile.ZIP_DEFLATED) as z:
        for d, _, names in os.walk(PACKAGE):
            for n in names:
                p = os.path.join(d, n)
                z.write(p, os.path.relpath(p, PACKAGE))
    payload = os.path.join(out, 'lantern-lake-game-%s.zip' % ver)
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(PACKAGE, 'game', f), f)
    man = {'version': ver, 'tag': 'v' + ver, 'notes': info.get('notes', []),
           'zip': os.path.basename(payload), 'sha256': sha256(payload), 'size': os.path.getsize(payload),
           'full': os.path.basename(full), 'min_launcher': cfg['min_launcher']}
    if cfg['github']:
        man['page'] = 'https://github.com/%s/releases/tag/v%s' % (cfg['github'], ver)
    with open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, indent=2)
    print('package ->', PACKAGE)
    print('release ->', out)
    for n in sorted(os.listdir(out)):
        print('   %-40s %8.1f KB' % (n, os.path.getsize(os.path.join(out, n)) / 1024))
    if not cfg['github']:
        print('note: release.json has no "github" yet, so this build cannot find updates.')


# ---------------------------------------------------------------------------- install
PLAYER_FILES = ('settings.json',)


def install(dest):
    """Makes or refreshes a playable copy. Saves already there are never overwritten."""
    if not os.path.exists(os.path.join(PACKAGE, 'LanternLake.exe')):
        sys.exit('Run "release.py build" first.')
    dest = os.path.abspath(dest)
    if os.path.normcase(dest) == os.path.normcase(ROOT):
        sys.exit('Install somewhere other than the development folder.')
    game = os.path.join(dest, 'game')
    os.makedirs(game, exist_ok=True)
    # the launcher: only when it changed, and never while the game or launcher is running
    exe = os.path.join(dest, 'LanternLake.exe')
    if not os.path.exists(exe) or sha256(exe) != sha256(os.path.join(PACKAGE, 'LanternLake.exe')):
        if os.path.exists(exe):
            try:
                with open(exe, 'r+b'):
                    pass
            except PermissionError:
                sys.exit('Lantern Lake is running. Close it, then run install again (nothing was changed).')
        shutil.copyfile(os.path.join(PACKAGE, 'LanternLake.exe'), exe)
        shutil.rmtree(os.path.join(dest, '_internal'), ignore_errors=True)
        shutil.copytree(os.path.join(PACKAGE, '_internal'), os.path.join(dest, '_internal'))
    else:
        print('launcher unchanged, kept')
    # the game files, dropping files the old version had and this one doesn't
    with open(os.path.join(PACKAGE, 'game', 'version.json'), encoding='utf-8') as f:
        new = json.load(f)['files']
    old = []
    try:
        with open(os.path.join(game, 'version.json'), encoding='utf-8') as f:
            old = json.load(f).get('files', [])
    except (OSError, ValueError):
        pass
    for rel in old:
        if rel not in new and rel.endswith('.py') and '/' not in rel and '\\' not in rel:
            p = os.path.join(game, rel)
            if os.path.isfile(p):
                os.remove(p)
    for rel in new:
        shutil.copyfile(os.path.join(PACKAGE, 'game', rel), os.path.join(game, rel))
    shutil.rmtree(os.path.join(game, '__pycache__'), ignore_errors=True)
    # where updates come from: keep the player's file unless it is still empty
    cfg = load_config()
    up = os.path.join(dest, 'update.json')
    cur = {}
    try:
        with open(up, encoding='utf-8') as f:
            cur = json.load(f)
    except (OSError, ValueError):
        pass
    if not cur.get('github') and not cur.get('manifest'):
        with open(up, 'w', encoding='utf-8') as f:
            json.dump({'github': cfg['github']}, f)
    # first install: bring the saves over from the development folder
    has_saves = any(n.startswith('save') and n.endswith('.json') for n in os.listdir(game))
    copied = []
    if not has_saves:
        for n in sorted(os.listdir(ROOT)):
            if (n.startswith('save') and n.endswith('.json')) or n in PLAYER_FILES:
                shutil.copy2(os.path.join(ROOT, n), os.path.join(game, n))
                copied.append(n)
        for d in ('photos', 'screenshots'):
            if os.path.isdir(os.path.join(ROOT, d)) and not os.path.exists(os.path.join(game, d)):
                shutil.copytree(os.path.join(ROOT, d), os.path.join(game, d))
                copied.append(d + '/')
    print('installed ->', dest)
    print('saves copied from the development folder:', ', '.join(copied) if copied else 'none (kept yours)')


# ---------------------------------------------------------------------------- upload
def api(method, url, token, data=None, ctype='application/json'):
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'User-Agent': UA,
        'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': ctype})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {'message': raw.decode('utf-8', 'replace')[:300]}


def upload():
    cfg = load_config()
    repo = cfg['github']
    if not repo:
        sys.exit('Set "github": "your-name/repo" in release.json first.')
    token = os.environ.get('GITHUB_TOKEN', '').strip()
    if not token:
        sys.exit('Set the GITHUB_TOKEN environment variable to a token that can write to %s.' % repo)
    ver = version_info()['version']
    out = os.path.join(RELEASES, ver)
    with open(os.path.join(out, 'manifest.json'), encoding='utf-8') as f:
        man = json.load(f)
    if man['version'] != ver:
        sys.exit('Build first: release/%s is out of date.' % ver)
    base = 'https://api.github.com/repos/' + repo
    code, info = api('GET', base, token)
    if code != 200:
        sys.exit('Could not open %s on GitHub (%s): %s' % (repo, code, (info or {}).get('message')))
    if info.get('private'):
        sys.exit('%s is private. The launcher can only see releases of a public repository.' % repo)
    tag = man['tag']
    body = 'What\'s new:\n\n' + '\n'.join('- ' + n for n in man.get('notes', [])) + \
        '\n\nNew here? Download **%s**, unzip it anywhere and run LanternLake.exe.\n' \
        'Already playing? The launcher updates the game for you.' % man['full']
    code, rel = api('GET', base + '/releases/tags/' + tag, token)
    if code == 200:
        print('release %s exists, replacing its files' % tag)
    else:
        code, rel = api('POST', base + '/releases', token, {
            'tag_name': tag, 'name': 'Lantern Lake ' + ver, 'body': body, 'draft': True})
        if code not in (200, 201):
            sys.exit('Could not create the release (%s): %s' % (code, rel.get('message')))
        print('created draft release', tag)
    # the manifest goes up last, so a launcher never sees it before the zip is there
    for name in (man['full'], man['zip'], 'manifest.json'):
        for a in rel.get('assets', []):
            if a['name'] == name:
                api('DELETE', base + '/releases/assets/%d' % a['id'], token)
        path = os.path.join(out, name)
        with open(path, 'rb') as f:
            data = f.read()
        url = rel['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(name)
        code, res = api('POST', url, token, data,
                        'application/json' if name.endswith('.json') else 'application/zip')
        if code not in (200, 201):
            sys.exit('Upload of %s failed (%s): %s' % (name, code, (res or {}).get('message')))
        print('uploaded', name, '(%.1f KB)' % (len(data) / 1024))
    if rel.get('draft'):
        code, rel = api('PATCH', base + '/releases/%d' % rel['id'], token, {'draft': False, 'make_latest': 'true'})
        if code != 200:
            sys.exit('Could not publish the release (%s): %s' % (code, rel.get('message')))
    print('published:', rel.get('html_url'))


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__)
        return
    cmd = argv[0]
    if cmd == 'bump':
        bump(argv[1], argv[2:])
    elif cmd == 'build':
        build(skip_exe='--skip-exe' in argv)
    elif cmd == 'install':
        install(argv[1] if len(argv) > 1 else load_config()['install'])
    elif cmd == 'upload':
        upload()
    else:
        sys.exit('unknown command: ' + cmd)


if __name__ == '__main__':
    main(sys.argv[1:])
