#!/usr/bin/env node
/**
 * AnythingLLM MCP Server
 * 为 presales-skills（solution-master / tender-workflow 等）提供知识库语义搜索能力
 */

const readline = require('readline');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

// F-025: keepalive agents 复用 TCP 连接，避免每次请求新建（4 个 maxSockets 足够 MCP 单客户端用量）
const httpAgent = new http.Agent({ keepAlive: true, maxSockets: 4 });
const httpsAgent = new https.Agent({ keepAlive: true, maxSockets: 4 });

// Read unified config as fallback to env vars.
// Priority order (higher overrides lower):
//   1. env var (highest)
//   2. unified presales-skills config (~/.config/presales-skills/config.yaml)
//   3. tender-workflow config (~/.config/tender-workflow/config.yaml)
//   4. solution-master config (~/.config/solution-master/config.yaml)
//   5. defaults (lowest)
// Implementation iterates CONFIG_CANDIDATES in reverse so later (higher-priority) sources overwrite.
// Multi-source: users who already configured via /twc or /solution-config don't need to re-enter keys.
const CONFIG_CANDIDATES = [
  path.join(os.homedir(), '.config', 'presales-skills', 'config.yaml'),
  path.join(os.homedir(), '.config', 'tender-workflow', 'config.yaml'),
  path.join(os.homedir(), '.config', 'solution-master', 'config.yaml'),
];

function parseAnythingllmBlock(text) {
  // Minimal YAML subset parser — only the `anythingllm:` block's scalar fields.
  // Avoids adding a YAML dep (MCP must stay zero-deps).
  //
  // F-023 WARNING: only flat scalars supported. Nested keys like `anythingllm.proxy.host`
  // will be silently ignored (no error). If schema grows nested fields, replace with a
  // proper YAML lib (mind the zero-deps constraint — this MCP server has no node_modules).
  const result = {};
  const lines = text.split('\n');
  let inBlock = false;
  for (const raw of lines) {
    const line = raw.replace(/\r$/, '');
    if (/^anythingllm\s*:\s*$/.test(line)) { inBlock = true; continue; }
    if (inBlock) {
      if (/^\S/.test(line)) { inBlock = false; continue; }  // dedented to top-level key
      const m = line.match(/^\s{2,}(\w+)\s*:\s*(.*?)\s*$/);
      if (m) {
        let v = m[2];
        if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
          v = v.slice(1, -1);
        }
        result[m[1]] = v;
      }
    }
  }
  return result;
}

function readConfigFallback() {
  const merged = {};
  // Iterate in reverse so later (higher-priority) sources overwrite.
  for (const p of [...CONFIG_CANDIDATES].reverse()) {
    if (!fs.existsSync(p)) continue;
    try {
      const parsed = parseAnythingllmBlock(fs.readFileSync(p, 'utf8'));
      for (const [k, v] of Object.entries(parsed)) {
        if (v !== '' && v !== undefined) merged[k] = v;
      }
    } catch (e) { /* ignore, try next */ }
  }
  return merged;
}

const _cfg = readConfigFallback();
const BASE_URL = process.env.ANYTHINGLLM_BASE_URL || _cfg.base_url || 'http://localhost:3001';
const API_KEY = process.env.ANYTHINGLLM_API_KEY || _cfg.api_key || '';
const DEFAULT_WS = process.env.ANYTHINGLLM_WORKSPACE || _cfg.workspace || '';

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function sendError(id, code, message) {
  send({ jsonrpc: '2.0', id, error: { code, message } });
}

