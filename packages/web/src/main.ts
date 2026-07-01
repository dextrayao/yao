import './styles.css';
import { deriveGenome, expressionFor, renderPetSvg, stageLabel, type Pet } from '@yao/core';
import { api, AuthError, getToken, setToken, type PetView } from './net/api.js';

const app = document.getElementById('app')!;
let current: Pet | null = null;
let es: EventSource | null = null;
// Re-render the creature only when its appearance key (stage + expression)
// changes, so live stat updates don't restart the CSS animations.
let renderedAppearance: string | null = null;

const appearanceKey = (pet: Pet): string =>
  `${pet.stage}|${expressionFor(pet.stage, pet.stats)}`;

const esc = (s: string): string =>
  s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

// --- screens ---------------------------------------------------------------

function showCenter(html: string): void {
  closeStream();
  app.innerHTML = `<div class="center-screen">${html}</div>`;
}

function showLoading(): void {
  showCenter(`<div class="spinner">· · ·</div><p>進入次元…</p>`);
}

function showError(msg: string): void {
  showCenter(`<h1>···</h1><p>連線異常：${esc(msg)}</p>
    <button class="btn-primary" id="retry">重試</button>`);
  app.querySelector('#retry')?.addEventListener('click', boot);
}

function showAuth(): void {
  showCenter(`<h1>空靈次元</h1>
    <p>輸入通行符記以連回你的 Mac Studio 次元。</p>
    <input id="tok" type="password" inputmode="text" autocomplete="off" placeholder="access token" value="${esc(getToken())}" />
    <button class="btn-primary" id="enter">連線</button>`);
  const input = app.querySelector<HTMLInputElement>('#tok')!;
  app.querySelector('#enter')?.addEventListener('click', () => {
    setToken(input.value.trim());
    boot();
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      setToken(input.value.trim());
      boot();
    }
  });
}

function showSummon(): void {
  showCenter(`<h1>空靈次元</h1>
    <p>此次元尚無生靈。召喚一隻，它將在此自行成長、永恆運作。</p>
    <button class="btn-primary" id="summon">召喚生靈</button>`);
  app.querySelector('#summon')?.addEventListener('click', async () => {
    showLoading();
    try {
      const view = await api.createPet({});
      await openPet(view.pet.id);
    } catch (e) {
      handleError(e);
    }
  });
}

function showPlay(view: PetView): void {
  current = view.pet;
  app.innerHTML = `
    <header class="header">
      <div class="name" id="name"></div>
      <div class="head-right">
        <button class="howto-btn" id="howto" aria-label="玩法">玩法</button>
        <div class="stage" id="stage"></div>
      </div>
    </header>
    <div class="stage-wrap" id="stagewrap"></div>
    <div class="panel">
      <div class="stats" id="stats"></div>
      <div class="tabs">
        <button class="tab on" data-tab="whispers">低語</button>
        <button class="tab" data-tab="footprints">足跡</button>
      </div>
      <div class="whispers" id="whispers"></div>
      <div class="footprints" id="footprints" hidden></div>
    </div>
    <div class="actions">
      <button class="act" data-act="feed"><span class="ico">✦</span>餵養</button>
      <button class="act" data-act="soothe"><span class="ico">❀</span>安撫</button>
      <button class="act" data-act="observe"><span class="ico">◌</span>凝視</button>
      <button class="act" data-act="rename"><span class="ico">✎</span>命名</button>
    </div>`;

  app.querySelectorAll<HTMLButtonElement>('button.act').forEach((b) =>
    b.addEventListener('click', () => onAction(b.dataset['act']!)),
  );
  app.querySelectorAll<HTMLButtonElement>('button.tab').forEach((b) =>
    b.addEventListener('click', () => switchTab(b.dataset['tab']!)),
  );
  app.querySelector('#howto')?.addEventListener('click', () => showHowTo());

  renderedAppearance = null;
  updateHeader(view.pet);
  updateStage(view.pet);
  updateStats(view.pet);
  renderWhispers(view.whispers ?? []);
  renderFootprints(view.pet);
  openStream(view.pet.id);

  if (!localStorage.getItem(HOWTO_KEY)) showHowTo(); // first-run onboarding
}

