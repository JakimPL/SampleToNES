const MESSAGES = {
  lead: (referee) => `Scored by ${referee}; higher is closer to the recording, and zero is exact.`,
  heading: (title, run) => `${title}: ${run}`,
  sounds: (count) => (count === 1 ? "1 sound" : `${count} sounds`),
  sound: "sound",
  recording: "recording",
  change: "change",
  play: "play",
  solo: "S",
  mute: "M",
  silent: "—",
  exact: "exact",
  closed: (nats) => `${nats} nats`,
  openAll: "Open all",
  closeAll: "Close all",
};

const SOUNDING_FRAME = "1";
const NAME_BREAK = "-";
const SHOWN_DIGITS = 2;
const BEFORE_FIRST = -1;
const CHANGE_COLUMNS = 2;
const INTERRUPTED = "AbortError";

const player = new Audio();
let playing = null;

/** An element of `tag`, with `className` and `text` where they are given. */
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) { node.className = className; }
  if (text !== undefined) { node.textContent = text; }
  return node;
}

/**
 * A button playing the clip at `source`, unpressed until it plays. Every such button carries the
 * class `clip`, which the page's one click handler and its keys find it by.
 */
function clip(label, source, className) {
  const button = element("button", className, label);
  button.dataset.source = source;
  button.setAttribute("aria-pressed", "false");
  return button;
}

/** A compact button playing a part of a render: one channel alone, or every other channel. */
function partNode(label, source) {
  return clip(label, source, "button secondary compact clip part");
}

/** The color a palette role holds, which the layout's stylesheet declares as a variable. */
function roleColor(role) {
  return `var(--${role})`;
}

/** A swatch of a channel's color. */
function swatchNode(role) {
  const swatch = element("span", "swatch");
  swatch.style.background = roleColor(role);
  return swatch;
}

/**
 * A sound's name, breakable after each hyphen, so a long name wraps at its parts and the sound
 * column keeps its width. The whole name stays in the tooltip.
 */
function breakable(name) {
  const node = element("b");
  const pieces = name.split(NAME_BREAK);
  pieces.forEach((piece, index) => {
    const last = index === pieces.length - 1;
    node.append(last ? piece : `${piece}${NAME_BREAK}`);
    if (!last) { node.append(element("wbr")); }
  });
  node.title = name;
  return node;
}

/** A timeline's stretches of equal frames, each from its first frame up to the next stretch's first. */
function stretches(timeline) {
  const found = [];
  let start = 0;
  while (start < timeline.length) {
    let end = start;
    while (end < timeline.length && timeline[end] === timeline[start]) { end += 1; }
    found.push({ start, end, sounding: timeline[start] === SOUNDING_FRAME });
    start = end;
  }
  return found;
}

/** Where `frame` falls along `frames`, in percent. */
function percent(frame, frames) {
  return (100 * frame) / frames;
}

/**
 * A channel's bar as a gradient of hard stops, one stretch of the channel's color per stretch of
 * frames it sounds, so a bar of any length draws as one background.
 */
function gradient(timeline, role) {
  const frames = timeline.length;
  if (!frames) { return "none"; }
  const stops = stretches(timeline).map(({ start, end, sounding }) => {
    const paint = sounding ? roleColor(role) : "transparent";
    return `${paint} ${percent(start, frames)}% ${percent(end, frames)}%`;
  });
  return `linear-gradient(90deg, ${stops.join(", ")})`;
}

/**
 * One channel of a cell: its swatch, its solo and mute clips where the render holds other
 * channels too, and the bar of the frames it sounds.
 */
function channelRow(channel, role) {
  const row = element("div", "channel");
  const swatch = swatchNode(role);
  swatch.title = channel.name;
  row.append(swatch);
  if (channel.solo) { row.append(partNode(MESSAGES.solo, channel.solo)); }
  if (channel.mute) { row.append(partNode(MESSAGES.mute, channel.mute)); }
  const bar = element("div", "bar");
  bar.style.backgroundImage = gradient(channel.timeline, role);
  bar.title = channel.name;
  row.append(bar);
  return row;
}

/**
 * A value to two decimals, a value rounding to zero shown as plain zero, so no sign stands on a
 * zero.
 */
function rounded(value) {
  const shown = value.toFixed(SHOWN_DIGITS);
  return Number(shown) === 0 ? (0).toFixed(SHOWN_DIGITS) : shown;
}

/**
 * A cell's score with its sign turned. A referee scores a distance, so the turned score rises as a
 * render comes closer to its recording and reaches zero where it is exact.
 */
function closeness(cell) {
  return -cell.score;
}

/**
 * How far a render stands from silence toward its recording, in nats: the natural logarithm of
 * silence's score over the render's. A recording silence matches leaves no distance to read, and a
 * render scoring zero is exact.
 */
function fromSilence(cell) {
  if (cell.silence <= 0) { return MESSAGES.silent; }
  if (cell.score <= 0) { return MESSAGES.exact; }
  return MESSAGES.closed(Math.log(cell.silence / cell.score).toFixed(SHOWN_DIGITS));
}

