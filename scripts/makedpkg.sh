#!/bin/bash

DPKG_DIR=$PROJECT_ROOT/dpkg
DPKG_CONTROL_FILE=$DPKG_DIR/DEBIAN/control

_Version=`git describe`
Version=${_Version:1}
Package="py-bill"
Architecture="unknown"
InstalledSize=`du --max-depth=0 $DPKG_DIR | awk '{ print $1 }'`


checkArchitecture() {
	Architecture="all"
}

generateControl() {
	cat >$DPKG_CONTROL_FILE <<EOF
Package: $Package
Version: $Version
Depends: nginx
Priority: optional
Architecture: $Architecture
Section: Network
Installed-Size: $InstalledSize
Maintainer: Peanutstars <peanutstars.job@gmail.com>
Description: This is a simple web-server.
 ...
EOF
}

checkArchitecture
generateControl
pushd $PROJECT_ROOT
fakeroot dpkg --build dpkg
mv dpkg.deb $Package-$Version-$Architecture.deb
popd
