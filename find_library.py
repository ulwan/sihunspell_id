#
# This is a cross-platform shared library search mechanism. Tested on:
# OSX, Ubuntu, Fedora, and Windows
#
import os
import glob
import platform
import re
import sys
import shutil
from subprocess import Popen, PIPE
from tar_download import download_and_extract
from distutils.sysconfig import get_python_lib
try:
    from subprocess import getstatusoutput
except ImportError:
    from commands import getstatusoutput

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_architecture():
    return 'x64' if sys.maxsize > 2**32 else 'x86'

def get_prefered_msvc():
    # 3.5+ need msvc14+ compilations
    return 'msvc14'

def form_possible_names(lib, exts, extact=False):
    ret = []
    for ext in exts:
        if not extact:
            ret.append('{}*{}'.format(lib, ext))
        else:
            ret.append('{}{}'.format(lib, ext))
    for ext in exts:
        if not extact:
            ret.append('lib{}*{}'.format(lib, ext))
        else:
            ret.append('lib{}{}'.format(lib, ext))
    return ret

def do_search(paths, names=[], test_fn=None):
    for pn in paths:
        globbed = []
        for name in names:
            if '*' in name:
                globbed.extend(glob.glob(os.path.join(pn, name)))
            else:
                globbed.append(os.path.join(pn, name))
        for filepath in globbed:
            if test_fn:
                if test_fn(filepath):
                    return filepath, pn
            elif os.path.exists(filepath):
                return filepath, pn
    return None, None

def is_library(filepath, acceptable_exts):
    # TODO - This is broken for ".dll.a"
    return os.path.isfile(filepath) and (os.path.splitext(filepath)[-1] in acceptable_exts)

def is_header(filepath):
    return os.path.isfile(filepath)

def include_dirs():
    dirs = [
        os.path.abspath(os.path.join(BASE_DIR, 'hunspell')),
        os.path.abspath(os.path.join(BASE_DIR, 'external', 'hunspell-1.7.0', 'src')),
    ]
    return [path for path in dirs if os.path.isdir(path)]

def library_dirs():
    dirs = [
        os.path.abspath(os.path.join(BASE_DIR, 'libs', 'msvc')),
    ]
    return [path for path in dirs if os.path.isdir(path)]

def get_library_path(lib):
    paths = library_dirs()
    acceptable_exts = [
        '',
        '.so'
    ]
    if platform.system() == 'Windows':
        acceptable_exts = [
            '.lib'
        ]
    elif platform.system() == 'Darwin':
        acceptable_exts.append('.dylib')

    names = form_possible_names(lib, acceptable_exts)
    found_lib, found_path = do_search(paths, names, lambda filepath: is_library(filepath, acceptable_exts))
    if found_lib and platform.system() == 'Windows':
        found_lib = os.path.splitext(found_lib)[0]
    return found_lib, found_path

def get_library_linker_name():
    lib = 'hunspell'
    found_lib, found_path = get_library_path(lib)
    if not found_lib:
        # Try x86 or x64
        found_lib, found_path = get_library_path(lib + get_architecture())
        if not found_lib:
            found_lib, found_path = get_library_path('-'.join(
                [lib, get_prefered_msvc(), get_architecture()]))

    if found_lib:
        found_lib = re.sub(r'.dylib$|.so$|.lib$', '', found_lib.split(os.path.sep)[-1])
        if platform.system() != 'Windows':
            found_lib = re.sub(r'^lib|', '', found_lib)

    return found_lib, found_path

def package_found(package, include_dirs):
    for idir in include_dirs:
        package_path = os.path.join(idir, package)
        if os.path.exists(package_path) and os.access(package_path, os.R_OK):
            return True
    return False

