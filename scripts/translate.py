import os
import json
import glob
import time
from datetime import datetime
from openai import OpenAI

# --- 配置区 ---
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GH_MODELS_TOKEN"],
)

# 升级到版本 4，强制重刷并修复截断问题
CURRENT_ENGINE_VER = 4 

TARGET_LANGS = ["zh", "en", "ms", "id", "th", "vi", "tl", "my", "km", "lo", "ja", "ko", "es", "fr", "de", "hi", "ru"]

def translate_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except: return

    meta = data.get("translation_meta", {})
    if meta.get("engine_ver", 0) == CURRENT_ENGINE_VER and meta.get("formula_ver", 0) == data.get("version", 1):
        return

    print(f"🔄 Auditing & Repairing: {file_path}...")

    # 提示词优化：强调 17 种语言的完整性，防止截断
    prompt = f"""
    You are a professional engineering translator. 
    Complete the 'name' and 'remarks' fields for EXACTLY these 17 languages: {', '.join(TARGET_LANGS)}.

    Input JSON:
    {json.dumps(data, ensure_ascii=False)}

    CRITICAL RULES:
    1. **NO TRUNCATION**: You must output the entire JSON object with all 17 language keys present in both 'name' and 'remarks'.
    2. **LANGUAGE AUDIT**: If text is in the wrong key, move it to the correct one.
    3. **DISCLAIMER**: For all newly translated or corrected fields, append "(AI translated, please check)" in the target language.
    4. **SECURITY**: Do not change 'expression', 'id', 'authorUid', 'version', or 'author'.
    5. **OUTPUT**: Return ONLY a valid, complete JSON object.
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional translator. You never truncate JSON. You always provide all 17 languages."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        ai_data = json.loads(response.choices[0].message.content)
        
        # --- 增量合并逻辑 ---
        if "name" in ai_data:
            if not isinstance(data.get("name"), dict): data["name"] = {}
            data["name"].update(ai_data["name"])
            
        if "remarks" in ai_data:
            if not isinstance(data.get("remarks"), dict): data["remarks"] = {}
            data["remarks"].update(ai_data["remarks"])
        
        # 验证是否补齐了 17 种语言
        missing = [l for l in TARGET_LANGS if l not in data.get("remarks", {})]
        if missing:
            print(f"⚠️ Warning: Still missing {len(missing)} languages in remarks. Retrying might be needed.")

        data["translation_meta"] = {
            "engine_ver": CURRENT_ENGINE_VER,
            "formula_ver": data.get("version", 1),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"✨ Success: {file_path}")
        time.sleep(1) # 给 API 喘息时间
        
    except Exception as e:
        print(f"❌ Error: {file_path} - {e}")

files = glob.glob("formulas/*.json")
for file in files:
    translate_file(file)
