import os
import sqlite3
import logging
from typing import Dict, Any, List

logger = logging.getLogger("OnionExplorer.Database")

class BaseDatabase:
    def save_entity(self, key: str, name: str, sector: str, type_val: str, sources: List[str], urls: List[Dict[str, Any]], stats: Dict[str, Any] = None):
        raise NotImplementedError()
        
    def save_entities_batch(self, batch: List[Dict[str, Any]]):
        raise NotImplementedError()
        
    def get_unified_data(self) -> Dict[str, Any]:
        raise NotImplementedError()
        
    def save_meta(self, meta: Dict[str, Any]):
        raise NotImplementedError()
        
    def get_meta(self) -> Dict[str, Any]:
        raise NotImplementedError()

    def update_location_screenshot(self, entity_key: str, url: str, screenshot_path: str, status: str):
        raise NotImplementedError()


class SQLiteIntelDatabase(BaseDatabase):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    type TEXT NOT NULL,
                    sources TEXT NOT NULL, -- JSON array
                    stats TEXT             -- JSON stats
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_key TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT,
                    fqdn TEXT,
                    version TEXT,
                    last_visit TEXT,
                    server_info TEXT,
                    url_type TEXT,
                    screenshot TEXT,
                    FOREIGN KEY (entity_key) REFERENCES entities (key) ON DELETE CASCADE,
                    UNIQUE(entity_key, url)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Migration check: add screenshot and analyst columns to locations if missing
            try:
                conn.execute("ALTER TABLE locations ADD COLUMN screenshot TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE locations ADD COLUMN analyst_working INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE locations ADD COLUMN analyst_notes TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
                
            conn.commit()

    def save_entity(self, key: str, name: str, sector: str, type_val: str, sources: List[str], urls: List[Dict[str, Any]], stats: Dict[str, Any] = None):
        import json
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO entities (key, name, sector, type, sources, stats)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    name = excluded.name,
                    sector = excluded.sector,
                    type = excluded.type,
                    sources = excluded.sources,
                    stats = excluded.stats
            """, (key, name, sector, type_val, json.dumps(sources), json.dumps(stats or {})))

            # Fetch existing screenshots and analyst notes to preserve them
            existing_rows = conn.execute("SELECT url, screenshot, analyst_working, analyst_notes FROM locations WHERE entity_key = ?", (key,)).fetchall()
            existing_screenshots = {row["url"]: row["screenshot"] for row in existing_rows if row["screenshot"]}
            existing_working = {row["url"]: row["analyst_working"] for row in existing_rows if row["analyst_working"] is not None}
            existing_notes = {row["url"]: row["analyst_notes"] for row in existing_rows if row["analyst_notes"]}

            # Clear and rebuild locations to stay fully synchronized with feeds
            conn.execute("DELETE FROM locations WHERE entity_key = ?", (key,))
            
            for u in urls:
                url_str = u.get("url", "")
                conn.execute("""
                    INSERT OR REPLACE INTO locations (entity_key, url, status, source, fqdn, version, last_visit, server_info, url_type, screenshot, analyst_working, analyst_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key,
                    url_str,
                    u.get("status", "Unknown"),
                    u.get("source", ""),
                    u.get("fqdn", ""),
                    u.get("version", ""),
                    u.get("last_visit", ""),
                    u.get("server_info", ""),
                    u.get("url_type", ""),
                    u.get("screenshot") or existing_screenshots.get(url_str),
                    existing_working.get(url_str, 0),
                    existing_notes.get(url_str, "")
                ))
            conn.commit()

    def save_entities_batch(self, batch: List[Dict[str, Any]]):
        import json
        with self._get_conn() as conn:
            for item in batch:
                key = item["key"]
                name = item["name"]
                sector = item["sector"]
                type_val = item["type_val"]
                sources = item["sources"]
                urls = item["urls"]
                stats = item["stats"]

                conn.execute("""
                    INSERT INTO entities (key, name, sector, type, sources, stats)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        name = excluded.name,
                        sector = excluded.sector,
                        type = excluded.type,
                        sources = excluded.sources,
                        stats = excluded.stats
                """, (key, name, sector, type_val, json.dumps(sources), json.dumps(stats or {})))

                # Fetch existing screenshots and analyst notes to preserve them
                existing_rows = conn.execute("SELECT url, screenshot, analyst_working, analyst_notes FROM locations WHERE entity_key = ?", (key,)).fetchall()
                existing_screenshots = {row["url"]: row["screenshot"] for row in existing_rows if row["screenshot"]}
                existing_working = {row["url"]: row["analyst_working"] for row in existing_rows if row["analyst_working"] is not None}
                existing_notes = {row["url"]: row["analyst_notes"] for row in existing_rows if row["analyst_notes"]}

                conn.execute("DELETE FROM locations WHERE entity_key = ?", (key,))
                
                for u in urls:
                    url_str = u.get("url", "")
                    conn.execute("""
                        INSERT OR REPLACE INTO locations (entity_key, url, status, source, fqdn, version, last_visit, server_info, url_type, screenshot, analyst_working, analyst_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        key,
                        url_str,
                        u.get("status", "Unknown"),
                        u.get("source", ""),
                        u.get("fqdn", ""),
                        u.get("version", ""),
                        u.get("last_visit", ""),
                        u.get("server_info", ""),
                        u.get("url_type", ""),
                        u.get("screenshot") or existing_screenshots.get(url_str),
                        existing_working.get(url_str, 0),
                        existing_notes.get(url_str, "")
                    ))
            conn.commit()

    def get_unified_data(self) -> Dict[str, Any]:
        import json
        forums_groups = {}
        markets = {}
        telegram_links = {}

        with self._get_conn() as conn:
            entities = conn.execute("SELECT * FROM entities").fetchall()
            for ent in entities:
                ekey = ent["key"]
                esector = ent["sector"]
                
                locs = conn.execute("SELECT * FROM locations WHERE entity_key = ?", (ekey,)).fetchall()
                urls_list = []
                for l in locs:
                    urls_list.append({
                        "url": l["url"],
                        "status": l["status"],
                        "source": l["source"],
                        "fqdn": l["fqdn"],
                        "version": l["version"],
                        "last_visit": l["last_visit"],
                        "server_info": l["server_info"],
                        "url_type": l["url_type"],
                        "screenshot": l["screenshot"],
                        "analyst_working": bool(l["analyst_working"]) if "analyst_working" in l.keys() else False,
                        "analyst_notes": l["analyst_notes"] if "analyst_notes" in l.keys() else ""
                    })
                
                on = sum(1 for u in urls_list if u["status"] == "Online")
                off = len(urls_list) - on
                entity_dict = {
                    "name": ent["name"],
                    "type": ent["type"],
                    "sources": json.loads(ent["sources"]),
                    "stats": json.loads(ent["stats"] or "{}"),
                    "urls": urls_list,
                    "online_count": on,
                    "offline_count": off,
                    "total_urls": len(urls_list)
                }
                
                if esector == "markets":
                    markets[ekey] = entity_dict
                elif esector == "telegram_links":
                    telegram_links[ekey] = entity_dict
                else:
                    forums_groups[ekey] = entity_dict

        meta = self.get_meta()
        return {
            "forums_groups": forums_groups,
            "markets": markets,
            "telegram_links": telegram_links,
            "meta": meta
        }

    def save_meta(self, meta: Dict[str, Any]):
        import json
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES (?, ?)
            """, ("scraper_meta", json.dumps(meta)))
            conn.commit()

    def get_meta(self) -> Dict[str, Any]:
        import json
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", ("scraper_meta",)).fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    pass
        return {}

    def update_location_screenshot(self, entity_key: str, url: str, screenshot_path: str, status: str):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE locations 
                SET screenshot = ?, status = ?
                WHERE entity_key = ? AND url = ?
            """, (screenshot_path, status, entity_key, url))
            conn.commit()

    def update_analyst_annotations(self, entity_key: str, url: str, analyst_working: bool, analyst_notes: str):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE locations
                SET analyst_working = ?, analyst_notes = ?
                WHERE entity_key = ? AND url = ?
            """, (1 if analyst_working else 0, analyst_notes, entity_key, url))
            conn.commit()


