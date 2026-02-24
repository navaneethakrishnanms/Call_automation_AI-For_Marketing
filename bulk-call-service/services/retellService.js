/**
 * Retell AI Service
 * Handles individual and batched outbound call triggering via the Retell API.
 */

const axios = require("axios");

const RETELL_API_URL = "https://api.retellai.com/v2/create-phone-call";

// Read from .env
const RETELL_API_KEY = process.env.RETELL_API_KEY;
const RETELL_FROM_NUMBER = process.env.RETELL_PHONE_NUMBER; // reuse existing env var name
const BATCH_SIZE = parseInt(process.env.BATCH_SIZE, 10) || 10;
const BATCH_DELAY_MS = parseInt(process.env.BATCH_DELAY_MS, 10) || 1000;

/**
 * Make a single outbound call via the Retell API.
 *
 * @param {{ toNumber: string, agentId: string }} params
 * @returns {Promise<object>} Retell API response data
 */
async function makeRetellCall({ toNumber, agentId }) {
    const response = await axios.post(
        RETELL_API_URL,
        {
            from_number: RETELL_FROM_NUMBER,
            to_number: toNumber,
            agent_id: agentId,
        },
        {
            headers: {
                Authorization: `Bearer ${RETELL_API_KEY}`,
                "Content-Type": "application/json",
            },
            timeout: 30000,
        }
    );
    return response.data;
}

/**
 * Trigger calls for an array of contacts in parallel batches.
 *
 * @param {Array<{ name: string, phone: string, agentId: string, rowIndex: number }>} contacts
 * @returns {Promise<{ results: Array }>}
 */
async function triggerBulkCalls(contacts) {
    const results = [];

    for (let i = 0; i < contacts.length; i += BATCH_SIZE) {
        const batch = contacts.slice(i, i + BATCH_SIZE);
        const batchNum = Math.floor(i / BATCH_SIZE) + 1;
        const totalBatches = Math.ceil(contacts.length / BATCH_SIZE);

        console.log(
            `📞 Batch ${batchNum}/${totalBatches} — ${batch.length} contacts`
        );

        const batchResults = await Promise.allSettled(
            batch.map(async (contact) => {
                const toNumber = `+91${contact.phone}`;
                try {
                    const data = await makeRetellCall({
                        toNumber,
                        agentId: contact.agentId,
                    });
                    console.log(`   ✅ ${contact.name} (${toNumber})`);
                    return {
                        rowIndex: contact.rowIndex,
                        name: contact.name,
                        phone: contact.phone,
                        success: true,
                        call_id: data.call_id || null,
                        data,
                    };
                } catch (err) {
                    const errorMsg =
                        err.response?.data?.message ||
                        err.response?.data?.error ||
                        err.message ||
                        "Unknown error";
                    console.error(`   ❌ ${contact.name} (${toNumber}): ${errorMsg}`);
                    return {
                        rowIndex: contact.rowIndex,
                        name: contact.name,
                        phone: contact.phone,
                        success: false,
                        error: errorMsg,
                    };
                }
            })
        );

        for (const r of batchResults) {
            results.push(r.status === "fulfilled" ? r.value : {
                rowIndex: -1, name: "Unknown", phone: "Unknown",
                success: false, error: r.reason?.message || "Unexpected error",
            });
        }

        // Delay between batches (skip after last)
        if (i + BATCH_SIZE < contacts.length) {
            console.log(`   ⏳ Waiting ${BATCH_DELAY_MS}ms before next batch...`);
            await new Promise((resolve) => setTimeout(resolve, BATCH_DELAY_MS));
        }
    }

    return { results };
}

module.exports = { makeRetellCall, triggerBulkCalls };
