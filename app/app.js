// Uliza Kahawa: the app on the household phone (tab 1) and the basic phone by USSD / SMS (tab 2).
// Everything runs in this page: the model (model.js + ../models/model.json) and the expert answers
// (../answers/answers.built.json) are saved by sw.js, so it keeps working with no internet.
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const S = {lang: localStorage.getItem('uk_lang') || 'sw', view: sessionStorage.getItem('uk_consent') ? 'home' : 'consent',
           share: sessionStorage.getItem('uk_consent') !== 'local', sel: 0, last: null, model: null, answers: null,
           log: JSON.parse(sessionStorage.getItem('uk_log') || '[]'), simOff: false};

// Phone screen text, per language.
const T = {
  sw: {ask: 'Uliza swali', price: 'Bei ya kahawa', log: 'Maswali yangu', person: 'Ongea na mtu', lang: 'Lugha: Kiswahili',
       type: 'Andika swali lako…', send: 'Tuma', more: 'Soma zaidi', back: 'Rudi', menu: 'Menyu', unsure: 'Sina uhakika',
       priceNote: 'Hii ni bei ya kulinganisha, si ofa. Wewe ndiye unaamua.', empty: 'Bado hujauliza swali.',
       listen: '🔊 Sikiliza', offline: 'bila mtandao', clear: 'Futa maswali yangu',
       consentT: 'Kabla ya kuanza',
       consent: 'Maswali yako yanahifadhiwa kwenye simu hii. Swali ambalo siwezi kujibu hutumwa kwa SMS kwa afisa ugani wa chama chako, pamoja na namba yako ili akupigie. Hakuna kingine kinachotumwa. Unaweza kufuta maswali yako wakati wowote kwenye menyu.',
       agree: 'Nakubali', noSend: 'Usitume maswali yangu', cleared: 'Maswali yamefutwa.', confirmClear: 'Futa maswali yote kwenye simu hii?',
       kept: 'Imehifadhiwa kwenye simu (haitumwi)'},
  en: {ask: 'Ask a question', price: 'Coffee price', log: 'My questions', person: 'Talk to a person', lang: 'Language: English',
       type: 'Type your question…', send: 'Send', more: 'Read more', back: 'Back', menu: 'Menu', unsure: 'Not sure',
       priceNote: 'This is a reference price, not an offer. You decide.', empty: 'No questions yet.',
       listen: '🔊 Listen', offline: 'no signal', clear: 'Clear my questions',
       consentT: 'Before you start',
       consent: 'Your questions are saved on this phone. A question I cannot answer is sent by SMS to your cooperative\'s extension officer, with your number so they can call you back. Nothing else is shared. You can clear your questions any time from the menu.',
       agree: 'I agree', noSend: 'Don\'t send my questions', cleared: 'Questions cleared.', confirmClear: 'Clear all questions on this phone?',
       kept: 'Kept on the phone (not sent)'},
};
const topic = (id, lang) => Channels.label(id, lang);
const t = k => T[S.lang][k];
const online = () => navigator.onLine && !S.simOff;
const intent = id => S.answers.intents.find(i => i.id === id) || S.answers.fallback;
// Demo: questions, consent and approvals live in this browser tab only (sessionStorage) and are gone when it closes.
const save = () => sessionStorage.setItem('uk_log', JSON.stringify(S.log.slice(-200)));
const pct = p => Math.round(p * 100) + '%';

// ---------------------------------------------------------------- the decision (shared by both phones)
function decide(text) {
  const d = CH.decide(text, {queue: false});
  S.log.push({id: Date.now(), ts: new Date().toISOString(), text, label: d.r.label, conf: +d.r.confidence.toFixed(3),
              answered: d.r.answered, status: d.toPerson ? 'waiting' : d.options ? 'asked' : 'answered'});
  save(); renderQueue();
  return d;
}

