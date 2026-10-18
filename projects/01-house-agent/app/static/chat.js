/* 显式保存 interrupt 状态；工具事件只表示执行进度。 */
(() => {
  "use strict";
  const config = window.HOUSE_CONFIG;
  const base = config.apiBase.replace(/\/$/, "");
  const byId = id => document.getElementById(id);
  const box = byId("chatMessages"), input = byId("chatInput"), send = byId("sendBtn");
  const finalNodes = new Set(["generate_query", "call_orders", "extend_node", "get_user_preferences"]);
  let threadId, creating, busy = false, pendingInterrupt = false;
  function bubble(text, className = "ai-message") {
    const el = document.createElement("div");
    el.className = `message ${className}`;
    el.style.whiteSpace = "pre-wrap";
    el.textContent = text;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }
  async function post(path, payload) {
    const response = await fetch(base + path, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${(await response.text()).slice(0, 300)}`);
    return response;
  }
  async function ensureThread() {
    if (threadId) return threadId;
    if (!creating) creating = post("/threads", {}).then(r => r.json()).then(data => {
      if (!data.thread_id) throw new Error("创建 thread 的响应缺少 thread_id");
      return (threadId = data.thread_id);
    }).finally(() => { creating = null; });
    return creating;
  }
  byId("chatIcon").onclick = () => { byId("chatContainer").style.display = "flex"; input.focus(); };
  byId("closeChat").onclick = () => { byId("chatContainer").style.display = "none"; };
  function contentText(content) {
    if (typeof content === "string") return content;
    return Array.isArray(content) ? content.filter(x => x.type === "text").map(x => x.text || "").join("") : "";
  }
  async function sendMessage() {
    const message = input.value.trim();
    if (!message || busy) return;
    busy = true; send.disabled = true;
    input.value = ""; bubble(message, "user-message");
    const resuming = pendingInterrupt;
    let observedInterrupt = false;
    try {
      await ensureThread();
      const payload = {
        assistant_id: config.assistantId,
        context: {user_id: config.userId},
        stream_mode: ["updates", "messages"], stream_subgraphs: true,
        ...(resuming ? {command: {resume: message}} : {input: {messages: [{role: "human", content: message}]}}),
      };
      const response = await post(`/threads/${threadId}/runs/stream`, payload);
      const nodes = new Map(), rendered = new Map(), seen = new Set();
      const showMessage = (msg, node) => {
        if (!msg || msg.type !== "ai" || msg.tool_calls?.length || !finalNodes.has(node)) return;
        const text = contentText(msg.content);
        if (!text) return;
        const key = msg.id || node;
        if (!rendered.has(key)) rendered.set(key, bubble(""));
        rendered.get(key).textContent = text;
        box.scrollTop = box.scrollHeight;
      };
      const parser = new window.SSEParser(({event, data}) => {
        const parsed = JSON.parse(data);
        if (event === "error") throw new Error(parsed.message || JSON.stringify(parsed));
        if (event.startsWith("messages/metadata")) {
          Object.entries(parsed).forEach(([id, info]) => nodes.set(id, info.metadata?.langgraph_node));
        } else if (event.startsWith("messages/partial") || event.startsWith("messages/complete")) {
          (Array.isArray(parsed) ? parsed : [parsed]).forEach(msg => showMessage(msg, nodes.get(msg.id)));
        } else if (event.startsWith("updates")) {
          for (const item of parsed.__interrupt__ || []) {
            const id = item.id || JSON.stringify(item.value);
            observedInterrupt = true;
            if (!seen.has(id)) { seen.add(id); bubble(String(item.value)); }
          }
          Object.entries(parsed).forEach(([node, update]) => {
            for (const msg of update?.messages || []) {
              showMessage(msg, node);
              for (const tool of msg.tool_calls || []) {
                const id = `tool:${tool.id}`;
                if (!seen.has(id)) { seen.add(id); bubble(`正在执行工具：${tool.name}`, "process-message"); }
              }
            }
          });
        }
      });
      if (!response.body) throw new Error("浏览器未提供可读取的流响应");
      const reader = response.body.getReader(), decoder = new TextDecoder();
      try {
        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          parser.feed(decoder.decode(value, {stream: true}));
        }
        parser.feed(decoder.decode(), true);
      } catch (error) {
        await reader.cancel();
        throw error;
      } finally { reader.releaseLock(); }
      pendingInterrupt = observedInterrupt;
    } catch (error) {
      pendingInterrupt = observedInterrupt || resuming;
      bubble(`请求失败：${error.message}\n请检查 API 地址、后端日志与 thread 状态。`);
    } finally { busy = false; send.disabled = false; input.focus(); }
  }
  send.onclick = sendMessage;
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.isComposing) { event.preventDefault(); sendMessage(); }
  });
})();
