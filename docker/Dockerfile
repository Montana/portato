FROM gentoo/stage3:latest

RUN emerge-webrsync || true

ENV EMERGE_DEFAULT_OPTS="--quiet-build=y --with-bdeps=y --keep-going"
ENV FEATURES="parallel-fetch"

RUN emerge -qv \
    dev-python/pygobject \
    x11-libs/gtk+:3 \
    app-admin/eselect \
    || true && \
    emerge -qv \
    app-portage/gentoolkit \
    x11-terms/xterm \
    x11-misc/x11vnc \
    x11-base/xorg-server \
    x11-apps/xauth \
    media-fonts/dejavu \
    || true

ARG USERNAME=portato
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

WORKDIR /opt/portato
COPY . /opt/portato

RUN emerge -qv dev-python/pip dev-python/setuptools dev-python/wheel || true && \
    mkdir -p /etc/portage/package.use && \
    echo 'x11-base/xorg-server xvfb' >> /etc/portage/package.use/portato && \
    emerge -qv x11-base/xorg-server x11-misc/x11vnc || true

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -e .

RUN mkdir -p /var/cache/distfiles /var/tmp/portage && \
    chown -R ${USERNAME}:${USERNAME} /opt/portato

COPY docker/headless.sh /usr/local/bin/headless.sh
RUN chmod +x /usr/local/bin/headless.sh

USER ${USERNAME}

CMD ["portato", "--help"]
