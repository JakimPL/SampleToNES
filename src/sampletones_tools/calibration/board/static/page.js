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
  if (channel.solo) { row.append(clip("S", channel.solo, "clip part")); }
  if (channel.mute) { row.append(clip("M", channel.mute, "clip part")); }
  const bar = element("div", "bar");
  bar.style.backgroundImage = gradient(channel.timeline, color);
  bar.title = channel.name;
  row.append(bar);
  return row;
}

function closed(cell) {
  if (cell.silence <= 0) { return "—"; }
  if (cell.score >= cell.silence) { return "past silence"; }
  return `${Math.round(100 * (1 - cell.score / cell.silence))}% of the gap`;
}

function cellNode(cell, colors) {
  const node = element("div", "cell");
  node.append(clip("play", cell.render, "clip"));
  const reading = element("div", "reading");
  reading.append(element("b", null, cell.score.toFixed(2)));
  reading.append(element("span", null, closed(cell)));
  node.append(reading);
  const channels = element("div", "channels");
  for (const channel of cell.channels) {
    channels.append(channelRow(channel, colors[channel.name]));
  }
  node.append(channels);
  return node;
}

function rowNode(row, colors) {
  const node = element("tr");
  const sound = element("td", "sound");
  sound.append(element("b", null, row.item));
  sound.append(element("span", null, row.category));
  node.append(sound);
  const recording = element("td");
  recording.append(clip("recording", row.recording, "clip"));
  node.append(recording);
  for (const cell of row.cells) {
    const holder = element("td");
    holder.append(cellNode(cell, colors));
    node.append(holder);
  }
  node.append(changeNode(row));
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

function legendNode(group, colors) {
  const sounding = new Set();
  for (const row of group.rows) {
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

function groupNode(group, colors) {
  const card = element("section", "card");
  card.dataset.group = group.name;
  const heading = element("h2");
  heading.append(element("span", null, group.name), legendNode(group, colors));
  card.append(heading);
  const scroll = element("div", "scroll");
  const table = element("table");
  const head = element("tr");
  for (const heading of ["sound", "recording", ...group.columns, "change"]) {
    head.append(element("th", null, heading));
  }
  const thead = element("thead");
  thead.append(head);
  table.append(thead);
  const body = element("tbody");
  for (const row of group.rows) {
    body.append(rowNode(row, colors));
  }
  table.append(body);
  scroll.append(table);
  card.append(scroll);
  return card;
}

function buttons() {
  return Array.from(document.querySelectorAll("section.card:not([hidden]) button.clip"));
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
}

function rows() {
  return Array.from(document.querySelectorAll("section.card:not([hidden]) tbody tr"));
}

function inRow(row) {
  return Array.from(row.querySelectorAll("button.clip"));
}

function stepAcross(offset) {
  const row = playing ? inRow(playing.closest("tr")) : buttons();
  if (!row.length) { return; }
  const place = playing ? row.indexOf(playing) : -1;
  play(row[(place + offset + row.length) % row.length]);
}

function stepDown(offset) {
  const all = rows();
  if (!all.length) { return; }
  if (!playing) { play(inRow(all[0])[0]); return; }
  const current = playing.closest("tr");
  const place = inRow(current).indexOf(playing);
  const next = inRow(all[(all.indexOf(current) + offset + all.length) % all.length]);
  play(next[Math.min(place, next.length - 1)]);
}

function selectGroup(name) {
  for (const tab of document.querySelectorAll("#tabs button")) {
    tab.setAttribute("aria-selected", String(tab.dataset.group === name));
  }
  for (const card of document.querySelectorAll("section.card")) {
    card.hidden = card.dataset.group !== name;
  }
  player.pause();
  mark(null);
}

function build(board) {
  document.title = board.title;
  document.getElementById("title").textContent = board.title;
  document.getElementById("lead").textContent =
    `Scored by ${board.referee}; lower is closer to the recording.`;
  const groups = document.getElementById("groups");
  for (const group of board.groups) {
    groups.append(groupNode(group, board.colors));
  }
  if (board.groups.length > 1) {
    const tabs = document.getElementById("tabs");
    tabs.hidden = false;
    for (const group of board.groups) {
      const tab = element("button", null, group.name);
      tab.dataset.group = group.name;
      tab.addEventListener("click", () => selectGroup(group.name));
      tabs.append(tab);
    }
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
