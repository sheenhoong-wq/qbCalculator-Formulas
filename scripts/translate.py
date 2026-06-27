import os
import json
import glob
import time
import subprocess
from datetime import datetime
from openai import OpenAI

# --- 配置区 ---
# 每次修改提示词(Prompt)或增加新语言，请将此版本号+1，脚本会强制重新审计所有公式
CURRENT_ENGINE_VER = 5 
INDEX_FILE = "index.json"
FORMULAS_DIR = "formulas"

# 初始化 GitHub Models 客户端
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GH_MODELS_TOKEN", ""),
)

# 定义支持的所有 17 种语言
TARGET_LANGS = [
    "zh", "en", "ms", "id", "th", "vi", "tl", "my", "km", "lo", 
    "ja", "ko", "es", "fr", "de", "hi", "ru"
]

def get_changed_files():
    """利用 Git 获取最近一次提交中变动的公式文件"""
    try:
        output = subprocess.check_output(['git', 'log', '-1', '--name-only', '--pretty=format:'], text=True)
        files = [f.strip() for f in output.splitlines() if f.startswith(f'{FORMULAS_DIR}/') and f.endswith('.json')]
        if files:
            print(f"🎯 Detected {len(files)} changed files in the last commit.")
            return files
    except:
        pass
    
    # 第一次运行或手动触发时，扫描所有文件
    print("🔍 Scanning all formulas (Skip logic will apply)...")
    return glob.glob(f"{FORMULAS_DIR}/*.json")

def update_index_entry(formula_data):
    """将翻译好的多语言内容同步回主索引文件 index.json"""
    if not os.path.exists(INDEX_FILE):
        print(f"⚠️ {INDEX_FILE} not found, skipping index update.")
        return

    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        updated = False
        if "formulas" in index_data:
            for i, item in enumerate(index_data["formulas"]):
                if item.get("id") == formula_data.get("id"):
                    # 同步翻译后的名称和备注
                    index_data["formulas"][i]["name"] = formula_data["name"]
                    index_data["formulas"][i]["remarks"] = formula_data["remarks"]
                    updated = True
                    break
        
        if updated:
            index_data["lastUpdated"] = datetime.now().isoformat()
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            print(f"📌 Updated {INDEX_FILE} entry for: {formula_data.get('id')}")
    except Exception as e:
        print(f"❌ Failed to update index: {e}")

def translate_file(file_path):
    """核心函数：审计、翻译、保存并同步索引"""
    if not os.path.exists(file_path): return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ Skip {file_path}: Invalid JSON. {e}")
        return

    # 版本检查
    meta = data.get("translation_meta", {})
    current_formula_ver = data.get("version", 1)
    
    # 只有当引擎升级或公式版本变动时，才调用 AI
    # 同时检查 17 种语言是否真的都存在（防止之前截断的情况）
    has_all_langs = all(lang in data.get("remarks", {}) for lang in TARGET_LANGS)
    
    if meta.get("engine_ver", 0) == CURRENT_ENGINE_VER and meta.get("formula_ver", 0) == current_formula_ver and has_all_langs:
        # 虽然不调 AI，但依然尝试同步回索引，确保 index.json 也是最新的
        update_index_entry(data)
        return

    print(f"🔄 Processing: {file_path} (AI Audit & Translate)...")

    prompt = f"""
    You are a professional engineering translator. 
    Audit and translate the 'name' and 'remarks' fields for EXACTLY these 17 languages: {', '.join(TARGET_LANGS)}.

    RULES:
    1. **LANGUAGE AUDIT**: Move text to the correct language key if it is misplaced (e.g., Chinese in 'en').
    2. **COMPLETENESS**: You MUST provide all 17 language keys in the output. NEVER truncate.
    3. **DISCLAIMER**: For all newly translated or corrected fields, append "(AI translated, please check)" at the end in that specific target language.
    4. **SECURITY**: NEVER MODIFY the 'expression', 'id', 'authorUid', 'version', or 'author' fields. 
    5. **TECHNICAL**: Use precise terminology for construction, carpentry, and finance.
    6. **OUTPUT**: Return ONLY a valid minified JSON object.

    Input Data:
    {json.dumps(data, ensure_ascii=False)}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional translator for a calculator app. You provide complete, accurate, non-truncated JSON."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        ai_data = json.loads(response.choices[0].message.content)
        
        # 安全合并：使用 update 确保即便 AI 少回了几种语言，原本已有的也不会丢失
        if "name" in ai_data:
            if not isinstance(data.get("name"), dict): data["name"] = {}
            data["name"].update(ai_data["name"])
            
        if "remarks" in ai_data:
            if not isinstance(data.get("remarks"), dict): data["remarks"] = {}
            data["remarks"].update(ai_data["remarks"])
        
        # 更新翻译元数据
        data["translation_meta"] = {
            "engine_ver": CURRENT_ENGINE_VER,
            "formula_ver": current_formula_ver,
            "updated_at": datetime.now().isoformat()
        }
        
        # 保存单个公式文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # 同步回 index.json
        update_index_entry(data)
        
        print(f"✨ Successfully processed: {file_path}")
        time.sleep(0.5) # 稍微延迟，尊重 API 频率限制
        
    except Exception as e:
        print(f"❌ Error translating {file_path}: {e}")

# --- 执行入口 ---
if __name__ == "__main__":
    if not os.path.exists(FORMULAS_DIR):
        print(f"Error: {FORMULAS_DIR} directory not found.")
    else:
        files_to_process = get_changed_files()
        for file in files_to_process:
            translate_file(file)
        print("🚀 All tasks completed.")
