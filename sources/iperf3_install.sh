#!/usr/bin/env bash

trap exit ERR

src_dir=$1
tmp_dir=$2
tar_file=iperf-3.1.3.tgz

cp -v ${src_dir}/${tar_file} ${tmp_dir}
cd $tmp_dir
tar zxf ${tar_file}
cd iperf-3.1.3
./configure --prefix=/usr 
make -j8 
sudo make install

exit 0
