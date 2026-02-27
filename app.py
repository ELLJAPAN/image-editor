import streamlit as st
from PIL import Image, ImageEnhance
import io
import zipfile

# --- ライブラリ確認 ---
try:
    from rembg import remove
except ImportError:
    st.error("必須ライブラリ 'rembg' がありません。")
    st.stop()

try:
    from streamlit_cropper import st_cropper
except ImportError:
    st.error("必須ライブラリ 'streamlit-cropper' がありません。")
    st.stop()

# --- ページ設定 ---
st.set_page_config(page_title="EC画像加工ツール (eBay対応)", page_icon="🛍️", layout="wide")

# --- セッション状態の初期化 (リセット機能用) ---
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

def reset_app():
    """アプリの状態をリセットする関数"""
    st.session_state.uploader_key += 1
    st.rerun()

def make_square(image, fill_color=(255, 255, 255)):
    """画像を正方形のキャンバスの中央に配置する関数"""
    width, height = image.size
    new_size = max(width, height)
    new_image = Image.new("RGB", (new_size, new_size), fill_color)
    left = (new_size - width) // 2
    top = (new_size - height) // 2
    new_image.paste(image, (left, top))
    return new_image

def process_image(image, use_rembg, erode_size, brightness, contrast, saturation, resize_mode, target_size, quality, is_ebay_mode):
    """画像処理の実行"""
    # 1. AI背景除去
    if use_rembg:
        image = remove(image, alpha_matting=True, alpha_matting_erode_size=erode_size)

    # 2. 背景処理 (透明部分を白にする)
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        alpha = image.convert('RGBA').split()[-1]
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=alpha)
        image = bg
    else:
        image = image.convert('RGB')

    # 3. eBayモードなら正方形化
    if is_ebay_mode:
        width, height = image.size
        if height > width:
            image = make_square(image, fill_color=(255, 255, 255))

    # 4. 画質調整
    if brightness != 1.0:
        image = ImageEnhance.Brightness(image).enhance(brightness)
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    if saturation != 1.0:
        image = ImageEnhance.Color(image).enhance(saturation)

    # 5. リサイズ処理
    width, height = image.size
    new_width, new_height = width, height

    if resize_mode == "500px以上を確保":
        min_size = 500
        if width < min_size or height < min_size:
            ratio = max(min_size / width, min_size / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
    elif resize_mode == "長辺を指定サイズに統一":
        if width >= height:
            ratio = target_size / width
            new_width = target_size
            new_height = int(height * ratio)
        else:
            ratio = target_size / height
            new_width = int(width * ratio)
            new_height = target_size

    if (new_width, new_height) != (width, height):
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 6. JPEG化
    output_buffer = io.BytesIO()
    image.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    return output_buffer.getvalue()

# --- サイドバー設定 ---
with st.sidebar:
    st.header("⚙️ 設定パネル")

    # 1. eBayモード
    st.subheader("🛍️ eBayモード")
    ebay_mode = st.toggle("eBay出品用に規格を統一する", value=False,
                          help="ONにすると、1600pxの高画質JPEGに設定されます。さらに、縦長の画像は自動的に白背景を足して正方形に補正されます。")
    st.divider()

    # 2. AI背景除去
    st.subheader("🤖 AI処理")
    use_rembg = st.checkbox("背景を自動で削除して白くする", value=False)
    if use_rembg:
        erode_size = st.slider("境界線の調整", 0, 25, 10, 1)
    else:
        erode_size = 10
    st.divider()

    # 3. 変動する設定項目
    if ebay_mode:
        st.info("eBayモード: ON\n・サイズ1600px / 高画質\n・縦長写真は正方形に自動補正")
        target_size_val = 1600
        resize_mode = "長辺を指定サイズに統一"
        quality = 95
        st.subheader("🎨 微調整")
        brightness = st.slider("明るさ", 0.5, 2.0, 1.1, 0.1)
        contrast = st.slider("コントラスト", 0.5, 2.0, 1.1, 0.1)
        saturation = st.slider("鮮やかさ", 0.0, 2.0, 1.0, 0.1)
    else:
        st.subheader("🎨 画質調整")
        brightness = st.slider("明るさ", 0.5, 2.0, 1.0, 0.1)
        contrast = st.slider("コントラスト", 0.5, 2.0, 1.0, 0.1)
        saturation = st.slider("鮮やかさ", 0.0, 2.0, 1.0, 0.1)
        st.divider()

        st.subheader("📏 リサイズ設定")
        resize_mode = st.radio("モード選択", ["500px以上を確保", "長辺を指定サイズに統一", "リサイズしない"])
        target_size_val = 1000
        if resize_mode == "長辺を指定サイズに統一":
            target_size_val = st.slider("長辺のピクセル数", 500, 4000, 1280, 100)
        st.divider()

        st.subheader("💾 出力設定")
        quality = st.slider("JPEG画質", 10, 100, 85, 5)

    st.divider()
    st.button("🗑️ 全てリセット", on_click=reset_app, type="secondary", use_container_width=True)

# --- メイン画面 ---
st.title("🛍️ EC画像加工ツール (eBay対応)")
st.markdown("""
画像をアップロードして、**トリミング**、**AI背景除去**、**リサイズ**を一括処理します。
eBayモードをONにすると、縦長の画像も自動的に正方形に補正されます。
""")

uploaded_files = st.file_uploader(
    "ここに画像をドラッグ＆ドロップ (複数可)",
    type=['png', 'jpg', 'jpeg', 'webp'],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

if uploaded_files:
    should_crop = False
    cropped_image_obj = None

    st.divider()
    st.subheader(f"🖼️ アップロード画像の確認 ({len(uploaded_files)}枚)")

    if len(uploaded_files) == 1:
        img = Image.open(uploaded_files[0])
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(img, caption="元画像", use_container_width=True)
        with col2:
            st.write("🔧 オプション")
            do_crop = st.checkbox("✂️ この画像をカット（トリミング）する", value=False)
            if do_crop:
                st.write("左の画像ではなく、**下に表示される画像**を操作してください↓")

        if do_crop:
            st.warning("👇 マウスで範囲を選択してください")
            cropped_image_obj = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
            should_crop = True
    else:
        cols = st.columns(3)
        for i, uploaded_file in enumerate(uploaded_files):
            img = Image.open(uploaded_file)
            with cols[i % 3]:
                st.image(img, caption=f"{i+1}. {uploaded_file.name}", use_container_width=True)

    st.divider()
    if st.button("🚀 変換を実行する", type="primary"):
        zip_buffer = io.BytesIO()
        processed_count = 0
        progress_bar = st.progress(0)
        st.subheader("👇 変換結果")
        result_cols = st.columns(3)

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, uploaded_file in enumerate(uploaded_files):
                progress_bar.progress((i) / len(uploaded_files))

                if should_crop and i == 0 and cropped_image_obj is not None:
                    input_image = cropped_image_obj
                else:
                    input_image = Image.open(uploaded_file)

                with st.spinner(f"処理中... {uploaded_file.name}"):
                    processed_data = process_image(
                        input_image.copy(),
                        use_rembg=use_rembg,
                        erode_size=erode_size,
                        brightness=brightness,
                        contrast=contrast,
                        saturation=saturation,
                        resize_mode=resize_mode,
                        target_size=target_size_val,
                        quality=quality,
                        is_ebay_mode=ebay_mode
                    )

                with result_cols[i % 3]:
                    st.image(processed_data, caption=f"完了: {uploaded_file.name}", use_container_width=True)

                filename_base = uploaded_file.name.rsplit('.', 1)[0]
                zf.writestr(f"{filename_base}_ebay.jpg", processed_data)
                processed_count += 1

        progress_bar.progress(100)

        if processed_count > 0:
            zip_buffer.seek(0)
            st.success("🎉 すべて完了しました！")
            st.download_button("📦 まとめてダウンロード (ZIP)", zip_buffer, "ebay_images.zip", "application/zip", type="primary")
