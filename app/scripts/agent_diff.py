import json
import sys
from deepdiff import DeepDiff

if len(sys.argv) != 3:
    print("Usage: python agent_diff.py before.json after.json")
    sys.exit(1)

with open(sys.argv[1]) as f:
    before = json.load(f)

with open(sys.argv[2]) as f:
    after = json.load(f)

diff = DeepDiff(before, after, ignore_order=True)

print(json.dumps(diff, indent=2))