/** One render under one column: its play button, its readings, and a row per channel. */
function cellNode(cell, board) {
  const node = element("div", "cell");
  const render = clip(board.glyphs.play, cell.render, "button clip glyph-button");
  render.title = MESSAGES.play;
  render.setAttribute("aria-label", MESSAGES.play);
  node.append(render);
  const reading = element("div", "reading");
  reading.append(element("b", null, rounded(closeness(cell))));
  reading.append(element("span", null, fromSilence(cell)));
  node.append(reading);
  const channels = element("div", "channels");
  for (const channel of cell.channels) {
    channels.append(channelRow(channel, board.colors[channel.name]));
  }
  node.append(channels);
  return node;
}

/**
 * The change of the turned score from the first column to the last, so a rise means the last
 * column is closer to the recording. A change rounding to zero is marked neither better nor worse,
 * and a row of one column leaves the cell empty.
 */
function changeNode(row) {
  const node = element("td", "change");
  if (row.cells.length < CHANGE_COLUMNS) { return node; }
  const change = closeness(row.cells[row.cells.length - 1]) - closeness(row.cells[0]);
  const shown = rounded(change);
  if (Number(shown) !== 0) { node.classList.add(change > 0 ? "better" : "worse"); }
  node.textContent = `${Number(shown) >= 0 ? "+" : ""}${shown}`;
  return node;
}

/**
 * A row's recordings, one per level its cells were matched at. A row of one level offers its
 * recording plainly, and a row of several names each recording by its level.
 */
function recordingsNode(row) {
  const node = element("td", "recording");
  const named = row.recordings.length > 1;
  for (const recording of row.recordings) {
    node.append(clip(named ? recording.level : MESSAGES.recording, recording.clip, "button clip"));
  }
  return node;
}

/** One sound across the table: its name, its recordings, a cell per column and the change. */
function rowNode(row, board) {
  const node = element("tr", "sound-row");
  const sound = element("td", "sound");
  sound.append(breakable(row.item));
  node.append(sound);
  node.append(recordingsNode(row));
  for (const cell of row.cells) {
    const holder = element("td");
    holder.append(cellNode(cell, board));
    node.append(holder);
  }
  node.append(changeNode(row));
  return node;
}

/** A heading row naming a category, spanning every column of the table. */
function categoryNode(name, span) {
  const node = element("tr", "category");
  const heading = element("th", null, name);
  heading.colSpan = span;
  heading.scope = "colgroup";
  node.append(heading);
  return node;
}

/** The swatch and name of every channel the rows sound, in the order the page's colors list them. */
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
    entry.append(swatchNode(colors[name]), element("span", null, name));
    legend.append(entry);
  }
  return legend;
}

/**
 * The table's columns, each by its width class and its heading: the sound, the recording, a
 * version per column the data names, and the change.
 */
function tableColumns(columns) {
  return [
    { className: "sound", heading: MESSAGES.sound },
    { className: "recording", heading: MESSAGES.recording },
    ...columns.map((column) => ({ className: "version", heading: column })),
    { className: "change", heading: MESSAGES.change },
  ];
}

/** A column per table column, carrying the class its width is set by. */
function widthsNode(layout) {
  const widths = element("colgroup");
  for (const { className } of layout) {
    widths.append(element("col", className));
  }
  return widths;
}

/** The heading row, a heading per table column. */
function headNode(layout) {
  const head = element("tr");
  for (const { heading } of layout) {
    const cell = element("th", null, heading);
    cell.scope = "col";
    head.append(cell);
  }
  const thead = element("thead");
  thead.append(head);
  return thead;
}

/** The sound rows, a category heading opening each stretch of rows of one category. */
function bodyNode(rows, span, board) {
  const body = element("tbody");
  let category = null;
  for (const row of rows) {
    if (row.category !== category) { body.append(categoryNode(row.category, span)); }
    category = row.category;
    body.append(rowNode(row, board));
  }
  return body;
}

/**
 * A family's table. Its fixed layout holds every column at its width, so tables of different
 * families line up, and the number of version columns sets how wide the table must stay.
 */
function tableNode(columns, rows, board) {
  const layout = tableColumns(columns);
  const table = element("table", "table sounds");
  table.style.setProperty("--columns", String(columns.length));
  table.append(widthsNode(layout), headNode(layout), bodyNode(rows, layout.length, board));
  return table;
}

/** Sets a card's chevron to the glyph of its state, open or closed. */
function chevron(card, glyphs) {
  card.querySelector(".card-chevron").textContent = card.open ? glyphs.expanded : glyphs.collapsed;
}

/**
 * A family's collapsible card: a header naming the family, its count of sounds and the channels
 * they sound, over the family's table. The chevron follows the card as it opens and closes.
 */
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

