/**
 * sync_script_automated.js
 * 自动从 Firestore 的 'formulas' 集合同步数据到 GitHub
 */
const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

// 校验环境变量
if (!process.env.FIREBASE_SERVICE_ACCOUNT) {
    console.error('错误: 缺少 FIREBASE_SERVICE_ACCOUNT 环境变量。');
    process.exit(1);
}

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

async function sync() {
    console.log('正在从 Firestore (formulas 集合) 拉取公式...');

    const snapshot = await db.collection('formulas')
        .where('status', '==', 'active')
        .get();

    if (snapshot.empty) {
        console.log('未发现状态为 active 的公式。跳过更新。');
        return;
    }

    const formulasDir = path.join(__dirname, 'formulas');
    if (!fs.existsSync(formulasDir)) {
        fs.mkdirSync(formulasDir, { recursive: true });
    }

    let formulaList = [];

    snapshot.forEach(doc => {
        const formulaData = doc.data();
        const formulaId = doc.id;

        // 1. 清理数据（移除 Firebase 特有字段）
        const cleanData = { ...formulaData };
        delete cleanData.timestamp;
        delete cleanData.authorUid; 

        // 确保 ID 一致性
        if (!cleanData.id) cleanData.id = formulaId;

        // 2. 写入单个 .json 文件（用于 App 详情下载）
        fs.writeFileSync(
            path.join(formulasDir, `${formulaId}.json`),
            JSON.stringify(cleanData, null, 2)
        );

        // 3. 构建索引数据（必须包含 MarketplaceRepositoryImpl 需要的所有字段）
        formulaList.push({
            id: cleanData.id,
            version: cleanData.version || 1,
            category: cleanData.category || 'General',
            name: cleanData.name,         // 这里已经是 {en: "...", zh: "..."} 格式
            remarks: cleanData.remarks,   // 这里已经是 {en: "...", zh: "..."} 格式
            factors: cleanData.factors,   // 数组格式
            expression: cleanData.expression,
            author: cleanData.author || 'Anonymous',
            // 额外同步统计信息
            download_count: cleanData.download_count || 0,
            rating_count: cleanData.rating_count || 0,
            rating_sum: cleanData.rating_sum || 0
        });
    });

    // 4. 按名称排序（让 index.json 顺序固定，防止 Git 产生无意义的冲突）
    formulaList.sort((a, b) => {
        const nameA = (a.name.en || '').toUpperCase();
        const nameB = (b.name.en || '').toUpperCase();
        return nameA.localeCompare(nameB);
    });

    // 5. 生成目录文件
    const catalog = {
        lastUpdated: new Date().toISOString(),
        formulas: formulaList
    };

    fs.writeFileSync(
        path.join(__dirname, 'index.json'),
        JSON.stringify(catalog, null, 2)
    );

    console.log(`同步成功！共更新了 ${formulaList.length} 个公式。`);
}

sync().catch(err => {
    console.error('同步进程崩溃:', err);
    process.exit(1);
});