function apiRequest(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE_URL + path);
    const lib = url.protocol === 'https:' ? https : http;
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname + url.search,
      method,
      timeout: 30000,  // F-025: socket-level timeout (30s)
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
      agent: url.protocol === 'https:' ? httpsAgent : httpAgent,  // F-025: keepalive
    };
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        // F-010: 4xx/5xx 状态码必须分类报错，避免 Claude 拿到 HTML 错误页当 JSON 解
        if (res.statusCode >= 400) {
          const hint =
            res.statusCode === 401 ? '认证失败 — ANYTHINGLLM_API_KEY 错误或已过期' :
            res.statusCode === 404 ? '端点不存在 — 检查 ANYTHINGLLM_BASE_URL / workspace slug' :
            res.statusCode >= 500  ? 'AnythingLLM 服务异常 — 检查服务状态' :
            `HTTP ${res.statusCode}`;
          reject(new Error(`[AnythingLLM ${res.statusCode}] ${hint}: ${data.substring(0, 200)}`));
          return;
        }
        try { resolve(JSON.parse(data)); }
        catch (e) { resolve(data); }
      });
    });
    req.on('error', err => reject(new Error(`Request failed: ${err.message}`)));
    req.on('timeout', () => req.destroy(new Error('Request timeout after 30s')));
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

const TOOLS = [
  {
    name: 'anythingllm_search',
    description: '在 AnythingLLM 知识库中进行语义搜索，返回相关文档片段',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: '搜索查询' },
        workspace: { type: 'string', description: 'workspace slug' },
        mode: { type: 'string', enum: ['query', 'chat'], default: 'query' },
      },
      required: ['query'],
    },
  },
  {
    name: 'anythingllm_list_workspaces',
    description: '列出所有可用的 workspace',
    inputSchema: { type: 'object', properties: {} },
  },
];

let defaultWorkspace = DEFAULT_WS || null;

async function getDefaultWorkspace() {
  if (defaultWorkspace) return defaultWorkspace;
  const result = await apiRequest('GET', '/api/v1/workspaces');
  if (result.workspaces && result.workspaces.length > 0) {
    defaultWorkspace = result.workspaces[0].slug;
  }
  return defaultWorkspace;
}

async function handleSearch({ query, workspace, mode = 'query' }) {
  const ws = workspace || await getDefaultWorkspace();
  if (!ws) throw new Error('No workspace available');
  const result = await apiRequest('POST', `/api/v1/workspace/${ws}/chat`, {
    message: query,
    mode,
  });
  if (result.error) throw new Error(result.error);
  return {
    answer: result.textResponse || '',
    sources: (result.sources || []).map(s => ({
      title: s.title,
      score: s.score ? s.score.toFixed(3) : 'N/A',
      text: s.text ? s.text.substring(0, 500) : '',
    })),
    workspace: ws,
  };
}

async function handleListWorkspaces() {
  const result = await apiRequest('GET', '/api/v1/workspaces');
  return (result.workspaces || []).map(w => ({
    id: w.id,
    name: w.name,
    slug: w.slug,
  }));
}

async function handleMessage(msg) {
  const { id, method, params } = msg;
  if (method === 'initialize') {
    send({
      jsonrpc: '2.0', id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'anythingllm', version: '1.0.0' },
      },
    });
    return;
  }
  if (method === 'notifications/initialized') return;
  if (method === 'tools/list') {
    send({ jsonrpc: '2.0', id, result: { tools: TOOLS } });
    return;
  }
  if (method === 'tools/call') {
    const { name, arguments: args } = params;
    try {
      let result;
      if (name === 'anythingllm_search') result = await handleSearch(args);
      else if (name === 'anythingllm_list_workspaces') result = await handleListWorkspaces(args);
      else throw new Error(`Unknown tool: ${name}`);
      send({
        jsonrpc: '2.0', id,
        result: {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        },
      });
    } catch (e) {
      sendError(id, -32000, e.message);
    }
    return;
  }
  sendError(id, -32601, `Method not found: ${method}`);
}

const rl = readline.createInterface({ input: process.stdin });
rl.on('line', (line) => {
  try {
    const msg = JSON.parse(line.trim());
    handleMessage(msg).catch(e => {
      if (msg.id) sendError(msg.id, -32000, e.message);
    });
  } catch (e) {}
});