function hoodHTML(r, text, basic, opts) {
  const need = pct(S.model.threshold);
  const rows = r.top.map(x => `<div class="row ${x.p < S.model.threshold ? 'low' : ''}"><span>${esc(topic(x.label, 'en'))}</span>
    <span class="barw"><i style="width:${pct(x.p)}"></i></span><span>${pct(x.p)}</span></div>`).join('');
  const verdict = opts
    ? `<b class="warn">Unsure</b> between ${opts.map(o => '<b>' + esc(topic(o, 'en')) + '</b>').join(' and ')}, so it asked the farmer to choose. It never guesses.`
    : r.answered
    ? `<b class="ok">Answered.</b> It was ${pct(r.confidence)} sure this is about <b>${esc(topic(r.label, 'en'))}</b>, so it showed the expert answer for that.`
    : r.label === S.model.none
      ? `<b class="warn">Not a coffee question it knows</b>, so it did not guess. The question goes to a person.`
      : `<b class="warn">Not sure enough</b> (${pct(r.confidence)}, it needs ${need}), so it did not guess. The question goes to a person.`;
  return `<p class="said">“${esc(text)}”</p><p>${verdict}</p><div class="rows">${rows}</div>
    <p class="note">It only answers when it is at least ${need} sure. ${basic ? 'On a basic phone this runs behind the USSD code or SMS number: it needs a phone signal, but no internet or data on the phone.' : 'All of this ran on the phone, with no internet.'}</p>`;
}

