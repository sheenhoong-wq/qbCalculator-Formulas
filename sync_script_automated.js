/**
 * sync_script_automated.js
 * 自动从 Firestore 的 'formulas' 集合同步数据
 */
const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

async function sync() {
    console.log('Fetching formulas from Firestore (collection: formulas)...');

    // 修改点 1: 改为读取 'formulas' 集合，状态为 'active'
    const snapshot = await db.collection('formulas')
        .where('status', '==', 'active')
        .get();

    const formulasDir = path.join(__dirname, 'formulas');
    if (!fs.existsSync(formulasDir)) fs.mkdirSync(formulasDir, { recursive: true });

    let formulaList = [];

    snapshot.forEach(doc => {
        // 修改点 2: 直接获取 doc.data()，因为 App 现在直接平铺写入数据
        const formulaData = doc.data();
        const formulaId = doc.id;

        // 修改点 3: 移除 Firebase 专用字段，保持 JSON 纯净
        const cleanData = { ...formulaData };
        delete cleanData.timestamp; 

        // 写入单个 .json 文件
        fs.writeFileSync(
            path.join(formulasDir, `${formulaId}.json`),
            JSON.stringify(cleanData, null, 2)
        );

        // 添加到索引，结构需匹配 MarketplaceRepositoryImpl 的解析要求
        formulaList.push({
            id: cleanData.id || formulaId,
            name: cleanData.name,
            category: cleanData.category,
            author: cleanData.author,
            version: cleanData.version,
            remarks: cleanData.remarks,
            factors: cleanData.factors,
            expression: cleanData.expression
        });
    });

    // 更新 index.json
    const catalog = {
        lastUpdated: new Date().toISOString(),
        formulas: formulaList
    };

    fs.writeFileSync(
        path.join(__dirname, 'index.json'),
        JSON.stringify(catalog, null, 2)
    );

    console.log(`Successfully synced ${formulaList.length} formulas to GitHub.`);
}

sync().catch(err => {
    console.error('Sync failed:', err);
    process.exit(1);
});
