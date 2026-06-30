// Dev tool: render a standalone HTML preview of the play screen using the real
// @yao/core renderer + the real web styles. Open the output in any browser/phone.
//   npx tsx scripts/gen-preview.ts

import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import {
  createPet,
  deriveGenome,
  renderPetSvg,
  advance,
  stageLabel,
  type Pet,
  type Stage,
} from '@yao/core';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const css = fs.readFileSync(path.join(ROOT, 'packages/web/src/styles.css'), 'utf8');

// Grow a pet to a target stage by fast-forwarding simulated time.
function petAtStage(seed: string, target: Stage): Pet {
  let pet = createPet({ id: seed, seed, name: 'preview', now: 0 });
  const stepDays = 0.25;
  for (let d = 0; d < 60 && pet.stage !== target; d += stepDays) {
    pet = advance(pet, d * 86_400_000).pet;
  }
  return pet;
}

const STAGES: Stage[] = ['egg', 'kong', 'wo', 'zhi', 'xi', 'shou', 'xing', 'yuan'];

const hero = petAtStage('aurora-spirit-77', 'xing');
const heroGenome = deriveGenome(hero.seed);
// Cheerful stats so the hero shows its happy face in the preview.
const heroStats = { ...hero.stats, mood: 82, energy: 70 };
const heroSvg = renderPetSvg(heroGenome, hero.stage, { idSuffix: 'hero', stats: heroStats, size: 360 });

const sampleWhispers = [
  { text: '空非無也，本然自現。', source: 'llm' }, // 衙墨·書
  { text: '正看著它的，是誰？', source: 'llm' }, // 寂照·勘
  { text: '週一早晨也是道場，雖然我也不太想承認。', source: 'template' }, // 映塵·讀
];

const STAT_LABELS: [keyof Pet['stats'], string][] = [
  ['vitality', '生命'],
  ['mood', '心情'],
  ['energy', '靈力'],
  ['growth', '成長'],
  ['hunger', '饑餓'],
];

const statsHtml = STAT_LABELS.map(
  ([k, label]) =>
    `<div class="stat"><label>${label}</label><div class="bar"><i style="width:${Math.round(hero.stats[k])}%"></i></div></div>`,
).join('');

const whispersHtml = sampleWhispers
  .map((w) => `<div class="whisper ${w.source === 'template' ? 'template' : ''}">「${w.text}」</div>`)
  .join('');

// Evolution filmstrip — eight unique creatures, one per volume (卵→空→…→圓).
const strip = STAGES.map((st, i) => {
  const seed = `evo-${i}-${st}`;
  const g = deriveGenome(seed);
  const svg = renderPetSvg(g, st, {
    idSuffix: `s${i}`,
    size: 150,
    stats: { hunger: 10, mood: 78, energy: 70, vitality: 90, growth: 60 },
  });
  return `<figure class="cell"><div class="thumb">${svg}</div><figcaption>${stageLabel(st)}</figcaption></figure>`;
}).join('');

const html = `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>空靈次元 · 預覽</title>
<style>${css}
  body { padding: 0; }
  .preview-wrap { max-width: 560px; margin: 0 auto; padding: 24px 14px 60px; }
  .filmstrip { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 28px; }
  .cell { margin: 0; text-align: center; }
  .cell .thumb { border: 1px solid var(--line); border-radius: 16px; background: var(--glass); padding: 6px; }
  .cell svg { width: 100%; height: auto; }
  .cell figcaption { color: var(--dim); font-size: 0.72rem; letter-spacing: 2px; text-transform: uppercase; margin-top: 6px; }
  h2.section { color: var(--dim); font-weight: 500; letter-spacing: 3px; font-size: 0.8rem; text-transform: uppercase; margin: 30px 0 4px; }
</style></head>
<body>
  <div class="preview-wrap">
    <header class="header">
      <div class="name">星澪 <span>· ${Math.floor(hero.bornAt === 0 ? 120 : 0)}h</span></div>
      <div class="stage">${stageLabel(hero.stage)}</div>
    </header>
    <div class="stage-wrap">${heroSvg}</div>
    <div class="panel">
      <div class="stats">${statsHtml}</div>
      <div class="whispers">${whispersHtml}</div>
    </div>
    <div class="actions">
      <button class="act"><span class="ico">✦</span>餵養</button>
      <button class="act"><span class="ico">❀</span>安撫</button>
      <button class="act"><span class="ico">◌</span>凝視</button>
      <button class="act"><span class="ico">✎</span>命名</button>
    </div>
    <h2 class="section">卵 · 七卷成長（空我知戲手行圓，每隻基因獨一無二）</h2>
    <div class="filmstrip">${strip}</div>
  </div>
</body></html>`;

const outDir = path.join(ROOT, 'previews');
fs.mkdirSync(outDir, { recursive: true });
const outPath = path.join(outDir, 'play-screen.html');
fs.writeFileSync(outPath, html);
console.log('wrote', outPath);
