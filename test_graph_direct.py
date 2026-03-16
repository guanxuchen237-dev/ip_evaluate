#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'd:\ip-lumina-main\integrated_system\backend')

print("Testing graph_generator module...")

from virtual_reader.graph_generator import graph_generator

print(f"graph_generator instance: {graph_generator}")
print(f"graph_generator.ai_service: {graph_generator.ai_service}")

if graph_generator.ai_service:
    print(f"models: {graph_generator.ai_service.models}")
    print(f"provider: {graph_generator.ai_service.provider}")
    print(f"base_url: {graph_generator.ai_service.base_url}")
    
    # Test generate
    print("\nGenerating graph for test...")
    result = graph_generator.generate_graph("test", "test book abstract")
    print(f"Result nodes count: {len(result.get('nodes', []))}")
    print(f"Result: {result}")
