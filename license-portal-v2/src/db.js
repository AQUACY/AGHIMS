const fs = require("fs");
const path = require("path");
const mysql = require("mysql2/promise");
const initSqlJs = require("sql.js");
const { config } = require("./config");

function splitSql(sql) {
  return sql
    .split(/;\s*(?:\r?\n|$)/)
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith("--"));
}

function nowSql() {
  return new Date().toISOString().slice(0, 19).replace("T", " ");
}

function parseRows(rows) {
  return rows.map((row) => {
    const out = { ...row };
    return out;
  });
}

class MysqlDb {
  constructor(pool) {
    this.dialect = "mysql";
    this.pool = pool;
  }

  async query(sql, params = [], conn = null) {
    const runner = conn || this.pool;
    const [result] = await runner.execute(sql, params.map((p) => (p === undefined ? null : p)));
    if (Array.isArray(result)) {
      return { rows: parseRows(result), insertId: 0, affectedRows: 0 };
    }
    return {
      rows: [],
      insertId: Number(result.insertId) || 0,
      affectedRows: Number(result.affectedRows) || 0,
    };
  }

  async withTransaction(fn) {
    const conn = await this.pool.getConnection();
    await conn.beginTransaction();
    const tx = {
      dialect: this.dialect,
      query: (sql, params) => this.query(sql, params, conn),
    };
    try {
      const out = await fn(tx);
      await conn.commit();
      return out;
    } catch (err) {
      await conn.rollback();
      throw err;
    } finally {
      conn.release();
    }
  }

  async close() {
    await this.pool.end();
  }
}

class SqliteDb {
  constructor(SQL, filePath) {
    this.dialect = "sqlite";
    this.filePath = filePath;
    this.SQL = SQL;
    this.inTx = false;
    if (fs.existsSync(filePath)) {
      const buf = fs.readFileSync(filePath);
      this.db = new SQL.Database(buf);
    } else {
      this.db = new SQL.Database();
    }
  }

  persist() {
    const data = this.db.export();
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
    fs.writeFileSync(this.filePath, Buffer.from(data));
  }

  async query(sql, params = []) {
    const trimmed = sql.trim();
    const isSelect = /^\s*(select|pragma|with)/i.test(trimmed);
    const safeParams = params.map((p) => (p === undefined ? null : p));
    if (isSelect) {
      const stmt = this.db.prepare(trimmed);
      try {
        if (safeParams.length) stmt.bind(safeParams);
        const rows = [];
        while (stmt.step()) {
          rows.push(stmt.getAsObject());
        }
        return { rows, insertId: 0, affectedRows: 0 };
      } finally {
        stmt.free();
      }
    }
    if (safeParams.length) this.db.run(trimmed, safeParams);
    else this.db.run(trimmed);
    const idRow = this.db.exec("SELECT last_insert_rowid() AS id");
    const insertId = Number((idRow[0] && idRow[0].values[0] && idRow[0].values[0][0]) || 0);
    const affectedRows = this.db.getRowsModified();
    if (!this.inTx) this.persist();
    return { rows: [], insertId, affectedRows };
  }

  async withTransaction(fn) {
    this.inTx = true;
    this.db.run("BEGIN IMMEDIATE");
    const tx = {
      dialect: this.dialect,
      query: (sql, params) => this.query(sql, params),
    };
    try {
      const out = await fn(tx);
      this.db.run("COMMIT");
      this.persist();
      return out;
    } catch (err) {
      try {
        this.db.run("ROLLBACK");
      } catch (_) {
        /* ignore */
      }
      this.persist();
      throw err;
    } finally {
      this.inTx = false;
    }
  }

  async close() {
    this.persist();
    this.db.close();
  }
}

let db;

function isLocalMysqlHost(host) {
  const h = String(host || "").toLowerCase();
  return !h || h === "localhost" || h === "127.0.0.1" || h === "::1";
}

function detectMysqlSocket() {
  if (config.mysql.socketPath) return config.mysql.socketPath;
  if (!isLocalMysqlHost(config.mysql.host)) return "";
  const candidates = [
    process.env.MYSQL_UNIX_PORT,
    "/tmp/mysql.sock",
    "/var/run/mysqld/mysqld.sock",
    "/run/mysqld/mysqld.sock",
    "/var/lib/mysql/mysql.sock",
  ].filter(Boolean);
  return candidates.find((p) => {
    try {
      return fs.existsSync(p);
    } catch (_) {
      return false;
    }
  }) || "";
}

function mysqlPoolBase() {
  return {
    user: config.mysql.user,
    password: config.mysql.password,
    database: config.mysql.database,
    waitForConnections: true,
    connectionLimit: 10,
    namedPlaceholders: false,
    charset: "utf8mb4",
    dateStrings: true,
  };
}

async function tryMysqlPool(extra) {
  const pool = mysql.createPool({ ...mysqlPoolBase(), ...extra });
  try {
    await pool.execute("SELECT 1");
    return pool;
  } catch (err) {
    try {
      await pool.end();
    } catch (_) {
      /* ignore */
    }
    throw err;
  }
}

