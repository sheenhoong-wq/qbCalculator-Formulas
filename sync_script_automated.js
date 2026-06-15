/**
 * sync_script_automated.js
 * Automatically syncs ALL 'approved' formulas from Firestore.
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
    console.log('Fetching formulas from Firestore...');

    // Sync everything with 'approved' status (which is set automatically by the App)
    const snapshot = await db.collection('submissions')
        .where('status', '==', 'approved')
        .get();

    const formulasDir = path.join(__dirname, 'formulas');
    if (!fs.existsSync(formulasDir)) fs.mkdirSync(formulasDir, { recursive: true });

    let formulaList = [];

    snapshot.forEach(doc => {
        const formulaData = doc.data().data;
        const formulaId = doc.id;

        // Write .json file
        fs.writeFileSync(
            path.join(formulasDir, `${formulaId}.json`),
            JSON.stringify(formulaData, null, 2)
        );

        // Add to index
        formulaList.push({
            id: formulaData.id,
            name: formulaData.name,
            category: formulaData.category,
            author: formulaData.author,
            version: formulaData.version
        });
    });

    // Update index.json with fresh catalog
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
