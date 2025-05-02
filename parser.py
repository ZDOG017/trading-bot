import re

def parse_signal(message):
    try:
        if "Entry price" not in message:
            return None

        # Check for explicit Short/Long signal in the first line
        first_line = message.split('\n')[0].lower()
        direction = "short" if "short" in first_line else "long"
        
        pair = re.search(r"#(\w+)", message).group(1)
        entry_range = re.findall(r"Entry price\s*:\s*([\d.]+)\s*-\s*([\d.]+)", message)[0]
        targets = [float(t) for t in re.findall(r"Target: ([\d.]+)", message)]
        stop_loss = float(re.search(r"Stop-Loss\s*:\s*([\d.]+)", message).group(1))

        return {
            "direction": direction,
            "pair": pair,
            "entry_range": [float(entry_range[0]), float(entry_range[1])],
            "targets": targets,
            "stop_loss": stop_loss
        }
    except Exception as e:
        print("Parse failed:", e)
        return None
