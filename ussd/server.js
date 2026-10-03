// The basic-phone channels as a server: the SAME classifier (app/model.js) and the SAME channel logic
// (app/channels.js) the demo page runs, ready to sit behind a USSD gateway or SMS number. Not needed for the demo:
// it shows the page is not a mock-up. Zero dependencies: `node ussd/server.js` (PORT=8790).
//
//   POST /ussd   form fields sessionId, serviceCode, phoneNumber, text ("1*my question") -> "CON ..." | "END ..."
//   POST /sms    (from, text) -> JSON {reply};  (From, Body) -> TwiML <Message>
//   GET  /health
//
// Privacy: no phone number is stored or logged. Questions for a person go to ussd/queue.jsonl with the last 2 digits
// only (a real deployment keeps the number in the cooperative's own system, with the farmer's consent).
const http = require('http');
const fs = require('fs');
const path = require('path');
const SmallModel = require('../app/model.js');
const Channels = require('../app/channels.js');

const ROOT = path.join(__dirname, '..');
const QUEUE = path.join(__dirname, 'queue.jsonl');
const model = SmallModel.load(JSON.parse(fs.readFileSync(path.join(ROOT, 'models/model.json'))));
const A = JSON.parse(fs.readFileSync(path.join(ROOT, 'answers/answers.built.json')));
let current = '';                              // phone of the request being handled (for the queue tail only)
const ch = Channels.make(model, A, q => fs.appendFileSync(QUEUE,
  JSON.stringify({ts: new Date().toISOString(), question: q, phone_tail: String(current).slice(-2)}) + '\n'));

const readBody = req => new Promise(res => { let b = ''; req.on('data', c => { b += c; }); req.on('end', () => res(b)); });
const xml = s => s.replace(/[<>&]/g, c => ({'<': '&lt;', '>': '&gt;', '&': '&amp;'}[c]));

const server = http.createServer(async (req, res) => {
  const t0 = process.hrtime.bigint();
  const url = new URL(req.url, 'http://x');
  if (req.method === 'GET' && url.pathname === '/health') return res.end('ok');
  if (req.method !== 'POST' || !['/ussd', '/sms'].includes(url.pathname)) { res.statusCode = 404; return res.end(); }
  const p = Object.fromEntries(new URLSearchParams(await readBody(req)));
  let out, type = 'text/plain', body;
  if (url.pathname === '/ussd') {
    current = p.phoneNumber || '';
    out = ch.ussd(p.text || '');
    body = out.reply;
  } else {
    current = p.From ?? p.from ?? '';
    out = ch.sms(p.Body ?? p.text, undefined, current);
    if (p.Body !== undefined) { type = 'text/xml'; body = `<Response><Message>${xml(out.reply)}</Message></Response>`; }
    else { type = 'application/json'; body = JSON.stringify({reply: out.reply}); }
  }
  current = '';
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  const d = out.decision;
  // Log the decision and the time, never the phone number or the question text.
  console.log(`${url.pathname} ${ms.toFixed(1)} ms of ${Channels.LIMIT_MS} ms` +
              (d ? ` · ${d.r.answered ? d.r.label : 'not sure'} (top: ${d.r.label} ${(d.r.confidence * 100).toFixed(0)}%)` : ''));
  res.setHeader('Content-Type', type);
  res.end(body);
});

if (require.main === module) {
  const port = +process.env.PORT || 8790;
  server.listen(port, () => console.log(`Uliza Kahawa basic-phone server on :${port} (POST /ussd, /sms)`));
}
module.exports = {server};
