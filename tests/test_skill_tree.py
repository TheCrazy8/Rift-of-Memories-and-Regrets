"""Test module for skill tree functionality."""
import unittest
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestSkillTree(unittest.TestCase):
    """Test skill tree data structures, persistence, and game integration."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).parent.parent
        cls.game_file_path = cls.project_root / "Rift of Memories and Regrets.py"

    def test_game_imports_json(self):
        """Test that the game file imports json for skill tree persistence."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('import json', content,
                         "Game should import json for skill tree save/load")

    def test_game_has_skill_tree_nodes(self):
        """Test that the game defines SKILL_TREE_NODES."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('SKILL_TREE_NODES', content,
                         "Game should define SKILL_TREE_NODES")

    def test_game_has_skill_tree_methods(self):
        """Test that the game has all required skill tree methods."""
        required_methods = [
            '_load_skill_tree',
            '_save_skill_tree',
            '_award_skill_points',
            '_get_unlocked_collectable_indices',
            '_get_max_lives',
            '_get_powerup_spawn_multiplier',
            '_get_speed_bonus',
            '_get_graze_multiplier',
            'show_skill_tree',
            '_purchase_skill',
        ]
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for method in required_methods:
                with self.subTest(method=method):
                    self.assertIn(f'def {method}', content,
                                 f"Game should have {method} method")

    def test_skill_tree_has_collectible_tiers(self):
        """Test that skill tree has collectible tier unlock nodes."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tier_nodes = ['collect_tier_2', 'collect_tier_3_4', 'collect_tier_5_6',
                         'collect_tier_7_8', 'collect_tier_9_10']
            for node in tier_nodes:
                with self.subTest(node=node):
                    self.assertIn(node, content,
                                 f"Skill tree should have {node} node")

    def test_skill_tree_has_upgrade_nodes(self):
        """Test that skill tree has upgrade nodes."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            upgrade_nodes = ['extra_heart_1', 'extra_heart_2', 'better_powerups',
                           'speed_boost', 'graze_mastery']
            for node in upgrade_nodes:
                with self.subTest(node=node):
                    self.assertIn(node, content,
                                 f"Skill tree should have {node} node")

    def test_skill_tree_tier_map_exists(self):
        """Test that SKILL_TIER_MAP is defined for collectible gating."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('SKILL_TIER_MAP', content,
                         "Game should define SKILL_TIER_MAP")

    def test_save_path_uses_user_data_directory(self):
        """Test that save path uses platform-appropriate user data directory, not game directory."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('APPDATA', content,
                         "Save path should reference APPDATA for Windows")
            self.assertIn('XDG_DATA_HOME', content,
                         "Save path should reference XDG_DATA_HOME for Linux")

    def test_game_over_navigation_options(self):
        """Test that game over screen has menu and skill tree navigation."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('_game_over_to_menu', content,
                         "Game should have _game_over_to_menu method")
            self.assertIn('_game_over_to_skill_tree', content,
                         "Game should have _game_over_to_skill_tree method")

    def test_sp_awarded_at_game_end(self):
        """Test that skill points are awarded when game ends."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('_award_skill_points', content,
                         "Game should call _award_skill_points")

    def test_lives_use_skill_tree(self):
        """Test that lives initialization uses skill tree max lives."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('self._get_max_lives()', content,
                         "Lives should be set from _get_max_lives()")

    def test_main_menu_has_skill_tree_button(self):
        """Test that main menu has a skill tree button."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('SKILL TREE', content,
                         "Main menu should have SKILL TREE button text")
            self.assertIn('show_skill_tree', content,
                         "Main menu should bind to show_skill_tree")

    def test_focus_bar_exists(self):
        """Test that focus charge bar drawing method exists."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('def _draw_focus_bar', content,
                         "Game should have _draw_focus_bar method")

    def test_focus_not_blocked_by_cooldown(self):
        """Test that focus activation is not blocked by pulse cooldown."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # The old buggy pattern: checking cooldown before activating focus
            # Should NOT exist anymore
            lines = content.split('\n')
            in_focus_pressed = False
            for i, line in enumerate(lines):
                if 'def _focus_key_pressed' in line:
                    in_focus_pressed = True
                    continue
                if in_focus_pressed:
                    if line.strip().startswith('def '):
                        break
                    # Should not have cooldown check that returns
                    if 'focus_pulse_cooldown' in line and 'return' in line:
                        self.fail("_focus_key_pressed should not block on cooldown")

    def test_powerups_use_ovals_not_polygons(self):
        """Test that freeze/rewind/shield powerup spawns use create_oval."""
        with open(self.game_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check spawn functions use create_oval
            for method_name in ['spawn_freeze_powerup', 'spawn_rewind_powerup', 'spawn_shield_powerup']:
                # Find the method and check it uses create_oval
                idx = content.find(f'def {method_name}')
                self.assertNotEqual(idx, -1, f"Should have {method_name}")
                # Get the method body (until next def)
                next_def = content.find('\n    def ', idx + 1)
                method_body = content[idx:next_def] if next_def != -1 else content[idx:]
                self.assertIn('create_oval', method_body,
                             f"{method_name} should use create_oval for reliable movement")


if __name__ == '__main__':
    unittest.main()
