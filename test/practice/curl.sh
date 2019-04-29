#!/bin/bash

URL="https://m.stock.naver.com/item/main.nhn"

#DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): m.stock.naver.com:443
#send: b'GET /item/main.nhn HTTP/1.1\r\nHost: m.stock.naver.com\r\nUser-Agent: python-requests/2.20.0\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\nreferer: https://m.stock.naver.com/item/index.nhn?code=035720&groupId=-1&type=total\r\n\r\n'



rm main.nhn
curl -v -X GET --url "$URL" \
         -o main.nhn \
         --header "referer: https://m.stock.naver.com/item/index.nhn?code=035720&groupId=-1&type=total"

#grep -n "전일" main.nhn 
