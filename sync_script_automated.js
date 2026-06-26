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

        // 1. 提取作者和公式名 (支持中文名)
        const author = formulaData.author || 'Anonymous';
        // 优先使用中文名，如果没有再使用英文名
        const formulaName = (formulaData.name && (formulaData.name.zh || formulaData.name.en)) || 'Unnamed';
        
        // --- 改进正则：允许中文字符 (\u4e00-\u9fa5)、字母、数字 ---
        const safeAuthor = author.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        const safeName = formulaName.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
        
        // 组合成好看的文件名：作者_公式名.json
        let readableFileName = `${safeAuthor}_${safeName}.json`;
        
        // 兜底方案：如果过滤后文件名变空了（比如全是特殊符号），则使用 ID 代替
        if (!safeName || safeName === '_' || safeName.trim() === '') {
            readableFileName = `${safeAuthor}_${formulaId.substring(0, 8)}.json`;
        }

        // 2. 清理数据（移除 Firebase 特有字段）
        const cleanData = { ...formulaData };
        delete cleanData.timestamp;
        delete cleanData.authorUid; 
        delete cleanData.updatedAt;

        // 确保 ID 依然保留在 JSON 内部供程序识别
        if (!cleanData.id) cleanData.id = formulaId;

        // 3. 写入单个 .json 文件
        fs.writeFileSync(
            path.join(formulasDir, readableFileName),
            JSON.stringify(cleanData, null, 2)
        );

        // 4. 构建索引数据
        formulaList.push({
            id: cleanData.id,
            file_name: readableFileName, // 记录对应的真实文件名
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

    // 5. 按名称排序（中文名也能正确排序）
    formulaList.sort((a, b) => {
        const nameA = a.name.zh || a.name.en || '';
        const nameB = b.name.zh || b.name.en || '';
        return nameA.localeCompare(nameB, 'zh-Hans-CN');
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

    console.log(`同步成功！共更新了 ${formulaList.length} 个公式，支持中文文件名。`);
}

sync().catch(err => {
    console.error('同步进程崩溃:', err);
    process.exit(1);
});
