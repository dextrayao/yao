export const FILTERS = [
  { id: "none",    name: "原圖",  css: "none" },
  { id: "mono",    name: "黑白",  css: "grayscale(1) contrast(1.05)" },
  { id: "vintage", name: "復古",  css: "sepia(0.7) contrast(1.05) saturate(1.1)" },
  { id: "vivid",   name: "鮮豔",  css: "saturate(1.6) contrast(1.1)" },
  { id: "cool",    name: "冷色",  css: "saturate(1.2) hue-rotate(-15deg) contrast(1.05)" },
  { id: "warm",    name: "暖色",  css: "saturate(1.2) hue-rotate(15deg) contrast(1.05)" },
  { id: "dreamy",  name: "夢幻",  css: "blur(1px) saturate(1.3) brightness(1.05)" },
  { id: "noir",    name: "暗調",  css: "grayscale(1) contrast(1.4) brightness(0.85)" },
];

let activeFilter = FILTERS[0];

export function getActiveFilter() {
  return activeFilter;
}

export function setActiveFilter(id) {
  activeFilter = FILTERS.find((f) => f.id === id) || FILTERS[0];
  return activeFilter;
}

export function renderFilterChips(containerEl, videoEl, onChange) {
  containerEl.innerHTML = "";
  FILTERS.forEach((f) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (f.id === activeFilter.id ? " active" : "");
    chip.dataset.id = f.id;
    chip.textContent = f.name;
    chip.setAttribute("role", "radio");
    chip.setAttribute("aria-checked", f.id === activeFilter.id);
    chip.onclick = () => {
      setActiveFilter(f.id);
      videoEl.style.filter = f.css;
      containerEl.querySelectorAll(".chip").forEach((c) => {
        const active = c.dataset.id === f.id;
        c.classList.toggle("active", active);
        c.setAttribute("aria-checked", active);
      });
      if (onChange) onChange(f);
    };
    containerEl.appendChild(chip);
  });
}
