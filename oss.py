import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
import time
import os
import plotly.express as px
from dotenv import load_dotenv

COORDS_PATH = 'data/daegu_restaurant_with_coords.csv'
DATA_PATH = 'data/daegu_restaurant.json'

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

# 네이버 지도 Geocoding API 함수 (UI에는 노출하지 않음)
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

def geocode_and_save(df, client_id, client_secret, save_path=COORDS_PATH):
    latitudes = []
    longitudes = []
    for i, address in enumerate(df['GNG_CS']):
        lat, lon = naver_geocode(address, client_id, client_secret)
        latitudes.append(lat)
        longitudes.append(lon)
        time.sleep(0.1)
    df = df.copy()
    df['위도'] = latitudes
    df['경도'] = longitudes
    df.to_csv(save_path, index=False)
    return df

def load_coords_data():
    if os.path.exists(COORDS_PATH):
        df = pd.read_csv(COORDS_PATH)
        df = df.dropna(subset=['위도', '경도'])
        return df
    else:
        # 원본 JSON에서 데이터 불러오기
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = pd.read_json(f)
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)
        # 좌표 변환 및 저장
        st.info('좌표 변환 파일이 없어 네이버 API로 변환을 시작합니다. (최초 실행 시 수 분 소요)')
        df = geocode_and_save(df, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)
        df = df.dropna(subset=['위도', '경도'])
        st.success('좌표 변환이 완료되어 CSV로 저장되었습니다.')
        return df

def main():
    st.title('대구 맛집 지도 대시보드')
    df = load_coords_data()

    # 날짜 및 시간 선택
    selected_date = st.date_input('날짜를 선택하세요')
    selected_time = st.time_input('시간을 선택하세요')

    # 선택한 날짜와 시간을 기준으로 현재 영업 중인 음식점 필터링
    if 'MBZ_HR' in df.columns:
        selected_datetime = pd.to_datetime(f"{selected_date} {selected_time}")

        def parse_hours(row):
            try:
                hours = row.split('~')
                open_time = pd.to_datetime(hours[0].strip(), format='%H:%M', errors='coerce').time()
                close_time = pd.to_datetime(hours[1].strip(), format='%H:%M', errors='coerce').time()
                return open_time, close_time
            except:
                return None, None

        df[['open_time', 'close_time']] = df['MBZ_HR'].apply(lambda x: pd.Series(parse_hours(x)))

        df = df.dropna(subset=['open_time', 'close_time'])
        df['open_time'] = df['open_time'].apply(lambda x: pd.Timestamp.combine(selected_date, x))
        df['close_time'] = df['close_time'].apply(lambda x: pd.Timestamp.combine(selected_date, x))

        df = df[(df['open_time'] <= selected_datetime) & (df['close_time'] >= selected_datetime)]

    # 지도 유형 선택 (Stamen 계열 삭제, 위성뷰 추가)
    map_types = {
        '기본': {
            'tiles': 'OpenStreetMap',
            'attr': None
        },
        '화이트': {
            'tiles': 'CartoDB positron',
            'attr': None
        },
        '블랙': {
            'tiles': 'CartoDB dark_matter',
            'attr': None
        },
        '위성': {
            'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'attr': 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        },
    }
    selected_map = st.selectbox('지도 유형을 선택하세요', list(map_types.keys()), index=0)
    map_info = map_types[selected_map]

    # 음식 종류별 레이어 선택 (UI를 지도 아래로 이동)
    food_types = df['FD_CS'].dropna().unique().tolist()
    food_types.sort()
    all_option = ['전체'] + food_types

    # 필터링 후 데이터 확인
    if df.empty:
        st.warning("선택한 시간에 영업 중인 음식점이 없습니다.")
    else:
        # folium 지도 생성 (tiles, attr 모두 적용)
        if map_info['attr']:
            m = folium.Map(location=[df['위도'].mean(), df['경도'].mean()], zoom_start=12, tiles=map_info['tiles'], attr=map_info['attr'])
        else:
            m = folium.Map(location=[df['위도'].mean(), df['경도'].mean()], zoom_start=12, tiles=map_info['tiles'])

        color_map = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
        color_dict = {ft: color_map[i % len(color_map)] for i, ft in enumerate(food_types)}

        # 음식 종류 선택값을 지도 아래에서 받음
        selected_foods = st.multiselect('지도에 표시할 음식 종류를 선택하세요', all_option, default=food_types[:3])

        # '전체'가 선택된 경우 모든 카테고리 표시
        if '전체' in selected_foods:
            display_foods = food_types
        elif selected_foods:
            display_foods = selected_foods
        else:
            display_foods = []

        # 아무 카테고리도 선택하지 않으면 마커 표시 안 함
        if display_foods:
            for ft in display_foods:
                sub_df = df[df['FD_CS'] == ft]
                for _, row in sub_df.iterrows():
                    folium.Marker(
                        location=[row['위도'], row['경도']],
                        popup=folium.Popup(f"{row['BZ_NM']}<br>{row['GNG_CS']}<br>{row['FD_CS']}", max_width=400),
                        icon=folium.Icon(color=color_dict[ft], icon='cutlery', prefix='fa')
                    ).add_to(m)

        folium_static(m, width=800, height=600)

    # 카테고리별 음식점 수 계산
    category_counts = df['FD_CS'].value_counts().reset_index()
    category_counts.columns = ['음식 종류', '음식점 수']
    
    # Plotly 원형그래프(파이차트) 생성 (범례에서 카테고리별 토글 가능)
    fig = px.pie(
        category_counts,
        names='음식 종류',
        values='음식점 수',
        title='대구 맛집 카테고리별 비율',
        color='음식 종류',
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.3
    )
    fig.update_traces(textinfo='percent+label', pull=[0.05]*len(category_counts), textposition='outside')
    fig.update_layout(
        legend_title='음식 종류',
        height=600,
        width=900,
        margin=dict(t=80, l=180, r=180, b=80),  # 좌우 마진 크게
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=14)
        )
    )
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
