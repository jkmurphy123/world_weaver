CREATE TABLE IF NOT EXISTS factions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id TEXT NOT NULL,
    name TEXT NOT NULL,
    ideology TEXT NOT NULL,
    influence INTEGER NOT NULL CHECK (influence >= 0 AND influence <= 100),
    confidence_tier TEXT NOT NULL CHECK (confidence_tier IN ('core_canon', 'established', 'rumored', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, name)
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id TEXT NOT NULL,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence_tier TEXT NOT NULL CHECK (confidence_tier IN ('core_canon', 'established', 'rumored', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, name)
);

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    affiliation TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_tier TEXT NOT NULL CHECK (confidence_tier IN ('core_canon', 'established', 'rumored', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, name)
);

CREATE TABLE IF NOT EXISTS lore_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    confidence_tier TEXT NOT NULL CHECK (confidence_tier IN ('core_canon', 'established', 'rumored', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, title)
);
