import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import { Boom } from "@hapi/boom";
import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import pino from "pino";
import QRCode from "qrcode";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const serviceRoot = path.resolve(__dirname, "..");
dotenv.config({ path: path.resolve(serviceRoot, "..", ".env") });

function resolveServicePath(configuredPath, fallback) {
  if (!configuredPath) return fallback;
  return path.isAbsolute(configuredPath) ? configuredPath : path.resolve(serviceRoot, configuredPath);
}

const authDir = resolveServicePath(
  process.env.WHATSAPP_AUTH_DIR,
  path.join(serviceRoot, "data", "whatsapp-auth"),
);
const messageLogPath = resolveServicePath(
  process.env.WHATSAPP_MESSAGE_LOG,
  path.join(serviceRoot, "data", "whatsapp-messages.json"),
);
const port = Number(process.env.WHATSAPP_PORT || 3001);
const maxMessagesPerRequest = Number(process.env.WHATSAPP_MAX_MESSAGES_PER_REQUEST || 10);
const reconnectBaseDelay = 2000;
const reconnectMaxDelay = 30000;

const logger = pino({ level: process.env.LOG_LEVEL || "info" });
const app = express();
app.use(cors());
app.use(express.json({ limit: "64kb" }));

const state = {
  status: "DISCONNECTED",
  qr: null,
  phone: null,
  error: null,
  socket: null,
  reconnectAttempt: 0,
  reconnectTimer: null,
  initializing: false,
};
const sendingKeys = new Set();

function publicStatus() {
  return {
    status: state.status,
    connected: state.status === "CONNECTED",
    authenticated: Boolean(state.phone),
    phone: state.phone,
    qr: state.qr,
    error: state.error,
  };
}

function normalizePhone(phone) {
  const value = String(phone || "").trim().replace(/[^0-9]/g, "");
  const normalized = value.startsWith("00") ? value.slice(2) : value;
  if (!/^[1-9][0-9]{7,14}$/.test(normalized)) {
    throw new Error("Invalid phone number. Use international format, for example 919876543210.");
  }
  return normalized;
}

async function ensureParentDirectory(filePath) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
}

async function readMessageLog() {
  try {
    return JSON.parse(await fs.readFile(messageLogPath, "utf8"));
  } catch (error) {
    if (error.code !== "ENOENT") logger.warn({ error }, "[WhatsApp] Could not read message log");
    return [];
  }
}

async function writeMessageLog(entries) {
  await ensureParentDirectory(messageLogPath);
  await fs.writeFile(messageLogPath, JSON.stringify(entries.slice(-500), null, 2), "utf8");
}

function idempotencyKey({ requestId, phone, message }) {
  return crypto.createHash("sha256").update(`${requestId || "adhoc"}|${phone}|${message}`).digest("hex");
}

async function sendMessage({ phone, message, seller, requestId }) {
  const normalizedPhone = normalizePhone(phone);
  const cleanMessage = String(message || "").trim();
  if (!cleanMessage || cleanMessage.length > 4096) throw new Error("Message must contain between 1 and 4096 characters.");
  if (state.status !== "CONNECTED" || !state.socket) throw new Error("WhatsApp is not connected. Scan the QR code first.");

  const key = idempotencyKey({ requestId, phone: normalizedPhone, message: cleanMessage });
  const log = await readMessageLog();
  const existing = log.find((entry) => entry.idempotencyKey === key);
  if (existing?.status === "SENT") return { success: true, duplicate: true, messageId: existing.messageId, log: existing };
  if (sendingKeys.has(key)) throw new Error("This message is already being sent.");

  sendingKeys.add(key);
  const entry = {
    idempotencyKey: key,
    seller: seller || null,
    phone: normalizedPhone,
    message: cleanMessage,
    status: "SENDING",
    timestamp: new Date().toISOString(),
  };
  log.push(entry);
  await writeMessageLog(log);
  try {
    const [recipient] = await state.socket.onWhatsApp(normalizedPhone);
    if (recipient && recipient.exists === false) throw new Error("This phone number is not available on WhatsApp.");
    const result = await state.socket.sendMessage(`${normalizedPhone}@s.whatsapp.net`, { text: cleanMessage });
    entry.status = "SENT";
    entry.messageId = result?.key?.id || null;
    await writeMessageLog(log);
    logger.info({ phone: normalizedPhone, seller, messageId: entry.messageId }, "[WhatsApp] Message sent");
    return { success: true, duplicate: false, messageId: entry.messageId, log: entry };
  } catch (error) {
    entry.status = "FAILED";
    entry.error = error.message || "Message send failed";
    await writeMessageLog(log);
    logger.error({ error, phone: normalizedPhone, seller }, "[WhatsApp] Message failed");
    throw new Error(entry.error);
  } finally {
    sendingKeys.delete(key);
  }
}

