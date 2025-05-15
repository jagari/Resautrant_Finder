import pandas as pd
import time
import requests

NAVER_CLIENT_ID = 'nlfv90howe'
NAVER_CLIENT_SECRET = 'ao9YqiDoMGgjTDNQCSMvAMwlJ64e8Or2yCIM4TtY'

# 네이버 지도 Geocoding API 함수
def naver_geocode(address, client_id, client_secret):
    url = 'https://maps.apigw.ntruss.com/map-geocode/v2/geocode'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
    }
    params = {'query': address}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        data = res.json()
        if data['addresses']:
            lat = float(data['addresses'][0]['y'])
            lon = float(data['addresses'][0]['x'])
            return lat, lon
    return None, None

# 데이터 불러오기
df = pd.read_csv('data/gwangju_restaurant_with_coords.csv')

latitudes = []
longitudes = []
for addr in df['주소']:
    lat, lon = naver_geocode(addr, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)
    latitudes.append(lat)
    longitudes.append(lon)
    time.sleep(0.1)

df['위도'] = latitudes
df['경도'] = longitudes

df.to_csv('data/gwangju_restaurant_with_coords.csv', index=False, encoding='utf-8-sig')
print('좌표 변환 및 저장이 완료되었습니다.') 