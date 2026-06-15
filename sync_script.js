/**
 * sync_script.js
 * This script runs inside GitHub Actions to sync 'approved' formulas
 * from Firestore to your GitHub Public Repository.
 */
const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

// 1. Initialize Firebase from the Secret
const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

async function sync() {
    console.log('Starting sync from Firestore...');

    // 2. Fetch all approved formulas from 'submissions' collection
    const snapshot = await db.collection('submissions')
        .where('status', '==', 'approved') // Only sync approved ones
        .get();

    if (snapshot.empty) {
        console.log('No new approved formulas found.');
        process.exit(0);
    }

    const formulasDir = path.join(__dirname, 'formulas');
    if (!fs.existsSync(formulasDir)) fs.mkdirSync(formulasDir);

    let formulaList = [];

    snapshot.forEach(doc => {
        const formulaData = doc.data().data; // The formula object stored in Android
        const formulaId = doc.id;

        // 3. Write individual JSON file
        fs.writeFileSync(
            path.join(formulasDir, `${formulaId}.json`),
            JSON.stringify(formulaData, null, 2)
        );

        // 4. Add to the index list
        formulaList.push(formulaData);
    });

    // 5. Update index.json
    const catalog = {
        lastUpdated: new Date().toISOString(),
        formulas: formulaList
    };

    fs.writeFileSync(
        path.join(__dirname, 'index.json'),
        JSON.stringify(catalog, null, 2)
    );

    console.log(`Successfully synced ${formulaList.length} formulas.`);
}

sync().catch(err => {
    console.error('Sync failed:', err);
    process.exit(1);
});
