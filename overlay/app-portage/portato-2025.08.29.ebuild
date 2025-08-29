# Copyright 2025
# Distributed under the terms of the MIT license

EAPI=8
PYTHON_COMPAT=( python3_11 python3_12 )

inherit distutils-r1

DESCRIPTION="Portato (Almost): small Gentoo Portage helper with room to revive GUI"
HOMEPAGE="https://example.invalid/portato-almost"
# Put the tarball into /var/cache/distfiles then run: ebuild ... manifest
SRC_URI="mirror://local/portato-almost-2025.08.29.tar.gz"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE=""

RDEPEND="
    sys-apps/portage
    dev-python/pygobject[gtk]
    x11-libs/gtk+:3
    app-admin/eselect
    || ( app-portage/gentoolkit app-portage/portage-utils )
    x11-terms/xterm
"
BDEPEND="${RDEPEND}"

S="${WORKDIR}/portato"

src_prepare() {
    default
}

python_install_all() {
    distutils-r1_python_install_all
    dodoc README.md
}
