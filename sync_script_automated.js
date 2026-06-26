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
    
    // 清空现有的 formulas 文件夹（防止旧的乱码 ID 文件残留）
    if (fs.existsSync(formulasDir)) {
        fs.rmSync(formulasDir, { recursive: true, force: true });
    }
    fs.mkdirSync(formulasDir, { recursive: true });

    let formulaList = [];

    snapshot.forEach(doc => {
        const formulaData = doc.data();
        const formulaId = doc.id;

        // 1. 提取作者和公式名，生成人类可读的文件名
        const author = formulaData.author || 'Anonymous';
        const formulaNameEn = (formulaData.name && formulaData.name.en) || 'Unnamed';
        
        // 移除非法字符，防止文件名报错
        const safeAuthor = author.replace(/[^a-z0-9]/gi, '_');
        const safeName = formulaNameEn.replace(/[^a-z0-9]/gi, '_');
        
        // 组合成好看的文件名：作者_公式名.json
        const readableFileName = `${safeAuthor}_${safeName}.json`;

        // 2. 清理数据（移除 Firebase 特有字段）
        const cleanData = { ...formulaData };
        delete cleanData.timestamp;
        delete cleanData.authorUid; 
        delete cleanData.updatedAt;

        // 确保 ID 依然保留在 JSON 内部供程序识别
        if (!cleanData.id) cleanData.id = formulaId;

        // 3. 写入单个 .json 文件（文件名现在是人类可读的）
        fs.writeFileSync(
            path.join(formulasDir, readableFileName),
            JSON.stringify(cleanData, null, 2)
        );

        // 4. 构建索引数据（增加 file_name 字段供 App 下载）
        formulaList.push({
            id: cleanData.id,
            file_name: readableFileName, // 关键：记录对应的文件名
            version: cleanData.version || 1,
            category: cleanData.category || 'General',
            name: cleanData.name,         
            remarks: cleanData.remarks,   
            factors: cleanData.factors,   
            expression: cleanData.expression,
            author: author,
            download_count: cleanData.download_count || 0,
            rating: cleanData.rating || 0,
            rating_count: cleanData.rating_count || 0
        });
    });

    // 5. 按名称排序
    formulaList.sort((a, b) => {
        const nameA = (a.name.en || '').toUpperCase();
        const nameB = (b.name.en || '').toUpperCase();
        return nameA.localeCompare(nameB);
    });

    // 6. 生成目录文件
    const catalog = {
        lastUpdated: new Date().toISOString(),
        formulas: formulaList
    };

    fs.writeFileSync(
        path.join(__dirname, 'index.json'),
        JSON.stringify(catalog, null, 2)
    );

    console.log(`同步成功！共更新了 ${formulaList.length} 个公式，文件名已优化为可读格式。`);
}

sync().catch(err => {
    console.error('同步进程崩溃:', err);
    process.exit(1);
});
