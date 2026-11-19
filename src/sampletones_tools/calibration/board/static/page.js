const MESSAGES = {
  lead: (referee) => `Scored by ${referee}; lower is closer to the recording.`,
  heading: (title, run) => `${title}: ${run}`,
  sounds: (count) => (count === 1 ? "1 sound" : `${count} sounds`),
  sound: "sound",
  recording: "recording",
  change: "change",
  play: "play",
  solo: "S",
  mute: "M",
  silent: "—",
  pastSilence: "past silence",
  closed: (percent) => `${percent}% of the gap`,
  openAll: "Open all",
  closeAll: "Close all",
};

const player = new Audio();
let playing = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) { node.className = className; }
  if (text !== undefined) { node.textContent = text; }
  return node;
}

function clip(label, source, className) {
  const button = element("button", className, label);
  button.dataset.source = source;
  button.setAttribute("aria-pressed", "false");
  return button;
}

function breakable(name) {
  const node = element("b");
  name.split("-").forEach((piece, index, pieces) => {
    node.append(index < pieces.length - 1 ? `${piece}-` : piece);
    if (index < pieces.length - 1) { node.append(element("wbr")); }
  });
  node.title = name;
  return node;
}

function gradient(timeline, color) {
  const frames = timeline.length;
  if (!frames) { return "none"; }
  const stops = [];
  let start = 0;
  while (start < frames) {
    let end = start;
    while (end < frames && timeline[end] === timeline[start]) { end += 1; }
    const paint = timeline[start] === "1" ? `var(--${color})` : "transparent";
    stops.push(`${paint} ${(100 * start) / frames}% ${(100 * end) / frames}%`);
    start = end;
  }
  return `linear-gradient(90deg, ${stops.join(", ")})`;
}

function channelRow(channel, color) {
  const row = element("div", "channel");
  const swatch = element("span", "swatch");
  swatch.style.background = `var(--${color})`;
  swatch.title = channel.name;
  row.append(swatch);
  if (channel.solo) { row.append(clip(MESSAGES.solo, channel.solo, "button secondary compact clip part")); }
  if (channel.mute) { row.append(clip(MESSAGES.mute, channel.mute, "button secondary compact clip part")); }
  const bar = element("div", "bar");
  bar.style.backgroundImage = gradient(channel.timeline, color);
  bar.title = channel.name;
  row.append(bar);
  return row;
}

function closed(cell) {
  if (cell.silence <= 0) { return MESSAGES.silent; }
  if (cell.score >= cell.silence) { return MESSAGES.pastSilence; }
  return MESSAGES.closed(Math.round(100 * (1 - cell.score / cell.silence)));
}

function cellNode(cell, board) {
  const node = element("div", "cell");
  const render = clip(board.glyphs.play, cell.render, "button clip glyph-button");
  render.title = MESSAGES.play;
  render.setAttribute("aria-label", MESSAGES.play);
  node.append(render);
  const reading = element("div", "reading");
  reading.append(element("b", null, cell.score.toFixed(2)));
  reading.append(element("span", null, closed(cell)));
  node.append(reading);
  const channels = element("div", "channels");
  for (const channel of cell.channels) {
    channels.append(channelRow(channel, board.colors[channel.name]));
  }
  node.append(channels);
  return node;
}

function changeNode(row) {
  const node = element("td", "change");
  if (row.cells.length < 2) { return node; }
  const change = row.cells[row.cells.length - 1].score - row.cells[0].score;
  const shown = change.toFixed(2);
  if (Number(shown) !== 0) { node.classList.add(change < 0 ? "better" : "worse"); }
  node.textContent = `${change >= 0 ? "+" : ""}${shown}`;
  return node;
}

function rowNode(row, board) {
  const node = element("tr", "sound-row");
  const sound = element("td", "sound");
  sound.append(breakable(row.item));
  node.append(sound);
  const recording = element("td", "recording");
  recording.append(clip(MESSAGES.recording, row.recording, "button clip"));
  node.append(recording);
  for (const cell of row.cells) {
    const holder = element("td");
    holder.append(cellNode(cell, board));
    node.append(holder);
  }
  node.append(changeNode(row));
  return node;
}

function categoryNode(name, span) {
  const node = element("tr", "category");
  const heading = element("th", null, name);
  heading.colSpan = span;
  heading.scope = "colgroup";
  node.append(heading);
  return node;
}

function legendNode(rows, colors) {
  const sounding = new Set();
  for (const row of rows) {
    for (const cell of row.cells) {
      for (const channel of cell.channels) { sounding.add(channel.name); }
    }
  }
  const legend = element("span", "legend");
  for (const name of Object.keys(colors).filter((channel) => sounding.has(channel))) {
    const entry = element("span");
    const swatch = element("span", "swatch");
    swatch.style.background = `var(--${colors[name]})`;
    entry.append(swatch, element("span", null, name));
    legend.append(entry);
  }
  return legend;
}

function tableNode(columns, rows, board) {
  const table = element("table", "table sounds");
  table.style.setProperty("--columns", String(columns.length));
  const widths = element("colgroup");
  for (const className of ["sound", "recording", ...columns.map(() => "version"), "change"]) {
    widths.append(element("col", className));
  }
  table.append(widths);
  const head = element("tr");
  for (const heading of [MESSAGES.sound, MESSAGES.recording, ...columns, MESSAGES.change]) {
    const cell = element("th", null, heading);
    cell.scope = "col";
    head.append(cell);
  }
  const thead = element("thead");
  thead.append(head);
  table.append(thead);
  const body = element("tbody");
  let category = null;
  for (const row of rows) {
    if (row.category !== category) { body.append(categoryNode(row.category, columns.length + 3)); }
    category = row.category;
    body.append(rowNode(row, board));
  }
  table.append(body);
  return table;
}

