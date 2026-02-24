/**
 * Intent Classification Route
 * GET /bulk-api/intent/:callId?phone=<phone_number>&name=<name>
 *
 * Fetches transcript from Retell, classifies customer intent via Groq LLM.
 * Also saves result to Excel.
 */

const express = require("express");
const { classifyCallIntent } = require("../services/intentService");
const { saveIntentResults } = require("../utils/excelParser");

const router = express.Router();

router.get("/:callId", async (req, res) => {
    const { callId } = req.params;
    const phone = req.query.phone || "unknown";
    const name = req.query.name || "Single Call";

    if (!callId) {
        return res.status(400).json({ error: "callId is required" });
    }

    try {
        console.log(`\n🎯 Intent request for call ${callId}`);
        const result = await classifyCallIntent(callId, phone);

        // Save to Excel
        const intentRow = { name, call_id: callId, ...result };
        const saved = saveIntentResults([intentRow]);
        result.intent_file = `/bulk-api/download-intent-csv`;

        return res.json(result);
    } catch (err) {
        console.error("❌ Intent route error:", err);
        return res.status(500).json({ error: err.message });
    }
});

module.exports = router;