async function startClient() {
  if (state.initializing) return;
  state.initializing = true;
  state.status = "CONNECTING";
  state.error = null;
  state.qr = null;
  logger.info("[WhatsApp] Starting client");
  try {
    await fs.mkdir(authDir, { recursive: true });
    const { state: authState, saveCreds } = await useMultiFileAuthState(authDir);
    const socket = makeWASocket({
      auth: authState,
      printQRInTerminal: false,
      logger: pino({ level: "silent" }),
      browser: ["DealMate", "Chrome", "1.0.0"],
    });
    state.socket = socket;
    socket.ev.on("creds.update", saveCreds);
    socket.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
      if (qr) {
        state.status = "QR_REQUIRED";
        state.qr = await QRCode.toDataURL(qr, { margin: 1, width: 320 });
        state.error = null;
        logger.info("[WhatsApp] QR generated");
      }
      if (connection === "open") {
        state.status = "CONNECTED";
        state.qr = null;
        state.error = null;
        state.phone = socket.user?.id?.split(":")[0] || null;
        state.reconnectAttempt = 0;
        logger.info({ phone: state.phone }, "[WhatsApp] Connected");
      }
      if (connection === "close") {
        state.socket = null;
        const statusCode = new Boom(lastDisconnect?.error)?.output?.statusCode;
        const loggedOut = statusCode === DisconnectReason.loggedOut;
        state.status = loggedOut ? "LOGGED_OUT" : "DISCONNECTED";
        state.qr = null;
        state.phone = loggedOut ? null : state.phone;
        state.error = loggedOut ? "WhatsApp session logged out. Connect again to scan a new QR code." : "WhatsApp connection closed.";
        state.initializing = false;
        if (loggedOut) await fs.rm(authDir, { recursive: true, force: true });
        if (!loggedOut) scheduleReconnect();
        logger.warn({ statusCode, loggedOut }, "[WhatsApp] Disconnected");
      }
    });
  } catch (error) {
    state.initializing = false;
    state.status = "ERROR";
    state.error = "WhatsApp service could not start.";
    logger.error({ error }, "[WhatsApp] Client startup failed");
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (state.reconnectTimer || state.status === "LOGGED_OUT") return;
  const delay = Math.min(reconnectBaseDelay * (2 ** state.reconnectAttempt), reconnectMaxDelay);
  state.reconnectAttempt += 1;
  logger.info({ delay }, "[WhatsApp] Reconnecting");
  state.reconnectTimer = setTimeout(() => {
    state.reconnectTimer = null;
    startClient();
  }, delay);
}

app.get("/health", (_req, res) => res.json({ ok: true }));
app.get("/whatsapp/status", (_req, res) => res.json(publicStatus()));
app.get("/whatsapp/qr", (_req, res) => res.json({ qr: state.qr, status: state.status }));
app.get("/whatsapp/messages", async (_req, res) => res.json(await readMessageLog()));
app.post("/whatsapp/connect", async (_req, res) => {
  await startClient();
  res.json(publicStatus());
});
app.post("/whatsapp/disconnect", async (_req, res) => {
  if (state.reconnectTimer) clearTimeout(state.reconnectTimer);
  state.reconnectTimer = null;
  if (state.socket) await state.socket.logout();
  state.socket = null;
  state.status = "LOGGED_OUT";
  state.qr = null;
  state.phone = null;
  res.json(publicStatus());
});
app.post("/whatsapp/send", async (req, res) => {
  try {
    const result = await sendMessage(req.body || {});
    res.json(result);
  } catch (error) {
    res.status(400).json({ success: false, error: error.message || "Could not send WhatsApp message." });
  }
});
app.get("/whatsapp/config", (_req, res) => res.json({ maxMessagesPerRequest }));

app.listen(port, () => {
  logger.info({ port }, "[WhatsApp] Service listening");
  startClient();
});
