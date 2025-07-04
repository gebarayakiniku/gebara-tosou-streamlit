import streamlit as st
import math
from PIL import Image
import pytesseract
import re # reモジュールを追加

# Tesseractのパスを設定 (Streamlit Cloudでは不要な場合が多いが、ローカルテスト用に残す)
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# --- アプリケーションの状態を初期化 ---
def initialize_state():
    # エリア情報 (アプリ1より)
    if 'areas' not in st.session_state:
        st.session_state.areas = [{
            'place_name': '', 'height': 0.0, 'lengths': [0.0] * 10, 'area': 0.0
        }]
    if 'ninku_kijun' not in st.session_state:
        st.session_state.ninku_kijun = 15.0 # 人工計算基準値
    if 'total_construction_area' not in st.session_state:
        st.session_state.total_construction_area = 0.0
    if 'ninku_rounded' not in st.session_state:
        st.session_state.ninku_rounded = 0.0

    # 材料設定情報 (新しい項目に変更)
    default_materials_settings = {
        "ファイバーテープ": {"unit_name": "m", "coverage_per_unit": 50.0},
        "下パテ": {"unit_name": "kg", "coverage_per_unit": 5.0},
        "上パテ": {"unit_name": "kg", "coverage_per_unit": 5.0},
        "下塗り": {"unit_name": "L", "coverage_per_unit": 10.0},
        "中塗り": {"unit_name": "L", "coverage_per_unit": 10.0},
        "上塗り": {"unit_name": "L", "coverage_per_unit": 10.0},
    }
    if 'material_settings' not in st.session_state:
        st.session_state.material_settings = {}
        for item_name, defaults in default_materials_settings.items():
            st.session_state.material_settings[item_name] = {
                "unit_name": defaults["unit_name"],
                "coverage_per_unit": defaults["coverage_per_unit"]
            }
    else:
        current_material_keys = list(st.session_state.material_settings.keys())
        for key in current_material_keys:
            if key not in default_materials_settings:
                del st.session_state.material_settings[key]
        for item_name, defaults in default_materials_settings.items():
            if item_name not in st.session_state.material_settings:
                st.session_state.material_settings[item_name] = {
                    "unit_name": defaults["unit_name"],
                    "coverage_per_unit": defaults["coverage_per_unit"]
                }
            else:
                pass

    if 'material_requirements_results' not in st.session_state:
        st.session_state.material_requirements_results = []

initialize_state()

# --- 計算ロジック ---
def calculate_area_for_single_area(area_data):
    """特定のエリアの施工面積を計算する"""
    try:
        h = float(area_data['height'])
        sum_w = sum(float(l) if isinstance(l, (int, float)) else 0.0 for l in area_data['lengths'])
        return h * sum_w
    except (ValueError, TypeError):
        return 0.0

def calculate_all():
    """全ての計算を実行し、session_stateを更新する"""
    current_total_construction_area_val = 0.0
    for i, area_data in enumerate(st.session_state.areas):
        area_data['area'] = calculate_area_for_single_area(area_data)
        current_total_construction_area_val += area_data['area']
    st.session_state.total_construction_area = current_total_construction_area_val

    if st.session_state.ninku_kijun > 0:
        ninku = current_total_construction_area_val / st.session_state.ninku_kijun
        st.session_state.ninku_rounded = round(ninku, 1)
    else:
        st.session_state.ninku_rounded = 0.0

    area_for_materials = st.session_state.total_construction_area
    results_data = []
    if area_for_materials > 0:
        for item_name, settings in st.session_state.material_settings.items():
            unit_name = settings["unit_name"]
            try:
                coverage_per_unit = float(settings["coverage_per_unit"])
            except (ValueError, TypeError):
                coverage_per_unit = 0.0

            if coverage_per_unit > 0:
                required_quantity_raw = area_for_materials / coverage_per_unit
                required_quantity = math.ceil(required_quantity_raw)
                results_data.append({
                    "項目": item_name,
                    "設定単位": unit_name,
                    "設定カバー面積/単位(㎡)": f"{coverage_per_unit:.2f}",
                    "必要数量 (切り上げ)": f"{required_quantity} {unit_name}"
                })
            else:
                results_data.append({
                    "項目": item_name,
                    "設定単位": unit_name,
                    "設定カバー面積/単位(㎡)": "0または未設定",
                    "必要数量 (切り上げ)": "計算不可"
                })
    st.session_state.material_requirements_results = results_data

