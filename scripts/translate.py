import os
import json
import glob
import time
import subprocess
from datetime import datetime
from openai import OpenAI

# --- 配置区 ---
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GH_MODELS_TOKEN"],
)

# 只有当你修改了 Prompt 或增加了新语言，想“全量重刷”时才改这个版本号
# 平时只需保持不变
CURRENT_ENGINE_VER = 4 

TARGET_LANGS = ["zh", "en", "ms", "id", "th", "vi", "tl", "my", "km", "lo", "ja", "ko", "es", "fr", "de", "hi", "ru"]

def get_changed_files():
    """获取最近一次 commit 中变动的公式文件"""
    try:
        # 获取最近一次提交的文件列表
        output = subprocess.check_output(['git', 'log', '-1', '--name-only', '--pretty=format:'], text=True)
        files = [f.strip() for f in output.splitlines() if f.startswith('formulas/') and f.endswith('.json')]
        if files:
            print(f"🎯 Detected {len(files)} changed files in the last commit.")
            return files
    except Exception as e:
        print(f"⚠️ Git lookup failed: {e}")
    
    # 如果 Git 检查失败（比如第一次运行），或者你是手动点击 Run Workflow
    # 则返回所有文件，但脚本内部的 Skip 逻辑依然会保护它们不被重复翻译
    print("🔍 Falling back to full directory scan (skip logic will apply).")
    return glob.glob("formulas/*.json")

def translate_file(file_path):
    if not os.path.exists(file_path): return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except: return

    # 内部双重保险：即便遍历了，如果版本号没变且翻译已补齐，也会秒跳过
    meta = data.get("translation_meta", {})
    if meta.get("engine_ver", 0) == CURRENT_ENGINE_VER and meta.get("formula_ver", 0) == data.get("version", 1):
        # 检查是否真的 17 种语言都在，防止之前有截断残留
        if all(lang in data.get("remarks", {}) for lang in TARGET_LANGS):
            return

    print(f"🔄 Processing: {file_path}...")

    prompt = f"""
    You are a professional engineering translator. 
    Complete the 'name' and 'remarks' fields for EXACTLY these 17 languages: {', '.join(TARGET_LANGS)}.

    Input JSON:
    {json.dumps(data, ensure_ascii=False)}

    CRITICAL RULES:
    1. **NO TRUNCATION**: You must output the entire JSON object with all 17 language keys present in both 'name' and 'remarks'.
    2. **LANGUAGE AUDIT**: If text is in the wrong key (e.g. Chinese in 'en'), MOVE it to the correct one first.
    3. **DISCLAIMER**: For all newly translated or corrected fields, append "(AI translated, please check)" in the target language at the end of 'remarks'.
    4. **SECURITY**: Do not change 'expression', 'id', 'authorUid', 'version', or 'author'.
    5. **OUTPUT**: Return ONLY a valid, complete JSON object.
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional JSON translator. You never truncate output."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        ai_data = json.loads(response.choices[0].message.content)
        
        # 增量合并，确保安全
        if "name" in ai_data:
            if not isinstance(data.get("name"), dict): data["name"] = {}
            data["name"].update(ai_data["name"])
            
        if "remarks" in ai_data:
            if not isinstance(data.get("remarks"), dict): data["remarks"] = {}
            data["remarks"].update(ai_data["remarks"])

        # 标记翻译元数据
        data["translation_meta"] = {
            "engine_ver": CURRENT_ENGINE_VER,
            "formula_ver": data.get("version", 1),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"✨ Successfully updated: {file_path}")
        time.sleep(1) 
        
    except Exception as e:
        print(f"❌ Error: {file_path} - {e}")

# --- 主执行逻辑 ---
files_to_process = get_changed_files()
for file in files_to_process:
    translate_file(file)