// 玩法教學 — 去聖語氣：它是一面鏡，不是一場輸贏。
const HOWTO_KEY = 'yao_howto_seen';

function showHowTo(): void {
  const prev = document.querySelector('.howto');
  if (prev) prev.remove();
  const el = document.createElement('div');
  el.className = 'howto';
  el.innerHTML = `
    <div class="howto-card">
      <h2>空靈次元 · 玩法</h2>
      <p class="lead">它是一面鏡，不是一場輸贏。</p>
      <p>你將陪一隻獨一無二的生靈，從「卵」自己長到「圓」（約 12 天）。<br>
         你不在，它也在長；你回來，讓它更好。</p>
      <ul class="howto-list">
        <li><b>✦ 餵養</b>　它餓了，餵它</li>
        <li><b>❀ 安撫</b>　讓它安定、生出靈力</li>
        <li><b>◌ 凝視</b>　靜靜看它，它會低語</li>
        <li><b>✎ 命名</b>　給它一個名</li>
      </ul>
      <p class="dimlead">心情好、不太餓時，它長得更快。<br>每一次蛻變都留在「足跡」裡，永不抹去。</p>
      <button class="btn-primary" id="howto-close">開始陪伴</button>
    </div>`;
  document.body.appendChild(el);
  const close = (): void => {
    localStorage.setItem(HOWTO_KEY, '1');
    el.remove();
  };
  el.querySelector('#howto-close')?.addEventListener('click', close);
  el.addEventListener('click', (e) => {
    if (e.target === el) close(); // tap backdrop to dismiss
  });
}

function switchTab(tab: string): void {
  app.querySelectorAll<HTMLButtonElement>('button.tab').forEach((b) =>
    b.classList.toggle('on', b.dataset['tab'] === tab),
  );
  const w = app.querySelector('#whispers');
  const fp = app.querySelector('#footprints');
  if (w) (w as HTMLElement).hidden = tab !== 'whispers';
  if (fp) (fp as HTMLElement).hidden = tab !== 'footprints';
}

// --- partial updates -------------------------------------------------------

function updateHeader(pet: Pet): void {
  const ageH = Math.floor((Date.now() - pet.bornAt) / 3_600_000);
  const name = app.querySelector('#name');
  const stage = app.querySelector('#stage');
  if (name) name.innerHTML = `${esc(pet.name)} <span>· ${ageH}h</span>`;
  if (stage) stage.textContent = stageLabel(pet.stage);
}

let lastStage: string | null = null;

function updateStage(pet: Pet): void {
  const key = appearanceKey(pet);
  if (key === renderedAppearance) return; // avoid resetting CSS animations
  renderedAppearance = key;
  const wrap = app.querySelector('#stagewrap');
  if (wrap)
    wrap.innerHTML = renderPetSvg(deriveGenome(pet.seed), pet.stage, {
      idSuffix: pet.id.slice(0, 8),
      stats: pet.stats,
    });
  // Evolution transition flash when the volume changes (not on first render).
  if (lastStage !== null && lastStage !== pet.stage) reactAnim('evolving', 1100);
  lastStage = pet.stage;
}

// Brief reaction animation on the creature stage. Adds a class the CSS animates,
// then removes it so it can retrigger. Respects prefers-reduced-motion via CSS.
function reactAnim(cls: string, durMs = 650): void {
  const wrap = app.querySelector('#stagewrap');
  if (!wrap) return;
  wrap.classList.remove(cls);
  void (wrap as HTMLElement).offsetWidth; // reflow so re-adding restarts it
  wrap.classList.add(cls);
  window.setTimeout(() => wrap.classList.remove(cls), durMs);
}

const REACT_BY_ACTION: Record<string, string> = {
  feed: 'react-feed',
  soothe: 'react-soothe',
  observe: 'react-observe',
};

