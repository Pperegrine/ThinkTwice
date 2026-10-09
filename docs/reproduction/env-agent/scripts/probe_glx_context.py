"""Request real GLX contexts; do not override advertised GL capabilities."""
import ctypes as c
import json
import os
import sys
from pathlib import Path

x = c.CDLL('libX11.so.6')
gl = c.CDLL('libGL.so.1')
x.XOpenDisplay.argtypes = [c.c_char_p]
x.XOpenDisplay.restype = c.c_void_p
x.XDefaultScreen.argtypes = [c.c_void_p]
x.XDefaultScreen.restype = c.c_int
x.XSync.argtypes = [c.c_void_p, c.c_int]
x.XCloseDisplay.argtypes = [c.c_void_p]
class XError(c.Structure):
    _fields_ = [('type', c.c_int), ('display', c.c_void_p), ('resourceid', c.c_ulong),
                ('serial', c.c_ulong), ('error_code', c.c_ubyte),
                ('request_code', c.c_ubyte), ('minor_code', c.c_ubyte)]
errors = []
handler_t = c.CFUNCTYPE(c.c_int, c.c_void_p, c.POINTER(XError))
@handler_t
def handler(display, e):
    errors.append({'error_code': e.contents.error_code,
                   'request_code': e.contents.request_code,
                   'minor_code': e.contents.minor_code})
    return 0
x.XSetErrorHandler.argtypes = [handler_t]
x.XSetErrorHandler(handler)
gl.glXChooseFBConfig.argtypes = [c.c_void_p, c.c_int, c.POINTER(c.c_int), c.POINTER(c.c_int)]
gl.glXChooseFBConfig.restype = c.POINTER(c.c_void_p)
gl.glXGetProcAddressARB.argtypes = [c.c_char_p]
gl.glXGetProcAddressARB.restype = c.c_void_p
gl.glXDestroyContext.argtypes = [c.c_void_p, c.c_void_p]
display = x.XOpenDisplay(os.environ.get('DISPLAY', ':0').encode())
if not display:
    raise RuntimeError('Cannot open X display')
attrs = (c.c_int * 7)(0x8012, 1, 0x8010, 4, 0x8011, 1, 0)
n = c.c_int()
configs = gl.glXChooseFBConfig(display, x.XDefaultScreen(display), attrs, c.byref(n))
if not n.value:
    raise RuntimeError('No RGBA pbuffer FBConfig')
create_t = c.CFUNCTYPE(c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p, c.c_int, c.POINTER(c.c_int))
create = create_t(gl.glXGetProcAddressARB(b'glXCreateContextAttribsARB'))
result = {'display': os.environ.get('DISPLAY'), 'contexts': []}
for major, minor in [(3, 3), (4, 3), (4, 6)]:
    errors.clear()
    context_attrs = (c.c_int * 7)(0x2091, major, 0x2092, minor, 0x9126, 1, 0)
    ctx = create(display, configs[0], None, 1, context_attrs)
    x.XSync(display, 0)
    result['contexts'].append({'requested': '%s.%s' % (major, minor),
                               'created': bool(ctx), 'x_errors': list(errors)})
    if ctx:
        gl.glXDestroyContext(display, ctx)
x.XCloseDisplay(display)
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
