import sys
import os
# Add path to backend
sys.path.append(os.path.join(os.getcwd(), 'integrated_system', 'backend'))

from ai_service import ai_service

def test():
    print("Testing NVIDIA AI Service...")
    
    # 1. Test Quality (Logic Model: GLM-4)
    print("\n[1] Testing Quality Assessment (GLM-4)...")
    text = "这是一个测试片段。主角林凡站在山巅，看着云海翻腾，心中万千感慨。风吹过他的衣角，猎猎作响。"
    res = ai_service.assess_quality(text)
    print(f"Result: {res}")
    
    # 2. Test SWOT (Logic Model: GLM-4)
    print("\n[2] Testing SWOT Report (GLM-4)...")
    title = "绝世神豪"
    abstract = "从今天开始，我要做世界首富。系统在手，天下我有。只要花钱就能变强，这日子真是枯燥且乏味。"
    res = ai_service.generate_swot_report(title, abstract)
    print(f"Summary: {res.get('summary')}")
    
    # 3. Test Chat (Chat Model: MiniMax)
    print("\n[3] Testing Chat (MiniMax)...")
    profile = {"name": "林凡", "persona": "高冷的修仙者，语气淡漠，不把凡人放在眼里", "scenario": "凡人误入仙山"}
    history = []
    res = ai_service.chat_with_character(profile, history, "你好，请问这里是哪里？")
    print(f"Response: {res}")

if __name__ == "__main__":
    test()
