#!/bin/bash
set -euo pipefail
export PATH=/opt/thinktwice/mesa-build-venv/bin:/opt/thinktwice/conda/bin:$PATH
export PKG_CONFIG_PATH=/opt/thinktwice/mesa24/lib/pkgconfig:${PKG_CONFIG_PATH:-}
cd /opt/thinktwice/src/mesa-24.0.5
reconfigure=()
if [ -f build-d3d12/meson-private/coredata.dat ]; then reconfigure=(--reconfigure); fi
meson setup "${reconfigure[@]}" build-d3d12 --prefix=/opt/thinktwice/mesa24 --libdir=lib \
  -Dbuildtype=release -Dgallium-drivers=swrast,d3d12 -Dvulkan-drivers= \
  -Dllvm=disabled -Dplatforms=x11 -Dglx=dri -Degl=enabled \
  -Dgles1=disabled -Dgles2=enabled -Dgbm=enabled \
  -Dgallium-va=disabled -Dgallium-vdpau=disabled -Dgallium-xa=disabled \
  -Dshared-glapi=enabled -Dvideo-codecs= -Dglvnd=false
ninja -C build-d3d12 -j2
meson install -C build-d3d12
