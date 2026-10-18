/* SSE 帧可能横跨任意网络 chunk。 */
(function (root) {
  "use strict";
  class SSEParser {
    constructor(onEvent) {
      this.onEvent = onEvent;
      this.buffer = "";
      this.event = "message";
      this.data = [];
      this.id = "";
    }
    feed(text, final = false) {
      this.buffer += text;
      while (true) {
        const match = /[\r\n]/.exec(this.buffer);
        if (!match) break;
        const i = match.index;
        if (this.buffer[i] === "\r" && i === this.buffer.length - 1 && !final) break;
        const line = this.buffer.slice(0, i);
        const length = this.buffer.slice(i, i + 2) === "\r\n" ? 2 : 1;
        this.buffer = this.buffer.slice(i + length);
        this.line(line);
      }
      // 连接结束时未以空行完成的事件不派发。
      if (final) this.buffer = "";
    }
    line(line) {
      if (line === "") {
        if (this.data.length) this.onEvent({event: this.event, data: this.data.join("\n"), id: this.id});
        this.event = "message";
        this.data = [];
        return;
      }
      if (line.startsWith(":")) return;
      const colon = line.indexOf(":");
      const field = colon < 0 ? line : line.slice(0, colon);
      let value = colon < 0 ? "" : line.slice(colon + 1);
      if (value.startsWith(" ")) value = value.slice(1);
      if (field === "event") this.event = value;
      else if (field === "data") this.data.push(value);
      else if (field === "id" && !value.includes("\0")) this.id = value;
    }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {SSEParser};
  else root.SSEParser = SSEParser;
})(typeof window === "undefined" ? globalThis : window);
