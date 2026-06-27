import os
import json
import glob
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GH_MODELS_TOKEN"],
)

# 目标语言列表（包含东南亚核心语言）
TARGET_LANGS = ["zh", "en", "ms", "id", "th", "vi", "tl", "my", "km", "lo", "ja", "ko", "es", "fr", "de", "hi", "ru"]

def translate_formula(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    prompt = f"""
    You are a professional engineering translator. Translate the following formula data into these languages: {', '.join(TARGET_LANGS)}.

    Mandatory Rules:
    1. For the 'remarks' field in every language EXCEPT the original language, you MUST append a disclaimer at the end:
       "(AI translated, please check for accuracy)" 
       (Translate this disclaimer into the target language).
    2. Keep construction terms precise (e.g., 'joist', 'stud', 'spacing').
    3. Return ONLY a valid JSON object. Do not change 'id', 'expression', 'authorUid', or 'version'.
    4. Ensure all keys {TARGET_LANGS} exist in both 'name' and 'remarks' objects.

    Input Data:
    {json.dumps(data, ensure_ascii=False, indent=2)}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional translator for a building tool. Output raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        translated_data = json.loads(response.choices[0].message.content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(translated_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Success: {file_path}")
        
    except Exception as e:
        print(f"❌ Error: {file_path} - {e}")

# 执行逻辑
for file in glob.glob("formulas/*.json"):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        # 如果任何一种语言缺失，则触发 AI
        if any(f'"{lang}":' not in content or f'"{lang}": ""' in content for lang in TARGET_LANGS):
            translate_formula(file)
