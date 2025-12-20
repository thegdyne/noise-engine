"""
Tests for critical project files that must exist.
"""
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent


class TestCriticalFiles:
    """Ensure critical project files exist."""
    
    def test_docs_index_exists(self):
        """Landing page must exist for GitHub Pages."""
        index = PROJECT_ROOT / "docs" / "index.html"
        assert index.exists(), "docs/index.html missing - GitHub Pages will break!"
    
    def test_readme_exists(self):
        """README must exist."""
        readme = PROJECT_ROOT / "README.md"
        assert readme.exists(), "README.md missing"
    
    def test_presets_module_exists(self):
        """Presets module must exist."""
        init = PROJECT_ROOT / "src" / "presets" / "__init__.py"
        assert init.exists(), "src/presets/__init__.py missing"
