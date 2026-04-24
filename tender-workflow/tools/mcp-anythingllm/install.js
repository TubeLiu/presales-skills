#!/usr/bin/env node
/**
 * AnythingLLM MCP Server 安装脚本
 *
 * 功能：
 * 1. 全局安装 npm 包
 * 2. 检测 ~/.claude.json 是否存在
 * 3. 添加 anythingllm MCP 配置到 mcpServers
 * 4. 支持通过命令行参数或交互式输入配置 API Key 和 workspace
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

// 配置文件路径
const CLAUDE_CONFIG_PATH = path.join(require('os').homedir(), '.claude.json');
const TW_CONFIG_DIR = path.join(require('os').homedir(), '.config', 'tender-workflow');
const TW_CONFIG_PATH = path.join(TW_CONFIG_DIR, 'config.yaml');
// Legacy paths (no longer written to, kept for reference)
const TAA_CONFIG_DIR = path.join(require('os').homedir(), '.config', 'taa');
const TAW_CONFIG_DIR = path.join(require('os').homedir(), '.config', 'taw');

// AnythingLLM 默认配置
const DEFAULT_CONFIG = {
  ANYTHINGLLM_BASE_URL: 'http://localhost:3001',
  ANYTHINGLLM_API_KEY: '',
  ANYTHINGLLM_WORKSPACE: '',
};

function log(message, type = 'info') {
  const prefix = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌',
  }[type] || 'ℹ️';
  console.log(`${prefix} ${message}`);
}

function error(message, exitCode = 1) {
  log(message, 'error');
  process.exit(exitCode);
}

// 创建 readline 接口用于交互式输入
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, (answer) => {
      resolve(answer);
    });
  });
}

// 检测操作系统和架构
function detectPlatform() {
  const platform = process.platform;
  const arch = process.arch;
  return { platform, arch };
}

// 全局安装 npm 包
function installGlobally() {
  log('正在全局安装 mcp-anythingllm...');
  try {
    execSync('npm install -g .', { stdio: 'inherit', cwd: __dirname });
    log('全局安装成功', 'success');
    return true;
  } catch (err) {
    error('全局安装失败：' + err.message);
  }
}

// 读取现有配置
function readClaudeConfig() {
  if (!fs.existsSync(CLAUDE_CONFIG_PATH)) {
    log('未找到 ~/.claude.json，将创建新配置');
    return { mcpServers: {} };
  }
  try {
    const content = fs.readFileSync(CLAUDE_CONFIG_PATH, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    error('读取配置文件失败：' + err.message);
  }
}

// 写入配置
function writeClaudeConfig(config) {
  const configDir = path.dirname(CLAUDE_CONFIG_PATH);
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }
  fs.writeFileSync(CLAUDE_CONFIG_PATH, JSON.stringify(config, null, 2), 'utf8');
  log('配置已写入 ~/.claude.json', 'success');
}

// 添加 MCP 配置
function addMcpConfig(config, envVars) {
  if (!config.mcpServers) {
    config.mcpServers = {};
  }

  config.mcpServers.anythingllm = {
    command: 'mcp-anythingllm',
    args: [],
    env: envVars,
  };

  log('已添加 anythingllm MCP 配置');
}

// 更新统一配置文件的 AnythingLLM 部分
function updateUnifiedConfig(workspace, baseUrl) {
  if (!fs.existsSync(TW_CONFIG_DIR)) {
    fs.mkdirSync(TW_CONFIG_DIR, { recursive: true });
  }

  // 读取现有配置（如果存在）
  let config = {};
  if (fs.existsSync(TW_CONFIG_PATH)) {
    try {
      const content = fs.readFileSync(TW_CONFIG_PATH, 'utf8');
      // 简单 YAML 解析（避免依赖额外包）
      // 使用 tw_config.py 来处理 YAML
      const { execSync } = require('child_process');
      const projectRoot = path.resolve(__dirname, '../..');
      execSync(`python3 ${path.join(projectRoot, 'tools/tw_config.py')} set anythingllm.enabled true`, { stdio: 'pipe' });
      execSync(`python3 ${path.join(projectRoot, 'tools/tw_config.py')} set anythingllm.workspace "${workspace}"`, { stdio: 'pipe' });
      if (baseUrl) {
        execSync(`python3 ${path.join(projectRoot, 'tools/tw_config.py')} set anythingllm.base_url "${baseUrl}"`, { stdio: 'pipe' });
      }
      log(`已更新统一配置文件：${TW_CONFIG_PATH}`, 'success');
      return;
    } catch (e) {
      log(`tw_config.py 调用失败，直接写入 YAML: ${e.message}`, 'warning');
    }
  }

  // 回退：直接写入 YAML
  const configContent = [
    'anythingllm:',
    '  enabled: true',
    `  base_url: "${baseUrl || 'http://localhost:3001'}"`,
    `  workspace: ${workspace}`,
    '',
  ].join('\n');

  if (fs.existsSync(TW_CONFIG_PATH)) {
    // 追加到现有文件（简单处理）
    const existing = fs.readFileSync(TW_CONFIG_PATH, 'utf8');
    if (!existing.includes('anythingllm:')) {
      fs.appendFileSync(TW_CONFIG_PATH, '\n' + configContent, 'utf8');
    }
  } else {
    fs.writeFileSync(TW_CONFIG_PATH, configContent, 'utf8');
  }
  log(`已更新统一配置文件：${TW_CONFIG_PATH}`, 'success');
}

// Legacy: 创建 TAA 配置文件（已废弃，保留兼容）
function createTaaConfig(workspace) {
  // 不再写入旧配置文件，改用统一配置
  log('TAA 配置已迁移到统一配置文件', 'info');
}

// Legacy: 创建 TAW 配置文件（已废弃，保留兼容）
function createTawConfig(workspace) {
  // 不再写入旧配置文件，改用统一配置
  log('TAW 配置已迁移到统一配置文件', 'info');
}

// 验证 AnythingLLM 连接
async function verifyConnection(baseUrl, apiKey) {
  const https = require('https');
  const http = require('http');

  return new Promise((resolve) => {
    const url = new URL(baseUrl + '/api/ping');
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname + url.search,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    };
    const lib = url.protocol === 'https:' ? https : http;
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          resolve(result.online === true);
        } catch (e) {
          resolve(false);
        }
      });
    });
    req.on('error', () => resolve(false));
    req.setTimeout(5000, () => {
      req.destroy();
      resolve(false);
    });
    req.end();
  });
}

// 获取 workspace 列表
async function getWorkspaces(baseUrl, apiKey) {
  const https = require('https');
  const http = require('http');

  return new Promise((resolve) => {
    const url = new URL(baseUrl + '/api/v1/workspaces');
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname + url.search,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    };
    const lib = url.protocol === 'https:' ? https : http;
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          resolve(result.workspaces || []);
        } catch (e) {
          resolve([]);
        }
      });
    });
    req.on('error', () => resolve([]));
    req.setTimeout(5000, () => {
      req.destroy();
      resolve([]);
    });
    req.end();
  });
}

// 主函数
async function main() {
  const args = process.argv.slice(2);

  // 解析命令行参数
  const argMap = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      const value = args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true;
      argMap[key] = value;
      if (value !== true) i++;
    }
  }

  log('═══════════════════════════════════════════');
  log('  AnythingLLM MCP Server 安装向导');
  log('═══════════════════════════════════════════\n');

  // 步骤 1：全局安装
  log('步骤 1/4: 全局安装 npm 包');
  installGlobally();

  // 步骤 2：获取配置
  log('\n步骤 2/4: 配置 AnythingLLM 连接');

  let baseUrl = argMap['base-url'] || argMap['baseUrl'] || DEFAULT_CONFIG.ANYTHINGLLM_BASE_URL;
  let apiKey = argMap['api-key'] || argMap['apiKey'] || '';
  let workspace = argMap['workspace'] || argMap['w'] || '';

  if (!apiKey) {
    apiKey = await question(`AnythingLLM API Key [默认：${DEFAULT_CONFIG.ANYTHINGLLM_API_KEY || '无'}]: `);
  }

  if (!apiKey) {
    error('API Key 不能为空');
  }

  // 验证连接
  log('正在验证 AnythingLLM 连接...');
  const isConnected = await verifyConnection(baseUrl, apiKey);
  if (!isConnected) {
    log('无法连接到 AnythingLLM，请检查：', 'warning');
    log(`  1. AnythingLLM Desktop 是否运行在 ${baseUrl}`);
    log('  2. API Key 是否正确');
    const continueAnyway = await question('是否继续安装？(y/N): ');
    if (continueAnyway.toLowerCase() !== 'y') {
      error('安装已取消');
    }
  } else {
    log('AnythingLLM 连接成功', 'success');
  }

  // 获取 workspace 列表
  log('正在获取 workspace 列表...');
  const workspaces = await getWorkspaces(baseUrl, apiKey);
  if (workspaces.length > 0) {
    log('可用的 workspace:');
    workspaces.forEach((ws, index) => {
      log(`  ${index + 1}. ${ws.name} (slug: ${ws.slug})`);
    });

    if (!workspace) {
      const choice = await question(`\n选择默认 workspace (1-${workspaces.length}, 或输入 slug)，留空使用第一个 [1]: `);
      if (choice) {
        const num = parseInt(choice);
        if (num >= 1 && num <= workspaces.length) {
          workspace = workspaces[num - 1].slug;
        } else {
          // 检查是否是 slug
          const found = workspaces.find(ws => ws.slug === choice || ws.name === choice);
          if (found) {
            workspace = found.slug;
          } else {
            workspace = choice; // 用户手动输入 slug
          }
        }
      } else {
        workspace = workspaces[0].slug;
      }
    }
  } else {
    log('未获取到 workspace 列表', 'warning');
    if (!workspace) {
      workspace = await question('请输入默认 workspace slug: ');
    }
  }

  // 步骤 3：配置 Claude Code
  log('\n步骤 3/4: 配置 Claude Code');
  const config = readClaudeConfig();
  const envVars = {
    ANYTHINGLLM_BASE_URL: baseUrl,
    ANYTHINGLLM_API_KEY: apiKey,
  };
  if (workspace) {
    envVars.ANYTHINGLLM_WORKSPACE = workspace;
  }
  addMcpConfig(config, envVars);
  writeClaudeConfig(config);

  // 步骤 4：更新统一配置文件
  log('\n步骤 4/4: 更新统一配置文件');
  if (workspace) {
    updateUnifiedConfig(workspace, baseUrl);
  }

  // 完成
  log('\n═══════════════════════════════════════════');
  log('  安装完成！');
  log('═══════════════════════════════════════════\n');

  log('配置摘要:');
  log(`  AnythingLLM 地址：${baseUrl}`);
  log(`  默认 workspace: ${workspace || '自动选择第一个'}`);
  log(`  Claude 配置：~/.claude.json`);
  log(`  统一配置：~/.config/tender-workflow/config.yaml`);

  log('\n下一步:');
  log('  1. 重启 Claude Code 以加载新的 MCP 配置');
  log('  2. 使用 /taa 或 /taw 命令测试 AnythingLLM 集成');
  log('  3. 运行 anythingllm_list_workspaces 验证连接\n');

  rl.close();
}

main().catch(err => {
  error('安装过程中出错：' + err.message);
});
