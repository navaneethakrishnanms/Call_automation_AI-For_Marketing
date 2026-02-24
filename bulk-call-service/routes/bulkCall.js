/**
 * Bulk Call Route
 * POST /bulk-api/bulk-call/upload
 *
 * Accepts an Excel/CSV file, parses contacts, triggers Retell API calls
 * for "Pending" rows in parallel batches, updates the file, and returns
 * a JSON summary.
 */

const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");

const { parseExcel, updateExcelStatus } = require("../utils/excelParser");
const { triggerBulkCalls } = require("../services/retellService");

const router = express.Router();

// ---------------------------------------------------------------------------
// Multer — accept .xlsx / .xls / .csv only, max 10 MB
// ---------------------------------------------------------------------------
const storage = multer.diskStorage({
    destination: (_req, _file, cb) => {
        const dir = path.join(__dirname, "..", "uploads");
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        cb(null, dir);
    },
    filename: (_req, file, cb) => {
        const unique = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
        cb(null, `contacts-${unique}${path.extname(file.originalname)}`);
    },
});

const fileFilter = (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if ([".xlsx", ".xls", ".csv"].includes(ext)) cb(null, true);
    else cb(new Error("Only .xlsx, .xls, and .csv files are accepted."));
};

const upload = multer({
    storage,
    fileFilter,
    limits: { fileSize: 10 * 1024 * 1024 },
});

// ---------------------------------------------------------------------------
// POST /upload
// ---------------------------------------------------------------------------
router.post("/upload", upload.single("file"), async (req, res) => {
    const startTime = Date.now();

    try {
        if (!req.file) {
            return res.status(400).json({ error: "No file uploaded." });
        }

        console.log(`\n📂 File received: ${req.file.originalname}`);

        // 1. Parse the spreadsheet
        let parsed;
        try {
            parsed = parseExcel(req.file.path);
        } catch (parseErr) {
            return res.status(400).json({ error: parseErr.message });
        }

        const { contacts } = parsed;
        const totalRows = contacts.length;

        // 2. Filter pending rows
        const pendingContacts = contacts.filter(
            (c) => c.status.toLowerCase() === "pending"
        );
        const alreadyCalled = totalRows - pendingContacts.length;

        console.log(
            `   Total: ${totalRows} | Pending: ${pendingContacts.length} | Already called: ${alreadyCalled}`
        );

        if (pendingContacts.length === 0) {
            return res.json({
                message: "No pending contacts to call.",
                summary: {
                    total_rows: totalRows,
                    already_called: alreadyCalled,
                    total_pending: 0,
                    successfully_triggered: 0,
                    failed: 0,
                    errors: [],
                },
            });
        }

        // 3. Trigger Retell API calls in parallel batches
        const { results } = await triggerBulkCalls(pendingContacts);

        const successResults = results.filter((r) => r.success);
        const failedResults = results.filter((r) => !r.success);

        console.log(
            `\n✅ Done — Success: ${successResults.length} | Failed: ${failedResults.length}`
        );

        // 4. Update status in the spreadsheet
        let updatedFileName = null;
        if (successResults.length > 0) {
            const successIndices = successResults.map((r) => r.rowIndex);
            const updatedPath = updateExcelStatus(req.file.path, successIndices);
            updatedFileName = path.basename(updatedPath);
        }

        // 5. Classify intent for each successful call (wait for calls to finish)
        let intentResults = [];
        const callsWithIds = successResults.filter((r) => r.call_id);

        if (callsWithIds.length > 0) {
            console.log(`\n🎯 Classifying intent for ${callsWithIds.length} calls...`);
            const { classifyCallIntent } = require("../services/intentService");

            intentResults = await Promise.all(
                callsWithIds.map((r) =>
                    classifyCallIntent(r.call_id, `+91${r.phone}`)
                        .then((intent) => ({ name: r.name, phone: r.phone, call_id: r.call_id, ...intent }))
                        .catch((err) => ({
                            name: r.name, phone: r.phone, call_id: r.call_id,
                            intent: "Needs Follow-up", confidence_score: 0,
                            note: err.message,
                        }))
                )
            );

            console.log(`\n📊 Intent classification complete:`);
            intentResults.forEach((r) => {
                console.log(`   ${r.name} (${r.phone}): ${r.intent} (${r.confidence_score}%)`);
            });

            // Save intent results to Excel
            const { saveIntentResults } = require("../utils/excelParser");
            const saved = saveIntentResults(intentResults);
            intentResults._savedFile = saved.fileName;
        }

        // 6. Return summary
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);

        return res.json({
            message: "Bulk call processing complete.",
            summary: {
                total_rows: totalRows,
                already_called: alreadyCalled,
                total_pending: pendingContacts.length,
                successfully_triggered: successResults.length,
                failed: failedResults.length,
                duration_seconds: parseFloat(elapsed),
                errors: failedResults.map((r) => ({
                    name: r.name,
                    phone: r.phone,
                    error: r.error,
                })),
            },
            intent_results: intentResults,
            intent_file: "/bulk-api/download-intent-csv",
            updated_file: updatedFileName
                ? `/bulk-api/downloads/${updatedFileName}`
                : null,
        });
    } catch (err) {
        console.error("❌ Bulk call route error:", err);
        return res.status(500).json({
            error: "Internal server error during bulk call processing.",
            details: err.message,
        });
    }
});

// Multer error handler
router.use((err, _req, res, _next) => {
    if (err instanceof multer.MulterError) {
        return res.status(400).json({ error: `Upload error: ${err.message}` });
    }
    if (err) return res.status(400).json({ error: err.message });
});

module.exports = router;