/** The rows by family, the families in the order the rows first name them. */
function byFamily(rows) {
  const held = new Map();
  for (const row of rows) {
    if (!held.has(row.family)) { held.set(row.family, []); }
    held.get(row.family).push(row);
  }
  return held;
}

/**
 * A group's panel: a card per family. The first family opens, so the page starts with sounds to
 * hear and the rest stay folded until asked for.
 */
function groupNode(group, board) {
  const panel = element("section", "group");
  panel.dataset.group = group.name;
  Array.from(byFamily(group.rows)).forEach(([family, rows], index) => {
    panel.append(familyNode(family, rows, group.columns, board, index === 0));
  });
  return panel;
}

/** The rows the keys reach: the sound rows of the open cards in the group shown. */
function shownRows() {
  return Array.from(document.querySelectorAll("section.group:not([hidden]) details[open] tr.sound-row"));
}

/** Every clip button of a row, in the order the row shows them. */
function rowClips(row) {
  return Array.from(row.querySelectorAll("button.clip"));
}

/** The row a clip button stands in. */
function rowOf(button) {
  return button.closest("tr");
}

/** The place `offset` steps on from `place` among `count` places, going round past either end. */
function stepped(place, offset, count) {
  return (place + offset + count) % count;
}

/** Marks `button` and its row as playing, clearing every earlier mark; `null` marks nothing. */
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
    rowOf(button).classList.add("playing");
  }
}

/**
 * Plays the player on for `button`. A play the browser refuses clears the mark while `button` still
 * holds it. An interruption, which a pause or a newer play raises, leaves the mark where it stands.
 */
function resume(button) {
  player.play().catch((error) => {
    if (error.name !== INTERRUPTED && playing === button) { mark(null); }
  });
}

/**
 * Plays the clip a button holds from its beginning and marks it. Its row scrolls into view, so a
 * key stepping past the screen's edge keeps the sound in sight.
 */
function play(button) {
  if (!button) { return; }
  player.pause();
  player.src = button.dataset.source;
  player.currentTime = 0;
  resume(button);
  mark(button);
  rowOf(button).scrollIntoView({ block: "nearest" });
}

/**
 * The place a step of `offset` enters a row of `count` clips from: just outside the row, on the side
 * the step comes from, so a step right reaches the first clip and a step left the last.
 */
function entry(offset, count) {
  return offset > 0 ? BEFORE_FIRST : count;
}

/**
 * Plays the clip `offset` places across from the one playing, within its row, going round. With
 * nothing playing, the first open row is entered from the side the step comes from.
 */
function stepAcross(offset) {
  const rows = shownRows();
  const clips = playing ? rowClips(rowOf(playing)) : rows.length ? rowClips(rows[0]) : [];
  if (!clips.length) { return; }
  const place = playing ? clips.indexOf(playing) : entry(offset, clips.length);
  play(clips[stepped(place, offset, clips.length)]);
}

/**
 * Plays the clip `offset` open rows down from the one playing, going round, in the same place
 * along the row, or the row's last where it holds fewer clips. With nothing playing in an open
 * row, the first open row's first clip plays.
 */
function stepDown(offset) {
  const rows = shownRows();
  if (!rows.length) { return; }
  const current = playing ? rowOf(playing) : null;
  const index = rows.indexOf(current);
  if (index < 0) { play(rowClips(rows[0])[0]); return; }
  const place = rowClips(current).indexOf(playing);
  const next = rowClips(rows[stepped(index, offset, rows.length)]);
  play(next[Math.min(place, next.length - 1)]);
}

/** Space: starts the first open row where nothing plays, and otherwise pauses or resumes. */
function toggle() {
  if (!playing) { stepDown(0); return; }
  if (player.paused) { resume(playing); } else { player.pause(); }
}

const KEYS = new Map([
  [" ", toggle],
  ["ArrowRight", () => stepAcross(1)],
  ["ArrowLeft", () => stepAcross(-1)],
  ["ArrowDown", () => stepDown(1)],
  ["ArrowUp", () => stepDown(-1)],
]);

/** Opens or closes every family card of the group shown. */
function openAll(open) {
  for (const card of document.querySelectorAll("section.group:not([hidden]) details.family")) {
    card.open = open;
  }
}

/** The buttons opening and closing every card at once. */
function toolbarNode() {
  const toolbar = element("div", "toolbar");
  const opening = element("button", "button secondary", MESSAGES.openAll);
  opening.addEventListener("click", () => openAll(true));
  const closing = element("button", "button secondary", MESSAGES.closeAll);
  closing.addEventListener("click", () => openAll(false));
  toolbar.append(opening, closing);
  return toolbar;
}

/** Shows the group named `name` alone and stops what plays, since its clip belongs to another tab. */
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

/** A tab per group, shown once the page holds more than one. */
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

/**
 * Draws the page from its data. A page of one group names that group in its title, and a page of
 * several shows them a tab at a time, the first selected.
 */
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
  const action = KEYS.get(event.key);
  if (!action) { return; }
  event.preventDefault();
  action();
});

build(BOARD);