function mysqlAccessDeniedHelp(err) {
  const seen = String((err && err.message) || "");
  return (
    `${seen} Hostinger's MySQL user is usually '${config.mysql.user}'@'localhost' (Unix socket), ` +
    `which is a different account from '${config.mysql.user}'@'127.0.0.1'. ` +
    `In hPanel → Databases → Remote MySQL add Access Host 127.0.0.1 (and localhost). ` +
    `Assign that user to ${config.mysql.database} with ALL PRIVILEGES. ` +
    `Reset the password and paste it into Node env with no quotes. ` +
    `If /tmp/mysql.sock exists, set MYSQL_SOCKET=/tmp/mysql.sock so Node logs in as @localhost.`
  );
}

async function connectMysql() {
  const attempts = [];
  const socket = detectMysqlSocket();
  if (socket) attempts.push({ label: `socket ${socket}`, extra: { socketPath: socket } });
  attempts.push({
    label: `tcp ${config.mysql.host}:${config.mysql.port}`,
    extra: { host: config.mysql.host, port: config.mysql.port },
  });

  let lastErr;
  for (const attempt of attempts) {
    try {
      const pool = await tryMysqlPool(attempt.extra);
      console.log(`MySQL connected via ${attempt.label} as ${config.mysql.user} / ${config.mysql.database}`);
      return pool;
    } catch (err) {
      lastErr = err;
      console.error(`MySQL ${attempt.label} failed: ${err.message}`);
    }
  }
  if (lastErr && lastErr.code === "ER_ACCESS_DENIED_ERROR") {
    throw new Error(mysqlAccessDeniedHelp(lastErr));
  }
  throw lastErr;
}

async function initDb() {
  fs.mkdirSync(config.dataDir, { recursive: true });
  fs.mkdirSync(config.documentsDir, { recursive: true });
  fs.mkdirSync(config.brandingDir, { recursive: true });

  if (config.databaseMode === "mysql") {
    const pool = await connectMysql();
    db = new MysqlDb(pool);
    const schema = fs.readFileSync(path.join(config.ROOT, "sql", "schema.mysql.sql"), "utf8");
    try {
      for (const stmt of splitSql(schema)) {
        await db.query(stmt);
      }
    } catch (err) {
      if (err && err.code === "ER_ACCESS_DENIED_ERROR") {
        throw new Error(mysqlAccessDeniedHelp(err));
      }
      throw err;
    }
  } else {
    const SQL = await initSqlJs({
      locateFile: (file) => path.join(path.dirname(require.resolve("sql.js")), file),
    });
    db = new SqliteDb(SQL, config.sqlitePath);
    await db.query("PRAGMA foreign_keys = ON");
    const schema = fs.readFileSync(path.join(config.ROOT, "sql", "schema.sqlite.sql"), "utf8");
    for (const stmt of splitSql(schema)) {
      await db.query(stmt);
    }
  }

  const seqInvoice = await db.query("SELECT name FROM sequences WHERE name = ?", ["invoice"]);
  if (!seqInvoice.rows.length) {
    await db.query("INSERT INTO sequences (name, next_value) VALUES (?, ?)", ["invoice", 1]);
  }
  const seqReceipt = await db.query("SELECT name FROM sequences WHERE name = ?", ["receipt"]);
  if (!seqReceipt.rows.length) {
    await db.query("INSERT INTO sequences (name, next_value) VALUES (?, ?)", ["receipt", 1]);
  }

  await ensurePaymentPeriodColumns(db);
  await ensureCustomerDeadlineColumn(db);

  return db;
}

async function ensureCustomerDeadlineColumn(db) {
  if (db.dialect === "sqlite") {
    const info = await db.query("PRAGMA table_info(customers)");
    const names = info.rows.map((r) => r.name);
    if (!names.includes("billing_deadline")) {
      await db.query("ALTER TABLE customers ADD COLUMN billing_deadline TEXT NULL");
    }
    return;
  }
  const cols = await db.query(
    `SELECT COLUMN_NAME AS name FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'customers'`
  );
  const names = cols.rows.map((r) => String(r.name || r.COLUMN_NAME || "").toLowerCase());
  if (!names.includes("billing_deadline")) {
    await db.query("ALTER TABLE customers ADD COLUMN billing_deadline DATETIME NULL");
  }
}

async function ensurePaymentPeriodColumns(db) {
  if (db.dialect === "sqlite") {
    const info = await db.query("PRAGMA table_info(payments)");
    const names = info.rows.map((r) => r.name);
    if (!names.includes("period_from")) {
      await db.query("ALTER TABLE payments ADD COLUMN period_from TEXT NULL");
    }
    if (!names.includes("period_until")) {
      await db.query("ALTER TABLE payments ADD COLUMN period_until TEXT NULL");
    }
    return;
  }
  const cols = await db.query(
    `SELECT COLUMN_NAME AS name FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'payments'`
  );
  const names = cols.rows.map((r) => String(r.name || r.COLUMN_NAME || "").toLowerCase());
  if (!names.includes("period_from")) {
    await db.query("ALTER TABLE payments ADD COLUMN period_from DATETIME NULL");
  }
  if (!names.includes("period_until")) {
    await db.query("ALTER TABLE payments ADD COLUMN period_until DATETIME NULL");
  }
}

function getDb() {
  if (!db) throw new Error("Database not initialized");
  return db;
}

function lockClause(runner) {
  return (runner.dialect || getDb().dialect) === "mysql" ? " FOR UPDATE" : "";
}

module.exports = { initDb, getDb, nowSql, lockClause };
