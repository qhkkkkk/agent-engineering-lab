const assert = require("node:assert/strict");
const {SSEParser} = require("../static/sse.js");
const source = ': heartbeat\r\nevent: updates|child:1\r\ndata: {"city":"太原"}\r\n\r\nevent: messages/partial\ndata: [1,\ndata: 2]\n\n';
const expected = [
  {event: "updates|child:1", data: '{"city":"太原"}', id: ""},
  {event: "messages/partial", data: "[1,\n2]", id: ""},
];
let checks = 0;
const bytes = Buffer.from(source);
for (let split = 0; split <= bytes.length; split++) {
  const output = [], parser = new SSEParser(x => output.push(x)), decoder = new TextDecoder();
  parser.feed(decoder.decode(bytes.subarray(0, split), {stream: true}));
  parser.feed(decoder.decode(bytes.subarray(split), {stream: true}));
  parser.feed(decoder.decode(), true);
  assert.deepEqual(output, expected); checks++;
}
{
  const output = [], parser = new SSEParser(x => output.push(x)), decoder = new TextDecoder();
  for (const byte of bytes) parser.feed(decoder.decode(Uint8Array.of(byte), {stream: true}));
  parser.feed(decoder.decode(), true);
  assert.deepEqual(output, expected); checks++;
}
{
  const output = [], parser = new SSEParser(x => output.push(x));
  parser.feed('id: run-1\revent: updates\rdata: {}\r\r');
  parser.feed('', true);
  assert.deepEqual(output, [{event: 'updates', data: '{}', id: 'run-1'}]); checks++;
  parser.feed('data: incomplete', true);
  assert.equal(output.length, 1); checks++;
}
console.log(`SSE checks passed: ${checks} (all byte split positions, UTF-8, CRLF, multiline, incomplete frame)`);
