/**
 * sync_script_automated.js
 * 终极兼容版：支持中文文件名、自动补全旧数据、确保 App 100% 显示
 */
const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

if (!process.env.FIREBASE_SERVICE_ACCOUNT) {
    console.error('Error: Missing FIREBASE_SERVICE_ACCOUNT');
    process.exit(1);
}

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
const db = admin.firestore();

async function sync() {
    console.log('开始同步公式...');
    
    // --- 关键修改：取回所有公式，不再因为缺少 status 字段而过滤 ---
    const snapshot = await db.collection('formulas').get();
    
    if (snapshot.empty) {
        console.log('数据库是空的。');
        return;
    }

    const formulasDir = path.join(__dirname, 'formulas');
    if (fs.existsSync(formulasDir)) fs.rmSync(formulasDir, { recursive: true, force: true });
    fs.mkdirSync(formulasDir, { recursive: true });

    let formulaList = [];
    snapshot.forEach(doc => {
        const data = doc.data();
        
        // 过滤掉明确标记为删除的
        if (data.status === 'deleted' || data.status === 'inactive') return;

        const formulaId = doc.id;

        // 标准化多语言字段
        const toLoc = (val) => {
            if (val && typeof val === 'object') return { zh: val.zh || "", en: val.en || "", ms: val.ms || "" };
            return { zh: val || "", en: val || "", ms: val || "" };
        };

        const nameObj = toLoc(data.name);
        const remarksObj = toLoc(data.remarks);
        const author = data.author || 'Anonymous';
        
        // 生成漂亮的中文文件名
        const title = nameObj.zh || nameObj.en || 'Unnamed';
        const safeAuthor = author.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        const safeName = title.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        const readableFileName = `${safeAuthor}_${safeName}.json`;

        // 写入单个公式文件（包含所有原始字段供下载）
        const cleanFullData = { 
            ...data, 
            id: formulaId, 
            name: nameObj, 
            remarks: remarksObj,
            file_name: readableFileName 
        };
        delete cleanFullData.timestamp;
        delete cleanFullData.updatedAt;
        fs.writeFileSync(path.join(formulasDir, readableFileName), JSON.stringify(cleanFullData, null, 2));

        // 构建 index.json 索引
        formulaList.push({
            id: formulaId,
            file_name: readableFileName,
            version: data.version || 1,
            category: data.category || 'General',
            name: nameObj,
            remarks: remarksObj,
            factors: Array.isArray(data.factors) ? data.factors.map(f => ({
                id: f.id || "",
                label: toLoc(f.label),
                unit: f.unit || null,
                defaultValue: Number(f.defaultValue || 0)
            })) : [],
            expression: data.expression || "",
            author: author,
            authorUid: data.authorUid || null,
            rating: Number(data.rating || 0)
        });
    });

    // 排序
    formulaList.sort((a, b) => (a.name.zh || a.name.en).localeCompare(b.name.zh || b.name.en, 'zh'));

    const catalog = {
        lastUpdated: new Date().toISOString(),
        formulas: formulaList
    };

    fs.writeFileSync(path.join(__dirname, 'index.json'), JSON.stringify(catalog, null, 2));
    console.log(`同步成功！共发布 ${formulaList.length} 个公式。`);
}

sync().catch(err => { console.error(err); process.exit(1); });
