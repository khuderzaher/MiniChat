# -*- coding: utf-8 -*-
"""
================================================================================
 MiniChat — واجهة داكنة زجاجية
================================================================================
"""
from __future__ import print_function

import os
import sys
import json
import threading
import webbrowser
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.chdir(HERE)

try:
    from flask import Flask, request, jsonify, Response
except ImportError:
    print("❌ Flask غير مثبّت")
    sys.exit(1)

from main import (
    StructuredDB, MemoryStore, Retriever, DialogueManager,
    CONFIG, set_seed,
)

# =============================================================================
# التهيئة
# =============================================================================
print("=" * 60)
print("  MiniChat — واجهة داكنة")
print("=" * 60)

set_seed(CONFIG["seed"])
db = StructuredDB(CONFIG["db_file"])
mem = MemoryStore(CONFIG["memory_file"])
retriever = Retriever(db, mem)
dm = DialogueManager(db, mem, retriever=retriever)

print("[APP] ✅ جاهز على http://127.0.0.1:5000")
print("=" * 60)


app = Flask(__name__)


# =============================================================================
# HTML — واجهة داكنة زجاجية بسيطة
# =============================================================================
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#0a0a15">
<title>MiniChat</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

html, body {
  height: 100%;
  font-family: -apple-system, 'SF Pro Display', 'Segoe UI', Tahoma, sans-serif;
  color: #e8eaf2;
  overflow: hidden;
  background: #050510;
}

/* خلفية متدرجة مع عناصر إضاءة */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 15% 20%, rgba(110, 100, 255, 0.15), transparent 45%),
    radial-gradient(circle at 85% 80%, rgba(255, 100, 200, 0.10), transparent 45%),
    radial-gradient(circle at 50% 50%, rgba(0, 200, 255, 0.06), transparent 60%),
    linear-gradient(160deg, #050510 0%, #0a0a18 50%, #06060f 100%);
  z-index: -2;
}

/* شبكة نقطية خفيفة */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image: radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 22px 22px;
  z-index: -1;
  pointer-events: none;
}

/* ============ التطبيق ============ */
.app {
  position: fixed;
  inset: 0;
  margin: auto;
  max-width: 720px;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 10px;
}

@media (min-width: 780px) {
  .app {
    height: 94vh;
    top: 3vh;
    padding: 16px;
  }
}

/* ============ الهيدر ============ */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(20, 20, 35, 0.55);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6ee7a8;
  box-shadow: 0 0 12px #6ee7a8, 0 0 4px #6ee7a8;
  animation: pulse 2.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.brand-name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #e8eaf2;
}

.brand-name span {
  color: #8b8fff;
  font-weight: 400;
  opacity: 0.7;
}

/* إحصائيات */
.stat {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: rgba(232, 234, 242, 0.5);
}

.stat b {
  color: #e8eaf2;
  font-weight: 600;
}

.sep {
  width: 1px;
  height: 12px;
  background: rgba(255,255,255,0.1);
}

/* زر الإعدادات */
.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.06);
  color: #b8bccb;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  transition: all 0.2s;
}

.icon-btn:hover,
.icon-btn:active {
  background: rgba(139, 143, 255, 0.15);
  border-color: rgba(139, 143, 255, 0.3);
  color: #8b8fff;
}

/* ============ منطقة المحادثة ============ */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 4px 4px 4px 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: rgba(139, 143, 255, 0.2) transparent;
}

.messages::-webkit-scrollbar { width: 4px; }
.messages::-webkit-scrollbar-thumb {
  background: rgba(139, 143, 255, 0.2);
  border-radius: 2px;
}

