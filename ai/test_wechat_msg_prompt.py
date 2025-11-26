#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GLM模型微信消息处理功能 - 建筑行业数据转换
从外部文件加载微信消息处理提示词
"""

from glm_agent import GLMAgent


def load_prompt_from_file(prompt_file: str = "wechat_msg_prompt.md") -> str:
    """从文件加载提示词"""
    import os
    prompt_path = os.path.join(os.path.dirname(__file__), prompt_file)

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 提示词文件 {prompt_path} 不存在")
        return ""
    except Exception as e:
        print(f"❌ 读取提示词文件失败: {e}")
        return ""


def test_wechat_message_processing():
    """测试微信消息建筑行业数据转换功能"""
    print("🏗️ 测试微信消息建筑行业数据转换功能")
    print("=" * 60)

    # 从文件加载建筑行业数据转换提示词
    construction_prompt = load_prompt_from_file("wechat_msg_prompt.md")

    if not construction_prompt:
        print("❌ 无法加载提示词，测试终止")
        return

    print("📝 已从 wechat_msg_prompt.md 文件加载提示词")
    print()

    # 测试数据
    test_data = """寻二级建造师机电，浙江绍兴，价格2万，配合出场，社保不转
寻一级建造师建筑，浙江杭州，价格4万/年，可出场，三唯一
出二级建造师市政，江苏南京，退休人员，价格1.5万，不用配合
寻二级建造师水利+中级职称，浙江宁波，价格3万/年，配合考勤，社保唯一"""

    try:
        # 创建AI Agent
        agent = GLMAgent(api_key="9ea7ae31c7864b8a9e696ecdbd062820.KBM8KO07X9dgTjRi")

        print("📝 输入的测试数据:")
        print(test_data)
        print("\n" + "="*60)
        print("🤖 AI处理结果:")

        # 调用AI进行处理 - 使用系统提示词
        response = agent.chat(
            test_data,  # 用户消息：测试数据
            session_id="construction_test",
            system_prompt=construction_prompt,  # 系统提示词：完整的提示词
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
                    print(f"   交易类型: {item.get('type')}")
                    print(f"   证书信息: {item.get('certificate')}")
                    print(f"   社保情况: {item.get('social_security')}")
                    print(f"   地点: {item.get('location')}")
                    print(f"   价格: {item.get('price')}")
                    print(f"   其他信息: {item.get('other_info')}")
                    print(f"   原始信息: {item.get('original_info')}")
                    print()

                # 数据质量分析
                print("📊 数据质量分析:")
                total_records = len(parsed_json)
                null_fields_count = 0

                for item in parsed_json:
                    for value in item.values():
                        if value is None:
                            null_fields_count += 1

                total_possible_fields = total_records * 7  # 7个字段
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
    print("🚀 GLM模型微信消息处理测试")
    print("🏗️ 建筑行业人才数据转换测试")
    print("=" * 60)

    test_wechat_message_processing()

    print("\n✨ 测试完成！")


if __name__ == "__main__":
    main()