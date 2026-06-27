import os
import json
import glob
import time
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GH_MODELS_TOKEN"],
)

# 定义需要翻译的所有语言
TARGET_LANGS = ["zh", "en", "ms", "id", "th", "vi", "tl", "my", "km", "lo", "ja", "ko", "es", "fr", "de", "hi", "ru"]

def translate_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ Skip {file_path}: Invalid JSON. {e}")
        return

    # 检查是否有任何语言版本缺失或为空
    needs_translate = False
    for field in ['name', 'remarks']:
        content_map = data.get(field, {})
        for lang in TARGET_LANGS:
            if lang not in content_map or not str(content_map.get(lang)).strip():
                needs_translate = True
                break
        if needs_translate: break

    if not needs_translate:
        print(f"✅ {file_path} is already fully translated.")
        return

    print(f"🔄 AI Translating: {file_path}...")

    # 构造翻译请求
    prompt = f"""
    You are an expert construction/carpentry translator. 
    Complete the 'name' and 'remarks' fields for all these languages: {', '.join(TARGET_LANGS)}.

    Input Data:
    {json.dumps(data, ensure_ascii=False)}

    Rules:
    1. For 'remarks', in every target language, append "(AI translated, please check)" at the end.
    2. Ensure the output is a valid JSON object.
    3. Keep technical terms professional.
    4. Do not modify: 'id', 'expression', 'authorUid', 'version', 'category', 'author'.
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional JSON translator. Return raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        ai_data = json.loads(response.choices[0].message.content)
        
        # 安全合并数据
        if "name" in ai_data: data["name"] = ai_data["name"]
        if "remarks" in ai_data: data["remarks"] = ai_data["remarks"]
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✨ Successfully updated {file_path}")
        
        # 避免 GitHub Models 频率限制
        time.sleep(1) 
        
    except Exception as e:
        print(f"❌ Error translating {file_path}: {e}")

# 核心逻辑：扫描 formulas 目录下所有的 json 文件
files = glob.glob("formulas/*.json")
print(f"🔍 Found {len(files)} formula files. Starting scan...")
for file in files:
    translate_file(file)
