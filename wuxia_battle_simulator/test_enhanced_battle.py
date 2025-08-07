#!/usr/bin/env python3
"""
测试增强的战斗叙事功能
"""

import random
from engine.battle_simulator import BattleSimulator
from engine.ai_policy import HeuristicAI
from engine.atb_system import ATBClock
from data.data_manager import DataManager

def test_enhanced_battle_narration():
    """测试新的战斗叙事功能，包括闪避和防御事件"""
    
    # 初始化数据管理器
    data_manager = DataManager()
    data_manager.load_characters("data/characters.json")
    data_manager.load_skills("data/skills.json")
    data_manager.load_config("data/config.json")
    
    # 选择两个角色进行战斗
    characters = data_manager.characters
    if len(characters) < 2:
        print("需要至少两个角色进行测试")
        return
    
    # 构建游戏状态
    selected_chars = characters[:2]  # 选择前两个角色
    state = data_manager.build_game_state(selected_chars)
    
    # 初始化战斗组件
    rng = random.Random(42)  # 固定种子以便重现
    skills_db = data_manager.skills
    ai = HeuristicAI(rng=rng, skills_db=skills_db)
    clock = ATBClock(threshold=100, tick_scale=1.0)
    
    # 创建战斗模拟器
    simulator = BattleSimulator(state, ai, clock, rng)
    
    print("=== 增强战斗叙事测试 ===")
    print(f"参战角色: {[actor.name for actor in state.actors()]}")
    print()
    
    # 运行几个回合的战斗
    max_rounds = 5
    round_count = 0
    
    while not state.is_battle_over() and round_count < max_rounds:
        round_count += 1
        print(f"--- 第 {round_count} 回合 ---")
        
        # 执行一步战斗
        events = simulator.step()
        
        if not events:
            print("本回合无事件发生")
            continue
            
        # 显示所有事件
        for i, event in enumerate(events, 1):
            try:
                # 映射事件为叙事上下文
                ctx = simulator.map_event_for_narration(event)
                
                # 简单的叙事渲染
                actor_name = ctx.get('actor_name', '未知')
                target_name = ctx.get('target_name', '未知')
                skill_name = ctx.get('skill_name', '未知技能')
                event_type = ctx.get('event_type', '未知')
                damage = ctx.get('damage_amount', 0)
                
                if event_type == 'dodge':
                    print(f"  事件 {i}: {target_name} 使用身法闪避 {actor_name} 的攻击")
                elif event_type == 'defend':
                    print(f"  事件 {i}: {target_name} 使用防御技能抵挡攻击")
                elif event_type in ['attack', 'critical', 'miss']:
                    if event_type == 'miss':
                        print(f"  事件 {i}: {actor_name} 使用 {skill_name} 攻击 {target_name}，但被完全闪避")
                    elif event_type == 'critical':
                        print(f"  事件 {i}: {actor_name} 使用 {skill_name} 暴击 {target_name}，造成 {damage} 点伤害")
                    else:
                        print(f"  事件 {i}: {actor_name} 使用 {skill_name} 攻击 {target_name}，造成 {damage} 点伤害")
                else:
                    print(f"  事件 {i}: {event_type} - {actor_name} -> {target_name}")
                    
            except Exception as e:
                print(f"  事件 {i}: 叙事处理失败 - {e}")
        
        # 显示当前血量状态
        print("  当前状态:")
        for actor in state.actors():
            if hasattr(actor, 'hp') and hasattr(actor, 'max_hp'):
                hp_ratio = actor.hp / actor.max_hp if actor.max_hp > 0 else 0
                print(f"    {actor.name}: {actor.hp}/{actor.max_hp} HP ({hp_ratio:.1%})")
            else:
                print(f"    {actor.name}: 状态未知")
        print()
    
    # 战斗结果
    living = [actor for actor in state.actors() if hasattr(actor, 'hp') and actor.hp > 0]
    if len(living) == 1:
        print(f"战斗结束！胜者: {living[0].name}")
    elif len(living) == 0:
        print("战斗结束！双方同归于尽")
    else:
        print(f"测试结束，剩余 {len(living)} 名角色存活")

if __name__ == "__main__":
    test_enhanced_battle_narration()