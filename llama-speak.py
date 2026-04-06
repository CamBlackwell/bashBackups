#!/usr/bin/env python3
import os, sys, pty, select, termios, tty, subprocess, threading, re

model = sys.argv[1]
voice = sys.argv[2]

def clean(text):
    # Strip ANSI escape codes
    text = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)
    text = re.sub(r'\x1b\[.*?[a-zA-Z]', '', text)
    return text.strip()

def speak(text):
    text = clean(text)
    if not text:
        return
    # Skip noise
    skip = ['>', '[', 'build', 'model :', 'llama', 'ggml', 'Log',
            'available', 'load', '██', '▄', 'system', 'Prompt:',
            'Generation:', 'modalities', '/exit', '/regen', '/clear', '/read']
    for s in skip:
        if text.startswith(s) or s in text[:20]:
            return
    proc = subprocess.run(
        ['piper', '--model', voice, '--output_raw'],
        input=text.encode(),
        capture_output=True
    )
    subprocess.run(
        ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-'],
        input=proc.stdout,
        capture_output=True
    )

# Create PTY
master_fd, slave_fd = pty.openpty()

proc = subprocess.Popen(
    [os.path.expanduser('~/llama.cpp/build/bin/llama-cli'),
     '-m', model, '--gpu-layers', '20', '--conversation'],
    stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
    close_fds=True
)

os.close(slave_fd)

# Save terminal state
old_settings = termios.tcgetattr(sys.stdin)
tty.setraw(sys.stdin.fileno())

buffer = ""
started = False

try:
    while proc.poll() is None:
        r, _, _ = select.select([master_fd, sys.stdin], [], [], 0.1)

        if sys.stdin.fileno() in r:
            data = os.read(sys.stdin.fileno(), 1024)
            os.write(master_fd, data)

        if master_fd in r:
            try:
                data = os.read(master_fd, 1024).decode('utf-8', errors='replace')
                # Write to terminal as normal
                sys.stdout.write(data)
                sys.stdout.flush()
                # Buffer for speaking
                buffer += data
                # Speak when we hit a sentence end
                if any(c in buffer for c in ['.', '!', '?', '\n']):
                    lines = re.split(r'(?<=[.!?\n])', buffer)
                    for line in lines[:-1]:
                        if '>' in buffer:
                            started = True
                        if started:
                            threading.Thread(target=speak, args=(line,), daemon=True).start()
                    buffer = lines[-1]
            except OSError:
                break
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

proc.wait()
