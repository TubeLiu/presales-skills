#!/bin/bash
# 端到端测试实施验证脚本

echo "========================================="
echo "端到端测试重构实施验证"
echo "========================================="
echo ""

# 1. 检查文件存在性
echo "1. 检查文件存在性..."
files=(
    "validators/consistency_validator.py"
    "validators/image_quality_validator.py"
    "validators/content_professionalism_validator.py"
    "test_parameters.py"
    "README.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
    fi
done
echo ""

# 2. 编译检查
echo "2. 编译检查..."
python3 -m py_compile validators/consistency_validator.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ consistency_validator.py"
else
    echo "  ❌ consistency_validator.py (编译失败)"
fi

python3 -m py_compile validators/image_quality_validator.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ image_quality_validator.py"
else
    echo "  ❌ image_quality_validator.py (编译失败)"
fi

python3 -m py_compile validators/content_professionalism_validator.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ content_professionalism_validator.py"
else
    echo "  ❌ content_professionalism_validator.py (编译失败)"
fi

python3 -m py_compile test_parameters.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ test_parameters.py"
else
    echo "  ❌ test_parameters.py (编译失败)"
fi
echo ""

# 3. 导入检查
echo "3. 导入检查..."
python3 -c "from validators.consistency_validator import ConsistencyValidator" 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ ConsistencyValidator"
else
    echo "  ❌ ConsistencyValidator (导入失败)"
fi

python3 -c "from validators.image_quality_validator import ImageQualityValidator" 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ ImageQualityValidator"
else
    echo "  ❌ ImageQualityValidator (导入失败)"
fi

python3 -c "from validators.content_professionalism_validator import ContentProfessionalismValidator" 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ ContentProfessionalismValidator"
else
    echo "  ❌ ContentProfessionalismValidator (导入失败)"
fi
echo ""

# 4. 统计代码行数
echo "4. 代码统计..."
echo "  新增验证器:"
wc -l validators/consistency_validator.py validators/image_quality_validator.py validators/content_professionalism_validator.py | tail -1
echo "  参数测试:"
wc -l test_parameters.py
echo ""

echo "========================================="
echo "验证完成！"
echo "========================================="
