#!/bin/bash

for dir in `ls -d data/source/*/`; do
    dir_name=${dir}/$(date '+%Y%m%d')
    mkdir ${dir_name}
    (cd ${dir} && ln -snf ${dir_name} latest)
done