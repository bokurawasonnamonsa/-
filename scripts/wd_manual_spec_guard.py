#!/usr/bin/env python3
"""後方互換: operator_spec_guard を呼ぶ。"""
from operator_spec_guard import run_operator_spec_guard as run_wd_spec_guard  # noqa: F401

__all__ = ["run_wd_spec_guard"]