/* ============ رسائل ============ */
.msg {
  display: flex;
  animation: slideIn 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  max-width: 88%;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.msg.user {
  justify-content: flex-end;
  align-self: flex-end;
}

.msg.bot {
  justify-content: flex-start;
  align-self: flex-start;
}

.bubble {
  padding: 11px 15px;
  border-radius: 18px;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.msg.user .bubble {
  background: linear-gradient(135deg, rgba(139, 143, 255, 0.25), rgba(255, 100, 200, 0.18));
  border: 1px solid rgba(139, 143, 255, 0.35);
  color: #fff;
  border-bottom-right-radius: 6px;
}

.msg.bot .bubble {
  background: rgba(20, 20, 35, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #e8eaf2;
  border-bottom-left-radius: 6px;
}

.msg.bot .bubble.mono {
  font-family: 'SF Mono', 'Courier New', monospace;
  font-size: 11px;
  direction: ltr;
  text-align: left;
  white-space: pre;
  overflow-x: auto;
  max-width: 100%;
  padding: 12px 14px;
  line-height: 1.5;
}

/* ============ أزرار سريعة ============ */
.quick-row {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 0 4px;
  -webkit-overflow-scrolling: touch;
  flex-shrink: 0;
}

.quick-row::-webkit-scrollbar { display: none; }

.chip {
  padding: 7px 13px;
  background: rgba(20, 20, 35, 0.5);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #b8bccb;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 5px;
}

.chip:active {
  background: rgba(139, 143, 255, 0.2);
  border-color: rgba(139, 143, 255, 0.4);
  color: #fff;
  transform: scale(0.96);
}

/* ============ الإدخال ============ */
.input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 6px 16px;
  background: rgba(20, 20, 35, 0.6);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  flex-shrink: 0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.input-bar input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e8eaf2;
  font-family: inherit;
  font-size: 14px;
  padding: 8px 0;
  min-width: 0;
}

.input-bar input::placeholder {
  color: rgba(232, 234, 242, 0.3);
}

.send-btn {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: linear-gradient(135deg, #8b8fff, #b266ff);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
  flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(139, 143, 255, 0.3);
}

.send-btn:active {
  transform: scale(0.92);
}

.send-btn:disabled {
  opacity: 0.4;
}

/* ============ Modal الذاكرة ============ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 16, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 100;
  display: none;
  align-items: flex-end;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.modal-overlay.show {
  display: flex;
  opacity: 1;
}

.modal {
  width: 100%;
  max-width: 720px;
  max-height: 88vh;
  background: rgba(15, 15, 28, 0.95);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-bottom: none;
  border-radius: 24px 24px 0 0;
  padding: 20px;
  overflow-y: auto;
  transform: translateY(20px);
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.modal-overlay.show .modal {
  transform: translateY(0);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
  color: #e8eaf2;
  letter-spacing: 0.3px;
}

.close-btn {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.06);
  color: #b8bccb;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:active {
  background: rgba(255, 80, 80, 0.15);
  color: #ff6b6b;
}

/* Sections */
.section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 11px;
  color: #8b8fff;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(139,143,255,0.2), transparent);
}

/* Input */
.field {
  margin-bottom: 8px;
}

.field input {
  width: 100%;
  padding: 11px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #e8eaf2;
  font-family: inherit;
  font-size: 13px;
  outline: none;
  transition: all 0.2s;
}

.field input:focus {
  border-color: rgba(139, 143, 255, 0.4);
  background: rgba(139, 143, 255, 0.05);
}

.field input::placeholder {
  color: rgba(232, 234, 242, 0.25);
}

/* Button */
.btn {
  padding: 11px 16px;
  border: none;
  border-radius: 12px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-primary {
  background: linear-gradient(135deg, #8b8fff, #b266ff);
  color: #fff;
  box-shadow: 0 4px 16px rgba(139, 143, 255, 0.25);
}

.btn-primary:active {
  transform: scale(0.98);
}

.btn-ghost {
  background: rgba(255,255,255,0.05);
  color: #b8bccb;
  border: 1px solid rgba(255,255,255,0.06);
}

.btn-ghost:active {
  background: rgba(255,255,255,0.1);
}

.btn-danger {
  background: rgba(255, 80, 80, 0.1);
  color: #ff8a8a;
  border: 1px solid rgba(255, 80, 80, 0.2);
}

.btn-full { width: 100%; }
.btn-row { display: flex; gap: 8px; margin-top: 10px; }

/* Memory list */
.mem-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
}

.mem-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  animation: slideIn 0.2s;
}

.mem-content {
  flex: 1;
  min-width: 0;
}

.mem-q {
  font-size: 12px;
  color: #8b8fff;
  font-weight: 600;
  margin-bottom: 2px;
  word-wrap: break-word;
}

.mem-a {
  font-size: 13px;
  color: #e8eaf2;
  word-wrap: break-word;
}

.mem-del {
  background: transparent;
  border: none;
  color: rgba(255, 138, 138, 0.6);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 6px;
  border-radius: 8px;
  flex-shrink: 0;
}

.mem-del:active {
  background: rgba(255, 80, 80, 0.15);
  color: #ff8a8a;
}

.empty {
  text-align: center;
  color: rgba(232, 234, 242, 0.3);
  font-size: 12px;
  padding: 30px 10px;
}

/* Stats in modal */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}

.stat-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 12px 8px;
  text-align: center;
}