// ---------------------------------------------------------------- tab 1: the app
const MENU = ['ask', 'price', 'log', 'person', 'lang', 'clear'];
function render() {
  const sc = $('screen');
  const bar = `<div class="bar"><span>Uliza Kahawa</span><span>${online() ? '📶' : '✈ ' + t('offline')}</span></div>`;
  let body = '';
  const soft = (l, r) => { $('softL').textContent = l; $('softR').textContent = r; };
  if (S.view === 'consent') {
    body = `<div class="ans"><b>${t('consentT')}</b><div class="small" style="margin:6px 0 4px;color:var(--ink)">${t('consent')}</div>
      <button class="btn" data-consent="share">1 ${t('agree')}</button><button class="btn alt" data-consent="local">2 ${t('noSend')}</button></div>`;
    soft('', '');
  } else if (S.view === 'cleared') {
    body = `<div class="small">${t('cleared')}</div>`;
    soft(t('back'), t('menu'));
  } else if (S.view === 'home') {
    body = `<ul class="menu">${MENU.map((m, i) => `<li data-go="${m}" class="${i === S.sel ? 'sel' : ''}">${t(m)}</li>`).join('')}</ul>`;
    soft('', 'OK');
  } else if (S.view === 'ask') {
    body = `<textarea id="q" placeholder="${t('type')}"></textarea><button class="btn" id="go">${t('send')}</button>`;
    soft(t('back'), t('send'));
  } else if (S.view === 'answer' && S.last.options) {
    body = `<div class="ans"><span class="tag unsure">${S.lang === 'sw' ? 'Ulimaanisha?' : 'Did you mean?'}</span>
      ${S.last.options.map((id, i) => `<button class="btn alt" data-pick="${i + 1}">${i + 1} ${esc(topic(id, S.lang))}</button>`).join('')}
      <button class="btn alt" data-pick="0">0 ${t('person')}</button></div>`;
    soft(t('back'), t('menu'));
  } else if (S.view === 'answer') {
    const {it, r} = S.last;
    body = `<div class="ans"><span class="tag ${r.answered ? '' : 'unsure'}">${r.answered ? esc(topic(it.id, S.lang)) : t('unsure')}</span>
      <div>${esc(it.sms[S.lang])}</div>${it.more && S.showMore ? `<div class="more">${esc(it.more[S.lang])}</div>` : ''}
      ${it.more && !S.showMore ? `<button class="btn alt" id="more">${t('more')}</button>` : ''}
      <button class="btn alt" id="listen">${t('listen')}</button></div>`;
    soft(t('back'), t('menu'));
  } else if (S.view === 'price') {
    const f = S.answers.filled;
    body = `<div class="small">Arabica · World Bank · ${esc(f.price_month)}</div><div class="price-big">${esc(f.arabica)}</div>
      <div class="small" style="margin-top:6px">${esc(intent('price').sms[S.lang])}</div>
      <div class="small" style="margin-top:8px"><b>${t('priceNote')}</b></div>`;
    soft(t('back'), t('menu'));
  } else if (S.view === 'log') {
    const items = S.log.slice(-12).reverse();
    body = items.length ? `<ul class="log">${items.map(e => `<li>${esc(e.text)}<br><span class="small">
      ${e.answered ? esc(topic(e.label, S.lang)) : t('unsure')}${e.status === 'waiting' ? ' · ⏳' : e.status === 'sent' ? ' · ✓' : ''}</span></li>`).join('')}</ul>`
      : `<div class="small">${t('empty')}</div>`;
    soft(t('back'), t('menu'));
  }
  sc.innerHTML = bar + `<div class="view">${body}</div>`;
  const q = $('q'); if (q) { q.focus(); q.onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(q.value); } }; }
  if ($('go')) $('go').onclick = () => ask($('q').value);
  if ($('more')) $('more').onclick = () => { S.showMore = true; render(); };
  if ($('listen')) $('listen').onclick = () => play(S.last.it.id);
  sc.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => {
    const it = CH.choose(S.last.q, S.last.options, b.dataset.pick);
    S.last = {it, q: S.last.q, r: {answered: true, label: it.id, confidence: 1, top: []}}; S.showMore = false; render();
  });
  sc.querySelectorAll('[data-go]').forEach(li => li.onclick = () => go(li.dataset.go));
  sc.querySelectorAll('[data-consent]').forEach(b => b.onclick = () => {
    sessionStorage.setItem('uk_consent', b.dataset.consent); S.share = b.dataset.consent === 'share';
    S.view = 'home'; render(); renderQueue();
  });
}
function go(m) {
  if (m === 'lang') return setLang(S.lang === 'sw' ? 'en' : 'sw');
  if (m === 'clear') {
    if (!confirm(t('confirmClear'))) return;
    S.log = []; save(); renderQueue(); S.view = 'cleared'; return render();
  }
  if (m === 'person') { S.last = fixed('ask_person', t('person')); S.view = 'answer'; return render(); }
  S.view = m; S.showMore = false; render();
}
function fixed(id, text) {
  S.log.push({id: Date.now(), ts: new Date().toISOString(), text, label: id, conf: 1, answered: true, status: 'waiting'});
  save(); renderQueue();
  return {it: intent(id), r: {answered: true, label: id, confidence: 1, top: []}};
}
function ask(text) {
  if (!text || !text.trim()) return;
  const d = decide(text.trim());
  S.last = {...d, q: text.trim()}; S.view = 'answer'; S.showMore = false; render();
  $('hood').innerHTML = hoodHTML(d.r, text.trim(), false, d.options);
}
function key(k) {
  if (S.view === 'consent') return;
  if (S.view === 'home' && (k === 'ok' || k === 'right')) return go(MENU[S.sel]);
  if (S.view === 'ask' && (k === 'right' || k === 'ok')) return ask($('q').value);
  if (k === 'left' || k === 'right') { S.view = 'home'; render(); }
}
document.querySelectorAll('.kai [data-key]').forEach(b => b.onclick = () => key(b.dataset.key));
document.addEventListener('keydown', e => {
  if ($('tab-smart').hidden || ['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName)) return;
  if (S.view === 'home' && e.key === 'ArrowDown') { S.sel = (S.sel + 1) % MENU.length; render(); }
  if (S.view === 'home' && e.key === 'ArrowUp') { S.sel = (S.sel + MENU.length - 1) % MENU.length; render(); }
  if (e.key === 'Enter') key('ok');
  if (e.key === 'Escape' || e.key === 'Backspace') key('left');
});

// ---------------------------------------------------------------- recorded answers (synthetic voice for the demo)
let player;
function play(id, lang) {
  const f = S.audio && S.audio[id] && S.audio[id][lang || S.lang];
  if (!f) return;
  if (player) player.pause();
  player = new Audio('../answers/' + f);
  player.play().catch(() => {});
}

// ---------------------------------------------------------------- questions for a person: saved, sent when there is signal
function renderQueue() {
  const w = S.log.filter(e => e.status === 'waiting' || e.status === 'sent').slice(-5).reverse();
  $('queue').innerHTML = w.length ? w.map(e => `<div class="${e.status}">${e.status === 'sent' ? '✓ Sent by SMS' : !S.share ? '🔒 ' + T.en.kept : '⏳ Saved, waiting for signal'}
    <span class="small">“${esc(e.text)}”</span></div>`).join('') : '<p class="note">None yet.</p>';
}
function flush() {
  if (!online() || !S.share) return;                 // the farmer chose not to send: keep questions on the phone
  let n = 0;
  S.log.forEach(e => { if (e.status === 'waiting') { e.status = 'sent'; n++; } });
  if (n) { save(); renderQueue(); }
}
function netBadge() {
  const on = online();
  $('net').textContent = on ? '📶 Signal' : '✈ No signal: still works';
  $('net').classList.toggle('off', !on);
  if (S.answers) render();
  if (on) setTimeout(flush, 1200);
}
window.addEventListener('online', netBadge); window.addEventListener('offline', netBadge);
$('simOff').onchange = e => { S.simOff = e.target.checked; netBadge(); };

// ---------------------------------------------------------------- tab 2: basic phone (USSD / SMS)
// The basic phone runs app/channels.js, the same code the server (ussd/server.js) runs behind a real USSD code or
// SMS number, so this screen shows exactly what a phone would get.
const U = {path: null, mode: 'ussd', thread: []};   // path: what has been typed this USSD session (null = no session)
let CH;                                            // channel logic, created at boot
function screen2(text) { $('ussd').innerHTML = `<div class="ussd-box">${esc(text)}</div>`; }
// Every USSD request has to be answered before the gateway gives up (~10 s). Show the time each reply took.
const LIMIT = 10000;
function timed(work) {
  const slow = $('slow2g').checked;
  const t0 = performance.now();
  const out = work();                                 // the model + answer lookup
  const model = performance.now() - t0;
  const net = slow ? 1700 + Math.random() * 600 : 150 + Math.random() * 100;   // phone -> network -> server -> back
  const total = model + net;
  const el = $('ussdTimer');
  el.hidden = false;
  screen2(S.lang === 'sw' ? 'Inatuma…' : 'Sending…');
  const start = performance.now();
  const tick = () => {
    const e = Math.min(performance.now() - start, total);
    el.innerHTML = `Waiting for the reply: ${(e / 1000).toFixed(1)} s of ~10 s<div class="tb"><i style="width:${(e / LIMIT * 100).toFixed(1)}%"></i></div>`;
    if (e < total) return requestAnimationFrame(tick);
    el.innerHTML = `Reply in ${(total / 1000).toFixed(2)} s of ~10 s (AI ${model < 1 ? '<1' : model.toFixed(0)} ms, network ${(net / 1000).toFixed(2)} s${slow ? ', slow 2G' : ''})
      <div class="tb"><i style="width:${(total / LIMIT * 100).toFixed(1)}%"></i></div>`;
    out();
  };
  requestAnimationFrame(tick);
}
function ussdRequest() {
  const text = U.path.join('*');
  timed(() => {
    const out = CH.ussd(text);
    return () => {
      const end = out.reply.startsWith('END ');
      const msg = out.reply.slice(4);
      screen2(end ? msg + `\n\n(${msg.length} of 182 characters. Session ended.)` : msg);
      const typed = U.path.filter(x => !/^[0-9]$/.test(x));         // the question (menu digits removed)
      if (out.decision) $('hood2').innerHTML = hoodHTML(out.decision.r, typed[typed.length - 1] || '', true, out.reply.startsWith('CON ') ? out.decision.options : null);
      if (end) U.path = null;
    };
  });
}
function ussdStep(input) {
  input = (input || '').trim();
  if (U.mode === 'sms') {
    if (!input) return;
    const out = CH.sms(input, S.lang, 'page');
    U.thread.push(['me', input], ['them', out.reply]);
    $('ussd').innerHTML = `<div class="sms">${U.thread.slice(-6).map(([w, m]) => `<div class="${w}">${esc(m)}</div>`).join('')}</div>`;
    if (out.decision) $('hood2').innerHTML = hoodHTML(out.decision.r, input, true, out.decision.options);
    return;
  }
  if (U.mode === 'voice') return voiceKey(input);
  if (U.path === null) {
    if (input.replace(/\s/g, '') === '*384*2026#') { U.path = S.lang === 'en' ? ['9'] : []; return ussdRequest(); }
    return screen2(S.lang === 'sw' ? 'Bonyeza "Dial code" kupiga *384*2026#\nau SMS kutuma swali' : 'Press "Dial code" to dial *384*2026#\nor SMS to text a question');
  }
  if (!input) return;
  U.path.push(input);
  ussdRequest();
}
$('ussdDial').onclick = () => { U.mode = 'ussd'; U.path = null; ussdStep('*384*2026#'); };
// Voice line: a keypad menu that plays the recorded answers (a basic phone has no offline speech recognition).
const VOICE = ['leaf_rust', 'cbd', 'berry_borer', 'spray_timing', 'yield_drop', 'price', 'ask_person'];
function voiceMenu() {
  const intro = S.lang === 'sw' ? '📞 Uliza Kahawa (sauti)\nBonyeza namba:' : '📞 Uliza Kahawa (voice)\nPress a number:';
  $('ussd').innerHTML = `<div class="voice"><div class="ussd-box" style="padding:0 0 6px">${esc(intro)}</div>${VOICE.map((id, i) =>
    `<button class="opt" data-v="${i === VOICE.length - 1 ? 0 : i + 1}">${i === VOICE.length - 1 ? 0 : i + 1} ${esc(topic(id, S.lang))}</button>`).join('')}</div>`;
  $('ussd').querySelectorAll('[data-v]').forEach(b => b.onclick = () => voiceKey(b.dataset.v));
}
function voiceKey(k) {
  const i = k === '0' ? VOICE.length - 1 : +k - 1;
  const id = VOICE[i];
  if (!id) return voiceMenu();
  if (id === 'ask_person') fixed('ask_person', '(voice) ' + t('person'));
  play(id);
  $('ussd').innerHTML = `<div class="voice"><div class="ussd-box" style="padding:0">🔊 ${esc(topic(id, S.lang))}\n\n${esc(intent(id).sms[S.lang])}</div>
    <button class="opt" id="vback">${S.lang === 'sw' ? '* Rudi kwenye menyu' : '* Back to the menu'}</button></div>`;
  $('vback').onclick = voiceMenu;
}
$('ussdVoice').onclick = () => { U.mode = 'voice'; U.path = null; $('ussdTimer').hidden = true; voiceMenu(); };
$('ussdSend').onclick = () => { ussdStep($('ussdIn').value); $('ussdIn').value = ''; $('ussdIn').focus(); };
$('ussdIn').onkeydown = e => { if (e.key === 'Enter') $('ussdSend').click(); };
$('ussdCancel').onclick = () => { if (player) player.pause(); U.path = null; U.mode = 'ussd'; U.thread = []; $('ussdTimer').hidden = true; ussdStep(''); };
$('ussdSms').onclick = () => {
  U.mode = 'sms'; U.thread = []; $('ussdTimer').hidden = true;
  screen2(S.lang === 'sw' ? 'SMS kwa Uliza Kahawa\nAndika swali chini, bonyeza Send.' : 'SMS to Uliza Kahawa\nType a question below and press Send.');
};

// ---------------------------------------------------------------- language, tabs, example questions, boot
function setLang(l) {
  S.lang = l; localStorage.setItem('uk_lang', l);
  document.querySelectorAll('[data-lang]').forEach(b => b.classList.toggle('on', b.dataset.lang === l));
  if (S.answers) { render(); renderBrief(); if (U.mode === 'ussd' && U.path === null) ussdStep(''); }
}
document.querySelectorAll('[data-lang]').forEach(b => b.onclick = () => setLang(b.dataset.lang));
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => {
  document.querySelectorAll('.tabs button').forEach(x => x.classList.toggle('on', x === b));
  ['smart', 'plain', 'brief'].forEach(k => { $('tab-' + k).hidden = b.dataset.tab !== k; });
  $('intro').innerHTML = b.dataset.tab === 'brief' ? INTRO_BRIEF : INTRO;
});

// ---------------------------------------------------------------- tab 3: sample weekly brief (connected tier)
const B = {data: null};
const INTRO = `A coffee farmer in Kenya asks a question in her own words. A tiny AI <b>on her phone</b> works out what she
  means and shows advice written by coffee experts. <b>No internet needed.</b> When it isn't sure, it says so and passes the
  question to a person.<br><span class="scope">It does one job well: <b>what is hurting her coffee, what to do and when, and what
  her crop is worth before she sells.</b> Anything else, like general coffee facts, goes to the extension officer on purpose.</span>`;
const INTRO_BRIEF = `Besides answering questions, the same service can <b>reach farmers first</b>. These are sample weekly SMS
  briefs a cooperative could send: funding, where to meet other farmers, and the coffee market. They arrive on any phone, with
  no app or data needed.`;
function briefItems() {
  if (!B.data) return [];
  const today = new Date().toISOString().slice(0, 10);
  return Object.entries(B.data.topics).flatMap(([k, tp]) => tp.items
    .filter(it => !((k === 'meet' || k === 'funding') && it.date && it.date < today))     // stale events / deadlines out
    .map(it => ({topic: tp.label[S.lang === 'sw' ? 1 : 0], it})));
}
function renderBrief() {
  if (!B.data) return;
  $('briefMeta').innerHTML = `Examples of the short SMS a cooperative can send each week to farmers who signed up, on any
    phone: funding they can apply for, where to meet other farmers, and coffee market news. Drafted on ${esc(B.data.generated)}
    with a web search that must cite its source. <b>In real use, an extension officer checks and approves every item
    before it is sent.</b>`;
  const items = briefItems();
  $('review').innerHTML = items.map(x => `<div class="rv"><div class="tp">${esc(x.topic)}</div>
    <div class="tx">${esc(x.it['sms_' + S.lang] || x.it.sms_en)}</div>
    <div class="src">${esc(x.it.publisher || '')} · <a href="${esc(x.it.source_url)}" target="_blank" rel="noopener">source</a></div></div>`).join('');
  const head = S.lang === 'sw' ? 'Uliza Kahawa · ujumbe wa wiki' : 'Uliza Kahawa · weekly brief';
  $('briefPhone').innerHTML = `<div class="sms"><div class="ussd-box" style="padding:0 0 4px">${esc(head)}</div>
    ${items.map(x => `<div class="them">${esc(x.it['sms_' + S.lang] || x.it.sms_en)}</div>`).join('')}
    <div class="ussd-box" style="padding:4px 0 0;font-size:11px">${S.lang === 'sw' ? 'Jibu STOP kuacha.' : 'Reply STOP to stop.'}</div></div>`;
}

const CHIPS = [
  ['Coffee questions', [
    ['majani yana unga wa njano chini', 'Kiswahili: "yellow powder under the leaves"'],
    ['mbona mavuno yamepungua', 'Kiswahili: "why has my harvest dropped"'],
    ['nipige dawa lini', 'Kiswahili: "when should I spray"'],
    ['broker ananipea 60 bob per kg', 'Kenyan SMS slang: "a broker is offering me 60 shillings a kilo"'],
    ['small holes in my berries', 'English'],
  ]],
  ['A mixed question: it asks you to choose', [
    ['tell me about rust berries', 'English: could be leaf rust or berry disease, so it shows "Did you mean…" instead of guessing'],
  ]],
  ['A harder language', [
    ['Mathangũ ma kahawa marĩ na mũtu wa njano rungu', 'Kikuyu, the local language: "the coffee leaves have yellow dust underneath". The AI was not trained on Kikuyu, so it often says "not sure"'],
  ]],
  ['Not about coffee: it should say "not sure"', [
    ['bei ya maziwa', 'Kiswahili: "milk price"'],
    ['wadudu wa antestia', 'Kiswahili: "antestia bugs", a pest we have no checked advice for'],
  ]],
];
function chips() {
  $('chips').innerHTML = CHIPS.map(([g, list]) => `<div class="group"><div class="gk">${esc(g)}</div>${list.map(([q, gloss]) =>
    `<button data-q="${esc(q)}"><span>${esc(q)}</span><small>${esc(gloss)}</small></button>`).join('')}</div>`).join('');
  $('chips').querySelectorAll('[data-q]').forEach(b => b.onclick = () => {
    document.querySelector('[data-tab=smart]').click(); S.view = 'ask'; render(); ask(b.dataset.q);
  });
}

async function boot() {
  const [m, a] = await Promise.all([fetch('../models/model.json').then(r => r.json()), fetch('../answers/answers.built.json').then(r => r.json())]);
  S.model = SmallModel.load(m); S.answers = a;
  CH = Channels.make(S.model, S.answers, q => {
    S.log.push({id: Date.now(), ts: new Date().toISOString(), text: q, label: '', conf: 0, answered: false, status: 'waiting'});
    save(); renderQueue();
  });
  S.audio = await fetch('../answers/audio/index.json').then(r => r.json()).then(x => x.files).catch(() => ({}));
  const kb = Math.round(JSON.stringify(m).length / 1024);
  $('intro').innerHTML = INTRO;
  $('offline-proof').innerHTML = `Everything the AI needs (${kb} KB, smaller than one photo) is saved on the phone.
    <span id="swstate"></span> Tick "No signal", or turn your Wi-Fi off, and keep asking.`;
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').then(() => navigator.serviceWorker.ready)
      .then(() => { $('swstate').textContent = 'Saved for offline use.'; })
      .catch(() => { $('swstate').textContent = ''; });
  }
  B.data = await fetch('briefing.sample.json').then(r => r.json()).catch(() => null);
  setLang(S.lang); chips(); render(); renderQueue(); netBadge(); ussdStep('');
  // Demo hooks (video / screenshots): ?q=<question>  ?lang=en  ?offline=1  ?tab=plain&u=*384*2026#|1|<question>  ?slow=1  ?sms=<question>  ?voice=1|<digit>
  const p = new URLSearchParams(location.search);
  if (p.get('lang')) setLang(p.get('lang'));
  if (p.get('offline')) { $('simOff').checked = true; S.simOff = true; netBadge(); }
  if (p.get('q')) { S.view = 'ask'; render(); ask(p.get('q')); }
  if (p.get('tab')) document.querySelector(`[data-tab=${p.get('tab')}]`)?.click();
  if (p.get('slow')) $('slow2g').checked = true;
  if (p.get('u')) p.get('u').split('|').forEach((x, i) => setTimeout(() => ussdStep(x), i * ($('slow2g').checked ? 2800 : 700)));
  if (p.get('voice')) { $('ussdVoice').click(); if (p.get('voice') !== '1') voiceKey(p.get('voice')); }
  if (p.get('sms')) { $('ussdSms').click(); ussdStep(p.get('sms')); }
}
boot();
