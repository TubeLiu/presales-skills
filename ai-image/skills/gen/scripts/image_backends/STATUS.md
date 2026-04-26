# Backend API spec & helper application status (F-054)

记录每个 backend 的 API 规范对齐状态与 F-030 retry helper 应用情况，便于发版前快速 audit。
所有 13 backend 当前均接入 F-012 `sanitize_error()`（API key 脱敏），下表不再重复记录该列。

| backend file | provider | API spec 已对齐（commit 76a29ff 或更新）| F-030 helper 已应用 | 备注 |
|---|---|---|---|---|
| `backend_volcengine.py` | ark / volcengine（火山方舟）| ✓（commit 76a29ff）| ✓ `get_timeout()` | 高频，default_provider 之一 |
| `backend_qwen.py` | qwen / dashscope（阿里云通义）| ✓ | ✓ `get_timeout()` | 高频，文件名为 qwen 不是 dashscope |
| `backend_gemini.py` | Google Gemini | ✓（最新 model：gemini-3.1-flash-image-preview）| ✓ import only（用 google-genai SDK，无 requests 直调）| 高频 |
| `backend_openai.py` | OpenAI / OpenAI-compatible | ✓（commit 76a29ff）| ✗ TODO（用 openai SDK）| 中频 |
| `backend_stability.py` | Stability AI | ✓（v2beta endpoint）| ✗ TODO | 中频 |
| `backend_bfl.py` | Black Forest Labs FLUX | ✓ | ✗ TODO | 中频 |
| `backend_minimax.py` | MiniMax | ✓ | ✗ TODO | 低频 |
| `backend_replicate.py` | Replicate | ✗ 待核对 | ✗ TODO | 低频 |
| `backend_ideogram.py` | Ideogram | ✗ 待核对 | ✗ TODO | 低频 |
| `backend_zhipu.py` | 智谱 GLM-Image | ✗ 待核对 | ✗ TODO | 低频 |
| `backend_siliconflow.py` | SiliconFlow | ✗ 待核对 | ✗ TODO | 低频 |
| `backend_fal.py` | fal.ai | ✗ 待核对 | ✗ TODO | 低频 |
| `backend_openrouter.py` | OpenRouter | ✗ 待核对 | ✗ TODO | 低频 |

## TODO 清单

- [ ] F-030 应用到剩余 10 个 backend（每个文件顶部已有 `# TODO(F-030)` 注释占位）
- [ ] API spec 重新核对剩余 7 个 backend（建议每季度一次，以 GitHub Release 节奏对齐）

## 核对方法

```bash
# 列出所有 backend 当前 timeout / retry 模式
grep -n 'timeout=\|retry_delay\|get_timeout\|retry_delay_from_header' \
  ai-image/scripts/image_backends/backend_*.py
```
