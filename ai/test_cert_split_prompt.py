#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GLM模型证书拆分功能
从外部文件加载证书拆分提示词
"""

from glm_agent import GLMAgent


def load_prompt_from_file(prompt_file: str = "cert_split_prompt.md") -> str:
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


def test_certificate_splitting():
    """测试证书拆分功能"""
    print("📋 测试证书拆分功能")
    print("=" * 60)

    # 从文件加载证书拆分提示词
    cert_split_prompt = load_prompt_from_file("cert_split_prompt.md")

    if not cert_split_prompt:
        print("❌ 无法加载提示词，测试终止")
        return

    print("📝 已从 cert_split_prompt.md 文件加载提示词")
    print()

    # 测试数据 - 单行输入，模拟实际使用场景
    test_line = "一级公路+水利+二级市政+中工带B"

    try:
        # 创建AI Agent
        agent = GLMAgent(api_key="9ea7ae31c7864b8a9e696ecdbd062820.KBM8KO07X9dgTjRi")

        print(f"📝 输入数据: {test_line}")
        print("-" * 40)

        # 调用AI进行处理 - 使用系统提示词
        response = agent.chat(
            test_line,  # 用户消息：单行测试数据
            session_id="cert_split_test",
            system_prompt=cert_split_prompt,  # 系统提示词：证书拆分提示词
            temperature=0.1  # 使用较低的温度以确保输出的准确性
        )

        print("🔍 AI响应:")
        print(response)

        # 清理响应，移除可能的markdown标记
        cleaned_response = response.strip()

        # 移除 ```python 和 ``` 标记
        if cleaned_response.startswith('```python'):
            cleaned_response = cleaned_response[9:]
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()

        print("🧹 清理后的响应:")
        print(cleaned_response)
        print()

        # 验证输出格式
        try:
            import ast
            # 使用ast.literal_eval安全地解析Python列表
            parsed_list = ast.literal_eval(cleaned_response)

            if isinstance(parsed_list, list):
                # 如果是二维列表（如[["cert1", "cert2"]]），取第一个子列表
                if len(parsed_list) > 0 and isinstance(parsed_list[0], list):
                    certs = parsed_list[0]
                    print(f"✅ 输出格式正确：二维列表，提取第一组证书")
                else:
                    # 如果是一维列表（如["cert1", "cert2"]），直接使用
                    certs = parsed_list
                    print(f"✅ 输出格式正确：一维列表")

                print(f"📋 解析结果：共 {len(certs)} 个证书")
                for i, cert in enumerate(certs, 1):
                    print(f"   证书 {i}: {cert}")

                # 数据质量分析
                print("\n📊 数据质量分析:")
                print(f"   输入证书组合数: 1")
                print(f"   输出证书数量: {len(certs)}")

                # 统计各类证书
                cert_types = {}
                for cert in certs:
                    if '建造师' in cert:
                        cert_types['建造师'] = cert_types.get('建造师', 0) + 1
                    elif '工程师' in cert and '建造师' not in cert:
                        cert_types['职称/工程师'] = cert_types.get('职称/工程师', 0) + 1
                    elif '证' in cert and '工程师' not in cert:
                        cert_types['安全证书'] = cert_types.get('安全证书', 0) + 1
                    else:
                        cert_types['其他'] = cert_types.get('其他', 0) + 1

                print("\n📋 证书类型分布:")
                for cert_type, count in cert_types.items():
                    print(f"   {cert_type}: {count}个")

            else:
                print("❌ 输出格式错误：不是Python列表")

        except (ValueError, SyntaxError) as e:
            print(f"❌ Python列表解析失败: {e}")
        except Exception as e:
            print(f"❌ 解析时发生未知错误: {e}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    """主测试函数"""
    print("🚀 GLM模型证书拆分测试")
    print("📋 建筑行业证书标准化处理测试")
    print("=" * 60)

    test_certificate_splitting()

    print("\n✨ 测试完成！")


if __name__ == "__main__":
    main()