.stat-box .num {
  font-size: 20px;
  font-weight: 700;
  color: #8b8fff;
  font-variant-numeric: tabular-nums;
}

.stat-box .lbl {
  font-size: 10px;
  color: rgba(232, 234, 242, 0.4);
  margin-top: 3px;
  letter-spacing: 0.5px;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 90px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 15, 28, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(139, 143, 255, 0.3);
  color: #e8eaf2;
  padding: 10px 20px;
  border-radius: 14px;
  font-size: 13px;
  z-index: 9999;
  opacity: 0;
  transition: all 0.3s;
  pointer-events: none;
  max-width: 80%;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}

.toast.show {
  opacity: 1;
  bottom: 100px;
}

/* Loading dots */
.dots {
  display: inline-flex;
  gap: 3px;
  align-items: center;
}

.dots span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #8b8fff;
  animation: dots 1.4s infinite;
}

.dots span:nth-child(2) { animation-delay: 0.15s; }
.dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes dots {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-3px); }
}
</style>
</head>
<body>

<div class="app">

  <!-- الهيدر -->
  <div class="header">
    <div class="brand">
      <div class="dot"></div>
      <div class="brand-name">MiniChat <span>v2.2</span></div>
    </div>
    <div class="stat">
      <b id="statTurns">0</b><span>رسالة</span>
      <div class="sep"></div>
      <b id="statMem">0</b><span>ذاكرة</span>
      <button class="icon-btn" onclick="openMemory()" title="الذاكرة">⚙</button>
    </div>
  </div>

  <!-- المحادثة -->
  <div class="messages" id="messages">
    <div class="msg bot">
      <div class="bubble">مرحبًا 👋

اكتب رسالتك، أو استخدم الأزرار السريعة بالأسفل.

للاطلاع على الدليل: <b>~مساعدة</b></div>
    </div>
  </div>

  <!-- أزرار سريعة -->
  <div class="quick-row">
    <button class="chip" onclick="quick('~مساعدة')">📖 دليل</button>
    <button class="chip" onclick="quick('~مذاكرة')">🧠 مذاكرة</button>
    <button class="chip" onclick="quick('~تدريب')">🎓 تدريب</button>
    <button class="chip" onclick="quick('~ذاكرة')">💾 ذاكرة</button>
    <button class="chip" onclick="quick('~إحصاء')">📊 إحصاء</button>
  </div>

  <!-- الإدخال -->
  <div class="input-bar">
    <input id="chatInput" placeholder="اكتب رسالتك..."
           autocomplete="off" autocorrect="off" autocapitalize="off"
           onkeypress="if(event.key==='Enter') send()">
    <button class="send-btn" id="sendBtn" onclick="send()">➤</button>
  </div>

</div>

<!-- Modal الذاكرة -->
<div class="modal-overlay" id="memModal" onclick="if(event.target===this) closeMemory()">
  <div class="modal">

    <div class="modal-head">
      <div class="modal-title">⚙ الإعدادات والذاكرة</div>
      <button class="close-btn" onclick="closeMemory()">✕</button>
    </div>

    <!-- إحصائيات -->
    <div class="stats-row">
      <div class="stat-box"><div class="num" id="mCount">0</div><div class="lbl">معلومات</div></div>
      <div class="stat-box"><div class="num" id="mAssoc">0</div><div class="lbl">ترابطات</div></div>
      <div class="stat-box"><div class="num" id="mFb">0</div><div class="lbl">تقييمات</div></div>
    </div>

    <!-- الاسم -->
    <div class="section">
      <div class="section-title">اسمك</div>
      <div class="field">
        <input id="userName" placeholder="اكتب اسمك هنا">
      </div>
      <button class="btn btn-primary btn-full" onclick="saveName()">💾 حفظ الاسم</button>
    </div>

    <!-- إضافة معلومة -->
    <div class="section">
      <div class="section-title">إضافة معلومة</div>
      <div class="field">
        <input id="addQ" placeholder="السؤال أو المفتاح">
      </div>
      <div class="field">
        <input id="addA" placeholder="الجواب أو القيمة">
      </div>
      <button class="btn btn-primary btn-full" onclick="addMem()">➕ إضافة</button>
    </div>

    <!-- قائمة المعلومات -->
    <div class="section">
      <div class="section-title">كل المعلومات</div>
      <div class="mem-list" id="memList">
        <div class="empty">لا توجد معلومات بعد</div>
      </div>
    </div>

    <!-- إجراءات -->
    <div class="section">
      <div class="section-title">إجراءات</div>
      <div class="btn-row">
        <button class="btn btn-ghost" style="flex:1;" onclick="exportMem()">💾 تصدير</button>
        <button class="btn btn-danger" style="flex:1;" onclick="resetMem()">🧹 تصفير</button>
      </div>
    </div>

  </div>
