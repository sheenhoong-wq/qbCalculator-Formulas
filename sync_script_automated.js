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
    const snapshot = await db.collection('formulas').where('status', '==', 'active').get();
    if (snapshot.empty) return;

    const formulasDir = path.join(__dirname, 'formulas');
    if (fs.existsSync(formulasDir)) fs.rmSync(formulasDir, { recursive: true, force: true });
    fs.mkdirSync(formulasDir, { recursive: true });

    let formulaList = [];
    snapshot.forEach(doc => {
        const data = doc.data();
        const author = data.author || 'Anonymous';
        const formulaName = (data.name && (data.name.zh || data.name.en)) || 'Unnamed';
        const safeAuthor = author.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        const safeName = formulaName.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        let readableFileName = `${safeAuthor}_${safeName}.json`;

        const cleanData = { ...data, id: doc.id };
        // 关键：保留在单个文件中
        fs.writeFileSync(path.join(formulasDir, readableFileName), JSON.stringify(cleanData, null, 2));

        // 关键：构建 index.json 索引，必须包含 authorUid 否则另一台手机无法下架
        formulaList.push({
            id: doc.id,
            file_name: readableFileName,
            version: data.version || 1,
            category: data.category || 'General',
            name: data.name || { en: formulaName },
            remarks: data.remarks || { en: "" },
            factors: data.factors || [],
            expression: data.expression || "",
            author: author,
            authorUid: data.authorUid || null, // 必须有这个，用于管理功能
            rating: data.rating || 0,
            download_count: data.download_count || 0
        });
    });

    const catalog = { lastUpdated: new Date().toISOString(), formulas: formulaList };
    fs.writeFileSync(path.join(__dirname, 'index.json'), JSON.stringify(catalog, null, 2));
    console.log(`同步成功！共更新 ${formulaList.length} 个公式。`);
}
sync().catch(err => { console.error(err); process.exit(1); });
