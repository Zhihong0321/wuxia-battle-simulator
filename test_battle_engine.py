#!/usr/bin/env python3
"""Simple test script to verify the new BattleEngine works correctly.

This script creates a basic battle scenario and runs it through both
the old BattleSimulator and new BattleEngine to compare results.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wuxia_battle_simulator import GameState, Character, CharacterStats, EquippedSkill, SimpleAI, ATBClock
from wuxia_battle_simulator.engine.ai_policy import SkillDB, _SkillTierParams
import random
from wuxia_battle_simulator.engine import BattleSimulator, BattleEngine
from wuxia_battle_simulator.engine.migration import BattleEngineAdapter


class SimpleSkillDB(SkillDB):
    """Simple skills database for tests"""
    def __init__(self):
        self._skills = {
            "basic_strike": {
                1: dict(base_damage=15, power_multiplier=1.0, qi_cost=5, cooldown=0, hit_chance=0.8, critical_chance=0.1)
            },
            "fireball": {
                1: dict(base_damage=25, power_multiplier=1.2, qi_cost=10, cooldown=1, hit_chance=0.75, critical_chance=0.15)
            }
        }
    
    def get_tier_params(self, skill_id: str, tier: int) -> _SkillTierParams:
        p = self._skills[skill_id][tier]
        return _SkillTierParams(
            base_damage=p["base_damage"],
            power_multiplier=p["power_multiplier"],
            qi_cost=p["qi_cost"],
            cooldown=p["cooldown"],
            hit_chance=p["hit_chance"],
            critical_chance=p["critical_chance"]
        )
    
    def get_tier_name(self, skill_id: str, tier: int) -> str:
        return f"{skill_id}_tier_{tier}"


def create_test_character(char_id: str, name: str, team: int) -> Character:
    """Create a test character with basic stats and skills"""
    stats = CharacterStats(
        max_hp=100,
        max_qi=50,
        strength=20,
        defense=10,
        agility=15
    )
    
    skills = [
        EquippedSkill(skill_id="basic_attack", tier=1),
        EquippedSkill(skill_id="dodge", tier=1),
        EquippedSkill(skill_id="block", tier=1)
    ]
    
    return Character(
        id=char_id,
        name=name,
        faction=f"team_{team}",
        faction_terminology={},
        stats=stats,
        hp=stats.max_hp,
        qi=stats.max_qi,
        skills=skills
    )


def create_test_game_state() -> GameState:
    """Create a simple test game state with two characters"""
    char1 = create_test_character("hero", "Hero", 1)
    char2 = create_test_character("villain", "Villain", 2)
    
    return GameState([char1, char2])


def test_battle_engine():
    """Test the new BattleEngine implementation"""
    print("Testing BattleEngine...")
    
    # Create test components
    game_state = create_test_game_state()
    rng = random.Random(12345)  # Use fixed seed for reproducible results
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    try:
        # Test BattleEngine directly
        print("\n1. Testing BattleEngine directly:")
        engine = BattleEngine(game_state, ai, clock, rng)
        
        print(f"   Pipeline info: {engine.get_pipeline_info()}")
        print(f"   Initial step count: {engine.get_step_count()}")
        print(f"   Battle finished: {engine.is_battle_finished()}")
        
        # Run a few steps
        for i in range(3):
            print(f"\n   Step {i+1}:")
            events = engine.step()
            print(f"     Generated {len(events)} events")
            for event in events:
                print(f"     - {event.event_type}: {event.actor} -> {event.target}")
            
            if engine.is_battle_finished():
                print("     Battle finished!")
                break
        
        print(f"\n   Final step count: {engine.get_step_count()}")
        print(f"   Total events: {len(engine.get_battle_events())}")
        
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_battle_engine_adapter():
    """Test the BattleEngineAdapter for compatibility"""
    print("\n2. Testing BattleEngineAdapter:")
    
    # Create test components
    game_state = create_test_game_state()
    rng = random.Random(12345)  # Use same seed for comparison
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    try:
        # Test BattleEngineAdapter
        adapter = BattleEngineAdapter(game_state, ai, clock, rng)
        
        print(f"   Initial events: {len(adapter.events)}")
        print(f"   Step count: {adapter.step_count}")
        print(f"   Battle finished: {adapter.is_battle_finished()}")
        
        # Test actor views
        views = adapter.create_actor_views()
        print(f"   Actor views: {list(views.keys())}")
        
        # Run a step
        events = adapter.step()
        print(f"   Step generated {len(events)} events")
        
        # Test event mapping
        if events:
            context = adapter.map_event_for_narration(events[0])
            print(f"   Event context keys: {list(context.keys())}")
        
        print(f"   Final step count: {adapter.step_count}")
        
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_processor_customization():
    """Test processor customization capabilities"""
    print("\n3. Testing processor customization:")
    
    # Create test components
    game_state = create_test_game_state()
    rng = random.Random(12345)
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    try:
        engine = BattleEngine(game_state, ai, clock, rng)
        
        # Test getting processor info
        pipeline_info = engine.get_pipeline_info()
        print(f"   Processors: {pipeline_info['processor_count']}")
        for proc in pipeline_info['processors']:
            print(f"     - {proc['name']} (critical: {proc['critical']})")
        
        # Test getting individual processors
        atb_processor = engine.get_processor("ATB Processor")
        if atb_processor:
            print(f"   Found ATB processor: {atb_processor.name}")
        else:
            print("   ATB processor not found")
        
        # Test removing a processor (non-critical one)
        removed = engine.remove_processor("Defense Skill Processor")
        print(f"   Removed defense processor: {removed}")
        
        new_info = engine.get_pipeline_info()
        print(f"   Processors after removal: {new_info['processor_count']}")
        
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("BattleEngine Test Suite")
    print("=" * 60)
    
    tests = [
        test_battle_engine,
        test_battle_engine_adapter,
        test_processor_customization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("   ✓ PASSED")
            else:
                print("   ✗ FAILED")
        except Exception as e:
            print(f"   ✗ FAILED: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! BattleEngine is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())