def run_proc_delay_print(*args):
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    for line in stdout.decode(encoding='utf-8').split('\n'):
        print(line)
    for line in stderr.decode(encoding='utf-8').split('\n'):
        print(line, file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError("Process '{}' returned with a non-zero exit code".format(args))

def build_hunspell_package(directory, force_build=False):
    if platform.system() == 'Windows':
        raise RuntimeError("Cannot build directly for windows OS. Please build manually by follow instructions at /libs/msvc/README")

    tmp_lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'external', 'build'))
    lib_path = os.path.join(tmp_lib_path, 'lib')
    if not os.path.exists(tmp_lib_path):
        os.makedirs(tmp_lib_path)

    if platform.system() == 'Linux':
        expected_lib_name = 'libhunspell-1.7.so.0'
        expected_lib_path = os.path.join(lib_path, expected_lib_name)
    else: # OSX
        expected_lib_name = 'libhunspell-1.7.dylib'
        expected_lib_path = os.path.join(lib_path, expected_lib_name)

    olddir = os.getcwd()
    if force_build or not os.contentspath.exists(expected_lib_path):
        if os.path.exists(lib_path):
            shutil.rmtree(lib_path)
        try:
            os.chdir(directory)
            run_proc_delay_print('autoreconf', '-vfi')
            run_proc_delay_print('./configure', '--prefix='+tmp_lib_path)
            run_proc_delay_print('make')
            run_proc_delay_print('make', 'install')
        finally:
            os.chdir(olddir)

        if platform.system() == 'Linux':
            # There's a build issue where sometimes linux builds look for symlink files that don't exist later
            os.rename(os.path.join(lib_path, 'libhunspell-1.7.so.0.0.1'), expected_lib_path)
            for f in glob.glob(os.path.join(lib_path, 'libhunspell-1.7.so.0.*')):
                os.remove(f)
            if os.path.exists(os.path.join(lib_path, 'libhunspell-1.7.so')):
                os.remove(os.path.join(lib_path, 'libhunspell-1.7.so'))
        else:
            # There's a build issue where sometimes mac builds look for symlink files that don't exist later
            os.rename(os.path.join(lib_path, 'libhunspell-1.7.0.dylib'), expected_lib_path)
            for f in glob.glob(os.path.join(lib_path, 'libhunspell-1.7.*.dylib')):
                os.remove(f)

        print("Built Hunspell library files:")
        for filename in os.listdir(lib_path):
            if os.path.isfile(os.path.join(lib_path, filename)):
                print('\t' + filename)

    return ':'+expected_lib_name, lib_path

def pkgconfig(**kw):
    try:
        flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
        status, response = getstatusoutput("pkg-config --libs --cflags hunspell")
        if status != 0:
            raise RuntimeError(response)
        for token in response.split():
            kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
            if token[:2] in flag_map:
                arg = flag_map.get(token[:2])
                kw.setdefault(arg, []).append(token[2:])
                kw[arg] = list(set(kw[arg]))
            else: # throw others to extra_link_args
                kw.setdefault('extra_link_args', []).append(token)
                kw['extra_link_args'] = list(set(kw['extra_link_args']))
    except RuntimeError:
        kw['include_dirs'] = include_dirs()
        kw['library_dirs'] = []
        kw['runtime_library_dirs'] = []
        kw['libraries'] = []
        kw['extra_link_args'] = []

        if not package_found('hunspell', kw['include_dirs']):
            # Prepare for hunspell if it's missing
            download_and_extract('https://github.com/hunspell/hunspell/archive/v1.7.0.tar.gz',
                os.path.join(BASE_DIR, 'external'))
            kw['include_dirs'] = include_dirs()

        if platform.system() == 'Windows':
            _linker_name, linker_path = get_library_linker_name()
            if not linker_path:
                raise RuntimeError("Could not find library dependencies for Windows")
            # These should be hardcoded to both architectures
            kw['libraries'] = ['libhunspell-msvc14-x64', 'libhunspell-msvc14-x86']
            kw['library_dirs'] = [linker_path]
            kw['extra_link_args'] = ['/NODEFAULTLIB:libucrt.lib ucrt.lib']
        else:
            lib_name, lib_path = build_hunspell_package(os.path.join(BASE_DIR, 'external', 'hunspell-1.7.0'), True)
            kw['library_dirs'] = [lib_path]
            kw['libraries'] = [lib_name]
            kw['extra_link_args'] = ['-Wl,-rpath,"{}"'.format(lib_path)]
    
    return kw
