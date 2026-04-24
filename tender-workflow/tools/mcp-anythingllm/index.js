#!/usr/bin/env node
/**
 * AnythingLLM MCP Server
 * 为 Tender Workflow 项目提供语义搜索能力
 */

const readline = require('readline');
const https = require('https');
const http = require('http');

const BASE_URL = process.env.ANYTHINGLLM_BASE_URL || 'http://localhost:3001';
const API_KEY = process.env.ANYTHINGLLM_API_KEY || '';

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function sendError(id, code, message) {
  send({ jsonrpc: '2.0', id, error: { code, message } });
}

function apiRequest(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE_URL + path);
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname + url.search,
      method,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
    };
    const lib = url.protocol === 'https:' ? https : http;
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { resolve(data); }
      });
    });
    req.on('error', reject);
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

let defaultWorkspace = null;

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
