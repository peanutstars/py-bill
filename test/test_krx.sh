#!/bin/bash

URL=https://short.krx.co.kr/contents/SRT/99/SRT99000001.jspx
echo "================================="
CODE=`curl -sX GET "http://short.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=COM/finder_srtisu&name=form"`
echo "[$CODE]"

curl \
         -X POST \
         --data-urlencode "isuCd=" \
         --data-urlencode "no=SRT2" \
         --data-urlencode "mktsel=ALL" \
         --data-urlencode "searchText=" \
         --data-urlencode "pagePath=/contents/COM/FinderSrtIsu.jsp" \
         --data-urlencode "code=$CODE" \
         --data-urlencode "pageFirstCall=Y" \
         $URL


echo '---------------------------------'
URL=https://short.krx.co.kr/contents/SRT/99/SRT99000001.jspx
CODE=`curl -sX GET "https://short.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=SRT/02/02010100/srt02010100&name=form"`
echo "[$CODE]"

#curl \
#         -X POST \
#         --data-urlencode "isu_cdnm=A035720/카카오" \
#         --data-urlencode "isu_cd=KR7035720002" \
#         --data-urlencode "isu_nm=카카오" \
#         --data-urlencode "isu_srt_cd=A035720" \
#         --data-urlencode "strt_dd=20190113" \
#         --data-urlencode "end_dd=20190213" \
#         --data-urlencode "pagePath=/contents/SRT/02/02010100/SRT02010100.jsp" \
#         --data-urlencode "code=$CODE" \
#         $URL

curl \
         -X POST \
         --data-urlencode "isu_cd=KR7035720002" \
         --data-urlencode "isu_srt_cd=A035720" \
         --data-urlencode "strt_dd=20190113" \
         --data-urlencode "end_dd=20190213" \
         --data-urlencode "pagePath=/contents/SRT/02/02010100/SRT02010100.jsp" \
         --data-urlencode "code=$CODE" \
         $URL
