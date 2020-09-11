import brukerbridge as bridge
import sys

sys.stdout = bridge.Logger_stdout()
sys.stderr = bridge.Logger_stderr()

print('hey!')