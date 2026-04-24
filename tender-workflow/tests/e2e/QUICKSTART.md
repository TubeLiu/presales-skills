# 端到端测试快速开始

## 前置条件

1. **测试文件**：确保测试文件存在
   ```bash
   ls -lh /home/ubuntu/testfile2.docx
   ```

2. **Skill 链接**：确保 skill 软连接正确
   ```bash
   ls -la ~/skills/ | grep -E "(taa|taw)"
   ```

3. **依赖安装**：确保依赖已安装
   ```bash
   pip list | grep -E "(pytest|python-docx|PyYAML)"
   ```

## 快速测试

### 1. 验证器单元测试（推荐先运行）

```bash
cd /home/ubuntu/tender-workflow
python3 tests/e2e/test_validators.py
```

预期输出：
```
============================================================
验证器模块单元测试
============================================================
测试 DOCX 解析器...
  ✅ DOCX 解析器测试通过
测试 taa 验证器...
  ✅ taa 验证器测试通过
测试 taw 验证器...
  ✅ taw 验证器测试通过
测试质量检查器...
  ✅ 质量检查器测试通过
============================================================
✅ 所有测试通过
============================================================
```

### 2. 完整端到端测试

```bash
cd /home/ubuntu/tender-workflow
python3 -m pytest tests/e2e/test_e2e_workflow.py -v -s
```

测试流程：
1. ✅ test_1_taa_execution - 执行 taa（约 2-5 分钟）
2. ✅ test_2_taa_analysis_quality - 验证分析报告
3. ✅ test_3_taa_outline_quality - 验证投标大纲
4. ✅ test_4_taw_execution - 执行 taw（约 10-30 分钟，3 个章节）
5. ✅ test_5_taw_content_quality - 验证章节内容
6. ⏭️ test_6_trv_integration - trv 审核（跳过）
7. ✅ test_7_generate_final_report - 生成最终报告

### 3. 查看测试报告

```bash
# 查看最新报告
ls -lt tests/e2e/reports/

# 查看 taa 验证报告
cat tests/e2e/reports/taa_validation_*.md | head -50

# 查看 taw 验证报告
cat tests/e2e/reports/taw_validation_*.md | head -50

# 查看最终测试报告
cat tests/e2e/reports/e2e_test_report_*.md
```

## 分步测试（推荐用于调试）

### 仅测试 taa 流程

```bash
# Step 1-3: taa 执行和验证
python3 -m pytest tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_1_taa_execution -v -s
python3 -m pytest tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_2_taa_analysis_quality -v -s
python3 -m pytest tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_3_taa_outline_quality -v -s
```

### 仅测试 taw 流程（需要先运行 taa）

```bash
# Step 4-5: taw 执行和验证
python3 -m pytest tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_4_taw_execution -v -s
python3 -m pytest tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_5_taw_content_quality -v -s
```

### 生成最终报告

```bash
python3 -m pytest tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_7_generate_final_report -v -s
```

## 预期结果

### 成功输出示例

```
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_1_taa_execution PASSED
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_2_taa_analysis_quality PASSED
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_3_taa_outline_quality PASSED
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_4_taw_execution PASSED
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_5_taw_content_quality PASSED
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_6_trv_integration SKIPPED
tests/e2e/test_e2e_workflow.py::TestE2EWorkflow::test_7_generate_final_report PASSED

========================== 6 passed, 1 skipped in 1200.00s ==========================
```

### 生成的文件

```
output/
├── 招标分析报告_<timestamp>.md
└── 投标文件大纲_<timestamp>.docx

drafts/
├── 1.2_<章节名>.docx
├── 1.3_<章节名>.docx
└── 1.10_<章节名>.docx

tests/e2e/reports/
├── taa_validation_<timestamp>.md
├── outline_validation_<timestamp>.md
├── taw_validation_<timestamp>.md
└── e2e_test_report_<timestamp>.md
```

## 故障排查

### 问题 1：找不到测试文件

```bash
# 检查文件是否存在
ls -lh /home/ubuntu/testfile2.docx

# 如果不存在，修改测试文件路径
# 编辑 tests/e2e/test_e2e_workflow.py
# 修改 TENDER_FILE = Path('/home/ubuntu/testfile2.docx')
```

### 问题 2：skill 执行失败

```bash
# 检查 skill 链接
ls -la ~/skills/

# 手动测试 skill
claude skill taa /home/ubuntu/testfile2.docx --vendor 灵雀云
claude skill taw output/ --chapter 1.2 --search-tool auto
```

### 问题 3：DOCX 解析失败

```bash
# 检查 python-docx 安装
pip list | grep python-docx

# 重新安装
pip install python-docx --break-system-packages
```

### 问题 4：pytest 找不到模块

```bash
# 检查 Python 路径
python3 -c "import sys; print('\n'.join(sys.path))"

# 确保 conftest.py 存在
cat tests/conftest.py
```

## 下一步

1. **查看测试报告**：分析发现的问题
2. **修复问题**：根据建议修复 taa/taw 输出
3. **重新测试**：验证修复效果
4. **持续改进**：根据测试结果优化 skill

## 参考文档

- 详细使用指南：`tests/e2e/README.md`
- 数据格式规范：`docs/data-format.md`
- taa Skill 文档：`skills/taa/SKILL.md`
- taw Skill 文档：`skills/taw/SKILL.md`
