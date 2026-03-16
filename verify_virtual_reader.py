
import sys
import os
import json
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'integrated_system/backend'))

try:
    from virtual_reader.service import virtual_reader_service
except ImportError:
    # Handle running from inside backend dir
    sys.path.append(os.path.join(os.getcwd(), '..'))
    pass

def test_virtual_reader():
    print("--- 1. Testing Profile Generation ---")
    try:
        # Create a group of 3 readers
        group_data = virtual_reader_service.create_reader_group(count=3, category="玄幻")
        group_id = group_data['group_id']
        print(f"✅ Generated Group ID: {group_id}")
        print(f"✅ Readers count: {group_data['count']}")
        for p in group_data['profiles']:
            print(f"   - [{p['name']}] (Toxic:{p['toxicity_level']}) {p['bio']}")
            
    except Exception as e:
        print(f"❌ Profile Generation Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n--- 2. Testing Simulation ---")
    try:
        novel_title = "斗破苍穹"
        chapter_title = "第一章 陨落的天才"
        content = """
        “斗之力，三段！”
        望着测验魔石碑上面闪亮得甚至有些刺眼的五个大字，少年面无表情，唇角有着一抹自嘲，紧握的手掌，因为大力，而导致略微尖锐的指甲深深的刺进了掌心之中，带来一阵阵钻心的疼痛…
        “萧炎，斗之力，三段！级别：低级！”
        测验魔石碑之旁，一位中年男子，看了一眼碑上所显示出来的信息，语气漠然的将之公布了出来...
        """
        
        result = virtual_reader_service.simulate_reading(group_id, novel_title, chapter_title, content)
        
        print(f"✅ Simulation ID: {result.get('simulation_id')}")
        print(f"✅ Avg Score: {result.get('avg_score')}")
        print("✅ Comments:")
        for c in result.get('comments', []):
            print(f"   - {c['reader_name']} ({c['score']}分): {c['comment']}")
            
    except Exception as e:
        print(f"❌ Simulation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_virtual_reader()
