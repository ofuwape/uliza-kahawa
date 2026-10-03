// End-to-end check of the basic-phone server over real HTTP: USSD sessions (Africa's Talking format), SMS (both
// formats), the 182-character limit, the reply time against the ~10 s USSD limit, and no phone number stored.
// Run: node tests/ussd_test.js
const fs = require('fs');
const path = require('path');
const {server} = require('../ussd/server.js');

const QUEUE = path.join(__dirname, '../ussd/queue.jsonl');
let pass = 0, fail = 0;
const check = (name, ok, detail = '') => { ok ? pass++ : (fail++, console.log('FAIL', name, detail)); };

async function post(port, route, params) {
  const t0 = Date.now();
  const r = await fetch(`http://localhost:${port}${route}`, {method: 'POST', body: new URLSearchParams(params)});
  return {text: await r.text(), ms: Date.now() - t0, type: r.headers.get('content-type')};
}

(async () => {
  if (fs.existsSync(QUEUE)) fs.unlinkSync(QUEUE);
  server.listen(0);
  const port = server.address().port;
  const s = {sessionId: 'ATUid_test', serviceCode: '*384*2026#', phoneNumber: '+254712345678'};

  let r = await post(port, '/ussd', {...s, text: ''});
  check('menu', r.text.startsWith('CON ') && r.text.includes('1 Uliza swali'), r.text);
  r = await post(port, '/ussd', {...s, text: '1'});
  check('prompt', r.text.startsWith('CON ') && r.text.includes('swali'), r.text);
  r = await post(port, '/ussd', {...s, text: '1*majani yana unga wa njano chini'});
  check('rust answer', r.text.startsWith('END ') && r.text.includes('kutu'), r.text);
  check('fits a USSD screen', r.text.length - 4 <= 182, r.text.length);
  check('reply well inside 10 s', r.ms < 1000, r.ms + ' ms');
  r = await post(port, '/ussd', {...s, text: '9*1*small holes in my berries'});
  check('english borer', r.text.startsWith('END ') && /borer/i.test(r.text), r.text);
  r = await post(port, '/ussd', {...s, text: '1*bei ya maziwa'});
  check('out of scope -> not sure', r.text.startsWith('END ') && r.text.includes('Naweza kusaidia tu'), r.text);
  r = await post(port, '/ussd', {...s, text: '9*1*tell me about rust berries'});
  check('mixed question -> did you mean', r.text.startsWith('CON Did you mean:') && r.text.includes('0 Talk to a person'), r.text);
  r = await post(port, '/ussd', {...s, text: '9*1*tell me about rust berries*1'});
  check('choice 1 -> that answer', r.text.startsWith('END ') && !r.text.includes('Not sure'), r.text);
  r = await post(port, '/ussd', {...s, text: 'nipige dawa lini'});
  check('free entry at the menu', r.text.startsWith('END ') && r.text.includes('Oktoba'), r.text);
  r = await post(port, '/ussd', {...s, text: '9*tell me about rust berries'});
  check('free entry -> did you mean', r.text.startsWith('CON Did you mean:'), r.text);
  r = await post(port, '/ussd', {...s, text: '9*tell me about rust berries*2'});
  check('free entry choice', r.text.startsWith('END ') && !r.text.includes('Not sure'), r.text);
  r = await post(port, '/ussd', {...s, text: '2'});
  check('price', r.text.startsWith('END ') && r.text.includes('Arabica'), r.text);

  r = await post(port, '/sms', {from: '+254700000001', text: 'nipige dawa lini'});
  check('AT sms json', r.type.includes('json') && JSON.parse(r.text).reply.includes('Oktoba'), r.text);
  r = await post(port, '/sms', {From: '+254700000002', Body: 'EN why is my yield dropping'});
  check('Twilio sms TwiML', r.type.includes('xml') && r.text.includes('<Message>Check:'), r.text);

  r = await post(port, '/sms', {from: '+254700000003', text: 'EN tell me about rust berries'});
  check('sms did you mean', JSON.parse(r.text).reply.startsWith('Did you mean:'), r.text);
  r = await post(port, '/sms', {from: '+254700000003', text: '0'});
  check('sms 0 -> a person', JSON.parse(r.text).reply.includes('extension officer'), r.text);

  const q = fs.readFileSync(QUEUE, 'utf8');
  check('not-sure question queued for a person', q.includes('bei ya maziwa'));
  check('no full phone number stored', !q.includes('712345678') && !q.includes('+2547'));

  server.close();
  console.log(`basic-phone server: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