</div>

<div class="toast" id="toast"></div>

<script>
/* ============ أدوات ============ */
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function toast(text) {
  const el = $('toast');
  el.textContent = text;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2200);
}

/* ============ المحادثة ============ */
const messagesEl = $('messages');
const inputEl = $('chatInput');
const sendBtn = $('sendBtn');
let isSending = false;

function addMsg(text, who) {
  const div = document.createElement('div');
  div.className = 'msg ' + who;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (text.length > 200 || text.includes('━') || text.includes('╔')) {
    bubble.classList.add('mono');
  }
  bubble.textContent = text;
  div.appendChild(bubble);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

async function send() {
  if (isSending) return;
  const text = inputEl.value.trim();
  if (!text) return;

  isSending = true;
  inputEl.value = '';
  addMsg(text, 'user');

  // مؤشر الكتابة
  const loading = document.createElement('div');
  loading.className = 'msg bot';
  loading.innerHTML = '<div class="bubble"><span class="dots"><span></span><span></span><span></span></span></div>';
  messagesEl.appendChild(loading);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  sendBtn.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    loading.remove();

    const reply = data.reply || '…';
    if (reply === '__EXIT__') {
      addMsg('إلى اللقاء 👋', 'bot');
    } else {
      addMsg(reply, 'bot');
    }
    refreshStats();
  } catch (e) {
    loading.remove();
    addMsg('⚠️ ' + e.message, 'bot');
  }

  sendBtn.disabled = false;
  isSending = false;
  inputEl.focus();
}

function quick(cmd) {
  inputEl.value = cmd;
  send();
}

/* ============ الإحصائيات ============ */
async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const s = await res.json();
    $('statTurns').textContent = s.turns || 0;
    $('statMem').textContent = s.learned_pairs || 0;
  } catch (e) {}
}

/* ============ Modal الذاكرة ============ */
function openMemory() {
  $('memModal').classList.add('show');
  loadMemory();
}
function closeMemory() {
  $('memModal').classList.remove('show');
}

async function loadMemory() {
  try {
    const res = await fetch('/api/memory/list');
    const data = await res.json();

    $('mCount').textContent = data.count || 0;
    $('mAssoc').textContent = data.assoc_count || 0;
    $('mFb').textContent = data.feedback_count || 0;
    $('userName').value = data.name || '';

    const box = $('memList');
    if (!data.pairs || !data.pairs.length) {
      box.innerHTML = '<div class="empty">لا توجد معلومات بعد</div>';
      return;
    }
    let html = '';
    for (const p of data.pairs) {
      html += `<div class="mem-item">
        <div class="mem-content">
          <div class="mem-q">${esc(p.q)}</div>
          <div class="mem-a">${esc(p.a)}</div>
        </div>
        <button class="mem-del" onclick="delMem('${esc(p.q).replace(/'/g, "\\'")}')">🗑</button>
      </div>`;
    }
    box.innerHTML = html;
  } catch (e) {
    toast('⚠️ فشل تحميل الذاكرة');
  }
}

async function saveName() {
  const name = $('userName').value.trim();
  if (!name) { toast('اكتب اسمًا'); return; }
  const res = await fetch('/api/memory/set_name', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name})
  });
  const d = await res.json();
  if (d.ok) { toast('✅ تم حفظ الاسم'); loadMemory(); }
  else toast('❌ فشل');
}

