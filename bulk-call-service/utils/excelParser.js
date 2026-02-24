/**
 * Excel/CSV Parser Utility
 * Reads uploaded spreadsheets, extracts contact rows, and updates status columns.
 */

const XLSX = require("xlsx");
const path = require("path");

const COLUMN_MAP = {
    name: ["name"],
    phone: ["phone", "phone_number", "phonenumber", "mobile", "number"],
    agentId: ["agent_id", "agentid", "agent id"],
    status: ["status"],
};

function normalise(header) {
    return String(header).trim().toLowerCase().replace(/[\s_-]+/g, "_");
}

function resolveHeaders(headers) {
    const resolved = {};
    for (const [canonical, variants] of Object.entries(COLUMN_MAP)) {
        const idx = headers.findIndex((h) => variants.includes(normalise(h)));
        if (idx !== -1) resolved[canonical] = idx;
    }
    return resolved;
}

/**
 * Parse an Excel or CSV file and return contact rows.
 */
function parseExcel(filePath) {
    const workbook = XLSX.readFile(filePath);
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rawData = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });

    if (rawData.length < 2) {
        throw new Error("File must contain a header row and at least one data row.");
    }

    const headers = rawData[0].map(String);
    const headerMap = resolveHeaders(headers);

    const missing = Object.keys(COLUMN_MAP).filter((k) => !(k in headerMap));
    if (missing.length > 0) {
        throw new Error(
            `Missing required columns: ${missing.join(", ")}. Found: [${headers.join(", ")}]`
        );
    }

    const contacts = [];
    const allRows = rawData.slice(1);

    for (let i = 0; i < allRows.length; i++) {
        const row = allRows[i];
        contacts.push({
            name: String(row[headerMap.name] || "").trim(),
            phone: String(row[headerMap.phone] || "").trim().replace(/\D/g, ""),
            agentId: String(row[headerMap.agentId] || "").trim(),
            status: String(row[headerMap.status] || "").trim(),
            rowIndex: i,
        });
    }

    return { contacts, allRows, headers, headerMap, sheetName };
}

/**
 * Update Status column to "Called" for success rows and save a new file.
 */
function updateExcelStatus(originalFilePath, successRowIndices) {
    const workbook = XLSX.readFile(originalFilePath);
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rawData = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });
    const headers = rawData[0].map(String);
    const headerMap = resolveHeaders(headers);
    const statusCol = headerMap.status;
    const successSet = new Set(successRowIndices);

    for (let i = 1; i < rawData.length; i++) {
        if (successSet.has(i - 1)) {
            rawData[i][statusCol] = "Called";
        }
    }

    const newSheet = XLSX.utils.aoa_to_sheet(rawData);
    workbook.Sheets[sheetName] = newSheet;

    const ext = path.extname(originalFilePath);
    const baseName = path.basename(originalFilePath, ext);
    const updatedPath = path.join(
        path.dirname(originalFilePath),
        `${baseName}_updated${ext}`
    );
    XLSX.writeFile(workbook, updatedPath);
    return updatedPath;
}

/**
 * Save intent classification results to a single persistent CSV file (appends).
 */
function saveIntentResults(intentResults) {
    const intentsDir = path.join(path.dirname(__dirname), "uploads", "intents");
    const fs = require("fs");
    if (!fs.existsSync(intentsDir)) {
        fs.mkdirSync(intentsDir, { recursive: true });
    }

    const fileName = "intent_results.csv";
    const filePath = path.join(intentsDir, fileName);

    const headers = "Name,Phone,Intent,Description,Confidence,Call_ID,Timestamp";

    // Build CSV rows
    const rows = intentResults.map((r) => {
        const name = csvEscape(r.name || "");
        const phone = csvEscape(r.phone_number || r.phone || "");
        const intent = csvEscape(r.intent || "");
        const description = csvEscape(r.description || "");
        const confidence = r.confidence_score ?? 0;
        const callId = csvEscape(r.call_id || "");
        const timestamp = csvEscape(new Date().toLocaleString());
        return `${name},${phone},${intent},${description},${confidence},${callId},${timestamp}`;
    });

    // If file doesn't exist, write headers first
    if (!fs.existsSync(filePath)) {
        fs.writeFileSync(filePath, headers + "\n", "utf8");
    }

    // Append rows
    fs.appendFileSync(filePath, rows.join("\n") + "\n", "utf8");

    console.log(`   💾 Intent results appended to ${filePath} (${rows.length} rows)`);
    return { fileName, filePath };
}

/**
 * Escape a value for CSV (wrap in quotes if it contains commas, quotes, or newlines).
 */
function csvEscape(value) {
    const str = String(value);
    if (str.includes(",") || str.includes('"') || str.includes("\n")) {
        return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
}

module.exports = { parseExcel, updateExcelStatus, saveIntentResults };
