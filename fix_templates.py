#!/usr/bin/env python
"""Fix template headers with proper line breaks"""

import os

analytics_path = "dashboard/templates/dashboard/analytics.html"
map_path = "dashboard/templates/dashboard/map.html"
index_path = "dashboard/templates/dashboard/index.html"

# Read and extract content after line 2
with open(analytics_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    analytics_body = ''.join(lines[2:]) if len(lines) > 2 else ""

with open(map_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    map_body = ''.join(lines[2:]) if len(lines) > 2 else ""

with open(index_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    index_body = ''.join(lines[2:]) if len(lines) > 2 else ""

# Write corrected files with proper headers
analytics_header = "{% extends 'dashboard/base.html' %}\n{% load static %}\n{% load math_filters %}\n\n{% block title %}Analytics - Oil Spill Detection{% endblock %}\n\n{% block content %}\n"
with open(analytics_path, 'w', encoding='utf-8') as f:
    f.write(analytics_header + analytics_body)

map_header = "{% extends 'dashboard/base.html' %}\n{% load static %}\n{% load math_filters %}\n\n{% block title %}Map View - Oil Spill Detection{% endblock %}\n\n{% block content %}\n"
with open(map_path, 'w', encoding='utf-8') as f:
    f.write(map_header + map_body)

index_header = "{% extends 'dashboard/base.html' %}\n{% load static %}\n\n{% block title %}Dashboard - Oil Spill Detection{% endblock %}\n\n{% block content %}\n"
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(index_header + index_body)

print("✅ All template files fixed successfully!")
print("✓ analytics.html header corrected")
print("✓ map.html header corrected")
print("✓ index.html header corrected")
