#!/usr/bin/python
import string, re, random

def allow_range_of_thread_counts(output):
    normalized_lines = []
    parallel = False
    for line in output.split('\n'):
        match = re.match(r'Number of requests: (\d+)', line)
        if match:
            num_requests = int(match.group(1))
            if num_requests in [14, 15, 16, 17, 18]:
                line = 'Number of parallel requests: 16 (+/- 2)'
                parallel = True
        match = re.match(r'Waiting requests released: (\d+)', line)
        if match:
            num_released = int(match.group(1))
            if parallel and num_released in [12, 13, 14, 15, 16]:
                line = 'All requests have been released.'
        normalized_lines.append(line)
    return '\n'.join(normalized_lines)

def allow_any_myth_ip_address(output):
    return re.sub(r'171\.64\.15\.\d{1,3}', '171.64.15.xyz', output)
