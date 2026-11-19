import hashlib
import subprocess


def ping(host):
    return subprocess.run("ping -c 1 " + host, shell=True, capture_output=True, text=True).stdout


def run_expression(text):
    return eval(text)


def fingerprint(data):
    return hashlib.md5(data.encode()).hexdigest()
