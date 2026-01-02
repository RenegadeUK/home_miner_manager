#!/usr/bin/env python3
"""
Quick script to fix the remaining DGB block reward values
"""

file_path = "app/api/dashboard.py"

with open(file_path, 'r') as f:
    content = f.read()

# Replace the old value with the new value
old_value = "earned_24h_dgb = blocks_24h * 665"
new_value = "earned_24h_dgb = blocks_24h * 277.376"

old_comment = "# DGB block reward: ~665 DGB (DigiShield adjusted, approximate)"
new_comment = "# DGB block reward: 277.376 DGB (current as of January 2025, post-halving)"

content = content.replace(old_comment, new_comment)
content = content.replace(old_value, new_value)

with open(file_path, 'w') as f:
    f.write(content)

print("✅ Fixed DGB block reward values in dashboard.py")
print(f"   Changed: {old_value}")
print(f"   To:      {new_value}")
