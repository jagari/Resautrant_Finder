# 맛집 지도 대시보드 (대구/광주)
# 주요 기능: 도시별 데이터 로드, 지도 시각화, 카테고리/시간 필터, 상세정보, 파이차트, 지도 표시 개수 슬라이더

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
import time
import os
import plotly.express as px
from dotenv import load_dotenv

# --- 경로 및 환경설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 도시별 데이터 파일 경로 관리
CITY_FILES = {
    '대구': {
        'coords': os.path.join(DATA_DIR, 'daegu_restaurant_with_coords.csv'),
        'raw': os.path.join(DATA_DIR, 'daegu_restaurant.json')
    },
    '광주': {
        'coords': os.path.join(DATA_DIR, 'gwangju_restaurant_with_coords.csv'),
        'raw': os.path.join(DATA_DIR, 'gwangju_restaurant.json')
    }
}

# .env 파일 로드 및 API 키 가져오기
load_dotenv()
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

# --- 네이버 지도 Geocoding API 함수 ---
def naver_geocode(address, client_id, client_secret):
    """도로명 주소를 위도/경도로 변환"""
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

# --- 데이터프레임에 좌표 변환 후 저장 ---
def geocode_and_save(df, client_id, client_secret, save_path):
    """데이터프레임의 주소를 위경도로 변환 후 CSV로 저장"""
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

# --- 도시별 데이터 로드 함수 ---
def load_city_data(city):
    """도시별로 좌표 변환된 CSV 또는 원본 JSON을 불러옴"""
    if city not in CITY_FILES:
        st.warning("해당 도시 데이터가 준비되지 않았습니다.")
        return pd.DataFrame()
    coords_path = CITY_FILES[city]['coords']
    raw_path = CITY_FILES[city]['raw']
    if os.path.exists(coords_path):
        df = pd.read_csv(coords_path)
        df = df.dropna(subset=['위도', '경도'])
        # 광주 데이터는 컬럼명을 표준화
        if city == '광주':
            col_map = {
                '음식점명': 'BZ_NM',
                '음식 종류': 'FD_CS',
                '주소': 'GNG_CS',
                '전화번호': 'TEL_NO',
                '위도': '위도',
                '경도': '경도',
            }
            df = df.rename(columns=col_map)
        return df
    elif os.path.exists(raw_path):
        with open(raw_path, 'r', encoding='utf-8') as f:
            data = pd.read_json(f)
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        st.info('좌표 변환 파일이 없어 네이버 API로 변환을 시작합니다. (최초 실행 시 수 분 소요)')
        df = geocode_and_save(df, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, save_path=coords_path)
        df = df.dropna(subset=['위도', '경도'])
        st.success('좌표 변환이 완료되어 CSV로 저장되었습니다.')
        return df
    else:
        st.error("도시 데이터 파일이 없습니다.")
        return pd.DataFrame()

# --- folium 지도 생성 함수 ---
def create_map(df, map_info, color_dict):
    """음식점 데이터프레임을 folium 지도에 마커로 표시"""
    m = folium.Map(
        location=[df['위도'].mean(), df['경도'].mean()],
        zoom_start=12,
        tiles=map_info['tiles'],
        attr=map_info.get('attr')
    )
    for ft in color_dict:
        sub_df = df[df['FD_CS'] == ft]
        for _, row in sub_df.iterrows():
            popup_html = f"<b>{row['BZ_NM']}</b><br>{row['GNG_CS']}<br>{row['FD_CS']}<br>"
            popup_html += f"<a href='?selected={row['BZ_NM']}' target='_self' style='color:#e74c3c;font-weight:bold;'>상세정보 보기</a>"
            folium.Marker(
                location=[row['위도'], row['경도']],
                popup=folium.Popup(popup_html, max_width=400),
                icon=folium.Icon(color=color_dict[ft], icon='cutlery', prefix='fa')
            ).add_to(m)
    return m

