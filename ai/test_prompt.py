#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GLM模型提示词功能 - 建筑行业数据转换
"""

from glm_agent import GLMAgent


def test_construction_data_transformation():
    """测试建筑行业数据转换提示词"""
    print("🏗️ 测试建筑行业数据转换提示词")
    print("=" * 60)

    # 建筑行业数据转换提示词
    construction_prompt = """# AI JSON Data Transformation Prompt

## 任务目标
将提供的建筑行业人才供求文本数据，转化为标准的JSON数组格式。此JSON应便于直接或经过最少处理后导入PostgreSQL数据库。

## 输出格式要求
1.  **最终输出必须是且仅是**一个包含对象的JSON数组 (`[{}, {}, ...]`)。
2.  **严格遵循下方提供的**JSON字段规范**。
3.  **不要包含任何markdown代码块标记** (如 ```json 或 ```)，直接输出纯JSON。
4.  不要包含任何解释性文字，只输出JSON数组。
5.  价格单位默认为**万元/年** (`w`)，除非文本明确提到是**月**或**元**。
6.  无法确定或不包含的信息，该字段应为 **null**。

## JSON 字段规范 (PostgreSQL Column Mapping Reference)

| JSON Key | Description (PostgreSQL Data Type Hint) |
| :--- | :--- |
| `deal_type` | **交易类型**: '出' (供)/'寻' (求)/'收' (求)。 (`TEXT`) |
| `main_certificate` | **核心证书**: 证书级别和名称。 (`TEXT`) |
| `aux_certificate` | **辅助证书**: 搭配的B证、其他专业、职称等。 (`TEXT`) |
| `social_security` | **社保情况**: '三唯一', '社保唯一', '退休', '不转社保', '社保停了' 等。 (`TEXT`) |
| `cooperation_req` | **配合要求**: '可出场', '配合出场刷脸', '不出场', '考勤' 等。 (`TEXT`) |
| `target_location` | **目标区域**: 具体的省、市、区或要求（如'省内找', '丽水人'）。 (`TEXT`) |
| `price_w` | **价格**: 转换为数值型。单位：**万元**。1000元/月应计算转换为年价（0.12）。 (`NUMERIC`) |
| `price_cycle` | **价格周期**: 记录价格的实际周期，如 '年', '月'。 (`TEXT`) |
| `notes` | **备注/其他信息**: 无法归类的细节、特殊时限、年龄要求等。 (`TEXT`) |

## 价格转换规则
* **W/年 (万元/年):** 直接使用数值。
* **W/月 (万元/月):** 转换为年价：`价格 * 12`。
* **元/月:** 转换为年价（万元）：`(价格 * 12) / 10000`。

## 原始数据 (Data to Process)
---

"""

    # 测试数据
    test_data = """寻二级建造师机电，浙江绍兴，价格2万，配合出场，社保不转
寻一级建造师建筑，浙江杭州，价格4万/年，可出场，三唯一
出二级建造师市政，江苏南京，退休人员，价格1.5万，不用配合
寻二级建造师水利+中级职称，浙江宁波，价格3万/年，配合考勤，社保唯一"""

    try:
        # 创建AI Agent
        agent = GLMAgent(api_key="9ea7ae31c7864b8a9e696ecdbd062820.KBM8KO07X9dgTjRi")

        # 构建完整的提示词
        full_prompt = construction_prompt + test_data

        print("📝 输入的测试数据:")
        print(test_data)
        print("\n" + "="*60)
        print("🤖 AI处理结果:")

        # 调用AI进行处理
        response = agent.chat(
            full_prompt,
            session_id="construction_test",
            temperature=0.1  # 使用较低的温度以确保输出的准确性
        )

        print("🔍 原始AI响应:")
        print(response)
        print("\n" + "="*60)

        # 清理响应，移除可能的markdown标记
        cleaned_response = response.strip()

        # 移除 ```json 和 ``` 标记
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()

        print("🧹 清理后的响应:")
        print(cleaned_response)
        print("\n" + "="*60)

        # 验证输出格式
        try:
            import json
            parsed_json = json.loads(cleaned_response)
            if isinstance(parsed_json, list):
                print(f"✅ 输出格式正确：JSON数组，包含 {len(parsed_json)} 个对象")

                # 显示解析结果摘要
                for i, item in enumerate(parsed_json, 1):
                    print(f"📋 记录 {i}:")
                    print(f"   交易类型: {item.get('deal_type')}")
                    print(f"   核心证书: {item.get('main_certificate')}")
                    print(f"   辅助证书: {item.get('aux_certificate')}")
                    print(f"   目标区域: {item.get('target_location')}")
                    print(f"   价格: {item.get('price_w')}万/{item.get('price_cycle')}")
                    print(f"   配合要求: {item.get('cooperation_req')}")
                    print(f"   社保情况: {item.get('social_security')}")
                    print(f"   备注: {item.get('notes')}")
                    print()

                # 数据质量分析
                print("📊 数据质量分析:")
                total_records = len(parsed_json)
                null_fields_count = 0

                for item in parsed_json:
                    for value in item.values():
                        if value is None:
                            null_fields_count += 1

                total_possible_fields = total_records * 9  # 9个字段
                completeness = ((total_possible_fields - null_fields_count) / total_possible_fields) * 100

                print(f"   总记录数: {total_records}")
                print(f"   字段完整性: {completeness:.1f}%")
                print(f"   空值字段数: {null_fields_count}")

            else:
                print("❌ 输出格式错误：不是JSON数组")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print("🔍 可能的问题:")
            print("   1. AI返回了非纯JSON格式")
            print("   2. JSON格式有语法错误")
            print("   3. 包含额外的文字说明")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    """主测试函数"""
    print("🚀 GLM模型提示词测试")
    print("🏗️ 建筑行业人才数据转换测试")
    print("=" * 60)

    test_construction_data_transformation()

    print("\n✨ 测试完成！")


if __name__ == "__main__":
    main()