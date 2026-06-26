/**
 * sync_script_automated.js
 * 终极健壮版：自动同步 Firestore 数据到 GitHub，确保 App 100% 兼容
 */
const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

if (!process.env.FIREBASE_SERVICE_ACCOUNT) {
    console.error('错误: 缺少 FIREBASE_SERVICE_ACCOUNT 环境变量。');
    process.exit(1);
}

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
const db = admin.firestore();

async function sync() {
    console.log('正在拉取公式...');
    const snapshot = await db.collection('formulas').where('status', '==', 'active').get();
    if (snapshot.empty) return;

    const formulasDir = path.join(__dirname, 'formulas');
    if (fs.existsSync(formulasDir)) fs.rmSync(formulasDir, { recursive: true, force: true });
    fs.mkdirSync(formulasDir, { recursive: true });

    let formulaList = [];
    snapshot.forEach(doc => {
        const data = doc.data();
        const formulaId = doc.id;

        // --- 1. 结构标准化：确保 name/remarks 永远是对象而非字符串 ---
        const ensureLocalized = (val, defaultText) => {
            if (typeof val === 'object' && val !== null) return { zh: val.zh || "", en: val.en || "", ms: val.ms || "" };
            return { zh: val || defaultText, en: val || defaultText, ms: val || defaultText };
        };

        const author = data.author || 'Anonymous';
        const nameObj = ensureLocalized(data.name, 'Unnamed Formula');
        const remarksObj = ensureLocalized(data.remarks, '');
        
        // 生成安全文件名 (支持中文)
        const displayTitle = nameObj.zh || nameObj.en || 'Formula';
        const safeAuthor = author.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        const safeName = displayTitle.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        const readableFileName = `${safeAuthor}_${safeName}.json`;

        // --- 2. 构建干净的数据供下载 ---
        const cleanData = {
            ...data,
            id: formulaId,
            name: nameObj,
            remarks: remarksObj,
            factors: Array.isArray(data.factors) ? data.factors : []
        };
        delete cleanData.timestamp;
        delete cleanData.updatedAt;
        
        fs.writeFileSync(path.join(formulasDir, readableFileName), JSON.stringify(cleanData, null, 2));

        // --- 3. 构建索引 (这是手机显示的源头) ---
        formulaList.push({
            id: formulaId,
            file_name: readableFileName,
            version: data.version || 1,
            category: data.category || 'General',
            name: nameObj,
            remarks: remarksObj,
            factors: cleanData.factors,
            expression: data.expression || "",
            author: author,
            authorUid: data.authorUid || null, // 重要：没有这个在别的手机下架不了
            rating: Number(data.rating || 0),
            download_count: Number(data.download_count || 0)
        });
    });

    // 按名称排序
    formulaList.sort((a, b) => (a.name.zh || a.name.en).localeCompare(b.name.zh || b.name.en, 'zh'));

    const catalog = { lastUpdated: new Date().toISOString(), formulas: formulaList };
    fs.writeFileSync(path.join(__dirname, 'index.json'), JSON.stringify(catalog, null, 2));
    console.log(`同步成功！已整理 ${formulaList.length} 个公式。`);
}

sync().catch(err => { console.error(err); process.exit(1); });