# --- 메인 Streamlit 앱 ---
def main():
    st.title('맛집 지도 대시보드')

    # --- 사이드바: 도시 선택 ---
    with st.sidebar:
        st.write('### 도시 선택')
        city_option = st.selectbox('도시를 선택하세요', ['전체', '대구', '광주'], index=1)
    if city_option == '전체':
        st.info("현재는 도시별 데이터만 지원합니다.")
        return

    # --- 데이터 로드 ---
    df = load_city_data(city_option)
    if df.empty:
        st.warning("데이터가 없습니다.")
        return

    # --- 날짜/시간 선택 ---
    selected_date = st.date_input('날짜를 선택하세요')
    selected_time = st.time_input('시간을 선택하세요')
    # 영업 시간 필터링
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

    # --- 지도 유형 선택 ---
    map_types = {
        '기본': {'tiles': 'OpenStreetMap', 'attr': None},
        '화이트': {'tiles': 'CartoDB positron', 'attr': None},
        '블랙': {'tiles': 'CartoDB dark_matter', 'attr': None},
        '위성': {
            'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'attr': 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        },
    }
    selected_map = st.selectbox('지도 유형을 선택하세요', list(map_types.keys()), index=0)
    map_info = map_types[selected_map]

    # --- 음식 종류 선택 ---
    food_types = df['FD_CS'].dropna().unique().tolist()
    food_types.sort()
    all_option = ['전체'] + food_types
    selected_foods = st.multiselect('지도에 표시할 음식 종류를 선택하세요', all_option, default=['전체'])

    if '전체' in selected_foods or not food_types:
        display_foods = df['FD_CS'].unique().tolist()
    else:
        display_foods = selected_foods

    # --- 마커 색상 매핑 ---
    color_map = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    color_dict = {ft: color_map[i % len(color_map)] for i, ft in enumerate(display_foods)}

    # --- 지도 및 음식점 표시 ---
    filtered_df = df[df['FD_CS'].isin(display_foods)] if display_foods else df.iloc[0:0]

    # 지도에 표시할 음식점 수 슬라이더 
    st.markdown('---')
    max_count = len(filtered_df)
    if max_count > 0:
        max_display = st.slider('지도에 표시할 최대 음식점 수', min_value=1, max_value=max_count, value=min(100, max_count), step=1)
        filtered_df = filtered_df.head(max_display)
    else:
        max_display = 0

    if max_display > 0:
        m = create_map(filtered_df, map_info, color_dict)
        folium_static(m, width=800, height=600)
    else:
        st.warning('지도에 표시할 데이터가 없습니다. (카테고리/필터를 확인하세요)')

    # --- 상세정보 표시 (쿼리 파라미터 활용) ---
    selected_restaurant = st.query_params.get('selected', [None])[0]
    if selected_restaurant:
        info_df = df[df['BZ_NM'] == selected_restaurant]
        if not info_df.empty:
            row = info_df.iloc[0]
            st.markdown('---')
            st.subheader(f"{row['BZ_NM']} 상세 정보")
            st.write(f"**주소:** {row['GNG_CS']}")
            st.write(f"**음식 종류:** {row['FD_CS']}")
            st.write(f"**영업 시간:** {row['MBZ_HR'] if 'MBZ_HR' in row else '정보 없음'}")
            st.write(f"**전화번호:** {row['TEL_NO'] if 'TEL_NO' in row else '정보 없음'}")
            st.write(f"**기타 정보:** {row['SMPL_DESC'] if 'SMPL_DESC' in row else '정보 없음'}")
            if st.button('닫기', key=f"close_detail_{row['BZ_NM']}__popup"):
                st.query_params.clear()
                st.rerun()

    # --- 카테고리별 음식점 수 파이차트 ---
    category_counts = df['FD_CS'].value_counts().reset_index()
    category_counts.columns = ['음식 종류', '음식점 수']
    fig = px.pie(
        category_counts,
        names='음식 종류',
        values='음식점 수',
        title=f'{city_option} 맛집 카테고리별 비율',
        color='음식 종류',
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.3
    )
    fig.update_traces(textinfo='percent+label', pull=[0.05]*len(category_counts), textposition='outside')
    fig.update_layout(
        legend_title='음식 종류',
        height=600,
        width=900,
        margin=dict(t=80, l=180, r=180, b=80),
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