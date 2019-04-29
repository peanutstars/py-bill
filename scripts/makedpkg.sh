#!/bin/bash

DPKG_DIR=$PROJECT_ROOT/dpkg
VERSION_FILE=$PROJECT_ROOT/VERSION
DPKG_CONTROL_FILE=$DPKG_DIR/DEBIAN/control

Version=`cat $VERSION_FILE`
Package="pybill"
Architecture="unknown"
InstalledSize=`du --max-depth=0 $DPKG_DIR | awk '{ print $1 }'`


checkArchitecture() {
	Architecture="all"
}

generateControl() {
	cat >$DPKG_CONTROL_FILE <<EOF
Package: $Package
Version: $Version
Depends: 
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
