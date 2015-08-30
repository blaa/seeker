#!/usr/bin/env python
# (C) 2013-2015 by Tomasz bla Fortuna
# License: MIT

from __future__ import print_function

import os
import sys

from random import random
from time import time, sleep
from datetime import datetime
import socket
import signal
import multiprocessing as mp

def humanize(bytes):
    if bytes > 1024*1024:
        unit = 'MB'
        total = bytes / 1024.0 / 1024.0
    elif bytes > 1024:
        total = bytes / 1024.0
        unit = 'kB'
    else:
        total = bytes
        unit = 'B'

    return total, unit

def report_part(data, cfg, full=True):
    "Print a part of a report"
    data = data[1]
    # Total bytes unit
    total, unit = humanize(data['bytes_read'])

    if cfg['sequential']:
        s = "Blocks read: "
    else:
        s = "Seeks:       "
    print("   {} {} ({:.1f} /s)".format(s, data['count'],
                                        data['count'] / data['time_total']))
    print("   Bytes read:   {:.3f} {} ({:.1f} {}/s)".format(total,
                                                             unit,
                                                             total / data['time_total'],
                                                             unit))
    #print("   Total time:   %.3f" % data['time_total'])

    if full:
        print()
        parts_formatted = ["%.2f" % t for t in data['parts']]
        print("   Some seek-times[ms]:", " ".join(parts_formatted[:7]), "(...) TAIL:", " ".join(parts_formatted[-7:]))
        print("   Average from parts: %.3f [ms]" % (sum(data['parts']) / len(data['parts'])))
        print("   Minimal / maximal: %.4f / %.4f [ms]" % (min(data['parts']), max(data['parts'])))


def report(results, cfg):
    exp_type = 'Sequential read' if cfg['sequential'] else 'Random-seek'
    when = cfg['start'].strftime('%Y-%m-%d %H:%M:%S')
    where = socket.gethostname()
    size = cfg['size'] / 1024./1024.

    print("============ RESULTS =============")
    print("{} test at {} on {}".format(exp_type, where, when))
    print("device={device} ({size_mb:.1f}MB) blocksize={blocksize} concurrency={concurrency} time_limit={limit}".format(size_mb=size, **cfg))

    # Create grouped results
    grouped = {}
    for key in ['count', 'bytes_read', 'time_total']:
        grouped[key] = [r[1][key] for r in results
                        if r[0] == 'RESULT']

    # Calculate major values
    total_bytes_read = sum(grouped['bytes_read'])
    total_bytes_read_human, total_bytes_unit = humanize(total_bytes_read)
    total_seeks = sum(grouped['count'])
    total_workers = len(grouped)
    total_time = sum(grouped['time_total'])
    avg_time = total_time / total_workers

    if total_bytes_read >= 0.1 * cfg['size']:
        print("-> WARNING: Read over 10% of device size - caching will impact the results")

    # Grouped data
    print("=== Totals")
    print("IOPS: {:.2f} (avg={:.2f})".format(total_seeks / avg_time,
                                              total_seeks / total_workers / avg_time))
    print("{:2}/s: {:.2f} (avg={:.2f})".format(total_bytes_unit,
                                     total_bytes_read_human,
                                     total_bytes_read_human / total_workers))



    # Detailed per process reports
    for i, result in enumerate(results):
        print()
        print("== Worker %d" % i)
        report_part(results[i], cfg,
                    full=True)





