#!/usr/bin/env node

/*
 * solution-master — npx installer
 *
 * Adapted from superpowers-zh/bin/superpowers-zh.js (MIT, jnMetaCode)
 * Source commit: 4a55cbf9f348ba694cf5cbf4d56df7340ff2b74f
 *
 * Changes from upstream:
 *   - Targets Claude Code only (.claude/{skills,agents,hooks})
 *   - Adds --global mode for ~/.claude/ installation
 *   - Adds --uninstall reverse operation
 *   - Smart merge of <target>/settings.json to register the SessionStart hook
 *     (backs up existing settings.json before modification)
 */

import {
  existsSync,
  mkdirSync,
  cpSync,
  rmSync,
  readFileSync,
  writeFileSync,
  copyFileSync,
  chmodSync,
  readdirSync,
  statSync,
} from 'fs';
import { resolve, dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { homedir } from 'os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = resolve(__dirname, '..');
const PKG = JSON.parse(readFileSync(resolve(PKG_ROOT, 'package.json'), 'utf8'));

const SKILLS_SRC = resolve(PKG_ROOT, 'skills');
const AGENTS_SRC = resolve(PKG_ROOT, 'agents');
const HOOKS_SRC = resolve(PKG_ROOT, 'hooks');

const HOOK_MARKER = 'solution-master';

function showHelp() {
  console.log(`
  solution-master v${PKG.version} — AI 辅助通用解决方案撰写框架

  用法：
    npx solution-master              安装到当前项目的 .claude/（项目模式）
    npx solution-master --global     安装到 ~/.claude/（全局模式）
    npx solution-master --uninstall  从当前项目 .claude/ 卸载
    npx solution-master --uninstall --global
                                     从 ~/.claude/ 卸载
    npx solution-master --help       显示帮助
    npx solution-master --version    显示版本

  说明：
    项目模式：把 skills/ agents/ hooks/ 复制到 <project>/.claude/ 下，
              并在 <project>/.claude/settings.json 中注册 SessionStart hook。
    全局模式：同上，但目标为 ~/.claude/，对所有项目生效。hook 脚本
              自身有项目门禁，只在有 drafts/ 或 docs/specs/ 的项目中触发。

    同一个 settings.json 中原有的 permissions、其他 hook、env 等配置
    都会被保留，修改前会备份到 settings.json.bak.<timestamp>。

  推荐（更强的安装方式）：使用 Claude Code plugin 系统：
    cd /your/sm/project   # 需含 drafts/ 或 docs/specs/ 目录
    claude                # SessionStart hook 才会触发项目门禁
    /plugin marketplace add /path/to/solution-master
    /plugin install solution-master@solution-master
    /reload-plugins
    （这样会使用 \${CLAUDE_PLUGIN_ROOT}，无需复制文件）

  项目：${PKG.description}
`);
}

function copyDir(src, dest) {
  if (!existsSync(src)) return;
  mkdirSync(dest, { recursive: true });
  cpSync(src, dest, { recursive: true });
}

function timestamp() {
  // Millisecond granularity to prevent backup filename collisions on
  // rapid successive installs (e.g. in tests or scripted setup).
  const d = new Date();
  const pad = (n, len = 2) => String(n).padStart(len, '0');
  return (
    `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}` +
    `-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}` +
    `-${pad(d.getMilliseconds(), 3)}`
  );
}

function loadSettings(path) {
  if (!existsSync(path)) return {};
  try {
    const raw = readFileSync(path, 'utf8');
    if (!raw.trim()) return {};
    return JSON.parse(raw);
  } catch (err) {
    console.error(`  ⚠️  无法解析 ${path}：${err.message}`);
    console.error(`      为安全起见，本次安装不会修改该文件。请手动修复后重试。`);
    process.exit(2);
  }
}

function saveSettings(path, obj) {
  writeFileSync(path, JSON.stringify(obj, null, 2) + '\n', 'utf8');
}

function backupSettings(path) {
  if (!existsSync(path)) return null;
  const bak = `${path}.bak.${timestamp()}`;
  copyFileSync(path, bak);
  return bak;
}

function buildHookEntry(hookDir) {
  // Use run-hook.cmd as a cross-platform wrapper. On Unix it's a bash
  // polyglot that execs the named script; on Windows it finds Git Bash
  // and runs the script there. This matches the plugin-mode hooks.json
  // command format and avoids Claude Code's Windows auto-detection
  // quirk where extensionless commands get "bash" prepended.
  const wrapper = join(hookDir, 'run-hook.cmd');
  return {
    SessionStart: [
      {
        matcher: 'startup|clear|compact',
        hooks: [
          {
            type: 'command',
            command: `"${wrapper}" session-start`,
            async: false,
            _owner: HOOK_MARKER,
          },
        ],
      },
    ],
  };
}

function mergeHooks(settings, newHooks) {
  settings.hooks = settings.hooks || {};
  for (const eventName of Object.keys(newHooks)) {
    // Remove existing SM-owned entries for this event (by _owner marker)
    const existing = Array.isArray(settings.hooks[eventName])
      ? settings.hooks[eventName]
      : [];
    const keptGroups = [];
    for (const group of existing) {
      const hooks = Array.isArray(group?.hooks) ? group.hooks : [];
      const filtered = hooks.filter((h) => h?._owner !== HOOK_MARKER);
      if (filtered.length > 0) {
        keptGroups.push({ ...group, hooks: filtered });
      } else if (hooks.length === 0) {
        keptGroups.push(group); // preserve empty group structure if pre-existing
      }
    }
    settings.hooks[eventName] = [...keptGroups, ...newHooks[eventName]];
  }
}

function removeOwnedHooks(settings) {
  if (!settings.hooks) return;
  for (const eventName of Object.keys(settings.hooks)) {
    const groups = Array.isArray(settings.hooks[eventName])
      ? settings.hooks[eventName]
      : [];
    const cleaned = [];
    for (const group of groups) {
      const hooks = Array.isArray(group?.hooks) ? group.hooks : [];
      const filtered = hooks.filter((h) => h?._owner !== HOOK_MARKER);
      if (filtered.length > 0) {
        cleaned.push({ ...group, hooks: filtered });
      }
    }
    if (cleaned.length > 0) {
      settings.hooks[eventName] = cleaned;
    } else {
      delete settings.hooks[eventName];
    }
  }
  if (Object.keys(settings.hooks).length === 0) {
    delete settings.hooks;
  }
}

function resolveTarget(isGlobal) {
  const claudeDir = isGlobal
    ? resolve(homedir(), '.claude')
    : resolve(process.cwd(), '.claude');
  return {
    claudeDir,
    skillsDest: join(claudeDir, 'skills'),
    agentsDest: join(claudeDir, 'agents'),
    hooksDest: join(claudeDir, 'hooks'),
    settingsPath: join(claudeDir, 'settings.json'),
  };
}

function install(isGlobal) {
  const scope = isGlobal ? '全局' : '项目';
  console.log(`\n  solution-master v${PKG.version} — ${scope}模式安装\n`);

  if (!existsSync(SKILLS_SRC) || !existsSync(AGENTS_SRC) || !existsSync(HOOKS_SRC)) {
    console.error('  ❌ 源目录缺失（skills / agents / hooks），请重新安装 solution-master。');
    process.exit(1);
  }

  const { claudeDir, skillsDest, agentsDest, hooksDest, settingsPath } =
    resolveTarget(isGlobal);

  mkdirSync(claudeDir, { recursive: true });

  console.log(`  目标目录：${claudeDir}`);
  console.log(`  复制 skills/ → ${skillsDest}`);
  copyDir(SKILLS_SRC, skillsDest);
  console.log(`  复制 agents/ → ${agentsDest}`);
  copyDir(AGENTS_SRC, agentsDest);
  console.log(`  复制 hooks/ → ${hooksDest}`);
  copyDir(HOOKS_SRC, hooksDest);

  // Ensure hook scripts are executable
  for (const name of ['session-start', 'run-hook.cmd']) {
    const p = join(hooksDest, name);
    if (existsSync(p)) {
      try {
        chmodSync(p, 0o755);
      } catch (e) {
        console.warn(`  ⚠️  无法设置 hook 脚本执行权限 ${name}：${e.message}`);
      }
    }
  }

  // Merge settings.json
  const bak = backupSettings(settingsPath);
  if (bak) {
    console.log(`  已备份 settings.json → ${bak}`);
  }
  const settings = loadSettings(settingsPath);
  mergeHooks(settings, buildHookEntry(hooksDest));
  saveSettings(settingsPath, settings);
  console.log(`  已更新 settings.json，注册 SessionStart hook`);

  console.log(`\n  ✅ 安装完成。`);
  console.log(
    `  重启 Claude Code 即可生效。${isGlobal ? '全局' : '项目'}范围内的 SM 项目会自动启用铁律注入。\n`
  );
}

function uninstall(isGlobal) {
  const scope = isGlobal ? '全局' : '项目';
  console.log(`\n  solution-master v${PKG.version} — ${scope}模式卸载\n`);

  const { claudeDir, skillsDest, agentsDest, hooksDest, settingsPath } =
    resolveTarget(isGlobal);

  if (!existsSync(claudeDir)) {
    console.log(`  ${claudeDir} 不存在，无需卸载。`);
    return;
  }

  // Derive the list of skill/agent names from the source package so we
  // never leave stray directories behind when the set of skills changes.
  const smSkillDirs = existsSync(SKILLS_SRC)
    ? readdirSync(SKILLS_SRC).filter((name) => {
        try {
          return statSync(join(SKILLS_SRC, name)).isDirectory();
        } catch {
          return false;
        }
      })
    : [];
  const smAgents = existsSync(AGENTS_SRC)
    ? readdirSync(AGENTS_SRC).filter((name) => name.endsWith('.md'))
    : [];

  for (const name of smSkillDirs) {
    const p = join(skillsDest, name);
    if (existsSync(p)) {
      rmSync(p, { recursive: true, force: true });
      console.log(`  ✂ 移除 skills/${name}`);
    }
  }
  for (const name of smAgents) {
    const p = join(agentsDest, name);
    if (existsSync(p)) {
      rmSync(p, { force: true });
      console.log(`  ✂ 移除 agents/${name}`);
    }
  }

  // Remove hook scripts we own
  for (const name of ['session-start', 'run-hook.cmd', 'hooks.json', 'hooks-cursor.json']) {
    const p = join(hooksDest, name);
    if (existsSync(p)) {
      rmSync(p, { force: true });
      console.log(`  ✂ 移除 hooks/${name}`);
    }
  }

  // Remove SM hook entries from settings.json
  if (existsSync(settingsPath)) {
    const bak = backupSettings(settingsPath);
    if (bak) console.log(`  已备份 settings.json → ${bak}`);
    const settings = loadSettings(settingsPath);
    removeOwnedHooks(settings);
    saveSettings(settingsPath, settings);
    console.log(`  已从 settings.json 清理 SM hook 条目（其他配置保留）`);
  }

  console.log(`\n  ✅ 卸载完成。\n`);
}

function main() {
  const args = process.argv.slice(2);
  const hasFlag = (f) => args.includes(f);

  if (hasFlag('--help') || hasFlag('-h')) {
    showHelp();
    return;
  }
  if (hasFlag('--version') || hasFlag('-v')) {
    console.log(PKG.version);
    return;
  }

  const isGlobal = hasFlag('--global');
  const isUninstall = hasFlag('--uninstall');

  try {
    if (isUninstall) {
      uninstall(isGlobal);
    } else {
      install(isGlobal);
    }
  } catch (err) {
    console.error(`  ❌ 失败：${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  }
}

main();
