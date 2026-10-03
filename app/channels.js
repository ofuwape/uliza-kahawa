// Shared decision + basic-phone channel logic, used by the demo page (app/app.js) and the server (ussd/server.js), so
// the page shows exactly what a real phone would get.
//
// decide(): answer when the model is sure; when it is unsure between coffee topics, ASK the farmer ("did you mean
// 1 Leaf rust 2 Coffee berry disease, 0 talk to a person"): she chooses, the tool never guesses. Anything else, or a
// "0", goes to a person.
//
// USSD uses the common gateway convention: the gateway sends the whole path typed so far joined by '*' ("" -> menu,
// "1" -> prompt, "1*<question>" or just "<question>" typed at the menu (free entry) -> answer or "did you mean",
// "...*2" -> the chosen answer) and the reply
// starts with "CON " (keep the session open) or "END " (close it).
(function (root) {
  const MENU = {sw: 'Uliza Kahawa\nAndika swali lako, au:\n1 Uliza swali\n2 Bei ya kahawa\n3 Ongea na mtu\n9 English',
                en: 'Uliza Kahawa\nType your question, or:\n1 Ask a question\n2 Coffee price\n3 Talk to a person\n9 Kiswahili'};
  const PROMPT = {sw: 'Andika swali lako:', en: 'Type your question:'};
  const DIDYOU = {sw: 'Ulimaanisha:', en: 'Did you mean:'};
  const PERSON = {sw: 'Ongea na mtu', en: 'Talk to a person'};
  // Plain topic names (phone screens + the page).
  const LABELS = {
    leaf_rust: ['Kutu ya majani', 'Leaf rust'], cbd: ['Ugonjwa wa matunda', 'Coffee berry disease'],
    berry_borer: ['Mdudu wa matunda', 'Berry borer (insect)'], spray_timing: ['Wakati wa kunyunyiza', 'When to spray'],
    yield_drop: ['Mavuno kupungua', 'Why the harvest dropped'], fertilizer_weeds: ['Mbolea na magugu', 'Fertilizer and weeds'],
    pruning: ['Kupogoa', 'Pruning'], harvest: ['Kuchuma', 'Picking'], quality: ['Ubora', 'Quality and sorting'],
    price: ['Bei', 'Price'], varieties: ['Aina za kahawa', 'Disease-resistant varieties'],
    ask_person: ['Ongea na mtu', 'Talk to a person'], none: ['Si kuhusu kahawa', 'Not a coffee question'],
  };
  const label = (id, lang) => (LABELS[id] || [id, id])[lang === 'sw' ? 0 : 1];
  const CLARIFY_MIN = 0.3, OPTION_MIN = 0.15;      // ask "did you mean" only when a coffee topic is a real candidate

  function make(model, A, onPerson) {
    const intent = id => A.intents.find(i => i.id === id) || A.fallback;
    const person = q => { if (onPerson) onPerson(q); };
    const pending = new Map();                      // SMS "did you mean" waiting for a digit, in memory only, by sender

    // -> {r, it, toPerson, options}: options = topics to offer when unsure (null if answered or off-topic)
    function decide(text, {queue = true} = {}) {
      const r = model.predict(text);
      let options = null;
      if (!r.answered && r.label !== model.none) {
        const c = r.top.filter(x => x.label !== model.none && x.label !== 'ask_person' && x.p >= OPTION_MIN
                                && x.p >= r.top[0].p / 3);                 // only real candidates, not long shots
        if (c.length && c[0].p >= CLARIFY_MIN) options = c.slice(0, 3).map(x => x.label);
      }
      const it = r.answered ? intent(r.label) : A.fallback;
      const toPerson = !options && (!r.answered || !!it.ask_person);
      if (toPerson && queue) person(text);
      return {r, it, toPerson, options};
    }
    const menuOf = (opts, lang) => DIDYOU[lang] + '\n' + opts.map((id, i) => `${i + 1} ${label(id, lang)}`).join('\n') + `\n0 ${PERSON[lang]}`;
    // A digit answering a "did you mean": the chosen topic's answer, or 0 = a person.
    function choose(q, opts, digit) {
      if (digit === '0') { person(q); return intent('ask_person'); }
      const id = opts[+digit - 1];
      return id ? intent(id) : null;
    }

    return {
      decide, label, menuOf,
      choose: (q, opts, digit) => choose(q, opts, digit),
      // -> {reply: "CON ..." | "END ...", decision?}. Each leading "9" switches the language.
      ussd(text) {
        let parts = text ? String(text).split('*') : [];
        let lang = 'sw';
        while (parts[0] === '9') { lang = lang === 'sw' ? 'en' : 'sw'; parts = parts.slice(1); }
        if (!parts.length) return {reply: 'CON ' + MENU[lang]};
        // Free entry: anything typed at the menu that is not a menu number is the question itself.
        if (!/^[123]$/.test(parts[0])) parts = ['1', ...parts];
        const [c, ...rest] = parts;
        if (c === '1' && !rest.length) return {reply: 'CON ' + PROMPT[lang]};
        if (c === '1') {
          if (rest.length >= 2 && /^[0-3]$/.test(rest[rest.length - 1])) {       // answering a "did you mean"
            const q = rest.slice(0, -1).join('*');
            const d = decide(q, {queue: false});
            const it = d.options && choose(q, d.options, rest[rest.length - 1]);
            if (it) return {reply: 'END ' + it.sms[lang].slice(0, 182), decision: d};
          }
          const q = rest.join('*');
          const d = decide(q);
          if (d.options) return {reply: 'CON ' + menuOf(d.options, lang), decision: d};
          return {reply: 'END ' + d.it.sms[lang].slice(0, 182), decision: d};
        }
        if (c === '2') return {reply: 'END ' + intent('price').sms[lang]};
        if (c === '3') { person('(asked for a person)'); return {reply: 'END ' + intent('ask_person').sms[lang]}; }
        return {reply: 'CON ' + MENU[lang]};
      },
      // One message in, one reply out. A leading "EN " / "SW " picks the language. A lone digit answers the last
      // "did you mean" from the same sender (kept in memory for 10 minutes, never stored).
      sms(text, defaultLang, sender = '') {
        let lang = defaultLang || 'sw', q = String(text || '').trim();
        const m = q.match(/^(en|sw)\s+/i);
        if (m) { lang = m[1].toLowerCase(); q = q.slice(m[0].length); }
        const p = pending.get(sender);
        if (p && /^[0-3]$/.test(q) && Date.now() - p.at < 600000) {
          pending.delete(sender);
          const it = choose(p.q, p.options, q);
          if (it) return {reply: it.sms[p.lang], decision: p.d};
        }
        const d = decide(q);
        if (d.options) {
          pending.set(sender, {q, options: d.options, lang, d, at: Date.now()});
          return {reply: menuOf(d.options, lang) + (lang === 'sw' ? '\nJibu kwa namba.' : '\nReply with the number.'), decision: d};
        }
        return {reply: d.it.sms[lang], decision: d};
      },
    };
  }

  const api = {make, label, LIMIT_MS: 10000};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Channels = api;
})(this);