class Worker(mp.Process):

    def __init__(self, cfg):

        self.cfg = cfg

        self.size = cfg['size'] - cfg['blocksize']

        self.interrupt = mp.Event()
        self.queue = mp.Queue(maxsize=1)

        super(Worker, self).__init__()

    def run(self):
        ""
        super(Worker, self).run()

        # Handle interrupts in parent
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        cfg = self.cfg
        try:
            data = self.wrk_test(cfg['device'],
                                 cfg['blocksize'],
                                 cfg['limit'],
                                 do_random=not cfg['sequential'])

        except Exception, e:
            import traceback as tb
            print("EXCEPTION ON THREAD", self.name)
            tb.print_exc()
            self.queue.put(('EXC', e.message))
            self.queue.close()
            return

        self.queue.put(('RESULT', data))
        self.queue.close()


    def wrk_test(self, device, block_size, time_limit=30, do_random=False):
        "Runs on worker: Perform random seek test"
        #print "Random seek-time test. Device=%s, block size=%d" % (device, block_size)
        dev = os.open(device, os.O_RDONLY)

        # List of times it took to perform X seeks
        parts = []
        count = 0
        bytes_read = 0
        time_start = time()
        time_prev = time_start

        try:
            while True:
                if do_random is True:
                    pos = int(random() * self.size)
                    os.lseek(dev, pos, os.SEEK_SET)
                data = os.read(dev, block_size)
                bytes_read += len(data)

                count += 1
                time_cur = time()
                if count % 1000 == 0:
                    parts.append((time_cur - time_prev) * 1000)
                    if self.interrupt.is_set():
                        break
                if time_cur - time_start > time_limit:
                    break
                time_prev = time_cur
        finally:
            os.close(dev)

        time_total = time_cur - time_start
        bytes_read = count * block_size

        data = {
            'parts': parts,
            'count': count,
            'bytes_read': bytes_read,
            'time_total': time_total,
        }
        return data


def parse_args():
    "Handle args and execute tests"
    import argparse

    parser = argparse.ArgumentParser(description='Measure disc performance')
    parser.add_argument('--device', metavar='DEVICE', type=str, action="store", required=True,
                        help='device to test')
    parser.add_argument('--limit', metavar='seconds', type=int, action="store", default=30,
                        help='time to spend on tests in seconds')
    parser.add_argument('--blocksize', metavar='bytes', type=int, action="store", default=None,
                        help='blocksize to use during tests (default - 4k for random, 1M for sequential)')
    parser.add_argument('-c', '--concurrency', metavar='processes', type=int, action="store", default=1,
                        help='number of parallel processes/disc queue depth')
    parser.add_argument('--sequential', action="store_true",
                        help='instead of random IOPS do sequential test')
    args = parser.parse_args()

    assert args.limit > 0.1

    return args


def main():
    "Handle arguments, run tests, gather results and show report"

    def get_size(device):
        "Get a device size"
        try:
            fd = os.open(device, os.O_RDONLY)

            cur_pos = os.lseek(fd, 0, os.SEEK_CUR)
            os.lseek(fd, 0, os.SEEK_END)
            size = os.lseek(fd, 0, os.SEEK_CUR)
            os.lseek(fd, cur_pos, os.SEEK_SET)
        finally:
            os.close(fd)

        return size

    def drop_caches():
        "Drop system caches before the test"
        if os.getuid() == 0:
            print("-> Syncing and dropping disc cache...", end=' ', file=sys.stderr)
            os.system("sync")
            os.system("sysctl vm.drop_caches=3 > /dev/null")
            print("done.", file=sys.stderr)
        else:
            print("-> WARNING: Program is not running as root - unable to drop caches", file=sys.stderr)
            os.system("sync")

    args = parse_args()

    size = get_size(args.device)

    cfg = {
        'sequential': args.sequential,
        'size': size,
        'device': args.device,
        'blocksize': args.blocksize,
        'limit': args.limit,
        'start': datetime.now(),
        'concurrency': args.concurrency,
    }

    if cfg['blocksize'] is None:
        cfg['blocksize'] = 1024 * 1024 if cfg['sequential'] else 4096

    workers = []
    for i in range(args.concurrency):
        workers.append(Worker(cfg))

    drop_caches()

    for worker in workers:
        worker.start()
    print("-> Measurements started - waiting for results", file=sys.stderr)

    try:
        results = [
            worker.queue.get()
            for worker in workers
        ]

        report(results, cfg)
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        print("-> Interrupting workers", file=sys.stderr)
        for worker in workers:
            worker.interrupt.set()
        sleep(0.1)
        for worker in workers:
            worker.queue.get(block=False)
    finally:
        for worker in workers:
            worker.queue.close()
            worker.join()


if __name__ == "__main__":
    main()
