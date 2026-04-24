# Product Index V2 使用指南

## 概述

Product Index V2 采用三层索引架构，大幅减少 token 消耗：

- **L0 层**：快速路由索引（~2KB）- 11个分类概览
- **L1 层**：分类索引（每个 0.5-19KB）- 每个分类的条目摘要
- **L2 层**：完整详情（按需加载）- 完整字段

## 文件结构

```
Local-KnowledgeBase/.index/
├── product_l0.yaml                          # L0 快速路由（必须加载）
├── product_l1_platform_lifecycle.yaml       # L1 分类索引
├── product_l1_container_management.yaml
├── product_l1_networking.yaml
├── ... (共11个L1文件)
├── product_l2_platform_lifecycle.yaml       # L2 完整详情
├── product_l2_container_management.yaml
├── product_l2_networking.yaml
└── ... (共11个L2文件)
```

## 分类列表

| 分类名称 | 条目数 | L1大小 | L2大小 | 核心关键词 |
|---------|-------|--------|--------|-----------|
| Platform Lifecycle | 45 | 8.5KB | 17KB | install, upgrade, lifecycle, deployment, disaster |
| Container Management | 126 | 19KB | 35KB | kubernetes, container, pod, cluster, workload |
| Multi-Cluster | 3 | 0.5KB | 1KB | multi-cluster, federation, global |
| Networking | 46 | 6.6KB | 12KB | network, ingress, service, load balancer |
| Storage | 13 | 2.1KB | 4.4KB | storage, volume, pv, pvc |
| Security & Access | 24 | 3.8KB | 7KB | security, rbac, authentication, policy |
| Observability | 19 | 2.8KB | 5KB | monitoring, logging, metrics, alert |
| DevOps & CI/CD | 59 | 9.4KB | 18KB | cicd, pipeline, git, build, deploy |
| AI & GPU | 25 | 3.5KB | 6.2KB | ai, gpu, machine learning, model |
| Service Mesh & Microservices | 15 | 2.2KB | 3.7KB | service mesh, istio, microservice |
| Other | 97 | 14KB | 26KB | 其他未分类功能 |

## 加载策略

### 策略 1：最小加载（推荐）

**适用场景**：章节内容主题明确，只需要特定分类的产品能力

**步骤**：
1. 加载 L0 索引（2KB）
2. 根据章节内容主题，匹配 1-2 个相关分类
3. 只加载匹配分类的 L1 文件（0.5-19KB）
4. 如需详细参数，再加载对应的 L2 文件

**示例**：
```yaml
# 章节：5.3 容器编排与管理
# 匹配分类：Container Management
# 加载文件：
#   - product_l0.yaml (2KB)
#   - product_l1_container_management.yaml (19KB)
# 总计：21KB（vs 原 149KB，节省 86%）
```

### 策略 2：多分类加载

**适用场景**：章节涉及多个技术领域

**步骤**：
1. 加载 L0 索引（2KB）
2. 匹配 2-3 个相关分类
3. 加载所有匹配分类的 L1 文件

**示例**：
```yaml
# 章节：5.5 DevOps 平台与 AI 能力
# 匹配分类：DevOps & CI/CD, AI & GPU
# 加载文件：
#   - product_l0.yaml (2KB)
#   - product_l1_devops_and_ci_cd.yaml (9.4KB)
#   - product_l1_ai_and_gpu.yaml (3.5KB)
# 总计：15KB（vs 原 149KB，节省 90%）
```

### 策略 3：全量加载（兜底）

**适用场景**：章节内容不明确，或需要全面评估

**步骤**：
1. 加载 L0 索引（2KB）
2. 加载所有 L1 文件（~73KB）

**总计**：75KB（vs 原 149KB，节省 50%）

## 在 taa SKILL.md 中使用

### 修改前（旧逻辑）

```markdown
**Step 2：解析产品能力来源**

若 --product 提供 → 解析指定文件 → PRODUCT_INDEX
否则若 Local-KnowledgeBase/.index/product.yaml 存在 → 加载默认索引
否则 → PRODUCT_INDEX = null
```

### 修改后（新逻辑）

```markdown
**Step 2：解析产品能力来源（三层索引）**

1. 检测索引版本：
   - 若 Local-KnowledgeBase/.index/product_l0.yaml 存在 → 使用 V2 三层索引
   - 否则若 Local-KnowledgeBase/.index/product.yaml 存在 → 使用 V1 单文件索引（向后兼容）
   - 否则 → PRODUCT_INDEX = null

2. V2 三层索引加载策略：
   - 默认：只加载 L0 索引（2KB）
   - 在 M4（技术要求评估）阶段：
     a. 读取招标文件的技术要求章节
     b. 提取核心技术关键词（如：容器、DevOps、AI、网络、存储等）
     c. 匹配 L0 中的分类（根据 core_keywords）
     d. 加载匹配分类的 L1 文件（1-3个，总计 5-30KB）
   - 如需详细参数（如评分标准中要求具体参数），再加载对应 L2 文件

3. 输出加载摘要：
   ```
   产品能力索引加载：
   • 版本：V2 三层索引
   • L0 分类：11 个
   • 已加载分类：Container Management (126条), DevOps & CI/CD (59条)
   • Token 消耗：~21KB（vs V1 149KB，节省 86%）
   ```
```

## 在 taw SKILL.md 中使用

taw 当前不直接使用 product.yaml，无需修改。

## 重新生成索引

```bash
# 重新生成三层索引
python skills/taa/tools/indexer_v2.py --input Local-KnowledgeBase/.index/product.yaml --output Local-KnowledgeBase/.index/

# 或使用 taa skill
/taa --build-index

# 指定 Local-KnowledgeBase 目录（skill 独立运行）
python skills/taa/tools/indexer_v2.py --input /path/to/Local-KnowledgeBase/.index/product.yaml
```

## Token 节省估算

| 场景 | V1 单文件 | V2 最小加载 | V2 多分类 | V2 全量 |
|------|----------|------------|----------|---------|
| 单一技术领域 | 149KB | 21KB (86%↓) | 15KB (90%↓) | 75KB (50%↓) |
| 多技术领域 | 149KB | - | 30KB (80%↓) | 75KB (50%↓) |
| 全面评估 | 149KB | - | - | 75KB (50%↓) |

**平均节省**：70-90% token 消耗
