import requests

client_id = 'nlfv90howe'
client_secret = 'ao9YqiDoMGgjTDNQCSMvAMwlJ64e8Or2yCIM4TtY'
address = '대구광역시 중구 동성로1가 2-1'
url = 'https://maps.apigw.ntruss.com/map-geocode/v2/geocode'
headers = {
    'X-NCP-APIGW-API-KEY-ID': client_id,
    'X-NCP-APIGW-API-KEY': client_secret
}
params = {'query': address}
res = requests.get(url, headers=headers, params=params)
print(res.status_code)
print(res.text)
