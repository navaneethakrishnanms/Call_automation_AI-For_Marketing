/**
 * Intent Classification Service
 * Polls Retell API for call transcripts, then classifies customer intent via Groq LLM.
 */

const axios = require("axios");

const RETELL_API_KEY = process.env.RETELL_API_KEY;
const GROQ_API_KEY = process.env.GROQ_API_KEY;
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";

const POLL_INTERVAL_MS = 5000;   // check every 5 seconds
const MAX_POLL_TIME_MS = 300000; // give up after 5 minutes

const INTENT_PROMPT = `You are a strict AI Intent Classification Engine.

Your task is to determine the CUSTOMER'S final intent from a sales/admission call transcript.

VERY IMPORTANT RULES:
- Focus ONLY on the CUSTOMER's responses.
- Ignore the AI agent completely.
- Base decision on the CUSTOMER'S FINAL POSITION in the conversation.
- Do not return anything outside JSON.
- Do not explain outside JSON.

---------------------------------------
INTENT CATEGORIES (CHOOSE EXACTLY ONE)
---------------------------------------

"Highly Interested"
"Interested"
"Needs Follow-up"
"Just Exploring"
"Not Interested"

---------------------------------------
OUTPUT FORMAT (STRICT JSON ONLY)
---------------------------------------

{
  "phone_number": "<PHONE_NUMBER>",
  "intent": "ONE_INTENT_FROM_LIST",
  "confidence_score": 0-100,
  "description": "A descriptive 1-2 sentence explanation of why this intent was assigned, referencing specific things the customer said or their overall tone/engagement."
}`;


/**
 * Poll Retell API until a call ends and a transcript is available.
 *
 * @param {string} callId  Retell call_id
 * @returns {Promise<{transcript: string, status: string, duration_ms: number}>}
 */
async function getCallTranscript(callId) {
    const start = Date.now();

    while (Date.now() - start < MAX_POLL_TIME_MS) {
        try {
            const { data } = await axios.get(
                `https://api.retellai.com/v2/get-call/${callId}`,
                {
                    headers: { Authorization: `Bearer ${RETELL_API_KEY}` },
                    timeout: 10000,
                }
            );

            if (data.call_status === "ended" || data.call_status === "error") {
                return {
                    transcript: data.transcript || "",
                    status: data.call_status,
                    duration_ms: data.duration_ms || 0,
                    disconnection_reason: data.disconnection_reason || "",
                };
            }

            // Still ongoing — wait before next poll
            await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        } catch (err) {
            console.error(`   ⚠️  Poll error for ${callId}:`, err.message);
            await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        }
    }

    return { transcript: "", status: "timeout", duration_ms: 0, disconnection_reason: "poll_timeout" };
}


/**
 * Classify customer intent from a transcript using Groq LLM.
 *
 * @param {string} phoneNumber
 * @param {string} transcript
 * @returns {Promise<{phone_number: string, intent: string, confidence_score: number, description: string}>}
 */
async function classifyIntent(phoneNumber, transcript) {
    if (!transcript || transcript.trim().length === 0) {
        return {
            phone_number: phoneNumber,
            intent: "Needs Follow-up",
            confidence_score: 0,
            description: "No transcript was available for this call, so intent could not be determined.",
            note: "No transcript available",
        };
    }

    const userPrompt = `PHONE NUMBER:\n${phoneNumber}\n\nTRANSCRIPT:\n${transcript}\n\nReturn ONLY valid JSON.`;

    try {
        const { data } = await axios.post(
            "https://api.groq.com/openai/v1/chat/completions",
            {
                model: GROQ_MODEL,
                messages: [
                    { role: "system", content: INTENT_PROMPT },
                    { role: "user", content: userPrompt },
                ],
                temperature: 0,
                max_tokens: 300,
            },
            {
                headers: {
                    Authorization: `Bearer ${GROQ_API_KEY}`,
                    "Content-Type": "application/json",
                },
                timeout: 30000,
            }
        );

        const raw = data.choices?.[0]?.message?.content || "";
        // Extract JSON from response (handle markdown code fences)
        const jsonMatch = raw.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            return {
                phone_number: parsed.phone_number || phoneNumber,
                intent: parsed.intent || "Needs Follow-up",
                confidence_score: parsed.confidence_score ?? 0,
                description: parsed.description || "No description provided by the model.",
            };
        }

        return { phone_number: phoneNumber, intent: "Needs Follow-up", confidence_score: 0, description: "Failed to parse LLM response.", note: "Failed to parse LLM response" };
    } catch (err) {
        console.error(`   ❌ Intent classification failed for ${phoneNumber}:`, err.message);
        return { phone_number: phoneNumber, intent: "Needs Follow-up", confidence_score: 0, description: "Intent classification encountered an error.", note: err.message };
    }
}


/**
 * Full pipeline: poll for transcript then classify intent.
 *
 * @param {string} callId       Retell call_id
 * @param {string} phoneNumber  Customer phone number
 * @returns {Promise<object>}   Intent classification result
 */
async function classifyCallIntent(callId, phoneNumber) {
    console.log(`🔍 Classifying intent for call ${callId} (${phoneNumber})...`);

    const callData = await getCallTranscript(callId);

    if (callData.status === "timeout") {
        console.log(`   ⏰ Timed out waiting for call ${callId}`);
        return { phone_number: phoneNumber, intent: "Needs Follow-up", confidence_score: 0, description: "Call polling timed out before a transcript was available.", note: "Call polling timed out" };
    }

    if (!callData.transcript) {
        console.log(`   📭 No transcript for call ${callId}`);
        return { phone_number: phoneNumber, intent: "Needs Follow-up", confidence_score: 0, description: "No transcript was recorded for this call.", note: "No transcript" };
    }

    console.log(`   📝 Got transcript (${callData.transcript.length} chars), classifying...`);
    const result = await classifyIntent(phoneNumber, callData.transcript);
    console.log(`   ✅ Intent: ${result.intent} (${result.confidence_score}%)`);

    return {
        ...result,
        call_status: callData.status,
        call_duration_ms: callData.duration_ms,
        disconnection_reason: callData.disconnection_reason,
    };
}


module.exports = { getCallTranscript, classifyIntent, classifyCallIntent };
