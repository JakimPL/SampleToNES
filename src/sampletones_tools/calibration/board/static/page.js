const MESSAGES = {
  lead: (referee) => `Scored by ${referee}; higher is closer to the recording, and zero is exact.`,
  heading: (title, run) => `${title}: ${run}`,
  sounds: (count) => (count === 1 ? "1 sound" : `${count} sounds`),
  prefix: (prefix) => `Every version's name starts with ${prefix}. The headings show only the rest.`,
  base: "base",
  sound: "sound",
  recording: "recording",
  change: "change",
  play: "play",
  solo: "S",
  mute: "M",
  silent: "—",
  exact: "exact",
  closed: (nats) => `${nats} nats`,
  spread: (lowest, highest) => `From ${lowest} to ${highest} over the starts the run drew`,
  unread: "—",
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

/** A channel's solo and mute clips, each where the render holds other channels too. */
function partsNode(channel) {
  const parts = element("span", "parts");
  if (channel.solo) { parts.append(partNode(MESSAGES.solo, channel.solo)); }
  if (channel.mute) { parts.append(partNode(MESSAGES.mute, channel.mute)); }
  return parts;
}

/** The bar of the frames a channel sounds. */
function barNode(channel, role) {
  const bar = element("span", "bar");
  bar.style.backgroundImage = gradient(channel.timeline, role);
  bar.title = channel.name;
  return bar;
}

/** The lane of a channel the render sounds: its square, its solo and mute clips, and its bar. */
function soundingLane(channel, role) {
  const lane = element("div", "lane");
  const square = swatchNode(role);
  square.title = channel.name;
  lane.append(square, partsNode(channel), barNode(channel, role));
  return lane;
}

/**
 * The lane kept for a channel the render leaves out: an empty square, and blank places where a
 * sounding lane holds its clips and its bar, so an open cell's columns stay in line.
 */
function silentLane() {
  const lane = element("div", "lane");
  lane.append(element("span", "swatch empty"), element("span"), element("span"));
  return lane;
}

/**
 * A cell's lanes, one per channel of its family in the family's order, so a channel stands at one
 * height in every cell of a row whichever channels each render holds.
 */
function lanesNode(cell, channels, colors) {
  const lanes = element("div", "lanes");
  const sounding = new Map(cell.channels.map((channel) => [channel.name, channel]));
  for (const name of channels) {
    const channel = sounding.get(name);
    lanes.append(channel ? soundingLane(channel, colors[name]) : silentLane());
  }
  return lanes;
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

/** The button playing a whole render. */
function playNode(cell, glyph) {
  const render = clip(glyph, cell.render, "button clip glyph-button");
  render.title = MESSAGES.play;
  render.setAttribute("aria-label", MESSAGES.play);
  return render;
}

/**
 * A render's score over how far it stands from silence. A score that is the mean of several
 * renders, as the oracle's is, names their closest and farthest in its tooltip.
 */
function readingNode(cell) {
  const reading = element("div", "reading");
  reading.append(element("b", null, rounded(closeness(cell))));
  reading.append(element("span", null, fromSilence(cell)));
  if (cell.spread) {
    const [lowest, highest] = cell.spread;
    reading.title = MESSAGES.spread(rounded(-highest), rounded(-lowest));
  }
  return reading;
}

/**
 * One render under one column: its play button, its readings and its lanes. A closed column shows
 * each lane's square, and an open one adds the channel's solo and mute clips and its bar.
 */
function cellNode(cell, channels, board) {
  const node = element("div", "cell");
  node.append(playNode(cell, board.glyphs.play), readingNode(cell), lanesNode(cell, channels, board.colors));
  return node;
}

/**
 * The change of the turned score from the first conversion's column to the last, so a rise means
 * the last column is closer to the recording. The oracle's column stands outside it. A change
 * rounding to zero is marked neither better nor worse, and a row of one conversion leaves the cell
 * empty.
 */
function changeNode(row, columns) {
  const node = element("td", "change");
  const cells = row.cells.filter((cell, place) => !columns[place].oracle);
  if (cells.length < CHANGE_COLUMNS) { return node; }
  const change = closeness(cells[cells.length - 1]) - closeness(cells[0]);
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

/** The class a version's heading and cells carry, the oracle's column marked apart. */
function versionClass(column) {
  return column.oracle ? "version oracle" : "version";
}

/**
 * One sound across the table: its name, its recordings, a cell per version and the change. A
 * sound the oracle reads no frames of leaves the oracle's cell holding a dash.
 */
function rowNode(row, columns, channels, board) {
  const node = element("tr", "sound-row");
  const sound = element("td", "sound");
  sound.append(breakable(row.item));
  node.append(sound);
  node.append(recordingsNode(row));
  row.cells.forEach((cell, place) => {
    const holder = inColumn(element("td", versionClass(columns[place])), place);
    holder.append(cell ? cellNode(cell, channels, board) : element("span", "unread", MESSAGES.unread));
    node.append(holder);
  });
  node.append(changeNode(row, columns));
  return node;
}

/**
 * A heading row naming a category, spanning every column of the table. The name stays in view as
 * the table scrolls sideways.
 */
function categoryNode(name, span) {
  const node = element("tr", "category");
  const heading = element("th");
  heading.append(element("span", null, name));
  heading.colSpan = span;
  heading.scope = "colgroup";
  node.append(heading);
  return node;
}

/** The swatch and name of every channel a family sounds. */
function legendNode(channels, colors) {
  const legend = element("span", "legend");
  for (const name of channels) {
    const entry = element("span");
    entry.append(swatchNode(colors[name]), element("span", null, name));
    legend.append(entry);
  }
  return legend;
}

/**
 * The table's columns, each by its class: the sound, the recording, a version per column the data
 * names, and the change. A version carries its column and its place among the versions.
 */
function tableColumns(columns) {
  return [
    { className: "sound", heading: MESSAGES.sound },
    { className: "recording", heading: MESSAGES.recording },
    ...columns.map((column, place) => ({ className: "version", column, place })),
    { className: "change", heading: MESSAGES.change },
  ];
}

/**
 * Marks a node as standing in the version column at `place`. A column's width, heading and cells
 * all carry the mark, which opening and closing the column finds them by.
 */
function inColumn(node, place) {
  node.dataset.column = String(place);
  return node;
}

/** A column per table column, carrying the class its width is set by. */
function widthsNode(layout) {
  const widths = element("colgroup");
  for (const { className, column, place } of layout) {
    widths.append(column ? inColumn(element("col", className), place) : element("col", className));
  }
  return widths;
}

/** The words a version's heading shows: those its name adds to the shared prefix, or the base's name. */
function headingWords(column) {
  return column.words.length ? column.words : [MESSAGES.base];
}

/**
 * A version's heading, which opens and closes its column: a chevron telling which it is, then the
 * words of the column's name one per line, so a long name keeps a closed column narrow. The whole
 * name stays in the tooltip.
 */
function versionHeading(column, place, glyphs) {
  const heading = inColumn(element("th", versionClass(column)), place);
  heading.title = column.name;
  const toggle = element("button", "column-toggle");
  toggle.setAttribute("aria-expanded", "false");
  toggle.append(element("span", "column-chevron", glyphs.collapsed));
  headingWords(column).forEach((word, index) => {
    if (index > 0) { toggle.append(element("br")); }
    toggle.append(word);
  });
  heading.append(toggle);
  heading.addEventListener("click", () => toggleColumn(heading, glyphs));
  return heading;
}

/** The heading row: a plain heading per fixed column, and an opening one per version. */
function headNode(layout, glyphs) {
  const head = element("tr");
  for (const { className, heading, column, place } of layout) {
    const cell = column ? versionHeading(column, place, glyphs) : element("th", className, heading);
    cell.scope = "col";
    head.append(cell);
  }
  const thead = element("thead");
  thead.append(head);
  return thead;
}

/** The sound rows, a category heading opening each stretch of rows of one category. */
function bodyNode(rows, columns, channels, span, board) {
  const body = element("tbody");
  let category = null;
  for (const row of rows) {
    if (row.category !== category) { body.append(categoryNode(row.category, span)); }
    category = row.category;
    body.append(rowNode(row, columns, channels, board));
  }
  return body;
}

/**
 * A family's table. Its fixed layout holds every column at its width, so tables of different
 * families line up, and the number of version columns sets how wide the table must stay.
 */
function tableNode(columns, family, rows, board) {
  const layout = tableColumns(columns);
  const table = element("table", "table sounds");
  table.style.setProperty("--columns", String(columns.length));
  table.append(
    widthsNode(layout),
    headNode(layout, board.glyphs),
    bodyNode(rows, columns, family.channels, layout.length, board),
  );
  return table;
}

/**
 * Opens or closes the version column a heading heads, in every table of its group, so the
 * families' tables keep lining up.
 */
function toggleColumn(heading, glyphs) {
  const panel = heading.closest("section.group");
  const place = heading.dataset.column;
  const open = !heading.classList.contains("open");
  for (const node of panel.querySelectorAll(`[data-column="${place}"]`)) {
    node.classList.toggle("open", open);
  }
  for (const toggle of panel.querySelectorAll(`th[data-column="${place}"] .column-toggle`)) {
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector(".column-chevron").textContent = open ? glyphs.expanded : glyphs.collapsed;
  }
  spread(panel);
}

/**
 * Tells a group how many of its columns are open, which its tables widen by. While any is open,
 * the group spreads every lane to a bar's height, so a channel's square stands level with its bar
 * in every cell of a row.
 */
function spread(panel) {
  const opened = panel.querySelector("table.sounds").querySelectorAll("th.version.open").length;
  panel.style.setProperty("--open-columns", String(opened));
  panel.classList.toggle("spread", opened > 0);
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
    element("span", "card-title", family.name),
    element("span", "count", MESSAGES.sounds(rows.length)),
    legendNode(family.channels, board.colors),
    element("span", "card-chevron"),
  );
  card.append(header);
  const scroll = element("div", "table-scroll");
  scroll.append(tableNode(columns, family, rows, board));
  card.append(scroll);
  card.addEventListener("toggle", () => chevron(card, board.glyphs));
  chevron(card, board.glyphs);
  return card;
}

/**
 * A group's panel: the prefix its versions' names share, then a card per family. The first family
 * opens, so the page starts with sounds to hear and the rest stay folded until asked for.
 */
function groupNode(group, board) {
  const panel = element("section", "group");
  panel.dataset.group = group.name;
  if (group.prefix) { panel.append(element("p", "prefix", MESSAGES.prefix(group.prefix))); }
  group.families.forEach((family, index) => {
    const rows = group.rows.filter((row) => row.family === family.name);
    panel.append(familyNode(family, rows, group.columns, board, index === 0));
  });
  return panel;
}

/** The rows the keys reach: the sound rows of the open cards in the group shown. */
function shownRows() {
  return Array.from(document.querySelectorAll("section.group:not([hidden]) details[open] tr.sound-row"));
}

/**
 * The clip buttons a row shows, in the order it shows them, so a closed column's solo and mute
 * clips are passed over. The clip playing counts as shown, so a step leaves from its place even
 * once its column has closed over it.
 */
function rowClips(row) {
  return Array.from(row.querySelectorAll("button.clip")).filter(
    (button) => button === playing || button.checkVisibility(),
  );
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
