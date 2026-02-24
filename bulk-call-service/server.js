/**
 * Bulk Call Service — Express entry point
 * Handles Excel/CSV uploads and triggers parallel Retell AI outbound calls.
 */

require("dotenv").config();
const express = require("express");
const cors = require("cors");
const path = require("path");
const fs = require("fs");

const bulkCallRouter = require("./routes/bulkCall");
const intentRouter = require("./routes/intentRoute");

const app = express();
const PORT = process.env.PORT || 3001;

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------
app.use(
  cors({
    origin: [
      "http://localhost:5173",
      "http://localhost:3000",
      "http://127.0.0.1:5173",
    ],
    credentials: true,
  })
);
app.use(express.json());

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, "uploads");
const intentsDir = path.join(uploadsDir, "intents");
if (!fs.existsSync(intentsDir)) {
  fs.mkdirSync(intentsDir, { recursive: true });
}

// Serve updated files for download
app.use("/bulk-api/downloads", express.static(uploadsDir));

// ---------------------------------------------------------------------------
// Intent History Route — read from single intent_results.csv
// ---------------------------------------------------------------------------
app.get("/bulk-api/intent-history", (_req, res) => {
  try {
    const csvPath = path.join(intentsDir, "intent_results.csv");
    if (!fs.existsSync(csvPath)) {
      return res.json({ intents: [], downloadUrl: null });
    }

    const csvContent = fs.readFileSync(csvPath, "utf8").trim();
    const lines = csvContent.split("\n");
    if (lines.length < 2) {
      return res.json({ intents: [], downloadUrl: "/bulk-api/download-intent-csv" });
    }

    // Parse CSV (simple parser for our known format)
    const headers = parseCSVLine(lines[0]);
    const intents = [];
    for (let i = 1; i < lines.length; i++) {
      const vals = parseCSVLine(lines[i]);
      if (vals.length >= headers.length) {
        const row = {};
        headers.forEach((h, idx) => { row[h] = vals[idx] || ""; });
        intents.push(row);
      }
    }

    return res.json({
      intents: intents.reverse(), // newest first
      count: intents.length,
      downloadUrl: "/bulk-api/download-intent-csv",
    });
  } catch (err) {
    console.error("Intent history error:", err);
    return res.json({ intents: [], downloadUrl: null });
  }
});

// ---------------------------------------------------------------------------
// CSV Download Route — download intent_results.csv
// ---------------------------------------------------------------------------
app.get("/bulk-api/download-intent-csv", (_req, res) => {
  const csvPath = path.join(intentsDir, "intent_results.csv");
  if (!fs.existsSync(csvPath)) {
    return res.status(404).json({ error: "No intent results CSV found." });
  }
  res.download(csvPath, "intent_results.csv");
});

/**
 * Simple CSV line parser that handles quoted fields.
 */
function parseCSVLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        current += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ',') {
        result.push(current.trim());
        current = "";
      } else {
        current += ch;
      }
    }
  }
  result.push(current.trim());
  return result;
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.use("/bulk-api/bulk-call", bulkCallRouter);
app.use("/bulk-api/intent", intentRouter);

// Health check
app.get("/bulk-api/health", (_req, res) => {
  res.json({
    status: "healthy",
    service: "Bulk Call Service (Retell AI)",
    version: "1.1.0",
    retell_configured: !!process.env.RETELL_API_KEY,
    groq_configured: !!process.env.GROQ_API_KEY,
  });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`\n🚀 Bulk Call Service running on http://localhost:${PORT}`);
  console.log(`   Health:  http://localhost:${PORT}/bulk-api/health`);
  console.log(`   Retell Key: ${process.env.RETELL_API_KEY ? "✅ configured" : "❌ MISSING"}`);
  console.log(`   Groq Key:   ${process.env.GROQ_API_KEY ? "✅ configured" : "❌ MISSING"}`);
  console.log(`   From Number: ${process.env.RETELL_PHONE_NUMBER || "❌ MISSING"}\n`);
});
