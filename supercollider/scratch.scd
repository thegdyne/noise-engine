# === SUPERCOLLIDER ===
# In SuperCollider IDE:
# 1. Clean slate
s.freeAll;

# 2. Reload everything (Cmd+A, Cmd+Return on init.scd)

# 3. Check node tree
s.queryAllNodes;

# Expected structure:
# NODE TREE Group 0
#    1 group
#       clockGroup
#          masterClock
#       genGroup
#          (generators here)
#       fxGroup
#          masterPassthrough