function chevron(card, glyphs) {
  card.querySelector(".card-chevron").textContent = card.open ? glyphs.expanded : glyphs.collapsed;
}

function familyNode(family, rows, columns, board, open) {
  const card = element("details", "card family");
  card.open = open;
  const header = element("summary", "card-header");
  header.append(
    element("span", "card-glyph", board.glyphs.header),
    element("span", "card-title", family),
    element("span", "count", MESSAGES.sounds(rows.length)),
    legendNode(rows, board.colors),
    element("span", "card-chevron"),
  );
  card.append(header);
  const scroll = element("div", "table-scroll");
  scroll.append(tableNode(columns, rows, board));
  card.append(scroll);
  card.addEventListener("toggle", () => chevron(card, board.glyphs));
  chevron(card, board.glyphs);
  return card;
}

function families(rows) {
  const held = new Map();
  for (const row of rows) {
    if (!held.has(row.family)) { held.set(row.family, []); }
    held.get(row.family).push(row);
  }
  return held;
}

function groupNode(group, board) {
  const panel = element("section", "group");
  panel.dataset.group = group.name;
  let first = true;
  for (const [family, rows] of families(group.rows)) {
    panel.append(familyNode(family, rows, group.columns, board, first));
    first = false;
  }
  return panel;
}

function shownRows() {
  return Array.from(document.querySelectorAll("section.group:not([hidden]) details[open] tr.sound-row"));
}

function inRow(row) {
  return Array.from(row.querySelectorAll("button.clip"));
}

function mark(button) {
  for (const other of document.querySelectorAll('button.clip[aria-pressed="true"]')) {
    other.setAttribute("aria-pressed", "false");
  }
  for (const row of document.querySelectorAll("tr.playing")) {
    row.classList.remove("playing");
  }
  playing = button;
  if (button) {
    button.setAttribute("aria-pressed", "true");
    button.closest("tr").classList.add("playing");
  }
}

function play(button) {
  if (!button) { return; }
  player.pause();
  player.src = button.dataset.source;
  player.currentTime = 0;
  player.play().catch(() => mark(null));
  mark(button);
  button.closest("tr").scrollIntoView({ block: "nearest" });
}

function stepAcross(offset) {
  const all = shownRows();
  const row = playing ? inRow(playing.closest("tr")) : all.length ? inRow(all[0]) : [];
  if (!row.length) { return; }
  const place = playing ? row.indexOf(playing) : -1;
  play(row[(place + offset + row.length) % row.length]);
}

function stepDown(offset) {
  const all = shownRows();
  if (!all.length) { return; }
  const current = playing ? playing.closest("tr") : null;
  const index = all.indexOf(current);
  if (index < 0) { play(inRow(all[0])[0]); return; }
  const place = inRow(current).indexOf(playing);
  const next = inRow(all[(index + offset + all.length) % all.length]);
  play(next[Math.min(place, next.length - 1)]);
}

function openAll(open) {
  for (const card of document.querySelectorAll("section.group:not([hidden]) details.family")) {
    card.open = open;
  }
}

function toolbarNode() {
  const toolbar = element("div", "toolbar");
  const opening = element("button", "button secondary", MESSAGES.openAll);
  opening.addEventListener("click", () => openAll(true));
  const closing = element("button", "button secondary", MESSAGES.closeAll);
  closing.addEventListener("click", () => openAll(false));
  toolbar.append(opening, closing);
  return toolbar;
}

function selectGroup(name) {
  for (const tab of document.querySelectorAll("#tabs button")) {
    tab.setAttribute("aria-selected", String(tab.dataset.group === name));
  }
  for (const panel of document.querySelectorAll("section.group")) {
    panel.hidden = panel.dataset.group !== name;
  }
  player.pause();
  mark(null);
}

function tabsNode(groups) {
  const tabs = document.getElementById("tabs");
  tabs.hidden = false;
  for (const group of groups) {
    const tab = element("button", "tab", group.name);
    tab.setAttribute("role", "tab");
    tab.dataset.group = group.name;
    tab.addEventListener("click", () => selectGroup(group.name));
    tabs.append(tab);
  }
}

function build(board) {
  const title = board.groups.length === 1 ? MESSAGES.heading(board.title, board.groups[0].name) : board.title;
  document.title = title;
  document.getElementById("title").textContent = title;
  document.getElementById("lead").textContent = MESSAGES.lead(board.referee);
  document.querySelector(".masthead").append(toolbarNode());
  const groups = document.getElementById("groups");
  for (const group of board.groups) {
    groups.append(groupNode(group, board));
  }
  if (board.groups.length > 1) {
    tabsNode(board.groups);
    selectGroup(board.groups[0].name);
  }
}

player.addEventListener("ended", () => mark(null));

document.addEventListener("click", (event) => {
  const button = event.target.closest("button.clip");
  if (button) { play(button); }
});

document.addEventListener("keydown", (event) => {
  if (event.key === " ") {
    event.preventDefault();
    if (!playing) { stepDown(0); return; }
    if (player.paused) { player.play().catch(() => mark(null)); } else { player.pause(); }
    return;
  }
  if (event.key === "ArrowRight") { event.preventDefault(); stepAcross(1); }
  if (event.key === "ArrowLeft") { event.preventDefault(); stepAcross(-1); }
  if (event.key === "ArrowDown") { event.preventDefault(); stepDown(1); }
  if (event.key === "ArrowUp") { event.preventDefault(); stepDown(-1); }
});

build(BOARD);
