FROM gentoo/stage3:latest

RUN emerge-webrsync || true
ENV EMERGE_DEFAULT_OPTS="--quiet-build=y --with-bdeps=y --keep-going"
ENV FEATURES="parallel-fetch"

RUN set -e; \
    mkdir -p /etc/portage; \
    { \
      echo 'VIDEO_CARDS="dummy"'; \
      echo 'INPUT_DEVICES="libinput"'; \
      echo 'USE="X elogind udev"'; \
    } >> /etc/portage/make.conf

RUN emerge -qv \
    dev-python/pip \
    dev-python/setuptools \
    dev-python/wheel \
    dev-python/pygobject \
    x11-libs/gtk+:3 \
    app-admin/eselect \
    app-portage/gentoolkit \
    x11-terms/xterm \
    dev-vcs/git

RUN set -e; \
    mkdir -p /etc/portage/package.use; \
    printf '%s\n' \
      'x11-base/xorg-server xvfb udev elogind xorg' \
      'media-libs/libglvnd X' \
      'sys-auth/pambase elogind' \
      > /etc/portage/package.use/portato; \
    emerge -pv x11-base/xorg-server x11-misc/x11vnc x11-apps/xauth media-fonts/dejavu || true; \
    emerge --autounmask-write --autounmask-continue -qv \
           x11-base/xorg-server x11-misc/x11vnc x11-apps/xauth media-fonts/dejavu || true; \
    etc-update --automode -5 || true; \
    emerge -qv x11-base/xorg-server x11-misc/x11vnc x11-apps/xauth media-fonts/dejavu

ARG USERNAME=portato
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

WORKDIR /opt/portato
COPY . /opt/portato

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel setuptools && \
    (/opt/venv/bin/pip install -e . || true)

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN printf '%s\n' '#!/usr/bin/env bash' \
    'set -e' \
    'if python3 -c "import portato" >/dev/null 2>&1; then' \
    '  exec python3 -m portato "$@"' \
    'elif [ -f /opt/portato/portato/gui.py ]; then' \
    '  exec python3 - <<PY "$@"' \
    'from portato.gui import run_gui' \
    'import sys' \
    'if __name__ == "__main__":' \
    '    if len(sys.argv) > 1 and sys.argv[1] == "gui":' \
    '        sys.argv.pop(1)' \
    '    run_gui()' \
    'PY' \
    'elif [ -f /opt/portato/gui.py ]; then' \
    '  exec python3 /opt/portato/gui.py "$@"' \
    'else' \
    '  echo "ERROR: Cannot find Portato entrypoint (portato package or gui.py)." >&2' \
    '  exit 1' \
    'fi' \
    > /usr/local/bin/portato && chmod +x /usr/local/bin/portato

COPY docker/headless.sh /usr/local/bin/headless.sh
RUN chmod +x /usr/local/bin/headless.sh

USER ${USERNAME}
CMD ["portato", "--help"]
