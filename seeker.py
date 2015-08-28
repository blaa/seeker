#!/usr/bin/env python
# (C) 2013-2015 by Tomasz bla Fortuna
# License: MIT

import os
import sys

from random import random
from time import time

def get_size(fd):
    "Get device size"
    cur_pos = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_END)
    size = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, cur_pos, os.SEEK_SET)
    return size

def drop_caches():
    print "Syncing and dropping disc cache...",
    os.system("sync")
    os.system("sysctl vm.drop_caches=3 > /dev/null")
    print "done."


def sequential_test(device, block_size, time_limit=30):
    "Sequential test, less interesting - use hdparm -tT probably better"
    print "Sequential read test. Device=%s, block size=%d" % (device, block_size)
    dev = os.open(device, os.O_RDONLY)
    size = get_size(dev)
    size -= block_size

    # List of times it took to perform X seeks
    parts = []
    count = 0
    bytes = 0
    time_start = time()
    time_prev = time_start

    try:
        while True:
            data = os.read(dev, block_size)
            bytes += len(data)

            count += 1
            time_cur = time()
            parts.append((time_cur - time_prev) * 1000)
            if time_cur - time_start > time_limit or bytes > size:
                break
            time_prev = time_cur
    except KeyboardInterrupt:
        print "Interrupted"
        pass
    except:
        print "Exception caught, closing device"
        print
        raise
    finally:
        os.close(dev)

    time_total = time_cur - time_start
    bytes_read = count * block_size
    print "  Total blocks read:", count
    print "  Total bytes read: %d (%d MB)" % (bytes_read,
                                              bytes_read / 1024 / 1024)
    print "  Blocks per second: %.2f" % (count / time_total)
    print "  Bytes per second: %.2f kB" % (bytes_read / time_total / 1024)
    print "  Total time: %.3f" % time_total
    print
    parts_formatted = ["%.2f" % t for t in parts]
    print "  Some block read-times[ms]:", " ".join(parts_formatted[:7]), "(...) TAIL:", " ".join(parts_formatted[-7:])
    print "  Average from parts: %.3f [ms]" % (sum(parts) / len(parts))
    print "  Minimal / maximal: %.4f / %.4f [ms]" % (min(parts), max(parts))




def random_test(device, block_size, time_limit=30):
    "Perform random seek test"
    print "Random seek-time test. Device=%s, block size=%d" % (device, block_size)
    dev = os.open(device, os.O_RDONLY)

    size = get_size(dev)
    print "  Device size is", size / 1024 / 1024, "MB"
    size -= block_size

    # List of times it took to perform X seeks
    parts = []
    count = 0
    time_start = time()
    time_prev = time_start

    try:
        while True:
            pos = int(random() * size)
            os.lseek(dev, pos, os.SEEK_SET)
            data = os.read(dev, block_size)

            count += 1
            time_cur = time()
            parts.append((time_cur - time_prev) * 1000)
            if time_cur - time_start > time_limit:
                break
            time_prev = time_cur
    except KeyboardInterrupt:
        print "Interrupted"
        pass
    except:
        print "Exception caught, closing device"
        print
        raise
    finally:
        os.close(dev)

    time_total = time_cur - time_start
    bytes_read = count * block_size
    print "  Total seeks:", count
    print "  Seeks per second: %.2f" % (count / time_total)
    print "  Total bytes read: %d (%d MB)" % (bytes_read,
                                              bytes_read / 1024 / 1024)
    print "  Total time: %.3f" % time_total
    print
    parts_formatted = ["%.2f" % t for t in parts]
    print "  Some seek-times[ms]:", " ".join(parts_formatted[:7]), "(...) TAIL:", " ".join(parts_formatted[-7:])
    print "  Average from parts: %.3f [ms]" % (sum(parts) / len(parts))
    print "  Minimal / maximal: %.4f / %.4f [ms]" % (min(parts), max(parts))


def main():
    "Handle args and execute tests"
    import argparse

    parser = argparse.ArgumentParser(description='Measure disc performance')
    parser.add_argument('--device', metavar='DEVICE', type=str, action="store", required=True,
                        help='device to test')
    parser.add_argument('--limit', metavar='seconds', type=int, action="store", default=30,
                        help='time to spend on tests in seconds')
    parser.add_argument('--blocksize', metavar='bytes', type=int, action="store", default=4096,
                        help='blocksize to use during tests')
    parser.add_argument('--sequential', action="store_true", 
                        help='instead of random IOPS do sequential test')
    args = parser.parse_args()

    assert args.blocksize > 1
    assert args.limit > 0.1

    drop_caches()
    if args.sequential is True:
        sequential_test(args.device, args.blocksize, args.limit)
    else:
        random_test(args.device, args.blocksize, args.limit)
    print


if __name__ == "__main__":
    main()
