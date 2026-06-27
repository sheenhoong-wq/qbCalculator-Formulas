import os
import json
import glob
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GH_MODELS_TOKEN"],
)

TARGET_LANGS = ["zh", "en", "ms", "id", "th", "vi", "tl", "my", "km", "lo", "ja", "ko", "es", "fr", "de", "hi", "ru"]

def translate_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except: return

    # 检查是否真的需要翻译
    needs_work = False
    for field in ['name', 'remarks']:
        obj = data.get(field, {})
        for lang in TARGET_LANGS:
            if not obj.get(lang): # 如果不存在该语言键，或者值为空字符串
                needs_work = True
                break
    
    if not needs_work:
        return

    print(f"🔄 Processing: {file_path}")

    prompt = f"""
    You are a professional engineering translator. 
    Translate the formula 'name' and 'remarks' into these languages: {', '.join(TARGET_LANGS)}.
    
    Rules:
    1. For 'remarks', append "(AI translated, please check)" at the end in each target language.
    2. Return ONLY a valid JSON object matching the input structure.
    3. Do not change expression, id, authorUid, version, or category.
    4. Use precise construction/carpentry terms.
    
    Data to translate:
    {json.dumps(data, ensure_ascii=False)}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional translator. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        translated_result = json.loads(response.choices[0].message.content)
        
        # 安全合并：只更新翻译字段，确保其他关键字段（如 expression）绝对安全
        if "name" in translated_result: data["name"] = translated_result["name"]
        if "remarks" in translated_result: data["remarks"] = translated_result["remarks"]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Successfully translated: {file_path}")
        
    except Exception as e:
        print(f"❌ Error during translation: {e}")

# 遍历文件夹
for file in glob.glob("formulas/*.json"):
    translate_file(file)
