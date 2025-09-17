import os
import re

# Find all Python files in workflows/nodes/
for root, dirs, files in os.walk('workflows/nodes/'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Replace self.node_type = "UPPERCASE" with lowercase
            original = content
            content = re.sub(r'self\.node_type = "([A-Z_]+)"', 
                           lambda m: f'self.node_type = "{m.group(1).lower()}"', 
                           content)
            
            if content != original:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Updated: {filepath}")

print("Done!")
