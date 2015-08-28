# seeker
Tool to measure IOPS on a device using non-destructive read test. 

Run a test on a device: 
```
# ./seeker.py --device /dev/sda 
Syncing and dropping disc cache... done.
Random seek-time test. Device=/dev/sda, block size=4096
  Device size is 228936 MB
  Total seeks: 187490
  Seeks per second: 6249.65
  Total bytes read: 767959040 (732 MB)   <- this should be much smaller than device size 
  Total time: 30.000

  Some seek-times[ms]: 0.22 0.12 0.39 0.28 0.14 0.25 0.38 (...) TAIL: 0.17 0.17 0.18 0.11 0.18 0.11 0.18
  Average from parts: 0.160 [ms]
  Minimal / maximal: 0.0029 / 6.1290 [ms]
  
# ./seeker.py --device /dev/sdb
Syncing and dropping disc cache... done.
Random seek-time test. Device=/dev/sdb, block size=4096
  Device size is 244198 MB
  Total seeks: 161176
  Seeks per second: 5372.53  <- a bit slower, still way faster than any HDDs.
  Total bytes read: 660176896 (629 MB)
  Total time: 30.000

  Some seek-times[ms]: 1.59 0.14 0.13 0.23 0.22 0.22 0.22 (...) TAIL: 0.14 0.24 0.22 0.14 0.23 0.24 0.24
  Average from parts: 0.186 [ms]
  Minimal / maximal: 0.0029 / 4.9670 [ms]


sda - 256GB SSD Drive
sdb - m2 slot SSD drive
```

You should be root to be able to drop filesystem caches via sysctl and 
testing device should be much smaller than data read during the test
- otherwise caching kicks in and you're measuring something completely 
different.

It's best to use the same sized file on each tested medium if their sizes 
differ - biggest possible.