# --- OCR処理関数 ---
def ocr_image_for_dimensions(image):
    # 日本語OCRを有効にする場合は lang='jpn+eng' などと設定
    # ただし、Streamlit CloudのTesseractに日本語言語パックがインストールされている必要があります
    text = pytesseract.image_to_string(image, lang=\'eng\')
    st.write("OCR結果 (生データ):")
    st.code(text)
    
    extracted_h = 0.0
    extracted_w_list = []

    # Hの抽出 (例: H: 12.3 の形式を想定)
    h_match = re.search(r'[Hh]:\s*([0-9.]+)', text)
    if h_match:
        try:
            extracted_h = float(h_match.group(1))
        except ValueError:
            pass

    # Wの抽出 (例: W: 12.3, 4.5, 6.7 の形式を想定)
    # 複数行にわたるWの値を考慮し、全ての行からWを抽出
    w_matches = re.findall(r'[Ww]:\s*([0-9.,\s]+)', text)
    for match_str in w_matches:
        # カンマやスペースで区切られた数値を個別に抽出
        for val_str in re.findall(r'[0-9.]+', match_str):
            try:
                extracted_w_list.append(float(val_str))
            except ValueError:
                pass

    return extracted_h, extracted_w_list

# --- UIの描画 ---
st.set_page_config(layout="wide")
st.title("施工面積・人工計算 兼 材料必要数量計算アプリ")

with st.sidebar:
    st.header("共通設定")
    new_kijun = st.number_input(
        "人工計算基準値 (㎡/人日):",
        min_value=0.1,
        value=st.session_state.ninku_kijun,
        step=0.1,
        format="%.1f",
        key="config_ninku_kijun_input"
    )
    if new_kijun != st.session_state.ninku_kijun:
        st.session_state.ninku_kijun = new_kijun

    if st.button("全入力クリア", key="clear_all_sidebar"):
        if 'confirm_clear' not in st.session_state:
            st.session_state.confirm_clear = False

        if st.session_state.confirm_clear:
            initialize_state()
            st.session_state.confirm_clear = False
            st.success("全ての入力データと設定をクリアしました。")
            st.rerun()
        else:
            st.warning("本当に全てのデータをクリアしますか？ もう一度ボタンを押すと実行されます。")
            st.session_state.confirm_clear = True

st.header("1. 施工エリア情報入力")

# --- 画像アップロードとOCR機能 ---
st.subheader("画像からWとHを読み込む (OCR)")
uploaded_file = st.file_uploader("平面詳細図の画像をアップロードしてください", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_column_width=True)
    
    if st.button("OCRを実行してWとHを抽出"): # OCR実行ボタンを追加
        extracted_h, extracted_w_list = ocr_image_for_dimensions(image)
        
        st.write(f"抽出された高さ H: {extracted_h:.2f} m")
        st.write(f"抽出された長さ W: {extracted_w_list} m")

        # 抽出された値を既存のエリア情報に自動入力するオプション
        if st.session_state.areas:
            st.session_state.areas[0]['height'] = extracted_h
            # Wの値を既存のlengthsリストにできるだけ多く入力
            for idx, val in enumerate(extracted_w_list):
                if idx < len(st.session_state.areas[0]['lengths']):
                    st.session_state.areas[0]['lengths'][idx] = val
                else:
                    break # lengthsリストのサイズを超える場合は停止
            st.success("抽出された値をエリア1に自動入力しました。")
            st.rerun() # UIを更新して自動入力された値を表示
        else:
            st.warning("エリア情報がありません。新しいエリアを追加してからOCR結果を自動入力できます。")

for i, area_data in enumerate(st.session_state.areas):
    with st.container():
        st.markdown(f"---")
        st.subheader(f"エリア {i+1}")

        cols_header = st.columns([3, 1.5, 1, 0.8])
        area_data['place_name'] = cols_header[0].text_input(
            f"場所名",
            value=area_data.get('place_name', ''),
            key=f"place_name_{i}"
        )
        area_data['height'] = cols_header[1].number_input(
            f"高さ H (m)",
            min_value=0.0,
            value=float(area_data.get('height', 0.0)),
            step=0.1,
            format="%.2f",
            key=f"height_{i}"
        )

        if len(st.session_state.areas) > 1:
            if cols_header[3].button("このエリアを削除", key=f"remove_area_{i}"):
                st.session_state.areas.pop(i)
                st.session_state.confirm_clear = False # クリア確認状態をリセット
                st.rerun()

        st.markdown("##### 長さ W (m) - 最大10箇所")
        cols_w = st.columns(5)
        for j in range(10):
            with cols_w[j % 5]:
                current_length_val = area_data['lengths'][j]
                if not isinstance(current_length_val, (int, float)):
                    current_length_val = 0.0
                area_data['lengths'][j] = st.number_input(
                    f"W{j+1}",
                    min_value=0.0,
                    value=float(current_length_val),
                    step=0.1,
                    format="%.2f",
                    key=f"length_{i}_{j}"
                )

        current_area_calc = calculate_area_for_single_area(area_data)
        st.markdown(f"**このエリアの面積: {current_area_calc:.2f} ㎡**")


if st.button("＋ エリア追加", key="add_area_main"):
    st.session_state.areas.append({
        'place_name': '', 'height': 0.0, 'lengths': [0.0] * 10, 'area': 0.0
    })
    st.session_state.confirm_clear = False # クリア確認状態をリセット
    st.rerun()

st.divider()

st.header("2. 材料設定")
st.caption("ここで設定した各材料のカバー面積/単位は、上記の総施工面積に対して適用されます。単位やカバー面積は実際の材料に合わせて調整してください。")

material_keys = list(st.session_state.material_settings.keys())
for item_name in material_keys:
    st.markdown(f"**{item_name}**")
    col_unit, col_coverage = st.columns([1,2])
    with col_unit:
        key_suffix = item_name.replace(' ', '_').replace('軽量', 'keiryo').replace('ファイバーテープ', 'fiber_tape').replace('下パテ', 'shita_pate').replace('上パテ', 'ue_pate').replace('下塗り', 'shita_nuri').replace('中塗り', 'naka_nuri').replace('上塗り', 'ue_nuri')
        new_unit_name = st.text_input(
            f"単位名:",
            value=st.session_state.material_settings[item_name]["unit_name"],
            key=f"material_unit_name_{key_suffix}"
        )
        st.session_state.material_settings[item_name]["unit_name"] = new_unit_name
    with col_coverage:
        new_coverage = st.number_input(
            f"1単位あたりカバー面積(㎡):",
            min_value=0.01,
            value=float(st.session_state.material_settings[item_name]["coverage_per_unit"]),
            step=0.01,
            format="%.2f",
            key=f"material_coverage_{key_suffix}"
        )
        st.session_state.material_settings[item_name]["coverage_per_unit"] = new_coverage
    st.caption("")

st.divider()

calculate_all()

st.header("3. 計算結果")

st.subheader("施工面積と必要人工")
col_area, col_ninku = st.columns(2)
col_area.metric(label="総施工面積", value=f"{st.session_state.get('total_construction_area', 0.0):.2f} ㎡")
col_ninku.metric(
    label="想定必要人工",
    value=f"{st.session_state.get('ninku_rounded', 0.0):.1f} 人日",
    delta=f"基準値: {st.session_state.ninku_kijun:.1f} ㎡/人日",
    delta_color="off"
)

st.markdown("---")

st.subheader("材料別 必要数量")
if st.session_state.total_construction_area > 0 and st.session_state.material_requirements_results:
    st.table(st.session_state.material_requirements_results)
elif st.session_state.total_construction_area <= 0:
    st.warning("総施工面積が0㎡のため、材料の必要数量は計算されません。エリア情報を入力してください。")
else:
    st.info("材料の必要数量が表示されます。")
