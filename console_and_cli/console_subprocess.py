import subprocess
import sys


def run_cmd_with_feedback(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if not output and process.poll() is not None:
            break
        if output:
            sys.stdout.write(str(output.strip(), "utf-8"))
            sys.stdout.write("\n")
    return_code = process.poll()
    return return_code
