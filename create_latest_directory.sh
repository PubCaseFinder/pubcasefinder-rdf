#!/bin/bash

# latestディレクトリの作成
for dir in `ls -d data/source/*/`; do
    dir_name=${dir}/$(date '+%Y%m%d')
    mkdir ${dir_name}
    (cd ${dir} && ln -snf ${dir_name} latest)
done

# HPOの旧翻訳をlatestにコピーする
old_dir=`ls -r data/source/HPO | sed -E 's@[^0-9]@@g' | grep -v '^$' | grep -v $(date '+%Y%m%d') | head -n 1`
cp data/source/HPO/${old_dir}/HPO_Inheritance_en_jp.txt data/source/HPO/latest/