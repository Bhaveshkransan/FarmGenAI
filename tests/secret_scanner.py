import os, re

files_to_scan = [
    'docker-compose.yml', 
    'Dockerfile', 
    'backend/core/config.py', 
    '.env.example',
    'backend/core/security.py',
    'backend/main.py'
]

pattern = re.compile(r'(?i)(api[_-]?key|secret|password|private_key)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?')
findings = []

for fpath in files_to_scan:
    if os.path.exists(fpath):
        with open(fpath, 'r', errors='ignore') as f:
            for idx, line in enumerate(f, 1):
                m = pattern.search(line)
                if m:
                    val = m.group(2).lower()
                    if not any(k in val for k in ['placeholder', 'example', 'changeme', 'postgres', 'default', 'localhost', '${', 'os.getenv', 'getenv']):
                        findings.append((fpath, idx, line.strip()[:80]))

print(f"Total potential secrets flagged: {len(findings)}")
for item in findings:
    print(item)