// 異文錄·足跡 — every evolution leaves a footprint; they are never erased.
function renderFootprints(pet: Pet): void {
  const el = app.querySelector('#footprints');
  if (!el) return;
  const log = pet.mutationLog;
  const born = `<div class="footprint"><span class="fp-mark">✶</span>降生為「${stageLabel('egg')}」</div>`;
  const steps = log
    .map((m) => {
      const h = Math.floor((m.at - pet.bornAt) / 3_600_000);
      return `<div class="footprint"><span class="fp-mark">○</span>${stageLabel(m.from)} → ${stageLabel(m.to)} <span class="fp-age">· ${h}h</span></div>`;
    })
    .join('');
  el.innerHTML = born + steps;
}

const STAT_LABELS: [keyof Pet['stats'], string][] = [
  ['vitality', '生命'],
  ['mood', '心情'],
  ['energy', '靈力'],
  ['growth', '成長'],
  ['hunger', '饑餓'],
];

function updateStats(pet: Pet): void {
  const el = app.querySelector('#stats');
  if (!el) return;
  el.innerHTML = STAT_LABELS.map(
    ([k, label]) =>
      `<div class="stat"><label>${label}</label><div class="bar"><i style="width:${Math.round(pet.stats[k])}%"></i></div></div>`,
  ).join('');
}

function renderWhispers(list: { text: string; source: string }[]): void {
  const el = app.querySelector('#whispers');
  if (!el) return;
  if (list.length === 0) {
    el.innerHTML = `<div class="whisper-empty">…它尚未低語。</div>`;
    return;
  }
  el.innerHTML = list
    .map((w) => `<div class="whisper ${w.source === 'template' ? 'template' : ''}">「${esc(w.text)}」</div>`)
    .join('');
}

function prependWhisper(text: string, source: string): void {
  const el = app.querySelector('#whispers');
  if (!el) return;
  const empty = el.querySelector('.whisper-empty');
  if (empty) empty.remove();
  const node = document.createElement('div');
  node.className = `whisper ${source === 'template' ? 'template' : ''}`;
  node.textContent = `「${text}」`;
  el.prepend(node);
}

// --- actions ---------------------------------------------------------------

async function onAction(action: string): Promise<void> {
  if (!current) return;
  try {
    if (action === 'rename') {
      const name = prompt('為它命名：', current.name)?.trim();
      if (!name) return;
      const view = await api.interact(current.id, 'rename', name);
      applyView(view);
      return;
    }
    const react = REACT_BY_ACTION[action];
    if (react) reactAnim(react);
    const view = await api.interact(current.id, action);
    applyView(view);
  } catch (e) {
    handleError(e);
  }
}

function applyView(view: PetView): void {
  current = view.pet;
  updateHeader(view.pet);
  updateStage(view.pet);
  updateStats(view.pet);
  renderFootprints(view.pet);
  if (view.whispers) renderWhispers(view.whispers);
}

// --- SSE -------------------------------------------------------------------

function openStream(id: string): void {
  closeStream();
  es = new EventSource(api.streamUrl(id));
  es.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.kind === 'state' && msg.pet) {
        current = msg.pet as Pet;
        updateHeader(current);
        updateStage(current);
        updateStats(current);
        renderFootprints(current);
      } else if (msg.kind === 'whisper') {
        prependWhisper(msg.text, msg.source);
      }
    } catch {
      /* ignore malformed frames */
    }
  };
  // EventSource auto-reconnects on error; nothing to do.
}

function closeStream(): void {
  es?.close();
  es = null;
}

// --- boot ------------------------------------------------------------------

async function openPet(id: string): Promise<void> {
  const view = await api.getPet(id);
  showPlay(view);
}

function handleError(e: unknown): void {
  if (e instanceof AuthError) return showAuth();
  showError(e instanceof Error ? e.message : String(e));
}

async function boot(): Promise<void> {
  showLoading();
  try {
    const pets = await api.listPets();
    if (pets.length === 0) return showSummon();
    await openPet(pets[0]!.pet.id);
  } catch (e) {
    handleError(e);
  }
}

// Pause SVG animations when backgrounded to save battery; backend keeps ticking.
document.addEventListener('visibilitychange', () => {
  document.body.classList.toggle('hidden-anim', document.hidden);
});

void boot();