async function addMem() {
  const q = $('addQ').value.trim();
  const a = $('addA').value.trim();
  if (!q || !a) { toast('املأ السؤال والجواب'); return; }
  const res = await fetch('/api/memory/add', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({q, a})
  });
  const d = await res.json();
  if (d.ok) {
    toast('✅ تمت الإضافة');
    $('addQ').value = '';
    $('addA').value = '';
    loadMemory();
  } else toast('❌ فشل');
}

async function delMem(q) {
  if (!confirm('حذف هذه المعلومة؟')) return;
  const res = await fetch('/api/memory/delete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({q})
  });
  const d = await res.json();
  if (d.ok) { toast('🗑 تم الحذف'); loadMemory(); }
}

async function resetMem() {
  if (!confirm('سيُمسح كل شيء (الذاكرة + الأنماط). متأكد؟')) return;
  const res = await fetch('/api/reset', {method: 'POST'});
  const d = await res.json();
  if (d.ok) {
    toast('🧹 تم التصفير');
    loadMemory();
    refreshStats();
  }
}

async function exportMem() {
  const res = await fetch('/api/export', {method: 'POST'});
  const d = await res.json();
  toast(d.ok ? '💾 ' + d.path : '❌ فشل');
}

/* ============ التهيئة ============ */
refreshStats();
setInterval(refreshStats, 5000);
inputEl.focus();
</script>
</body>
</html>
"""


# =============================================================================
# Routes
# =============================================================================
@app.route("/")
def index():
    import os
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
    try:
        with open(tpl, "r", encoding="utf-8") as fh:
            html = fh.read()
    except Exception:
        html = INDEX_HTML
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "app": "MiniChat"})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get("message") or "").strip()
        if not text:
            return jsonify({"reply": "…"})
        reply = dm.respond(text)
        if reply == "__EXIT__":
            reply = "إلى اللقاء!"
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": "⚠️ خطأ: %s" % e})


@app.route("/api/stats")
def api_stats():
    try:
        return jsonify(mem.stats())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/list")
def api_memory_list():
    try:
        lp = mem.data.get("learned_pairs", {})
        pairs = []
        for item in sorted(lp.values(), key=lambda x: -x.get("count", 0)):
            pairs.append({
                "q": item.get("q", ""),
                "a": item.get("a", ""),
                "count": item.get("count", 1),
            })
        return jsonify({
            "pairs": pairs,
            "count": len(pairs),
            "name": mem.get_name(),
            "assoc_count": len(mem.data.get("associations", {})),
            "feedback_count": len(mem.data.get("feedback", {})),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/add", methods=["POST"])
def api_memory_add():
    try:
        data = request.get_json(force=True, silent=True) or {}
        q = (data.get("q") or "").strip()
        a = (data.get("a") or "").strip()
        if not q or not a:
            return jsonify({"ok": False, "message": "ناقص"})
        mem.add_learned_pair(q, a, score=2.0)
        mem.save()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/memory/delete", methods=["POST"])
def api_memory_delete():
    try:
        data = request.get_json(force=True, silent=True) or {}
        q = (data.get("q") or "").strip()
        if not q:
            return jsonify({"ok": False})
        ok = mem.forget(q)
        if ok:
            mem.save()
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/memory/set_name", methods=["POST"])
def api_set_name():
    try:
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"ok": False})
        mem.set_name(name)
        mem.save()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/train", methods=["POST"])
def api_train():
    try:
        count, msg = mem.train_patterns(db)
        return jsonify({"ok": True, "message": msg, "pairs": count})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/export", methods=["POST"])
def api_export():
    try:
        p = mem.export_to_json()
        return jsonify({"ok": bool(p), "path": p or ""})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    try:
        mem.data = mem._empty()
        mem.patterns = mem._empty_patterns()
        mem.save()
        mem._save_patterns()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


# =============================================================================
# التشغيل
# =============================================================================
def _open_browser():
    import time
    time.sleep(1.5)
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    try:
        app.run(host="0.0.0.0", port=5000, debug=False,
                use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[APP] تم الإيقاف.")
    except Exception as e:
        print("\n[APP] ❌ %s" % e)