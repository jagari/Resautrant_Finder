import pandas as pd
import numpy as np

# 광주 데이터 읽기 (cp949 인코딩 사용)
df_gwangju = pd.read_csv('data/gwangju_restaurant.csv', encoding='cp949')

# 필요한 컬럼만 추출 및 컬럼명 변경
df_gwangju = df_gwangju.rename(columns={
    '상호명': '음식점명',
    '소재지도로명주소': '주소',
    '전화번호': '전화번호'
})

# '음식 종류' 컬럼 추가 (임시로 '기타'로 채움)
df_gwangju['음식 종류'] = '기타'

# 위도, 경도 컬럼 추가 (나중에 geocoding으로 채울 예정)
df_gwangju['위도'] = np.nan
df_gwangju['경도'] = np.nan

# 컬럼 순서 재배치
df_gwangju = df_gwangju[['음식점명', '음식 종류', '주소', '전화번호', '위도', '경도']]

# 결과 저장
df_gwangju.to_csv('data/gwangju_restaurant_with_coords.csv', index=False, encoding='utf-8-sig')

print("데이터 변환이 완료되었습니다.")
print(f"총 {len(df_gwangju)}개의 음식점 데이터가 변환되었습니다.") 