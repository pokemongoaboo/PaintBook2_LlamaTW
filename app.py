import streamlit as st
from openai import OpenAI
import time
import random
import json
import ast
import re


# 設置OpenAI客戶端
client = OpenAI(
    base_url = "https://integrate.api.nvidia.com/v1",
    api_key=st.secrets["OPENAI_API_KEY"]
)

# 主角選項
characters = ["貓咪", "狗狗", "花花", "小鳥", "小石頭"]

# 主題選項
themes = ["親情", "友情", "冒險", "度假", "運動比賽"]

# 頁面設置
st.set_page_config(page_title="互動式繪本生成器", layout="wide")
st.title("互動式繪本生成器")

# 選擇或輸入主角
character = st.selectbox("選擇或輸入繪本主角:", characters + ["其他"])
if character == "其他":
    character = st.text_input("請輸入自定義主角:")

# 選擇或輸入主題
theme = st.selectbox("選擇或輸入繪本主題:", themes + ["其他"])
if theme == "其他":
    theme = st.text_input("請輸入自定義主題:")

# 選擇頁數
page_count = st.slider("選擇繪本頁數:", min_value=6, max_value=12, value=8)


def generate_plot_points(character, theme):
    prompt = f"""為一個關於{character}的{theme}故事生成3到5個可能的故事轉折重點。
    每個重點應該簡短而有趣。
    請直接列出轉折重點，每個轉折點佔一行，不要加入額外的說明或編號。
    例如：
    主角遇到一個神秘的陌生人
    意外發現一個魔法物品
    朋友陷入危險需要救援
    """
    response = client.chat.completions.create(
        model="yentinglin/llama-3-taiwan-70b-instruct",
        messages=[{"role": "user", "content": prompt}]
    )
    plot_points = response.choices[0].message.content.split('\n')
    # 移除空行和可能的前導/尾隨空白
    plot_points = [point.strip() for point in plot_points if point.strip()]
    
    # 調試輸出
    #st.write("生成的原始轉折重點：")
    #st.write(response.choices[0].message.content)
    #st.write("處理後的轉折重點列表：")
    #st.write(plot_points)
    
    return plot_points

# 生成並選擇故事轉折重點
if st.button("生成故事轉折重點選項"):
    plot_points = generate_plot_points(character, theme)
    if plot_points:
        st.session_state.plot_points = plot_points
    else:
        st.error("未能生成有效的轉折重點。請重試。")

if 'plot_points' in st.session_state:
    plot_point = st.selectbox("選擇或輸入繪本故事轉折重點:", 
                              ["請選擇"] + st.session_state.plot_points + ["其他"])
    if plot_point == "其他":
        plot_point = st.text_input("請輸入自定義故事轉折重點:")
    elif plot_point == "請選擇":
        st.warning("請選擇一個轉折重點或輸入自定義轉折重點。")

# 生成故事函數
def generate_story(character, theme, plot_point, page_count):
    prompt = f"""
    請你角色扮演成一個暢銷的童書繪本作家，你擅長以孩童的純真眼光看這世界，製作出許多溫暖人心的作品。
    請以下列主題：{theme}發想故事，
    在{page_count}的篇幅內，
    說明一個{character}的故事，
    並注意在倒數第三頁加入{plot_point}的元素，
    最後的故事需要是溫馨、快樂的結局。
    """
    response = client.chat.completions.create(
        model="yentinglin/llama-3-taiwan-70b-instruct",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成分頁故事函數
def generate_paged_story(story, page_count, character, theme, plot_point):
    prompt = f"""
    將以下故事大綱細分至預計{page_count}個跨頁的篇幅，每頁需要包括(text，image_prompt)，
    {page_count-3}(倒數第三頁)才可以出現{plot_point}，
    在這之前應該要讓{character}的{theme}世界發展故事更多元化。
    請以JSON格式回覆，格式如下：
    [
        {{"text": "第一頁的文字", "image_prompt": "第一頁的圖像提示"}},
        {{"text": "第二頁的文字", "image_prompt": "第二頁的圖像提示"}},
        ...
    ]

    故事：
    {story}
    """
    response = client.chat.completions.create(
        model="yentinglin/llama-3-taiwan-70b-instruct",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成風格基礎函數
def generate_style_base(story):
    prompt = f"""
    基於以下故事，請思考大方向上你想要呈現的視覺效果，這是你用來統一整體繪本風格的描述，請盡量精簡，使用英文撰寫：

    {story}
    """
    response = client.chat.completions.create(
        model="yentinglin/llama-3-taiwan-70b-instruct",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 生成圖片函數
def generate_image(image_prompt, style_base):
    final_prompt = f"""
    Based on the image prompt: "{image_prompt}" and the style base: "{style_base}",
    please create a detailed image description including color scheme, background details, specific style, and scene details.
    Describe the current color, shape, and features of the main character.
    Include at least 3 effect words (lighting effects, color tones, rendering effects, visual styles) and 1 or more composition techniques.
    Set a random seed value of 42. Ensure no text appears in the image.
    """
    response = client.images.generate(
        model="dall-e-3",
        prompt=final_prompt,
        size="1024x1024",
        n=1
    )
    return response.data[0].url


def preprocess_json(json_string):
    # 移除可能的 Markdown 代碼塊標記
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'\s*```', '', json_string)
    
    # 移除開頭和結尾的空白字符
    json_string = json_string.strip()
    
    # 確保 JSON 字符串以 [ 開始並以 ] 結束
    if not json_string.startswith('['):
        json_string = '[' + json_string
    if not json_string.endswith(']'):
        json_string = json_string + ']'
    
    return json_string

# 主要生成流程
if st.button("生成繪本"):
    try:
        with st.spinner("正在生成故事..."):
            story = generate_story(character, theme, plot_point, page_count)
            st.write("故事大綱：", story)

        with st.spinner("正在分頁故事..."):
            paged_story = generate_paged_story(story, page_count, character, theme, plot_point)
            #st.write("分頁故事（原始）：", paged_story)

        with st.spinner("正在生成風格基礎..."):
            style_base = generate_style_base(story)
            #st.write("風格基礎：", style_base)

        # 預處理 JSON 字符串
        processed_paged_story = preprocess_json(paged_story)
        
        st.write("處理後的 JSON 字符串：")
        st.code(processed_paged_story)
        
        pages = json.loads(processed_paged_story)
        
        if not isinstance(pages, list):
            raise ValueError("解析後的結果不是列表")
        
        st.success(f"成功解析 JSON。共有 {len(pages)} 頁。")

        for i, page in enumerate(pages, 1):
            st.write(f"第 {i} 頁")
            st.write("文字：", page.get('text', '無文字'))
            with st.spinner(f"正在生成第 {i} 頁的圖片..."):
                image_prompt = page.get('image_prompt', '')
                if image_prompt:
                    image_url = generate_image(image_prompt, style_base)
                    st.image(image_url, caption=f"第 {i} 頁的插圖")
                else:
                    st.warning(f"第 {i} 頁沒有圖像提示")
            time.sleep(5)  # 添加延遲以避免API限制

    except json.JSONDecodeError as e:
        st.error(f"JSON 解析錯誤：{str(e)}")
        st.text("處理後的 JSON 字符串：")
        st.code(processed_paged_story)
    except ValueError as e:
        st.error(f"值錯誤：{str(e)}")
        st.text("解析後的數據：")
        st.write(pages)
    except Exception as e:
        st.error(f"發生未知錯誤：{str(e)}")
        st.text("錯誤詳情：")
        st.exception(e)
    finally:
        st.write("生成過程完成。如果有任何錯誤，請檢查上面的錯誤信息。")
