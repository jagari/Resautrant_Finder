import pandas as pd

# 남길 컬럼 목록
columns_to_keep = [
    'GNG_CS',    # 주소
    'FD_CS',     # 음식 종류
    'BZ_NM',     # 음식점명
    'TLNO',      # 전화번호
    'SBW',       # 지하철 정보
    'BUS',       # 버스 정보
    '위도',      # 위도
    '경도'       # 경도
]

# 데이터 불러오기
df = pd.read_csv('data/daegu_restaurant_with_coords.csv')

# 필요한 컬럼만 추출
df_clean = df[columns_to_keep]

# 새 파일로 저장
df_clean.to_csv('data/daegu_restaurant_cleaned.csv', index=False, encoding='utf-8-sig')
print('불필요 컬럼 제거 및 저장이 완료되었습니다.') 