import re

with open('/Users/vinayak/.gemini/antigravity/brain/7ed6e800-bd1d-4154-b465-1bca8e4ed818/technical_report.md', 'r') as f:
    content = f.read()

images = ['diagrams/architecture.png', 'diagrams/two_brain.png', 'diagrams/thesis_agent.png']
captions = ['Figure 1: System Architecture', 'Figure 2: Two-Brain AI Pipeline', 'Figure 3: Thesis Agent 4-Stage Flow']

pattern = r'```mermaid\n.*?```'
matches = list(re.finditer(pattern, content, re.DOTALL))
print(f'Found {len(matches)} mermaid blocks')

# Replace in reverse order to preserve positions
for i in range(len(matches) - 1, -1, -1):
    m = matches[i]
    replacement = f'![{captions[i]}]({images[i]})'
    content = content[:m.start()] + replacement + content[m.end():]

with open('/Users/vinayak/Documents/Antigravity/Project 1/technical_report_pdf.md', 'w') as f:
    f.write(content)

print('Done - PDF-ready markdown written')