class MongoIntelDatabase(BaseDatabase):
    def __init__(self, connection_uri: str = "mongodb://localhost:27017"):
        import pymongo
        self.client = pymongo.MongoClient(connection_uri, serverSelectionTimeoutMS=2000)
        self.db = self.client["onion_explorer"]
        self.client.server_info() # verify connection

    def save_entity(self, key: str, name: str, sector: str, type_val: str, sources: List[str], urls: List[Dict[str, Any]], stats: Dict[str, Any] = None):
        existing = self.db.entities.find_one({"_id": key})
        existing_screenshots = {}
        existing_working = {}
        existing_notes = {}
        if existing:
            for u in existing.get("urls", []):
                if u.get("screenshot"):
                    existing_screenshots[u.get("url")] = u.get("screenshot")
                if u.get("analyst_working") is not None:
                    existing_working[u.get("url")] = u.get("analyst_working")
                if u.get("analyst_notes"):
                    existing_notes[u.get("url")] = u.get("analyst_notes")
        
        for u in urls:
            url_str = u.get("url", "")
            if not u.get("screenshot") and url_str in existing_screenshots:
                u["screenshot"] = existing_screenshots[url_str]
            u["analyst_working"] = existing_working.get(url_str, False)
            u["analyst_notes"] = existing_notes.get(url_str, "")

        self.db.entities.replace_one(
            {"_id": key},
            {
                "_id": key,
                "name": name,
                "sector": sector,
                "type": type_val,
                "sources": sources,
                "stats": stats or {},
                "urls": urls
            },
            upsert=True
        )

    def save_entities_batch(self, batch: List[Dict[str, Any]]):
        import pymongo
        operations = []
        for item in batch:
            key = item["key"]
            urls = item["urls"]
            
            existing = self.db.entities.find_one({"_id": key})
            existing_screenshots = {}
            existing_working = {}
            existing_notes = {}
            if existing:
                for u in existing.get("urls", []):
                    if u.get("screenshot"):
                        existing_screenshots[u.get("url")] = u.get("screenshot")
                    if u.get("analyst_working") is not None:
                        existing_working[u.get("url")] = u.get("analyst_working")
                    if u.get("analyst_notes"):
                        existing_notes[u.get("url")] = u.get("analyst_notes")
            
            for u in urls:
                url_str = u.get("url", "")
                if not u.get("screenshot") and url_str in existing_screenshots:
                    u["screenshot"] = existing_screenshots[url_str]
                u["analyst_working"] = existing_working.get(url_str, False)
                u["analyst_notes"] = existing_notes.get(url_str, "")

            operations.append(
                pymongo.ReplaceOne(
                    {"_id": key},
                    {
                        "_id": key,
                        "name": item["name"],
                        "sector": item["sector"],
                        "type": item["type_val"],
                        "sources": item["sources"],
                        "stats": item["stats"] or {},
                        "urls": urls
                    },
                    upsert=True
                )
            )
        if operations:
            self.db.entities.bulk_write(operations)

    def update_location_screenshot(self, entity_key: str, url: str, screenshot_path: str, status: str):
        self.db.entities.update_one(
            {"_id": entity_key, "urls.url": url},
            {"$set": {"urls.$.screenshot": screenshot_path, "urls.$.status": status}}
        )

    def update_analyst_annotations(self, entity_key: str, url: str, analyst_working: bool, analyst_notes: str):
        self.db.entities.update_one(
            {"_id": entity_key, "urls.url": url},
            {"$set": {"urls.$.analyst_working": analyst_working, "urls.$.analyst_notes": analyst_notes}}
        )

    def get_unified_data(self) -> Dict[str, Any]:
        forums_groups = {}
        markets = {}
        telegram_links = {}

        entities = list(self.db.entities.find())
        for ent in entities:
            ekey = ent["_id"]
            esector = ent.get("sector", "forums_groups")
            urls_list = ent.get("urls", [])
            on = sum(1 for u in urls_list if u.get("status") == "Online")
            off = len(urls_list) - on
            entity_dict = {
                "name": ent.get("name", ekey),
                "type": ent.get("type", "group"),
                "sources": ent.get("sources", []),
                "stats": ent.get("stats", {}),
                "urls": [
                    {
                        **u,
                        "analyst_working": u.get("analyst_working", False),
                        "analyst_notes": u.get("analyst_notes", "")
                    }
                    for u in urls_list
                ],
                "online_count": on,
                "offline_count": off,
                "total_urls": len(urls_list)
            }
            if esector == "markets":
                markets[ekey] = entity_dict
            elif esector == "telegram_links":
                telegram_links[ekey] = entity_dict
            else:
                forums_groups[ekey] = entity_dict

        meta = self.get_meta()
        return {
            "forums_groups": forums_groups,
            "markets": markets,
            "telegram_links": telegram_links,
            "meta": meta
        }

    def save_meta(self, meta: Dict[str, Any]):
        self.db.metadata.replace_one(
            {"_id": "scraper_meta"},
            {"_id": "scraper_meta", "value": meta},
            upsert=True
        )

    def get_meta(self) -> Dict[str, Any]:
        doc = self.db.metadata.find_one({"_id": "scraper_meta"})
        if doc and "value" in doc:
            return doc["value"]
        return {}


def get_database() -> BaseDatabase:
    try:
        import pymongo
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        db = MongoIntelDatabase(mongo_uri)
        logger.info("Database Connection: Successfully connected to MongoDB.")
        return db
    except Exception as e:
        logger.info(f"Database Connection: MongoDB not available or unreachable ({e}). Falling back to local SQLite.")
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "onion_explorer.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return SQLiteIntelDatabase(db_path)
